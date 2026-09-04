"""Azure resource resolver for ``cu analyzer copy`` (and future cross-resource commands).

Turns a user-supplied ``--from`` / ``--to`` selector (a Foundry endpoint URL, a
Cognitive Services account name, or a full ARM ID) into a canonical
:class:`ResolvedResource` — the tuple of ARM ID, region, and CU endpoint that
the data-plane copy orchestration needs.

Resolution rules:

* URL → parse hostname → discover the matching Microsoft.CognitiveServices
  account in the explicitly selected or active Azure CLI subscription.
* Name → search Microsoft.CognitiveServices/accounts in that one subscription;
  an optional ``resource_group`` argument narrows the search further.
* ARM ID → parse the ``/subscriptions/.../accounts/<name>`` shape and verify
  the account exists via management-plane ``get``.
* Zero matches → raise :class:`CuCliError` with a hint requesting more scope.
* Multiple matches → raise :class:`CuCliError` listing candidates; **never
  guess.**
* Validate CU support — only ``AIServices`` (Foundry) or ``ContentUnderstanding``
  kinds pass through. Non-CU accounts fail with a clear ``metadata mismatch``
  error.
* Use the signed-in Azure identity (:class:`DefaultAzureCredential`); do **not**
  retrieve account keys.

Nothing in this module reads or writes CU profiles.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import TYPE_CHECKING, List, Optional
from urllib.parse import urlparse

from ..errors import CuCliError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from azure.core.credentials import TokenCredential


# ARM ID pattern (case-insensitive, but Azure canonicalizes to lowercase
# provider names; we parse loosely).
_ARM_ID_PREFIX = "/subscriptions/"

# Kinds that expose Content Understanding data plane. As of 2026-08-24 CU is
# accessed via AIServices (Foundry) accounts; ContentUnderstanding is the
# legacy kind name still present in some resources.
_CU_KINDS = frozenset({"aiservices", "contentunderstanding"})


@dataclass(frozen=True)
class ResolvedResource:
    """Canonical (ARM ID, region, endpoint) tuple for a CU-capable account.

    :param arm_id: Full canonical ARM ID
        (``/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<name>``).
    :param region: Azure region short name (for example ``eastus``).
    :param endpoint: CU / Foundry service endpoint
        (typically ``https://<name>.services.ai.azure.com/`` or a regional
        ``services.azure.com`` variant returned by ARM).
    :param subscription_id: Subscription containing the account (parsed from
        ``arm_id`` for convenience).
    :param resource_group: Resource group containing the account.
    :param account_name: Bare account name.
    """

    arm_id: str
    region: str
    endpoint: str
    subscription_id: str
    resource_group: str
    account_name: str

    def display(self) -> str:
        """Short human-readable label suitable for progress lines and ``--info``."""
        return f"{self.account_name} ({self.region}, sub {self.subscription_id[:8]}…)"


# --- Selector classification -------------------------------------------------


def classify_selector(selector: str) -> str:
    """Classify a raw ``--from`` / ``--to`` value.

    Returns one of ``"arm-id"``, ``"url"``, ``"name"``. This is a cheap
    string-level classifier — it never touches the network.
    """
    s = selector.strip()
    if not s:
        raise CuCliError("empty resource selector.", hint="pass a Foundry endpoint URL, "
                         "an account name, or a full ARM ID.")
    normalized = s.lower()
    if normalized.startswith(_ARM_ID_PREFIX):
        return "arm-id"
    if normalized.startswith(("http://", "https://")):
        return "url"
    if "/" in s or " " in s:
        # Ambiguous: not a URL scheme, not an ARM ID, but contains chars that
        # aren't legal in a CS account name. Fail fast rather than treating as
        # a name and confusing the downstream discovery message.
        raise CuCliError(
            f"cannot classify resource selector '{s}'.",
            hint="pass a Foundry endpoint URL (https://<host>/), a bare Cognitive "
                 "Services account name, or a full /subscriptions/... ARM ID.",
        )
    return "name"


# --- ARM ID parsing ----------------------------------------------------------


def parse_arm_id(arm_id: str) -> tuple[str, str, str]:
    """Return ``(subscription_id, resource_group, account_name)`` from an ARM ID.

    Raises :class:`CuCliError` if the shape isn't
    ``/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<name>``.
    """
    parts = arm_id.strip("/").split("/")
    # Expect: subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<name>
    if (len(parts) != 8
            or parts[0].lower() != "subscriptions"
            or parts[2].lower() != "resourcegroups"
            or parts[4].lower() != "providers"
            or parts[5].lower() != "microsoft.cognitiveservices"
            or parts[6].lower() != "accounts"):
        raise CuCliError(
            f"'{arm_id}' is not a Microsoft.CognitiveServices/accounts ARM ID.",
            hint="expected /subscriptions/<sub>/resourceGroups/<rg>/providers/"
                 "Microsoft.CognitiveServices/accounts/<name>.",
        )
    return parts[1], parts[3], parts[7]


def _canonical_arm_id(subscription_id: str, resource_group: str, account_name: str) -> str:
    """Build a canonical ARM ID (used for equality checks between resolved sides)."""
    return (
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
    )


# --- Kind validation ---------------------------------------------------------


def _is_cu_capable(kind: Optional[str]) -> bool:
    """Return True if the account's ``kind`` supports Content Understanding."""
    if not kind:
        return False
    return kind.lower() in _CU_KINDS


