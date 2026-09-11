# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Generate the CU azd/Bicep project using Azure CLI host context."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from azure.cli.core._profile import Profile as AzureCliProfile
from knack.prompting import prompt, prompt_choice_list, prompt_y_n

from cu_cli_core import infra as core_infra
from cu_cli_core.errors import UsageError

from ._client_factory import ensure_supported_cloud
from ._resources import resolve_resource

DEFAULT_ENVIRONMENT = core_infra.DEFAULT_ENVIRONMENT
DEFAULT_LOCATION = core_infra.DEFAULT_LOCATION
DEFAULT_API_VERSION = "2025-11-01"
CU_REGION_SUPPORT_URL = core_infra.CU_REGION_SUPPORT_URL
CU_SUPPORTED_REGIONS = core_infra.CU_SUPPORTED_REGIONS
AzureAccount = core_infra.AzureAccount
InfraChoices = core_infra.InfraChoices


def _template_root():
    return core_infra.template_root()


def _iter_template_files(root):
    yield from core_infra.iter_template_files(root)


def _validate_environment(value: str) -> str:
    return core_infra.validate_environment(value)


def _validate_location(value: str) -> str:
    return core_infra.validate_location(value)


def _validate_prefix(value: str | None) -> str | None:
    return core_infra.validate_foundry_prefix(value)


def _parse_models(value: str | None) -> str:
    return core_infra.normalize_model_selection(value)


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
        resolved["models"] = "prompt"
    if resolved.get("assign_roles") is None and not resolved.get("foundry_endpoint"):
        resolved["assign_roles"] = prompt_y_n(
            "Assign required RBAC roles to the signed-in user?", default="n"
        )
    del account
    return resolved


def _render_env(choices: InfraChoices) -> dict[str, str]:
    return core_infra.render_env_assignments(choices)


def _merge_env(existing: str | None, choices: InfraChoices) -> str:
    return core_infra.merge_env(existing, choices)


def _safe_environment_directory(target: Path, environment: str) -> Path:
    return core_infra.safe_environment_directory(target, environment)


def _write_project(target: Path, choices: InfraChoices, *, force: bool) -> tuple[list[str], bool]:
    return core_infra.materialize_project(target, choices, force=force)


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
            else False
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
