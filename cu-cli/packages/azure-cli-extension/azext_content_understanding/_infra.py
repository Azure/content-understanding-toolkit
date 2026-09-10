# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Generate the CU azd/Bicep project using Azure CLI host context."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import copyfile
from typing import Any, Iterable

from azure.cli.core._profile import Profile as AzureCliProfile
from knack.prompting import prompt, prompt_choice_list, prompt_y_n

from cu_cli_core.errors import LocalIOError, UsageError, ValidationError

from ._client_factory import ensure_supported_cloud
from ._resources import resolve_resource

DEFAULT_ENVIRONMENT = "dev"
DEFAULT_LOCATION = "eastus2"
DEFAULT_API_VERSION = "2025-11-01"
CU_REGION_SUPPORT_URL = (
    "https://learn.microsoft.com/azure/ai-services/content-understanding/"
    "language-region-support"
)
CU_SUPPORTED_REGIONS = (
    "australiaeast",
    "eastus",
    "eastus2",
    "japaneast",
    "northeurope",
    "southcentralus",
    "southeastasia",
    "swedencentral",
    "uksouth",
    "westeurope",
    "westus",
    "westus3",
)
_AZD_ENV_NAME_RE = re.compile(r"^[a-z0-9()_.-]{1,64}$")
_AZD_ENV_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*="
)
_AZD_ENV_MANAGED_KEYS = (
    "AZURE_ENV_NAME",
    "AZURE_LOCATION",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_TENANT_ID",
    "CU_API_VERSION",
    "CU_MODEL_SELECTION",
    "CU_MODEL_SETUP_COMPLETE",
    "FOUNDRY_RESOURCE_PREFIX",
    "FOUNDRY_EXISTING_ENDPOINT",
    "FOUNDRY_EXISTING_RESOURCE_GROUP",
    "AZD_ASSIGN_ROLES",
    "CU_PROFILE_SETUP_FORCE",
)


@dataclass(frozen=True)
class AzureAccount:
    subscription_id: str
    subscription_name: str
    tenant_id: str


@dataclass
class InfraChoices:
    environment: str
    location: str
    api_version: str
    account: AzureAccount
    foundry_prefix: str | None
    foundry_endpoint: str | None
    foundry_resource_group: str | None
    model_selection: str
    assign_roles: bool
    force_profile_setup: bool


def _template_root() -> Path:
    packaged = Path(__file__).with_name("_infra_template")
    if packaged.is_dir():
        return packaged
    raise LocalIOError("the infrastructure template is missing from the extension package.")


def _iter_template_files(root: Path) -> Iterable[tuple[Path, Path]]:
    for source in sorted(path for path in root.rglob("*") if path.is_file()):
        yield source, source.relative_to(root)


def _copy_template_file(source: Path, relative: Path, destination: Path) -> None:
    copyfile(source, destination)


def _validate_environment(value: str) -> str:
    name = value.strip().lower()
    if name in {".", ".."} or not _AZD_ENV_NAME_RE.fullmatch(name):
        raise ValidationError(
            "invalid azd environment name.",
            hint=(
                "Use 1-64 letters, numbers, hyphens, underscores, periods, or "
                "parentheses; '.' and '..' are not allowed."
            ),
        )
    return name


def _validate_location(value: str) -> str:
    location = value.strip().lower().replace(" ", "")
    if location not in CU_SUPPORTED_REGIONS:
        raise ValidationError(
            f"'{value}' is not a CU-supported region.",
            hint=f"Supported: {', '.join(CU_SUPPORTED_REGIONS)}. See {CU_REGION_SUPPORT_URL}",
        )
    return location


def _validate_prefix(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    prefix = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,18}[a-z0-9])?", prefix):
        raise ValidationError(
            "invalid Foundry resource prefix.",
            hint="Use 1-20 lowercase letters, numbers, or internal hyphens.",
        )
    return prefix


def _parse_models(value: str | None) -> str:
    if value is None:
        return "recommended"
    parts = [part.strip() for part in value.split(",")]
    if any(not part for part in parts):
        raise ValidationError("--models contains an empty entry.")
    special = {part.lower() for part in parts} & {"none", "recommended"}
    if special and len(parts) != 1:
        raise ValidationError("'none' and 'recommended' must each be used alone with --models.")
    return ",".join(parts).lower() if special else ",".join(parts)


