"""``cu infra generate`` — generate an azd template for CU infrastructure."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys

import rich_click as click

from ..apiversion import API_VERSION_HELP, DEFAULT_API_VERSION, ensure_supported
from ..core.foundry import endpoint_host, host_label, normalize_foundry_endpoint
from ..errors import CuCliError, friendly_errors
from ..exit_codes import VALIDATION_FAILURE
from ..output import console
from ._help import common_commands
from ._infra_wizard import _validate_azd_environment_name, run_wizard

AZURE_SIGNUP_URL = "https://azure.microsoft.com/free/"


@dataclass(frozen=True)
class AzureAccount:
    subscription_id: str
    subscription_name: str
    tenant_id: str


def _check_az_subscription(subscription: str | None = None) -> AzureAccount:
    az = shutil.which("az")
    if not az:
        raise CuCliError(
            "Provisioning requires Azure CLI (`az`), which was not found on PATH.",
            hint=f"install it (https://aka.ms/azcli), sign up at {AZURE_SIGNUP_URL}, "
            "then rerun `cu infra generate`.",
        )
    command = [az, "account", "show"]
    if subscription:
        command.extend(["--subscription", subscription])
    command.extend(["--output", "json"])
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except OSError as exc:
        raise CuCliError(f"could not run `az account show`: {exc}") from exc
    if result.returncode != 0:
        target = f" '{subscription}'" if subscription else ""
        raise CuCliError(
            f"Azure subscription{target} is not accessible.",
            hint=f"run `az login`, select a subscription, or sign up at "
            f"{AZURE_SIGNUP_URL}, then rerun `cu infra generate`.",
        )
    try:
        payload = json.loads(result.stdout or "")
    except json.JSONDecodeError as exc:
        raise CuCliError("`az account show` returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise CuCliError("`az account show` returned an invalid account record.")
    subscription_id = str(payload.get("id") or "").strip()
    subscription_name = str(payload.get("name") or "").strip()
    tenant_id = str(payload.get("tenantId") or "").strip()
    if not subscription_id or not subscription_name or not tenant_id:
        raise CuCliError(
            "`az account show` did not return subscription id, name, and tenant id."
        )
    return AzureAccount(subscription_id, subscription_name, tenant_id)


def _parse_models(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parts = [part.strip() for part in value.split(",")]
    if any(not part for part in parts):
        raise CuCliError(
            "--models requires 'recommended', 'none', or one or more "
            "comma-separated model names; empty entries are not allowed.",
            hint="use `--models none` to deploy no models, or omit `--models` "
                 "for the interactive picker.",
            exit_code=VALIDATION_FAILURE,
        )
    special = {"none", "recommended"}
    if len(parts) > 1 and special.intersection(parts):
        raise CuCliError(
            "'none' and 'recommended' must each be used alone with --models.",
            hint="use one special value or provide only comma-separated model names.",
            exit_code=VALIDATION_FAILURE,
        )
    return parts


def _resolve_existing_foundry_account(
    foundry_endpoint: str,
    subscription_id: str,
) -> tuple[str, str, str | None]:
    az = shutil.which("az")
    if not az:
        raise CuCliError(
            "resolving an existing Foundry endpoint requires Azure CLI (`az`)."
        )
    result = subprocess.run(
        [
            az,
            "cognitiveservices",
            "account",
            "list",
            "--subscription",
            subscription_id,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CuCliError(
            "could not list Cognitive Services accounts to resolve the endpoint.",
            hint=(result.stderr or result.stdout).strip()
            or "run `az account show` and retry.",
        )
    try:
        accounts = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CuCliError(
            "Azure CLI returned invalid JSON while resolving the Foundry endpoint."
        ) from exc
    target = foundry_endpoint.rstrip("/").lower()
    target_host = endpoint_host(foundry_endpoint)
    target_label = host_label(target_host)
    for account in accounts:
        if not isinstance(account, dict):
            continue
        properties_value = account.get("properties")
        properties = (
            properties_value if isinstance(properties_value, dict) else {}
        )
        account_endpoint = str(
            properties.get("endpoint") or account.get("endpoint") or ""
        )
        name = str(account.get("name") or "").strip()
        resource_group = str(account.get("resourceGroup") or "").strip()
        if not name or not resource_group:
            continue
        exact_match = account_endpoint.rstrip("/").lower() == target
        host_match = False
        if target_host.endswith(".services.ai.azure.com"):
            candidates = {name.lower()}
            custom_subdomain = str(
                properties.get("customSubDomainName") or ""
            ).strip().lower()
            if custom_subdomain:
                candidates.add(custom_subdomain)
            properties_host = endpoint_host(
                str(properties.get("endpoint") or "")
            )
            if properties_host:
                candidates.add(host_label(properties_host))
            host_match = bool(target_label and target_label in candidates)
        if exact_match or host_match:
            location = str(account.get("location") or "").strip()
            return name, resource_group, location or None
    raise CuCliError(
        f"no Microsoft Foundry resource matched endpoint '{foundry_endpoint}'.",
        hint="verify the endpoint, subscription, and your access with Azure CLI.",
    )


@click.group(
    "infra",
    help=(
        "Generate infrastructure-as-code used to provision and configure "
        "Content Understanding resources."
    ),
    epilog=common_commands(
        (
            "cu infra generate",
            "Generate an azd/Bicep project. Run azd up to provision Azure resources.",
        ),
    ),
)
def infra_group() -> None:
    """Infrastructure-as-code generation commands."""


@infra_group.command(
    "generate",
    help=(
        "Generate an azd/Bicep project used to provision a Microsoft Foundry "
        "resource and configure Content Understanding. This command writes files "
        "only; run `azd up` to provision Azure resources."
    ),
    epilog=common_commands(
        (
            "cu infra generate",
            "Generate a project for a new resource and optional model deployments. "
            "Run azd up to provision it.",
        ),
        (
            "cu infra generate --foundry-endpoint URL",
            "Generate a project for optional model deployments and defaults on an "
            "existing resource. Run azd up to apply it.",
        ),
    ),
)
@click.option(
    "-d",
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("provision"),
    show_default=True,
    help="Directory where the azd template is generated.",
)
@click.option("-e", "--environment", default=None, help="azd environment name.")
@click.option("-l", "--location", default=None, help="Azure region.")
@click.option("--subscription", default=None, help="Azure subscription name or ID.")
@click.option("--api-version", default=None, help=API_VERSION_HELP)
@click.option(
    "--models",
    default=None,
    help=(
        "Comma-separated model names, 'recommended', or 'none'; omit for an interactive "
        "picker. Explicit names are validated against the live model catalog during azd up."
    ),
)
@click.option(
    "--foundry-endpoint",
    default=None,
    help="Existing Microsoft Foundry resource endpoint; only selected models are deployed.",
)
@click.option(
    "--foundry-prefix",
    default=None,
    help="Prefix for a new globally unique Microsoft Foundry resource name.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing generated template.")
@friendly_errors
def cmd_infra_generate(
    output_dir: Path,
    environment: str | None,
    location: str | None,
    subscription: str | None,
    api_version: str | None,
    models: str | None,
    foundry_endpoint: str | None,
    foundry_prefix: str | None,
    force: bool,
) -> None:
    selected_models = _parse_models(models)
    version = ensure_supported(api_version or DEFAULT_API_VERSION)
    if environment is not None:
        environment = _validate_azd_environment_name(environment)
    if foundry_endpoint and foundry_prefix:
        raise CuCliError(
            "--foundry-prefix cannot be used with --foundry-endpoint.",
            hint="omit the prefix when targeting an existing Foundry resource.",
        )

    normalized_endpoint = (
        normalize_foundry_endpoint(foundry_endpoint)
        if foundry_endpoint
        else None
    )
    account = _check_az_subscription(subscription)
    existing_resource_group: str | None = None
    if normalized_endpoint:
        _, existing_resource_group, existing_location = (
            _resolve_existing_foundry_account(
                normalized_endpoint,
                account.subscription_id,
            )
        )
        if location is None:
            location = existing_location

    target = output_dir.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[bold]cu infra generate[/bold] -> [cyan]{target}[/cyan]")
    console.print(
        f"  [dim]Azure subscription: {account.subscription_name} "
        f"({account.subscription_id})[/dim]"
    )
    run_wizard(
        target,
        interactive=sys.stdin.isatty(),
        already_opted_in=True,
        env=environment,
        location=location,
        api_version=version,
        subscription_id=account.subscription_id,
        subscription_name=account.subscription_name,
        tenant_id=account.tenant_id,
        foundry_account_prefix=foundry_prefix,
        foundry_endpoint=normalized_endpoint,
        foundry_resource_group=existing_resource_group,
        models=selected_models,
        assign_roles=None,
        force=force,
    )