# --- Endpoint derivation -----------------------------------------------------


def _account_endpoint(account: object) -> str:
    """Return the CU/Foundry endpoint for an account.

    Prefers ``properties.endpoints["Content Understanding"]`` when the ARM
    response includes it; falls back to ``properties.endpoint`` (older shape);
    falls back to the AIServices default ``https://<name>.services.ai.azure.com/``.
    """
    props = getattr(account, "properties", None)
    name = getattr(account, "name", None) or ""
    if props is not None:
        endpoints = getattr(props, "endpoints", None)
        if endpoints and isinstance(endpoints, dict):
            for key in ("Content Understanding", "ContentUnderstanding", "OpenAI", "Cognitive Services"):
                if key in endpoints and endpoints[key]:
                    return endpoints[key].rstrip("/") + "/"
        ep = getattr(props, "endpoint", None)
        if ep:
            return ep.rstrip("/") + "/"
    return f"https://{name}.services.ai.azure.com/"


def _hostname_of(url: str) -> str:
    """Return the lowercase hostname of a URL, without port."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    return host


# --- Public resolver ---------------------------------------------------------


def resolve_resource(
    selector: str,
    *,
    subscription_id: Optional[str] = None,
    resource_group: Optional[str] = None,
    credential: Optional["TokenCredential"] = None,
) -> ResolvedResource:
    """Resolve a ``--from``/``--to`` selector to a canonical :class:`ResolvedResource`.

    The classifier dispatches to one of the three private helpers. Discovery
    uses :class:`DefaultAzureCredential` by default. The optional
    ``subscription_id`` scopes URL/name discovery. When omitted, the active
    Azure CLI subscription is used. ARM IDs carry their own subscription.
    Discovery never fans out across subscriptions.
    """
    # Lazy imports so `cu` starts fast and users who never call `analyzer copy`
    # aren't forced to have azure-mgmt-* installed at runtime.
    from azure.identity import DefaultAzureCredential

    cred = credential or DefaultAzureCredential()
    kind = classify_selector(selector)
    if kind == "arm-id":
        return _resolve_arm_id(selector, cred)
    effective_subscription = subscription_id or current_azure_cli_subscription_id()
    if kind == "url":
        return _resolve_url(selector, cred, subscription_id=effective_subscription,
                            resource_group=resource_group)
    return _resolve_name(selector, cred, subscription_id=effective_subscription,
                         resource_group=resource_group)


def current_azure_cli_subscription_id() -> str:
    """Return the active ``az`` subscription ID or fail with actionable guidance."""
    az = shutil.which("az")
    if not az:
        raise CuCliError(
            "Azure CLI (`az`) is required to determine the active subscription.",
            hint="install Azure CLI and run `az login`, or pass an explicit "
                 "`--source-subscription` / `--destination-subscription`.",
        )
    try:
        result = subprocess.run(
            [
                az,
                "account",
                "show",
                "--query",
                "id",
                "-o",
                "tsv",
                "--only-show-errors",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        raise CuCliError(
            "timed out while reading the active Azure CLI subscription.",
            hint="run `az account show` to verify Azure CLI, or pass an explicit "
                 "`--source-subscription` / `--destination-subscription`.",
        ) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise CuCliError(
            "no active Azure CLI subscription is available.",
            hint=(detail + " " if detail else "")
                 + "Run `az login` and `az account set --subscription <id>`, "
                 "or pass an explicit `--source-subscription` / "
                 "`--destination-subscription`.",
        )
    subscription_id = result.stdout.strip()
    if not subscription_id:
        raise CuCliError(
            "`az account show` returned an empty subscription ID.",
            hint="run `az account set --subscription <id>`, or pass an explicit "
                 "`--source-subscription` / `--destination-subscription`.",
        )
    return subscription_id


# --- ARM ID resolution -------------------------------------------------------


def _resolve_arm_id(arm_id: str, credential: "TokenCredential") -> ResolvedResource:
    from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
    from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

    sub, rg, name = parse_arm_id(arm_id)
    client = CognitiveServicesManagementClient(credential, sub)
    try:
        account = client.accounts.get(rg, name)
    except ResourceNotFoundError as exc:
        raise CuCliError(
            f"account '{name}' was not found in resource group '{rg}' (sub {sub}).",
            hint="verify the ARM ID; run `az cognitiveservices account show "
                 f"--name {name} --resource-group {rg} --subscription {sub}` to check "
                 "access with the signed-in identity.",
        ) from exc
    except HttpResponseError as exc:
        _reraise_login_or_rbac(exc, hint_scope=f"subscription {sub}")
        raise
    return _account_to_resolved(account)


# --- URL resolution ----------------------------------------------------------


def _resolve_url(
    url: str,
    credential: "TokenCredential",
    *,
    subscription_id: str,
    resource_group: Optional[str] = None,
) -> ResolvedResource:
    """Resolve a Foundry endpoint URL by matching its hostname to a discovered account."""
    hostname = _hostname_of(url)
    if not hostname:
        raise CuCliError(
            f"could not parse hostname from '{url}'.",
            hint="pass a Foundry endpoint URL like https://<account>.services.ai.azure.com/.",
        )
    # AIServices/CU endpoints follow one of these hostname shapes:
    #   <account>.services.ai.azure.com
    #   <account>.cognitiveservices.azure.com
    # We use the leading label as the candidate account name; the full match
    # comes from comparing the account's actual endpoint(s) against the URL.
    candidate_name = hostname.split(".", 1)[0]
    matches = _discover_accounts(
        credential,
        subscription_id=subscription_id,
        resource_group=resource_group,
        name_hint=candidate_name,
    )
    hostname_matches: List[object] = []
    for account in matches:
        try:
            endpoint = _account_endpoint(account)
            if _hostname_of(endpoint) == hostname:
                hostname_matches.append(account)
        except Exception:  # pragma: no cover - be permissive during scan
            continue
    # Never fall back from a URL to a merely name-matched account. A typo such
    # as https://acct.evil.example/ must not silently select the Azure account
    # named ``acct``. ``_account_endpoint`` already synthesizes the standard
    # AIServices hostname when endpoint metadata is absent, so valid standard
    # URLs still match without this unsafe fallback.
    _fail_on_ambiguous(hostname_matches, selector=url, hint_extra=(
        "try `--source-subscription <sub>` and `--source-resource-group <rg>` "
        "(or use the full ARM ID) to disambiguate."))
    return _account_to_resolved(hostname_matches[0])


# --- Name resolution ---------------------------------------------------------


def _resolve_name(
    name: str,
    credential: "TokenCredential",
    *,
    subscription_id: str,
    resource_group: Optional[str] = None,
) -> ResolvedResource:
    matches = _discover_accounts(
        credential,
        subscription_id=subscription_id,
        resource_group=resource_group,
        name_hint=name,
    )
    # For name resolution we require an *exact* case-insensitive match on
    # account name. Substring candidates are useful only to reduce discovery
    # work; accepting one here would let a typo like ``contoso`` select the
    # sole account ``contoso-prod``.
    exact = [a for a in matches if (getattr(a, "name", "") or "").lower() == name.lower()]
    _fail_on_ambiguous(exact, selector=name, hint_extra=(
        "try `--source-subscription <sub>` and `--source-resource-group <rg>` "
        "to narrow the search, or use the full ARM ID."))
    return _account_to_resolved(exact[0])


# --- Shared discovery + error surfacing --------------------------------------


def _discover_accounts(
    credential: "TokenCredential",
    *,
    subscription_id: str,
    resource_group: Optional[str],
    name_hint: Optional[str] = None,
) -> List[object]:
    """Discover Microsoft.CognitiveServices accounts in one subscription.

    When provided, ``name_hint`` filters account names case-insensitively as a
    substring or exact match. Account ``kind`` is deliberately retained until
    after selector disambiguation so selecting an existing incompatible account
    produces the specific kind/metadata error from ``_account_to_resolved``
    instead of a misleading "no account matched" result.
    """
    from azure.core.exceptions import HttpResponseError
    from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
    accounts: List[object] = []
    try:
        client = CognitiveServicesManagementClient(credential, subscription_id)
        if resource_group:
            iterator = client.accounts.list_by_resource_group(resource_group)
        else:
            iterator = client.accounts.list()
        for account in iterator:
            nm = (getattr(account, "name", "") or "").lower()
            if name_hint and name_hint.lower() not in nm:
                continue
            accounts.append(account)
    except HttpResponseError as exc:
        _reraise_login_or_rbac(exc, hint_scope=f"subscription {subscription_id}")
        raise
    return accounts


def _fail_on_ambiguous(accounts: List[object], *, selector: str, hint_extra: str) -> None:
    if not accounts:
        raise CuCliError(
            f"no Content Understanding-capable account matched '{selector}'.",
            hint=hint_extra + " Also check you're logged in with `az login` and the "
                 "signed-in identity has access to the target subscription.",
        )
    if len(accounts) > 1:
        candidates = "\n".join(
            f"  {getattr(a, 'name', '?')}  {getattr(a, 'id', '?')}"
            for a in accounts[:10]
        )
        more = f"\n  ...+{len(accounts) - 10} more" if len(accounts) > 10 else ""
        raise CuCliError(
            f"multiple accounts matched '{selector}' — refusing to guess. "
            f"Candidates:\n{candidates}{more}",
            hint=hint_extra,
        )


def _reraise_login_or_rbac(exc: BaseException, *, hint_scope: str) -> None:
    """Translate common discovery failures to actionable :class:`CuCliError`."""
    status = getattr(exc, "status_code", None)
    msg = str(exc)
    if status == 404 and "SubscriptionNotFound" in msg:
        raise CuCliError(
            f"Azure {hint_scope} was not found or is not accessible.",
            hint="verify the subscription ID or name and the signed-in identity's access.",
        ) from exc
    if status in (401,) or "AuthenticationFailed" in msg or "unauthorized" in msg.lower():
        raise CuCliError(
            f"Azure login is not active (or the token is invalid) for {hint_scope}.",
            hint="run `az login` and try again.",
        ) from exc
    if status in (403,) or "Forbidden" in msg or "AuthorizationFailed" in msg:
        raise CuCliError(
            f"signed-in identity is not authorized for {hint_scope}.",
            hint="verify the identity has *Reader* on the subscription/resource group "
                 "for discovery, plus *Cognitive Services User* on both source and "
                 "target CU accounts for the copy itself.",
        ) from exc


def _account_to_resolved(account: object) -> ResolvedResource:
    """Adapt a management-plane ``Account`` object to :class:`ResolvedResource`."""
    arm_id = getattr(account, "id", "") or ""
    name = getattr(account, "name", "") or ""
    region = getattr(account, "location", "") or ""
    kind = getattr(account, "kind", "") or ""
    if not _is_cu_capable(kind):
        raise CuCliError(
            f"account '{name}' has kind '{kind}', which is not Content Understanding-capable.",
            hint="pass a Foundry (AIServices) or ContentUnderstanding account.",
        )
    # Parse ARM ID so downstream compares don't drift on casing.
    try:
        sub, rg, acct = parse_arm_id(arm_id)
    except CuCliError as exc:  # ARM should always be well-formed; be defensive
        raise CuCliError(
            f"account '{name}' returned an unexpected ARM ID '{arm_id}'.",
            hint="report this to the CU CLI maintainers.",
        ) from exc
    return ResolvedResource(
        arm_id=_canonical_arm_id(sub, rg, acct),
        region=region,
        endpoint=_account_endpoint(account),
        subscription_id=sub,
        resource_group=rg,
        account_name=acct,
    )


# --- Canonical equality ------------------------------------------------------


def resources_equal(a: ResolvedResource, b: ResolvedResource) -> bool:
    """Return True when two resolved resources refer to the same Azure resource."""
    return a.arm_id.lower() == b.arm_id.lower()