def _subscriptions(cli_ctx: Any) -> list[AzureAccount]:
    profile = AzureCliProfile(cli_ctx=cli_ctx)
    subscriptions = profile.load_cached_subscriptions()
    accounts = []
    for item in subscriptions:
        subscription_id = str(item.get("id") or "").strip()
        tenant_id = str(item.get("tenantId") or item.get("tenant_id") or "").strip()
        name = str(item.get("name") or subscription_id).strip()
        if subscription_id and tenant_id and str(item.get("state", "Enabled")) == "Enabled":
            accounts.append(AzureAccount(subscription_id, name, tenant_id))
    return sorted(accounts, key=lambda account: account.subscription_name.casefold())


def _active_account(cli_ctx: Any) -> AzureAccount:
    profile = AzureCliProfile(cli_ctx=cli_ctx)
    item = profile.get_subscription()
    if not item:
        raise UsageError("no active Azure subscription is available; run 'az login'.")
    return AzureAccount(
        str(item.get("id") or profile.get_subscription_id()),
        str(item.get("name") or item.get("id") or ""),
        str(item.get("tenantId") or item.get("tenant_id") or ""),
    )


def _choose_account(cli_ctx: Any, *, interactive: bool) -> AzureAccount:
    active = _active_account(cli_ctx)
    if not interactive:
        return active
    accounts = _subscriptions(cli_ctx)
    if len(accounts) < 2:
        return active
    labels = [
        f"{account.subscription_name} ({account.subscription_id})"
        + (" [active]" if account.subscription_id == active.subscription_id else "")
        for account in accounts
    ]
    selected = prompt_choice_list("Select an Azure subscription:", labels)
    return accounts[selected]


def _interactive_choices(values: dict[str, Any], account: AzureAccount) -> dict[str, Any]:
    resolved = dict(values)
    resolved["environment"] = resolved.get("environment") or prompt(
        "azd environment name", default=DEFAULT_ENVIRONMENT
    )
    if not resolved.get("foundry_endpoint") and not resolved.get("foundry_prefix"):
        target = prompt_choice_list(
            "Choose a Microsoft Foundry resource:",
            ["Create a new resource", "Use an existing resource endpoint"],
        )
        if target == 1:
            resolved["foundry_endpoint"] = prompt("Existing Foundry endpoint")
        else:
            resolved["foundry_prefix"] = prompt(
                "New resource prefix (blank for generated name)", default=""
            )
    if not resolved.get("location") and not resolved.get("foundry_endpoint"):
        selected = prompt_choice_list("Select a Content Understanding region:", list(CU_SUPPORTED_REGIONS))
        resolved["location"] = CU_SUPPORTED_REGIONS[selected]
    if not resolved.get("models"):
        model_mode = prompt_choice_list(
            "Select model deployment behavior:",
            ["Recommended completion and embedding models", "No models", "Explicit model names"],
        )
        if model_mode == 0:
            resolved["models"] = "recommended"
        elif model_mode == 1:
            resolved["models"] = "none"
        else:
            resolved["models"] = prompt("Comma-separated model names or name@version selectors")
    if resolved.get("assign_roles") is None and not resolved.get("foundry_endpoint"):
        resolved["assign_roles"] = prompt_y_n(
            "Assign required RBAC roles to the signed-in user?", default="y"
        )
    del account
    return resolved


def _render_env(choices: InfraChoices) -> dict[str, str]:
    values = (
        choices.environment,
        choices.location,
        choices.account.subscription_id,
        choices.account.tenant_id,
        choices.api_version,
        choices.model_selection,
        "false",
        choices.foundry_prefix or "",
        choices.foundry_endpoint or "",
        choices.foundry_resource_group or "",
        str(choices.assign_roles).lower(),
        str(choices.force_profile_setup).lower(),
    )
    return {key: f'{key}="{value}"' for key, value in zip(_AZD_ENV_MANAGED_KEYS, values)}


def _merge_env(existing: str | None, choices: InfraChoices) -> str:
    assignments = _render_env(choices)
    if existing is None:
        return "\n".join((*assignments.values(), ""))
    newline = "\r\n" if "\r\n" in existing else "\n"
    seen: set[str] = set()
    output: list[str] = []
    for line in existing.splitlines(keepends=True):
        match = _AZD_ENV_ASSIGNMENT_RE.match(line)
        key = match.group("key") if match else None
        if key not in assignments:
            output.append(line)
        elif key not in seen:
            ending = "\r\n" if line.endswith("\r\n") else "\n"
            output.append(line if key == "CU_MODEL_SETUP_COMPLETE" else assignments[key] + ending)
            seen.add(key)
    if output and not output[-1].endswith(("\r", "\n")):
        output.append(newline)
    output.extend(assignments[key] + newline for key in _AZD_ENV_MANAGED_KEYS if key not in seen)
    return "".join(output)


