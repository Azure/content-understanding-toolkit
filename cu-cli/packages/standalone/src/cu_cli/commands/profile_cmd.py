"""``cu profile`` — manage resource-specific settings in Azure CLI configuration."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import rich_click as click
from azure.core.exceptions import HttpResponseError
from click.exceptions import Exit
from cu_cli_core.command_spec import (
    PROFILE_COPY,
    PROFILE_CREATE,
    PROFILE_DELETE,
    PROFILE_GET,
    PROFILE_LIST,
    PROFILE_RENAME,
    PROFILE_SET,
    PROFILE_SET_ACTIVE,
    PROFILE_SHOW,
    PROFILE_SYNC_DEFAULTS,
    PROFILE_UNSET,
    CommandBindingError,
    build_request,
    resolve_identifier,
)
from cu_cli_core.defaults import (
    extract_model_deployments,
    with_prebuilt_default_mappings,
)

from ..apiversion import ensure_supported
from ..client import build_client
from ..core.foundry import (
    endpoint_host,
    host_label,
    normalize_foundry_endpoint,
)
from ..core.defaults import is_defaults_not_set
from ..errors import CuCliError, friendly_errors
from ..exit_codes import GENERIC_ERROR, VALIDATION_FAILURE
from ..output import console, kv_table, result_console
from ..profile import Profile, ProfileStore
from ._command_spec import with_command_arguments
from ._help import common_commands
from ._model_setup import print_model_free_analyzers, print_model_setup_steps
from ._options import CALLING_TIME_OPTION, calling_time


def _request(spec, values: dict[str, Any]):
    try:
        return build_request(spec, values)
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc


def _resolve_foundry_account(endpoint: str) -> tuple[str, str] | None:
    az = shutil.which("az")
    if not az:
        return None
    result = subprocess.run(
        [az, "cognitiveservices", "account", "list", "-o", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        accounts = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return None

    target = endpoint.rstrip("/").lower()
    target_host = endpoint_host(endpoint)
    target_label = host_label(target_host)
    for account in accounts:
        if not isinstance(account, dict):
            continue
        properties_value = account.get("properties")
        properties: dict[str, Any] = (
            properties_value if isinstance(properties_value, dict) else {}
        )
        account_endpoint = str(
            properties.get("endpoint") or account.get("endpoint") or ""
        )
        name = str(account.get("name") or "").strip()
        resource_group = str(account.get("resourceGroup") or "").strip()
        if not name or not resource_group:
            continue
        if account_endpoint.rstrip("/").lower() == target:
            return name, resource_group
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
            if target_label and target_label in candidates:
                return name, resource_group
    return None


def _live_foundry_deployments(profile: Profile) -> dict[str, str] | None:
    if not profile.endpoint:
        console.print(
            "[yellow]warn:[/yellow] live deployments unavailable "
            "(no endpoint is saved in this profile)."
        )
        return None
    az = shutil.which("az")
    if not az:
        console.print(
            "[yellow]warn:[/yellow] live deployments unavailable "
            "(Azure CLI `az` was not found)."
        )
        return None
    resolved = _resolve_foundry_account(profile.endpoint)
    if not resolved:
        console.print(
            "[yellow]warn:[/yellow] live deployments unavailable "
            "(the Microsoft Foundry resource could not be resolved from the endpoint)."
        )
        return None
    account_name, resource_group = resolved
    result = subprocess.run(
        [
            az,
            "cognitiveservices",
            "account",
            "deployment",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            account_name,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(
            "[yellow]warn:[/yellow] live deployments unavailable "
            f"(Azure CLI returned: {(result.stderr or 'unknown error').strip()})."
        )
        return None
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CuCliError(
            "Azure CLI returned invalid JSON while listing Foundry deployments."
        ) from exc
    rows: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        deployment_name = str(item.get("name") or "").strip()
        if not deployment_name:
            continue
        properties_value = item.get("properties")
        properties: dict[str, Any] = (
            properties_value if isinstance(properties_value, dict) else {}
        )
        model_value = properties.get("model")
        model: dict[str, Any] = model_value if isinstance(model_value, dict) else {}
        sku_value = item.get("sku")
        sku: dict[str, Any] = sku_value if isinstance(sku_value, dict) else {}
        rows[f"deployment={deployment_name}"] = (
            f"model={model.get('name') or '?'}, version={model.get('version') or '?'}, "
            f"sku={sku.get('name') or '?'}, capacity={sku.get('capacity') or '?'}"
        )
    return dict(sorted(rows.items()))


@click.group(
    "profile",
    help="Manage local CU CLI settings for Microsoft Foundry resources.",
    epilog=common_commands(
        ("cu profile show", "Show the active CU CLI profile."),
        ("cu profile set endpoint URL", "Configure the default CU CLI profile."),
        ("cu profile create dev", "Create a CU CLI profile for another resource."),
        ("cu profile set-active dev", "Select a saved CU CLI profile."),
    ),
)
def profile_group() -> None:
    pass


@profile_group.command(
    "_has-values",
    hidden=True,
    epilog=common_commands(("cu profile show --name default", "Show the default profile.")),
)
@click.option("--name", "profile_name", default="default")
def cmd_has_values(profile_name: str) -> None:
    if not ProfileStore.load().get_profile(profile_name):
        raise click.exceptions.Exit(3)


@profile_group.command(
    "show",
    help=PROFILE_SHOW.help,
    epilog=common_commands(
        ("cu profile show", "Show the active CU CLI profile."),
        ("cu profile show --name dev", "Inspect a CU CLI profile without activating it."),
        ("cu profile show --deployments", "Also list live Foundry deployments."),
    ),
)
@with_command_arguments(PROFILE_SHOW)
@CALLING_TIME_OPTION
@friendly_errors
def cmd_show(
    profile_name: str | None,
    deployments: bool,
    show_calling_time: bool,
) -> None:
    request = _request(
        PROFILE_SHOW,
        {"profile_name": profile_name, "deployments": deployments},
    )
    active_name = ProfileStore.load().get_active_name()
    profile = resolve_identifier(PROFILE_SHOW.operation)(request)
    title = f"CU CLI profile: {profile.profile_name}"
    if profile_name is None:
        title += " (active)"
    else:
        console.print(f"[dim]view only; active CU CLI profile remains:[/dim] {active_name}")
    result_console.print(kv_table(profile.to_public_dict(), title=title))
    if deployments:
        with calling_time(show_calling_time) as timer:
            live = _live_foundry_deployments(profile)
        if live:
            result_console.print(kv_table(live, title="foundry deployments (live)"))
        timer.print()


@profile_group.command(
    "list",
    help=PROFILE_LIST.help,
    epilog=common_commands(("cu profile list", "List profiles and mark the active one.")),
)
@friendly_errors
def cmd_list() -> None:
    request = build_request(PROFILE_LIST, {})
    active, names = resolve_identifier(PROFILE_LIST.operation)(request)
    rows = {name: "(active)" if name == active else "" for name in names}
    result_console.print(kv_table(rows, title="cu profile list"))


@profile_group.command(
    "get",
    help=PROFILE_GET.help,
    epilog=common_commands(
        ("cu profile get endpoint", "Print the active CU CLI profile's endpoint."),
    ),
)
@with_command_arguments(PROFILE_GET)
@friendly_errors
def cmd_get(
    profile_key: str | None,
    positional_profile_key: str | None,
    profile_name: str | None,
) -> None:
    request = _request(PROFILE_GET, locals())
    value = resolve_identifier(PROFILE_GET.operation)(request)
    if request.key == "api_key" and value:
        value = "***redacted***"
    click.echo("" if value is None else str(value))


@profile_group.command(
    "set",
    help=PROFILE_SET.help,
    epilog=common_commands(
        ("cu profile set endpoint URL", "Save the default CU CLI profile endpoint."),
        (
            "cu profile set auth_mode login --name dev",
            "Use Azure login authentication for a named CU CLI profile.",
        ),
        (
            "cu profile set model_deployments.gpt-5.2 DEPLOYMENT",
            "Save one model deployment mapping.",
        ),
    ),
)
@with_command_arguments(PROFILE_SET)
@friendly_errors
def cmd_set(
    profile_key: str | None,
    positional_profile_key: str | None,
    profile_value: str | None,
    positional_profile_value: str | None,
    profile_name: str | None,
) -> None:
    request = _request(PROFILE_SET, locals())
    value = request.value
    if request.key == "endpoint":
        value = normalize_foundry_endpoint(value)
    elif request.key == "api_version":
        value = ensure_supported(value)
    request = type(request)(key=request.key, value=value, name=request.name)
    path = resolve_identifier(PROFILE_SET.operation)(request)
    target = request.name or ProfileStore.load().get_active_name()
    console.print(
        f"[green]ok[/green] saved {request.key} for CU CLI profile '{target}' -> {path}"
    )
    if request.key == "endpoint":
        console.print(
            "[dim]next:[/dim] authenticate if needed, then run "
            "`cu profile sync-defaults` to import Content Understanding defaults."
        )


@profile_group.command(
    "unset",
    help=PROFILE_UNSET.help,
    epilog=common_commands(
        ("cu profile unset api_key", "Remove a saved key and return to login auth."),
    ),
)
@with_command_arguments(PROFILE_UNSET)
@friendly_errors
def cmd_unset(
    profile_key: str | None,
    positional_profile_key: str | None,
    profile_name: str | None,
) -> None:
    request = _request(PROFILE_UNSET, locals())
    path = resolve_identifier(PROFILE_UNSET.operation)(request)
    target = request.name or ProfileStore.load().get_active_name()
    console.print(
        f"[green]ok[/green] unset {request.key} for CU CLI profile '{target}' -> {path}"
    )


@profile_group.command(
    "create",
    help=PROFILE_CREATE.help,
    epilog=common_commands(
        ("cu profile create dev", "Create an empty named profile."),
    ),
)
@with_command_arguments(PROFILE_CREATE)
@friendly_errors
def cmd_create(
    profile_name: str | None,
    positional_profile_name: str | None,
) -> None:
    request = _request(PROFILE_CREATE, locals())
    path = resolve_identifier(PROFILE_CREATE.operation)(request)
    console.print(f"[green]ok[/green] created CU CLI profile '{request.name}' -> {path}")


@profile_group.command(
    "delete",
    help=PROFILE_DELETE.help,
    epilog=common_commands(
        ("cu profile delete dev", "Delete an inactive named profile."),
    ),
)
@with_command_arguments(PROFILE_DELETE)
@friendly_errors
def cmd_delete(
    profile_name: str | None,
    positional_profile_name: str | None,
) -> None:
    request = _request(PROFILE_DELETE, locals())
    path = resolve_identifier(PROFILE_DELETE.operation)(request)
    console.print(f"[green]ok[/green] deleted CU CLI profile '{request.name}' -> {path}")


@profile_group.command(
    "copy",
    help=PROFILE_COPY.help,
    epilog=common_commands(
        ("cu profile copy dev test", "Copy one profile to a new name."),
        (
            "cu profile copy --source dev --destination test",
            "Copy using canonical named selectors.",
        ),
        (
            "cu profile copy --destination test",
            "Copy the active CU CLI profile.",
        ),
    ),
)
@with_command_arguments(PROFILE_COPY)
@friendly_errors
def cmd_copy(
    source_profile: str | None,
    destination_profile: str | None,
    positional_source_profile: str | None,
    positional_destination_profile: str | None,
) -> None:
    request = _request(PROFILE_COPY, locals())
    path, source = resolve_identifier(PROFILE_COPY.operation)(request)
    console.print(
        f"[green]ok[/green] copied CU CLI profile '{source}' -> "
        f"'{request.destination}' -> {path}"
    )


@profile_group.command(
    "rename",
    help=PROFILE_RENAME.help,
    epilog=common_commands(
        ("cu profile rename dev prod", "Rename a saved CU CLI profile."),
    ),
)
@with_command_arguments(PROFILE_RENAME)
@friendly_errors
def cmd_rename(
    source_profile: str | None,
    destination_profile: str | None,
    positional_source_profile: str | None,
    positional_destination_profile: str | None,
) -> None:
    request = _request(PROFILE_RENAME, locals())
    path = resolve_identifier(PROFILE_RENAME.operation)(request)
    console.print(
        f"[green]ok[/green] renamed CU CLI profile '{request.source}' -> "
        f"'{request.destination}' -> {path}"
    )


@profile_group.command(
    "set-active",
    help=PROFILE_SET_ACTIVE.help,
    epilog=common_commands(
        ("cu profile set-active dev", "Select a saved CU CLI profile."),
    ),
)
@with_command_arguments(PROFILE_SET_ACTIVE)
@friendly_errors
def cmd_set_active(
    profile_name: str | None,
    positional_profile_name: str | None,
) -> None:
    request = _request(PROFILE_SET_ACTIVE, locals())
    path = resolve_identifier(PROFILE_SET_ACTIVE.operation)(request)
    console.print(f"[green]ok[/green] active CU CLI profile -> {request.name} -> {path}")


@profile_group.command(
    "sync-defaults",
    help=PROFILE_SYNC_DEFAULTS.help,
    epilog=common_commands(
        (
            "cu profile sync-defaults --name dev",
            "Refresh model mappings using the profile's saved endpoint.",
        ),
    ),
)
@with_command_arguments(PROFILE_SYNC_DEFAULTS)
@click.option("--auth-mode", type=click.Choice(["login", "key"]), default=None)
@click.option("--api-key", default=None, help="Override the profile API key.")
@CALLING_TIME_OPTION
@friendly_errors
def cmd_sync_defaults(
    profile_name: str | None,
    auth_mode: str | None,
    api_key: str | None,
    show_calling_time: bool,
) -> None:
    request = _request(PROFILE_SYNC_DEFAULTS, {"profile_name": profile_name})
    saved = Profile.load_saved(profile_name=request.name)
    if not saved.endpoint:
        raise CuCliError(
            f"no endpoint is saved in CU CLI profile '{saved.profile_name}'.",
            hint="set it with `cu profile set endpoint URL` before synchronizing.",
        )
    effective = Profile.load(profile_name=request.name)
    effective.endpoint = saved.endpoint
    with calling_time(show_calling_time) as timer:
        try:
            defaults = build_client(
                effective,
                api_key_override=api_key,
                auth_mode_override=auth_mode,
            ).get_defaults()
        except HttpResponseError as exc:
            if not is_defaults_not_set(exc):
                raise
            _print_sync_defaults_not_configured(saved)
        models = with_prebuilt_default_mappings(
            extract_model_deployments(defaults)
        )
        if not models:
            _print_sync_defaults_not_configured(saved)
        path, target = resolve_identifier(PROFILE_SYNC_DEFAULTS.operation)(
            request,
            models,
        )
    console.print(
        f"[green]ok[/green] synchronized {len(models)} model mapping(s) "
        f"for CU CLI profile '{target}' -> {path}"
    )
    timer.print()


def _print_sync_defaults_not_configured(profile: Profile) -> None:
    console.print(
        "[yellow]Content Understanding defaults are not configured on this "
        "resource.[/yellow]\n\n"
        f"No changes were made to CU CLI profile '{profile.profile_name}'."
    )
    print_model_free_analyzers()
    print_model_setup_steps(
        profile.endpoint or "",
        profile_name=profile.profile_name,
        heading="To use analyzers that require generative AI:",
    )
    raise Exit(GENERIC_ERROR)
