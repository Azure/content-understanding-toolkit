"""``cu defaults`` — read and update Content Understanding defaults.

Wraps the CU SDK's ``get_defaults`` and ``update_defaults`` operations so users
can manage resource-level model deployment mappings from the CLI.
"""

from __future__ import annotations

import rich_click as click

from cu_cli_core.command_spec import (
    DEFAULTS_SET,
    DEFAULTS_SHOW,
    CommandBindingError,
    build_request,
    resolve_identifier,
)
from ..client import build_client, resolve
from ..profile import Profile
from cu_cli_core.defaults import (
    extract_model_deployments as _extract_model_deployments,
    parse_model_kv as _parse_model_kv,
)
from ..errors import CuCliError, friendly_errors
from ..output import console, dump_json, dump_markdown_kv
from ._help import common_commands
from ._command_spec import with_command_arguments
from ._options import calling_time, print_runtime_context, with_auth_options


def _client(profile: Profile, endpoint, api_key, api_version, entra, show_runtime_context):
    auth = resolve(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )
    if show_runtime_context:
        print_runtime_context(auth, profile)
    return profile, build_client(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )




@click.group(
    "defaults",
    help="Show or configure Content Understanding defaults (model-to-deployment mappings).",
    epilog="[bold cyan]Common commands:[/bold cyan]\n\n"
           "[bold green]cu defaults show[/bold green]\n\n"
           "[white]\u00a0\u00a0Show Content Understanding model-to-deployment mappings.[/white]\n\n"
           "[bold green]cu defaults set[/bold green] "
           "[bold cyan]--from-profile[/bold cyan]\n\n"
           "[white]\u00a0\u00a0Apply model mappings from the current profile as defaults.[/white]",
)
def defaults_group() -> None:
    pass


@defaults_group.command(
    "show",
    help=DEFAULTS_SHOW.help,
    epilog=common_commands(
        ("cu defaults show", "Print model deployment mappings as JSON."),
        ("cu defaults show --table", "Print model mappings as a readable table."),
    ),
)
@with_command_arguments(DEFAULTS_SHOW)
@with_auth_options
@friendly_errors
def cmd_show(
    table_output, endpoint, api_key, api_version, entra, profile_name, show_runtime_context,
    show_calling_time
) -> None:
    try:
        build_request(DEFAULTS_SHOW, {"table_output": table_output})
    except CommandBindingError as exc:
        raise CuCliError(str(exc)) from exc
    profile = Profile.load(profile_name=profile_name)
    _, client = _client(profile, endpoint, api_key, api_version, entra, show_runtime_context)
    with calling_time(show_calling_time) as calling_timer:
        defaults = resolve_identifier(DEFAULTS_SHOW.operation)(client)

    if not table_output:
        dump_json(defaults)
        calling_timer.print()
        return

    mappings = _extract_model_deployments(defaults)
    if mappings:
        dump_markdown_kv(mappings, headers=("Model", "Deployment"))
        calling_timer.print()
        return
    console.print("[yellow]Content Understanding defaults are not configured.[/yellow]")
    calling_timer.print()


@defaults_group.command(
    "set",
    help=DEFAULTS_SET.help,
    epilog=common_commands(
        ("cu defaults set --from-profile", "Push mappings from the effective profile."),
        (
            "cu defaults set --model MODEL=DEPLOYMENT",
            "Add or update one model-to-deployment mapping.",
        ),
    ),
)
@with_command_arguments(DEFAULTS_SET)
@with_auth_options
@friendly_errors
def cmd_set(
    model_kv, from_profile, replace, json_output,
    endpoint, api_key, api_version, entra, profile_name,
    show_runtime_context, show_calling_time
) -> None:
    try:
        request = build_request(
            DEFAULTS_SET,
            {
                "model_kv": model_kv,
                "from_profile": from_profile,
                "replace": replace,
                "json_output": json_output,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc)) from exc
    profile = Profile.load(profile_name=profile_name)
    desired: dict[str, str] = {}
    if request.from_profile:
        desired.update({str(k): str(v) for k, v in profile.model_deployments.items()})
    desired.update(_parse_model_kv(request.models))

    if not desired:
        raise CuCliError(
            "no model deployment mappings provided.",
            hint="pass `--from-profile` to use the effective profile mappings "
                 "or pass `--model MODEL=DEPLOYMENT`.",
        )

    _, client = _client(
        profile, endpoint, api_key, api_version, entra, show_runtime_context
    )

    with calling_time(show_calling_time) as calling_timer:
        updated, merged = resolve_identifier(DEFAULTS_SET.operation)(
            client,
            desired,
            replace=request.replace,
        )

    if json_output:
        dump_json(updated)
        calling_timer.print()
        return

    console.print(
        f"[green]ok[/green] updated Content Understanding defaults "
        f"with {len(merged)} mapping(s)."
    )
    dump_markdown_kv(merged, headers=("Model", "Deployment"))
    calling_timer.print()