def _safe_environment_directory(target: Path, environment: str) -> Path:
    target = target.resolve(strict=False)
    azure_root = target / ".azure"
    if azure_root.resolve(strict=False) != azure_root:
        raise LocalIOError("refusing to write through a redirected .azure directory.")
    environment_dir = azure_root / environment
    if environment_dir.resolve(strict=False).parent != azure_root:
        raise LocalIOError("refusing to write the azd environment outside .azure.")
    return environment_dir


def _write_project(target: Path, choices: InfraChoices, *, force: bool) -> tuple[list[str], bool]:
    environment_dir = _safe_environment_directory(target, choices.environment)
    has_content = target.exists() and any(target.iterdir())
    existing_template = (target / "azure.yaml").is_file() and (target / "infra/main.bicep").is_file()
    if has_content and not force and not existing_template:
        raise LocalIOError(
            f"'{target}' already exists and is non-empty.",
            hint="Choose another directory or pass --force to replace it.",
        )
    reused = has_content and existing_template and not force
    written: list[str] = []
    target.mkdir(parents=True, exist_ok=True)
    if not reused:
        for source, relative in _iter_template_files(_template_root()):
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            _copy_template_file(source, relative, destination)
            if destination.suffix == ".sh":
                destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            written.append(relative.as_posix())
    models = target / "infra/models.json"
    if force or not models.exists():
        models.parent.mkdir(parents=True, exist_ok=True)
        models.write_text("[]\n", encoding="utf-8")
        if "infra/models.json" not in written:
            written.append("infra/models.json")
    environment_dir.mkdir(parents=True, exist_ok=True)
    env_path = environment_dir / ".env"
    existing_env = env_path.read_text(encoding="utf-8") if reused and env_path.exists() else None
    env_path.write_text(_merge_env(existing_env, choices), encoding="utf-8", newline="")
    config_path = target / ".azure/config.json"
    config: dict[str, Any] = {}
    if reused and config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LocalIOError(f"could not read existing azd config: {config_path}") from exc
        if not isinstance(loaded, dict):
            raise LocalIOError(f"existing azd config must be a JSON object: {config_path}")
        config = loaded
    config.update({"version": 1, "defaultEnvironment": choices.environment})
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    written.extend([f".azure/{choices.environment}/.env", ".azure/config.json"])
    return sorted(set(written)), reused


def generate_infrastructure(cmd: Any, **values: Any) -> dict[str, Any]:
    """Generate a self-contained azd project; this command never runs azd."""

    ensure_supported_cloud(cmd.cli_ctx)
    interactive = bool(sys.stdin.isatty())
    account = _choose_account(cmd.cli_ctx, interactive=interactive)
    if interactive:
        values = _interactive_choices(values, account)
    if values.get("foundry_endpoint") and values.get("foundry_prefix"):
        raise UsageError("--foundry-endpoint and --foundry-prefix cannot be combined.")

    endpoint = values.get("foundry_endpoint")
    resource_group = None
    location = values.get("location")
    if endpoint:
        resource = resolve_resource(cmd, endpoint, subscription_id=account.subscription_id)
        endpoint = resource.endpoint
        resource_group = resource.resource_group
        location = location or resource.region
    choices = InfraChoices(
        environment=_validate_environment(values.get("environment") or DEFAULT_ENVIRONMENT),
        location=_validate_location(location or DEFAULT_LOCATION),
        api_version=str(values.get("api_version") or DEFAULT_API_VERSION),
        account=account,
        foundry_prefix=_validate_prefix(values.get("foundry_prefix")),
        foundry_endpoint=endpoint,
        foundry_resource_group=resource_group,
        model_selection=_parse_models(values.get("models")),
        assign_roles=(
            values["assign_roles"]
            if values.get("assign_roles") is not None
            else True
        ),
        force_profile_setup=bool(values.get("force")),
    )
    target = Path(values.get("output_dir") or "provision").expanduser().resolve()
    written, reused = _write_project(target, choices, force=bool(values.get("force")))
    result = asdict(choices)
    result.pop("account")
    result.update(
        {
            "outputDirectory": os.fspath(target),
            "subscriptionId": account.subscription_id,
            "subscriptionName": account.subscription_name,
            "tenantId": account.tenant_id,
            "files": written,
            "reusedExistingTemplate": reused,
            "nextSteps": [f"cd {target}", "azd auth login", "azd up"],
        }
    )
    return result
