"""Unit tests for the Azure resource resolver used by ``cu analyzer copy``.

All tests are network-free — they inject fake management-plane clients via a
:class:`_FakeAccount`/``_FakeMgmt`` pair. Real Azure identity is stubbed with a
sentinel credential; the resolver only calls it through the management-plane
clients we replace.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cu_cli.core.azure_resources import (
    ResolvedResource,
    _account_endpoint,
    _canonical_arm_id,
    _hostname_of,
    _is_cu_capable,
    classify_selector,
    parse_arm_id,
    resolve_resource,
    resources_equal,
)
from cu_cli.errors import CuCliError

pytestmark = pytest.mark.unit


# --- fixtures ---------------------------------------------------------------


class _FakeAccount:
    def __init__(self, *, name: str, sub: str, rg: str, region: str = "eastus",
                 kind: str = "AIServices", endpoint: str | None = None) -> None:
        self.name = name
        self.location = region
        self.kind = kind
        self.id = _canonical_arm_id(sub, rg, name)
        default_ep = endpoint or f"https://{name}.services.ai.azure.com/"
        self.properties = SimpleNamespace(
            endpoints={"Content Understanding": default_ep},
            endpoint=default_ep,
        )


class _FakeAccountsOps:
    """Fake ``accounts`` operations for :class:`CognitiveServicesManagementClient`."""

    def __init__(self, accounts):
        self._accounts = list(accounts)

    def list(self):
        return iter(self._accounts)

    def list_by_resource_group(self, rg):
        return iter([a for a in self._accounts
                     if a.id.split("/")[4].lower() == rg.lower()])

    def get(self, rg, name):
        for a in self._accounts:
            if (a.name.lower() == name.lower()
                    and a.id.split("/")[4].lower() == rg.lower()):
                return a
        from azure.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(message=f"account '{name}' not found in rg '{rg}'")


class _FakeMgmtClient:
    """Stand-in for ``CognitiveServicesManagementClient``."""

    def __init__(self, accounts_by_sub: dict[str, list[_FakeAccount]]):
        self._accounts_by_sub = accounts_by_sub
        self._current_sub: str | None = None

    def __call__(self, credential, subscription_id):
        # Called as a constructor by the resolver.
        clone = _FakeMgmtClient(self._accounts_by_sub)
        clone._current_sub = subscription_id
        clone.accounts = _FakeAccountsOps(self._accounts_by_sub.get(subscription_id, []))
        return clone


class _FakeCred:
    """Cheap DefaultAzureCredential stand-in — never called."""


@pytest.fixture(autouse=True)
def _active_subscription(monkeypatch, request):
    if request.node.name.startswith("test_current_subscription_"):
        return
    monkeypatch.setattr(
        "cu_cli.core.azure_resources.current_azure_cli_subscription_id",
        lambda: "sub-a",
    )


# --- selector classification ------------------------------------------------


def test_classify_selector_arm_id():
    assert classify_selector(
        "/subscriptions/aaaa/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/acct"
    ) == "arm-id"
    assert classify_selector(
        "/SUBSCRIPTIONS/AAAA/RESOURCEGROUPS/RG/PROVIDERS/MICROSOFT.COGNITIVESERVICES/ACCOUNTS/ACCT"
    ) == "arm-id"


def test_classify_selector_url():
    assert classify_selector("https://acct.services.ai.azure.com/") == "url"
    assert classify_selector("http://x.example/") == "url"
    assert classify_selector("HTTPS://ACCT.SERVICES.AI.AZURE.COM/") == "url"


def test_classify_selector_name():
    assert classify_selector("my-account") == "name"
    assert classify_selector("contoso_cu") == "name"


def test_classify_selector_ambiguous_rejects():
    """Slash-containing non-URL non-ARM strings are refused (not silently treated as names)."""
    with pytest.raises(CuCliError):
        classify_selector("foo/bar")


def test_classify_selector_empty_rejects():
    with pytest.raises(CuCliError):
        classify_selector("")


# --- ARM ID parsing --------------------------------------------------------


def test_parse_arm_id_happy():
    sub, rg, name = parse_arm_id(
        "/subscriptions/S/resourceGroups/RG/providers/Microsoft.CognitiveServices/accounts/A"
    )
    assert (sub, rg, name) == ("S", "RG", "A")


def test_parse_arm_id_rejects_wrong_provider():
    with pytest.raises(CuCliError):
        parse_arm_id("/subscriptions/S/resourceGroups/RG/providers/Microsoft.Storage/accounts/A")


def test_parse_arm_id_rejects_short_id():
    with pytest.raises(CuCliError):
        parse_arm_id("/subscriptions/S/resourceGroups/RG")


# --- helpers ---------------------------------------------------------------


def test_hostname_of_strips_port_and_lowercases():
    assert _hostname_of("HTTPS://Foo.Example:443/x") == "foo.example"


def test_is_cu_capable_accepts_aiservices():
    assert _is_cu_capable("AIServices")
    assert _is_cu_capable("aiservices")
    assert _is_cu_capable("ContentUnderstanding")


def test_is_cu_capable_rejects_others():
    assert not _is_cu_capable("OpenAI")
    assert not _is_cu_capable("Storage")
    assert not _is_cu_capable(None)


def test_account_endpoint_prefers_content_understanding_key():
    a = _FakeAccount(name="a1", sub="s", rg="rg",
                     endpoint="https://a1.services.ai.azure.com/")
    assert _account_endpoint(a) == "https://a1.services.ai.azure.com/"


# --- resource equality -----------------------------------------------------


def test_resources_equal_canonical():
    r1 = ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/RG/providers/Microsoft.CognitiveServices/accounts/A",
        region="eastus", endpoint="https://a.example/",
        subscription_id="S", resource_group="RG", account_name="A",
    )
    r2 = ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/RG/providers/Microsoft.CognitiveServices/accounts/a",
        region="eastus", endpoint="https://a.example/",
        subscription_id="S", resource_group="RG", account_name="a",
    )
    assert resources_equal(r1, r2)  # case-insensitive


def test_resources_not_equal_when_arm_differs():
    r1 = ResolvedResource(arm_id="/subscriptions/S1/resourceGroups/RG/providers/Microsoft.CognitiveServices/accounts/A",
                          region="eastus", endpoint="", subscription_id="S1", resource_group="RG", account_name="A")
    r2 = ResolvedResource(arm_id="/subscriptions/S2/resourceGroups/RG/providers/Microsoft.CognitiveServices/accounts/A",
                          region="eastus", endpoint="", subscription_id="S2", resource_group="RG", account_name="A")
    assert not resources_equal(r1, r2)


# --- URL resolution --------------------------------------------------------


def test_resolve_url_matches_by_hostname(monkeypatch):
    """Given a URL, resolver finds the account whose endpoint hostname matches."""
    accounts = {
        "sub-a": [_FakeAccount(name="acct-a", sub="sub-a", rg="rg-a",
                               endpoint="https://acct-a.services.ai.azure.com/")],
        "sub-b": [_FakeAccount(name="acct-b", sub="sub-b", rg="rg-b",
                               endpoint="https://acct-b.services.ai.azure.com/")],
    }
    fake_mgmt = _FakeMgmtClient(accounts)
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient", fake_mgmt)

    resolved = resolve_resource("https://acct-b.services.ai.azure.com/",
                                subscription_id="sub-b",
                                credential=_FakeCred())
    assert resolved.account_name == "acct-b"
    assert resolved.subscription_id == "sub-b"
    assert resolved.region == "eastus"


def test_resolve_url_no_match_raises_with_scope_hint(monkeypatch):
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient({"sub-a": [_FakeAccount(name="other", sub="sub-a", rg="rg-a")]}))
    with pytest.raises(CuCliError) as ei:
        resolve_resource("https://nonexistent.services.ai.azure.com/", credential=_FakeCred())
    assert "no Content Understanding-capable account matched" in ei.value.message
    assert (
        "az login" in (ei.value.hint or "").lower()
        or "--source-subscription" in (ei.value.hint or "").lower()
    )


def test_resolve_url_never_falls_back_to_account_name(monkeypatch):
    """A URL host must match the discovered endpoint exactly.

    The leading label in ``acct.evil.example`` matches the Azure account name,
    but selecting that account would violate the resolver's never-guess contract.
    """
    accounts = {"sub-a": [_FakeAccount(name="acct", sub="sub-a", rg="rg-a")]}
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts),
    )
    with pytest.raises(CuCliError) as ei:
        resolve_resource("https://acct.evil.example/", credential=_FakeCred())
    assert "no Content Understanding-capable account matched" in ei.value.message


def test_resolve_name_uses_only_active_subscription(monkeypatch):
    """Unqualified discovery never falls back to another accessible subscription."""
    accounts = {
        "sub-a": [_FakeAccount(name="contoso", sub="sub-a", rg="rg-dev")],
        "sub-b": [_FakeAccount(name="contoso", sub="sub-b", rg="rg-prod")],
    }
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts))
    resolved = resolve_resource("contoso", credential=_FakeCred())
    assert resolved.subscription_id == "sub-a"
    assert resolved.resource_group == "rg-dev"


def test_resolve_name_scope_narrowing(monkeypatch):
    """Source subscription and resource-group options narrow the search."""
    accounts = {
        "sub-a": [_FakeAccount(name="contoso", sub="sub-a", rg="rg-dev")],
        "sub-b": [_FakeAccount(name="contoso", sub="sub-b", rg="rg-prod")],
    }
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts))
    monkeypatch.setattr(
        "cu_cli.core.azure_resources.current_azure_cli_subscription_id",
        lambda: pytest.fail("explicit subscription must bypass Azure CLI lookup"),
    )
    resolved = resolve_resource(
        "contoso",
        subscription_id="sub-b",
        resource_group="rg-prod",
        credential=_FakeCred(),
    )
    assert resolved.subscription_id == "sub-b"
    assert resolved.resource_group == "rg-prod"


def test_resolve_name_requires_exact_match(monkeypatch):
    """A unique substring candidate must not be accepted as the requested name."""
    accounts = {
        "sub-a": [_FakeAccount(name="contoso-prod", sub="sub-a", rg="rg-prod")],
    }
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts),
    )
    with pytest.raises(CuCliError) as ei:
        resolve_resource("contoso", credential=_FakeCred())
    assert "no Content Understanding-capable account matched 'contoso'" in ei.value.message


def test_resolve_arm_id_verifies_via_management_plane(monkeypatch):
    accounts = {"sub-a": [_FakeAccount(name="acct", sub="sub-a", rg="rg")]}
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts))
    arm_id = "/subscriptions/sub-a/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/acct"
    resolved = resolve_resource(arm_id, credential=_FakeCred())
    assert resolved.arm_id.lower() == arm_id.lower()


def test_resolve_arm_id_missing_account_raises(monkeypatch):
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient({"sub-a": []}))
    with pytest.raises(CuCliError) as ei:
        resolve_resource(
            "/subscriptions/sub-a/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/gone",
            credential=_FakeCred(),
        )
    assert "was not found" in ei.value.message


def test_resolve_url_selects_matching_cu_account(monkeypatch):
    """AIServices resolves even when an unrelated OpenAI account is present."""
    accounts = {
        "sub-a": [
            _FakeAccount(name="acct", sub="sub-a", rg="rg", kind="OpenAI",
                         endpoint="https://acct.openai.azure.com/"),
            _FakeAccount(name="acct-cu", sub="sub-a", rg="rg", kind="AIServices",
                         endpoint="https://acct-cu.services.ai.azure.com/"),
        ]
    }
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts))
    resolved = resolve_resource("https://acct-cu.services.ai.azure.com/", credential=_FakeCred())
    assert resolved.account_name == "acct-cu"


def test_resolve_existing_non_cu_account_reports_its_kind(monkeypatch):
    """Retain non-CU candidates until validation to surface metadata mismatch."""
    accounts = {
        "sub-a": [
            _FakeAccount(
                name="openai-only",
                sub="sub-a",
                rg="rg",
                kind="OpenAI",
                endpoint="https://openai-only.openai.azure.com/",
            ),
        ],
    }
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts),
    )
    with pytest.raises(CuCliError) as ei:
        resolve_resource(
            "https://openai-only.openai.azure.com/",
            credential=_FakeCred(),
        )
    assert "kind 'OpenAI'" in ei.value.message
    assert "not Content Understanding-capable" in ei.value.message


# --- Azure login / RBAC failure surfacing ------------------------------------


def test_current_subscription_uses_active_azure_cli_account(monkeypatch):
    from cu_cli.core import azure_resources

    monkeypatch.setattr(azure_resources.shutil, "which", lambda _: "/usr/bin/az")
    monkeypatch.setattr(
        azure_resources.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="selected-sub\n",
            stderr="",
        ),
    )

    assert azure_resources.current_azure_cli_subscription_id() == "selected-sub"


def test_current_subscription_failure_gives_az_login_hint(monkeypatch):
    from cu_cli.core import azure_resources

    monkeypatch.setattr(azure_resources.shutil, "which", lambda _: "/usr/bin/az")
    monkeypatch.setattr(
        azure_resources.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Please run az login",
        ),
    )

    with pytest.raises(CuCliError) as ei:
        azure_resources.current_azure_cli_subscription_id()
    assert "az login" in (ei.value.hint or "").lower()
    assert "no active Azure CLI subscription" in ei.value.message


@pytest.mark.parametrize("status", [401, 403])
def test_scoped_subscription_auth_failure_is_not_swallowed(monkeypatch, status):
    """401s always surface; a 403 on an explicitly selected sub surfaces too."""
    from azure.core.exceptions import HttpResponseError

    failure = HttpResponseError(
        message="AuthenticationFailed" if status == 401 else "AuthorizationFailed"
    )
    failure.status_code = status

    class _FailingAccounts:
        def list(self):
            raise failure

        def list_by_resource_group(self, resource_group):
            raise failure

    class _FailingMgmt:
        def __call__(self, credential, subscription_id):
            return SimpleNamespace(accounts=_FailingAccounts())

    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FailingMgmt(),
    )

    with pytest.raises(CuCliError) as ei:
        resolve_resource(
            "acct",
            subscription_id="explicit-sub",
            credential=_FakeCred(),
        )
    if status == 401:
        assert "az login" in (ei.value.hint or "").lower()
    else:
        assert "Reader" in (ei.value.hint or "")


def test_missing_explicit_subscription_is_actionable(monkeypatch):
    from azure.core.exceptions import HttpResponseError

    failure = HttpResponseError(message="SubscriptionNotFound")
    failure.status_code = 404

    class _FailingAccounts:
        def list(self):
            raise failure

    class _FailingMgmt:
        def __call__(self, credential, subscription_id):
            return SimpleNamespace(accounts=_FailingAccounts())

    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FailingMgmt(),
    )

    with pytest.raises(CuCliError) as ei:
        resolve_resource(
            "acct",
            subscription_id="missing-sub",
            credential=_FakeCred(),
        )

    assert "subscription missing-sub was not found or is not accessible" in ei.value.message
    assert "verify the subscription ID or name" in (ei.value.hint or "")


def test_unqualified_discovery_does_not_search_other_subscriptions(monkeypatch):
    accounts = {
        "sub-a": [],
        "sub-b": [_FakeAccount(name="acct", sub="sub-b", rg="rg")],
    }
    monkeypatch.setattr(
        "azure.mgmt.cognitiveservices.CognitiveServicesManagementClient",
        _FakeMgmtClient(accounts),
    )

    with pytest.raises(CuCliError) as ei:
        resolve_resource("acct", credential=_FakeCred())
    assert "no Content Understanding-capable account matched" in ei.value.message

    resolved = resolve_resource(
        "acct",
        subscription_id="sub-b",
        credential=_FakeCred(),
    )
    assert resolved.subscription_id == "sub-b"


# --- Endpoint fallback when ARM omits endpoint metadata ---------------------


def test_account_endpoint_falls_back_when_metadata_missing():
    """When the ARM ``Account`` payload omits every endpoint field, the CU CLI
    must still produce a working URL by falling back to the AIServices default
    hostname (``https://<name>.services.ai.azure.com/``). Otherwise a
    conforming ARM response with a stripped ``properties.endpoints`` map would
    break ``cu analyzer copy`` even though the account exists and is reachable.

    Covers three progressively-empty ARM shapes:

    1. ``properties=None`` (very old / stripped response),
    2. ``properties`` present but ``endpoints`` and ``endpoint`` both ``None``,
    3. ``endpoints={}`` (empty dict) and ``endpoint=None``.
    """
    from types import SimpleNamespace

    from cu_cli.core.azure_resources import _account_endpoint

    a1 = SimpleNamespace(name="myacct", properties=None)
    assert _account_endpoint(a1) == "https://myacct.services.ai.azure.com/"

    a2 = SimpleNamespace(
        name="myacct2",
        properties=SimpleNamespace(endpoints=None, endpoint=None),
    )
    assert _account_endpoint(a2) == "https://myacct2.services.ai.azure.com/"

    a3 = SimpleNamespace(
        name="myacct3",
        properties=SimpleNamespace(endpoints={}, endpoint=None),
    )
    assert _account_endpoint(a3) == "https://myacct3.services.ai.azure.com/"
