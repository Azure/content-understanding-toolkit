# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu analyzer`` — manage and author custom analyzers.

MVP command surface: ``list``, ``show``, ``create``, ``delete``,
``test``, ``validate``, and ``schema create``. The ``validate`` and default
``schema create`` paths are **LLM-free and offline** — they give coding
agents a deterministic author->validate loop with no service round-trips.

Exit-code convention: ``validate`` exits ``2`` on a schema error so agents can
branch on structural validity without parsing prose.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

import rich_click as click
from rich.markup import escape as _esc
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..apiversion import API_VERSION_HELP, resolve_api_version
from ..client import build_client, resolve
from cu_cli_core.command_spec import (
    ANALYZER_COPY,
    ANALYZER_CREATE,
    ANALYZER_DELETE,
    ANALYZER_LIST,
    ANALYZER_SCHEMA_CREATE,
    ANALYZER_SHOW,
    ANALYZER_TEST,
    ANALYZER_VALIDATE,
    CommandBindingError,
    build_request,
    resolve_identifier,
)
from ..profile import Profile
from ..core import analyzers as _analyzers
from cu_cli_core.schema import (
    FIELD_SCHEMA_SUGGEST_ANALYZER_ID,
    MODALITY_BASE,
    starter_schema,
    template_completion_model,
    validate_document_sample,
)
from ..errors import CuCliError, friendly_errors
from ..exit_codes import GENERIC_ERROR, SUCCESS, VALIDATION_FAILURE
from ..output import analyzer_table, console, dump_json
from cu_cli_core.schema_validation import (
    custom_analyzer_id_error,
    parse_and_validate,
    schema_pinned_version,
)
from ._options import calling_time, print_runtime_context, with_auth_options
from ._command_spec import with_command_arguments
from ._help import common_commands

# Backward-compatible aliases: schema authoring logic now lives in
# ``cu_cli_core.schema``; these names are kept for existing integrations and tests.
_MODALITY_BASE = MODALITY_BASE
_FIELD_SCHEMA_SUGGEST_ANALYZER_ID = FIELD_SCHEMA_SUGGEST_ANALYZER_ID
_starter_schema = starter_schema
_template_completion_model = template_completion_model


def _non_directory_parent(path: Path) -> Path | None:
    parent = path.parent
    while not parent.exists() and not parent.is_symlink():
        if parent == parent.parent:
            return None
        parent = parent.parent
    return None if parent.is_dir() else parent


def _require_output_available(
    path: Path | None,
    *,
    force: bool,
    description: str,
) -> None:
    if path is None:
        return
    blocking_parent = _non_directory_parent(path)
    if blocking_parent is not None:
        raise CuCliError(
            f"{description} parent path is not a directory: {blocking_parent}",
            hint="choose another output path or replace the parent file with a directory.",
        )
    if force:
        return
    if path.exists() or path.is_symlink():
        raise CuCliError(
            f"{description} already exists: {path}",
            hint="choose another path or pass --force to overwrite it.",
        )


def _write_json_output(
    payload: Any,
    path: Path | None,
    *,
    force: bool,
    description: str,
) -> None:
    try:
        dump_json(payload, out=path, overwrite=force)
    except FileExistsError as exc:
        blocking_parent = _non_directory_parent(path) if path is not None else None
        if blocking_parent is not None:
            raise CuCliError(
                f"{description} parent path is not a directory: {blocking_parent}",
                hint="choose another output path or replace the parent file with a directory.",
            ) from exc
        raise CuCliError(
            f"{description} already exists: {path}",
            hint="choose another path or pass --force to overwrite it.",
        ) from exc


def _extract_fields_from_result(result: Any) -> dict[str, dict[str, Any]]:
    from cu_cli_core.operations.analysis import extract_fields_from_result

    return extract_fields_from_result(result)


def _test_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    from cu_cli_core.operations.analysis import analyzer_test_summary

    return analyzer_test_summary(samples)


def _client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context):
    profile = Profile.load(profile_name=profile_name)
    auth = resolve(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )
    if show_runtime_context:
        print_runtime_context(auth, profile)
    return build_client(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )


def _require_custom_analyzer_id(analyzer_id: str) -> None:
    error = custom_analyzer_id_error(analyzer_id)
    if error:
        raise CuCliError(
            f"invalid custom analyzer ID '{analyzer_id}'.",
            hint=error,
        )


@click.group("analyzer",
               help="Manage analyzers, which define how Content Understanding processes files. "
               "List, show, create, copy, delete, and test analyzers, or create and validate "
               "local analyzer schemas.",
             epilog="[bold cyan]Common commands:[/bold cyan]\n\n"
                    "[bold green]cu analyzer list[/bold green]\n\n"
                    "[white]\u00a0\u00a0List available analyzers.[/white]\n\n"
                    "[bold green]cu analyzer schema create[/bold green] "
                    "[bold cyan]--from-sample[/bold cyan] [bold yellow]SAMPLE_FILE[/bold yellow]\n\n"
                    "[white]\u00a0\u00a0Create a custom schema from one document sample.[/white]\n\n"
                    "[bold green]cu analyzer create[/bold green] [bold yellow]NAME[/bold yellow] "
                    "[bold cyan]--schema[/bold cyan] [bold yellow]SCHEMA.json[/bold yellow]\n\n"
                    "[white]\u00a0\u00a0Create a custom analyzer from a schema.[/white]")
def analyzer_group() -> None:
    pass


# --- CRUD ------------------------------------------------------------------


@analyzer_group.command(
    "list",
    help="List analyzers in the Microsoft Foundry resource.",
    epilog=common_commands(
        ("cu analyzer list", "List all analyzers as a table."),
        ("cu analyzer list --kind custom", "List only custom analyzers."),
        ("cu analyzer list --json", "List analyzers as machine-readable JSON."),
    ),
)
@with_command_arguments(ANALYZER_LIST)
@with_auth_options
@friendly_errors
def cmd_list(
    kind, sort_by, json_output, endpoint, api_key, api_version, entra, profile_name,
    show_runtime_context, show_calling_time
) -> None:
    request = build_request(
        ANALYZER_LIST,
        {"kind": kind, "sort_by": sort_by, "json_output": json_output},
    )
    client = _client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context)
    with calling_time(show_calling_time) as calling_timer:
        items = resolve_identifier(ANALYZER_LIST.operation)(
            client,
            kind=request.kind,
            sort_by=request.sort_by,
        )
    if json_output:
        dump_json([a.as_dict() for a in items])
    else:
        console.print(analyzer_table(items))
        console.print(f"\n[dim]{len(items)} analyzer(s)[/dim]")
    calling_timer.print()


@analyzer_group.command(
    "show",
    help=ANALYZER_SHOW.help,
    epilog=common_commands(
        ("cu analyzer show ANALYZER_NAME", "Print one analyzer definition as JSON."),
    ),
)
@with_command_arguments(ANALYZER_SHOW)
@with_auth_options
@friendly_errors
def cmd_show(
    positional_analyzer_name, analyzer_name, endpoint, api_key, api_version, entra,
    profile_name, show_runtime_context, show_calling_time
) -> None:
    try:
        request = build_request(
            ANALYZER_SHOW,
            {
                "positional_analyzer_name": positional_analyzer_name,
                "analyzer_name": analyzer_name,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    client = _client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context)
    with calling_time(show_calling_time) as calling_timer:
        analyzer = resolve_identifier(ANALYZER_SHOW.operation)(client, request.name)
    dump_json(analyzer.as_dict())
    calling_timer.print()


@analyzer_group.command(
    "create",
    help=ANALYZER_CREATE.help,
    epilog=common_commands(
        (
            "cu analyzer create ANALYZER_NAME --schema SCHEMA.json",
            "Create an analyzer using the standalone positional shortcut.",
        ),
        (
            "cu analyzer create --name ANALYZER_NAME --schema SCHEMA.json",
            "Create an analyzer using the canonical named selector.",
        ),
    ),
)
@with_command_arguments(ANALYZER_CREATE)
@with_auth_options
@friendly_errors
def cmd_create(
    positional_analyzer_name, analyzer_name, schema_path,
    endpoint, api_key, api_version, entra, profile_name,
    show_runtime_context, show_calling_time
) -> None:
    try:
        request = build_request(
            ANALYZER_CREATE,
            {
                "positional_analyzer_name": positional_analyzer_name,
                "analyzer_name": analyzer_name,
                "schema_path": schema_path,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    parse_result, body = parse_and_validate(request.schema.read_text(encoding="utf-8"))
    if body is None:
        message = parse_result.errors[0].msg
        if message.startswith("file "):
            message = f"schema {message}"
        raise CuCliError(message)
    if parse_result.errors:
        finding = parse_result.errors[0]
        raise CuCliError(
            f"invalid schema at {finding.path}: {finding.msg}",
            hint=f"run `cu analyzer validate {request.schema}` for all validation findings.",
        )
    aid = request.name
    _require_custom_analyzer_id(aid)
    profile = Profile.load(profile_name=profile_name)
    resolved_api_version = resolve_api_version(
        flag=api_version,
        schema_pinned=schema_pinned_version(body),
        profile=profile.api_version,
    )
    client = _client(
        endpoint,
        api_key,
        resolved_api_version,
        entra,
        profile_name,
        show_runtime_context,
    )
    with calling_time(show_calling_time) as calling_timer:
        result = resolve_identifier(ANALYZER_CREATE.operation)(client, aid, body)
    final_id = getattr(result, "analyzer_id", aid)
    console.print(f"[green]ok[/green] created analyzer: {final_id}")
    calling_timer.print()


@analyzer_group.command(
    "delete",
    help="Delete an analyzer.",
    epilog=common_commands(
        ("cu analyzer delete ANALYZER_NAME", "Confirm and delete a custom analyzer."),
        ("cu analyzer delete -n ANALYZER_NAME --yes", "Delete without confirmation."),
    ),
)
@with_command_arguments(ANALYZER_DELETE)
@with_auth_options
@friendly_errors
def cmd_delete(
    positional_analyzer_name, analyzer_name, yes,
    endpoint, api_key, api_version, entra, profile_name,
    show_runtime_context, show_calling_time
) -> None:
    try:
        request = build_request(
            ANALYZER_DELETE,
            {
                "positional_analyzer_name": positional_analyzer_name,
                "analyzer_name": analyzer_name,
                "yes": yes,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    if not request.yes:
        click.confirm(f"Delete analyzer '{request.name}'?", abort=True)
    client = _client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context)
    with calling_time(show_calling_time) as calling_timer:
        resolve_identifier(ANALYZER_DELETE.operation)(client, request.name)
    console.print(f"[green]ok[/green] deleted {request.name}")
    calling_timer.print()


class _CopyProgress:
    """Render live copy phases in a terminal and durable lines elsewhere."""

    def __init__(self, initial_message: str) -> None:
        self._message = initial_message
        self._progress: Progress | None = None
        self._task_id: Any = None

    def start(self) -> None:
        if console.is_terminal:
            self._progress = Progress(
                SpinnerColumn(style="cyan"),
                TextColumn("{task.description}", markup=False),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            )
            self._task_id = self._progress.add_task(self._message, total=None)
            self._progress.start()
        else:
            self._print_line(self._message)

    def update(self, message: str) -> None:
        self._message = message
        if self._progress is not None:
            self._progress.update(self._task_id, description=message)
        else:
            self._print_line(message)

    def stop(self) -> None:
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
            self._task_id = None

    @staticmethod
    def _print_line(message: str) -> None:
        console.print(f"[dim]…[/dim] {_esc(message)}")


@analyzer_group.command(
    "copy",
    help=ANALYZER_COPY.help,
    epilog=common_commands(
        (
            "cu analyzer copy SOURCE DESTINATION",
            "Copy within the active resource.",
        ),
        (
            "cu analyzer copy --source SOURCE --destination DESTINATION "
            "--source-profile dev --destination-profile prod",
            "Copy between resources represented by named profiles.",
        ),
        (
            "cu analyzer copy SOURCE DESTINATION "
            "--source-resource RESOURCE --destination-resource RESOURCE",
            "Resolve source and destination resources directly from Azure.",
        ),
    ),
)
@with_command_arguments(ANALYZER_COPY)
@with_auth_options
@friendly_errors
def cmd_copy(
    positional_source, positional_destination, named_source, named_destination,
    source_resource, source_subscription, source_resource_group, source_profile,
    destination_resource, destination_subscription, destination_resource_group,
    destination_profile,
    endpoint, api_key, api_version, entra, profile_name,
    show_runtime_context, show_calling_time,
) -> None:
    """Copy an analyzer within one resource or across two.

    **Same-resource** (normal path):
    ``cu analyzer copy SOURCE DESTINATION`` — uses the active or
    ``--profile``-selected CU profile for both sides and performs one
    ``begin_copy_analyzer`` call.

    Before copying, the CLI resolves each selected endpoint to a canonical
    Azure resource (ARM ID, region, endpoint) in the explicitly selected or
    active Azure CLI subscription. For a **cross-resource** copy, it then
    automatically calls
    ``grant_copy_authorization`` on the source and ``begin_copy_analyzer`` on
    the destination with source ARM ID + region. The authorization record is
    destination-scoped, time-limited, and never printed or persisted.

    The signed-in Azure identity needs **Reader** on each selected
    subscription/resource group for management-plane discovery. Login-authenticated
    copies also need **Cognitive Services User** on both CU accounts.

    Content Understanding has no in-place replace — an existing destination ID
    stops the copy with a hint to delete-and-re-copy or pick a versioned ID.
    Recursive copy of classification/segmentation dependencies is out of
    scope; if the source references custom analyzers missing on the destination,
    the CLI fails **before** the parent copy and prints the required IDs plus
    ``cu analyzer copy`` commands to run first.
    """
    try:
        request = build_request(
            ANALYZER_COPY,
            {
                "positional_source": positional_source,
                "positional_destination": positional_destination,
                "named_source": named_source,
                "named_destination": named_destination,
                "source_resource": source_resource,
                "source_subscription": source_subscription,
                "source_resource_group": source_resource_group,
                "source_profile": source_profile,
                "destination_resource": destination_resource,
                "destination_subscription": destination_subscription,
                "destination_resource_group": destination_resource_group,
                "destination_profile": destination_profile,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    source_analyzer_id = request.source
    destination_analyzer_id = request.destination

    # Validate analyzer IDs before any auth or service call. This catches
    #     the common typo of passing a schema path or URL where an ID was
    #     expected, without burning a management-plane discovery + Entra token
    #     exchange first.
    _validate_analyzer_id(source_analyzer_id, role="source")
    _validate_analyzer_id(destination_analyzer_id, role="destination")

    # --endpoint composes with the active/named-profile path only. Combining it
    # with direct resource selectors is ambiguous because discovery resolves the
    # endpoint from the Azure management plane.
    if endpoint and (source_resource or destination_resource or destination_profile):
        raise CuCliError(
            "--endpoint cannot be combined with --source-resource, "
            "--destination-resource, or --destination-profile.",
            hint="resource selectors resolve their own endpoints, and one endpoint "
                 "override cannot safely represent two named resources. Drop "
                 "--endpoint, or use it only when the destination defaults to the source.",
        )
    if api_key and (source_resource or destination_resource or destination_profile):
        raise CuCliError(
            "--api-key cannot be combined with --source-resource, "
            "--destination-resource, or --destination-profile.",
            hint="direct Azure resource selectors always use the signed-in Entra "
                 "identity, and one account-scoped key cannot safely authenticate "
                 "two named resources. Store side-specific keys in the source and "
                 "destination profiles instead.",
        )
    # Resource-group narrowing applies only to direct selectors. Subscription
    # selection also composes with profile-backed sides and is authoritative
    # for endpoint discovery.
    if not source_resource and source_resource_group:
        raise CuCliError(
            "--source-resource-group requires --source-resource.",
            hint="use --source-subscription to scope an active or named source profile.",
        )
    if not destination_resource and destination_resource_group:
        raise CuCliError(
            "--destination-resource-group requires --destination-resource.",
            hint="use --destination-subscription to scope a named destination profile.",
        )
    if destination_subscription and not (destination_resource or destination_profile):
        raise CuCliError(
            "--destination-subscription requires --destination-resource "
            "or --destination-profile.",
            hint="select the destination resource or named profile to scope.",
        )

    # Fast-path same-ID guard before anything expensive. Selector/profile
    #    paths need final resolved-resource comparison, so they are checked
    #    again below after ``cross_resource`` is known.
    if source_analyzer_id == destination_analyzer_id and not (
        source_resource or source_profile or destination_resource or destination_profile
    ):
        _reject_identical_ids_same_resource(source_analyzer_id, destination_analyzer_id)

    # Resolve source and destination contexts.
    copy_progress = _CopyProgress(
        f"Resolving source and destination resources for analyzer copy "
        f"'{source_analyzer_id}' -> '{destination_analyzer_id}'..."
    )
    copy_progress.start()
    ctx = click.get_current_context()
    if ctx is not None:
        ctx.call_on_close(copy_progress.stop)
    src_ctx = _resolve_side(
        selector=source_resource,
        sub=source_subscription,
        rg=source_resource_group,
        profile_name=source_profile,
        # Fall through to the standard top-level auth options only for the source.
        fallback_profile=profile_name,
        endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        entra=entra,
        side="source",
    )
    src_ctx = _ensure_arm_metadata(
        src_ctx,
        side_flag="--source-resource",
        subscription_id=source_subscription,
    )
    destination_ctx = _resolve_side(
        selector=destination_resource,
        sub=destination_subscription,
        rg=destination_resource_group,
        profile_name=destination_profile,
        # If the user set no destination selector, it defaults to the resolved source
        # context (matches the "same resource, distinct IDs" mainline).
        fallback_profile=profile_name if (destination_resource or destination_profile) else None,
        endpoint=endpoint if (destination_resource or destination_profile) else None,
        api_key=api_key if (destination_resource or destination_profile) else None,
        api_version=api_version if (destination_resource or destination_profile) else None,
        entra=entra if (destination_resource or destination_profile) else False,
        side="destination",
        default_from=src_ctx,
    )
    destination_ctx = _ensure_arm_metadata(
        destination_ctx,
        side_flag="--destination-resource",
        subscription_id=destination_subscription,
    )

    # Both sides now carry canonical ARM metadata, so the copy mode is based on
    # resource identity rather than endpoint spelling or profile provenance.
    cross_resource = _is_cross_resource(src_ctx, destination_ctx)

    # Selector presence alone does not prove a cross-resource copy: a source-only
    # resource selector defaults the destination to that source, and two named profiles may
    # resolve to the same account. Reject identical IDs after final resolution
    # whenever the effective mode is same-resource.
    if not cross_resource:
        _reject_identical_ids_same_resource(source_analyzer_id, destination_analyzer_id)
    elif src_ctx.api_version != destination_ctx.api_version:
        raise CuCliError(
            "source and destination API versions must match for analyzer copy: "
            f"source={src_ctx.api_version}, destination={destination_ctx.api_version}.",
            hint="select profiles with the same API version or pass --api-version "
                 "to use one version for both sides, then retry.",
        )

    # --info: show resolved source/destination before any data-plane call.
    if show_runtime_context:
        _print_copy_runtime_context(src_ctx, destination_ctx, cross_resource=cross_resource)

    # Dependency preflight for cross-resource copies. Same-resource copies
    #    inherit the source resource's own catalog, so nothing to check.
    source_analyzer = None
    if cross_resource:
        copy_progress.update("Checking source analyzer and destination dependencies...")
        source_analyzer = _analyzers.get_copy_source_analyzer(
            src_ctx.client,
            source_analyzer_id,
        )
        deps = _analyzers.collect_custom_dependencies(source_analyzer)
        if deps:
            missing = _analyzers.preflight_dependencies_on_target(destination_ctx.client, deps)
            if missing:
                cmds = "\n".join(
                    "  " + _dependency_copy_cli_command(
                        d,
                        src_ctx,
                        destination_ctx,
                        source_subscription=source_subscription,
                        destination_subscription=destination_subscription,
                        api_version=api_version,
                    )
                    for d in missing
                )
                raise CuCliError(
                    f"source analyzer '{source_analyzer_id}' references custom analyzers "
                    f"that are missing on the destination resource: {', '.join(missing)}.",
                    hint="Content Understanding does not recursively copy classifier "
                         "sub-analyzers. Copy each dependency first, then re-run:\n" + cmds,
                )

    # Perform the copy.
    copy_progress.update("Checking source and destination analyzers...")
    with calling_time(show_calling_time) as calling_timer:
        resolve_identifier(ANALYZER_COPY.operation)(
            src_ctx.client,
            source_analyzer_id,
            destination_analyzer_id,
            target_client=(destination_ctx.client if cross_resource else None),
            source_azure_resource_id=(src_ctx.resource.arm_id if cross_resource and src_ctx.resource else None),
            source_region=(src_ctx.resource.region if cross_resource and src_ctx.resource else None),
            target_azure_resource_id=(
                destination_ctx.resource.arm_id
                if cross_resource and destination_ctx.resource
                else None
            ),
            target_region=(
                destination_ctx.resource.region
                if cross_resource and destination_ctx.resource
                else None
            ),
            progress=copy_progress.update,
            source_analyzer=source_analyzer,
            target_cli_options=_target_cli_options(destination_ctx),
        )
    copy_progress.stop()
    if cross_resource:
        console.print(
            f"[green]ok[/green] copied '{source_analyzer_id}' -> '{destination_analyzer_id}' "
            f"on destination [cyan]"
            f"{destination_ctx.resource.account_name if destination_ctx.resource else destination_ctx.endpoint}"
            f"[/cyan]"
        )
    else:
        console.print(
            f"[green]ok[/green] copied '{source_analyzer_id}' -> '{destination_analyzer_id}'"
        )
    show_command = _target_cli_command("show", destination_analyzer_id, destination_ctx)
    console.print(f"[dim]hint:[/dim] inspect the copy with [cyan]{show_command}[/cyan]")
    calling_timer.print()


# --- cmd_copy internals ------------------------------------------------------


class _SideCtx:
    """Resolved copy side: an SDK client plus optional Azure resource metadata.

    - ``client``: the CU SDK client bound to this side's endpoint + auth.
    - ``endpoint``: the resolved endpoint URL (for display when no ARM resource
      was involved).
    - ``resource``: the :class:`ResolvedResource` when the side came from a
      direct resource selector; ``None`` when it came from a CU profile
      (no ARM-ID / region available without discovery, and none is needed for
      a same-resource copy).
    - ``source_label``: short human string for progress lines and --info.
    - ``api_version``: the effective request API version for this side.
    """

    __slots__ = (
        "client",
        "endpoint",
        "resource",
        "source_label",
        "profile_name",
        "force_entra",
        "api_version",
    )

    def __init__(
        self,
        client: Any,
        endpoint: str,
        resource: Any,
        source_label: str,
        *,
        profile_name: str | None = None,
        force_entra: bool | str = False,
        api_version: str,
    ) -> None:
        self.client = client
        self.endpoint = endpoint
        self.resource = resource
        self.source_label = source_label
        self.profile_name = profile_name
        self.force_entra = force_entra
        self.api_version = api_version

# Content Understanding 2025-11-01 REST contract:
# ``^[a-zA-Z0-9._-]{1,64}$``. Every allowed character is legal in the first
# position too; Click users can pass a leading-hyphen positional after ``--``.
_ANALYZER_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _validate_analyzer_id(aid: str | None, *, role: str) -> None:
    """Fail fast on obviously-invalid analyzer IDs before any auth or service call.

    Catches the common typo case of passing a schema JSON path (contains ``/``)
    or a URL where an ID was expected — the service would reject with 400, but
    not before the CLI has already run management-plane discovery and Entra
    token exchange. Empty strings are rejected too; Click's positional argument
    parsing shouldn't yield them, but a shell script passing ``""`` explicitly
    would otherwise reach the service.
    """
    if not aid:
        raise CuCliError(
            f"{role} analyzer ID is empty.",
            hint="pass a valid analyzer ID (1-64 chars, alphanumeric + underscore/dot/hyphen).",
        )
    if not _ANALYZER_ID_RE.fullmatch(aid):
        raise CuCliError(
            f"{role} analyzer ID {aid!r} is not a valid Content Understanding analyzer ID.",
            hint="use 1-64 alphanumeric, underscore, dot, or hyphen characters "
                 "(regex: [A-Za-z0-9._-]{1,64}). "
                 "If you meant a schema file, pass it to `cu analyzer create --schema` instead.",
        )


def _reject_identical_ids_same_resource(
    source_analyzer_id: str,
    destination_analyzer_id: str,
) -> None:
    """Reject an effective same-resource copy whose object names match."""
    if source_analyzer_id != destination_analyzer_id:
        return
    raise CuCliError(
        f"source and destination analyzers are identical ('{source_analyzer_id}'); "
        "copy is a no-op on the same resource.",
        hint="pick a distinct DESTINATION (for example append '_v2' "
             "for a versioned copy), or select a destination that resolves to a "
             "different Azure resource.",
    )


def _resolve_side(
    *,
    selector: str | None,
    sub: str | None,
    rg: str | None,
    profile_name: str | None,
    fallback_profile: str | None,
    endpoint: str | None,
    api_key: str | None,
    api_version: str | None,
    entra: bool,
    side: str,
    default_from: _SideCtx | None = None,
) -> _SideCtx:
    """Resolve one side (source or destination) to a :class:`_SideCtx`.

    Precedence (highest to lowest):
      1. ``selector`` (a side-specific resource option) → Azure management discovery.
      2. ``profile_name`` (a side-specific profile option) → named CU profile.
      3. ``fallback_profile`` (top-level ``--profile``) → named CU profile.
      4. active CU profile.
    For the destination side only, when no destination selector or profile is provided,
    all, we return ``default_from`` so the same client is reused (guarantees a
    same-resource copy with one SDK call).
    """
    if selector:
        from ..core.azure_resources import resolve_resource
        resolved = resolve_resource(selector, subscription_id=sub, resource_group=rg)
        resolved_api_version = _resolve_copy_api_version(
            profile_name=None,
            api_version=api_version,
        )
        client = _client_from_resource(resolved, api_version=resolved_api_version)
        return _SideCtx(client=client, endpoint=resolved.endpoint,
                        resource=resolved, source_label=selector, force_entra=True,
                        api_version=resolved_api_version)
    if profile_name:
        client, resolved_ep, resolved_api_version = _client_from_named_profile(
            profile_name,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            entra=entra,
        )
        return _SideCtx(client=client, endpoint=resolved_ep,
                        resource=None, source_label=f"CU CLI profile '{profile_name}'",
                        profile_name=profile_name, force_entra=entra,
                        api_version=resolved_api_version)
    if side == "destination" and default_from is not None:
        # No destination context provided: reuse the source client and resource.
        return default_from
    # Fall through: active or --profile-selected profile with top-level overrides.
    selected_profile = fallback_profile or profile_name
    resolved_api_version = _resolve_copy_api_version(
        profile_name=selected_profile,
        api_version=api_version,
    )
    client = _client(endpoint, api_key, resolved_api_version, entra, selected_profile,
                     show_runtime_context=False)
    profile = Profile.load(profile_name=selected_profile)
    active = (
        f"CU CLI profile '{profile.profile_name}'"
        if profile.profile_name != "default"
        else "active CU CLI profile"
    )
    return _SideCtx(client=client, endpoint=(endpoint or profile.endpoint or ""),
                    resource=None, source_label=active,
                    profile_name=profile.profile_name, force_entra=entra,
                    api_version=resolved_api_version)


def _resolve_copy_api_version(
    *,
    profile_name: str | None,
    api_version: str | None,
) -> str:
    profile = Profile.load(profile_name=profile_name)
    return resolve_api_version(flag=api_version, profile=profile.api_version)


def _client_from_resource(resolved: Any, *, api_version: str | None) -> Any:
    """Build a CU SDK client directly from a :class:`ResolvedResource`.

    Bypasses ``cu profile`` — the endpoint came from Azure discovery, and the
    Direct resource flows must not create or
    modify profiles. Uses :class:`DefaultAzureCredential` because API keys are
    Foundry-account-scoped and can't be inferred from a discovered account
    without extra key-retrieval calls (which the spec forbids).

    ``api_version`` falls back to the active CU profile's api_version when
    ``None`` (so a direct source inherits the caller's usual API version without
    needing an extra ``--api-version`` flag).
    """
    profile = Profile.load(profile_name=None)
    return build_client(
        profile,
        endpoint_override=resolved.endpoint,
        api_version_override=api_version or profile.api_version,
        force_entra=True,
    )


def _client_from_named_profile(
    profile_name: str,
    *,
    endpoint: str | None,
    api_key: str | None,
    api_version: str | None,
    entra: bool,
) -> tuple[Any, str, str]:
    """Return a named-profile client, endpoint, and effective API version."""
    profile = Profile.load(profile_name=profile_name)
    auth = resolve(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )
    return build_client(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    ), auth.endpoint, auth.api_version


def _is_cross_resource(src: _SideCtx, tgt: _SideCtx) -> bool:
    """Decide whether the copy needs cross-resource orchestration.

    * If both sides carry resolved resources, compare canonical ARM IDs.
    * If either side lacks a ``resource``, fall back to comparing endpoints —
      profiles without ARM metadata may still point at the same resource.
    * Same client identity is a definite same-resource signal.
    """
    from ..core.azure_resources import resources_equal
    if src.resource is not None and tgt.resource is not None:
        return not resources_equal(src.resource, tgt.resource)
    if src.client is tgt.client:
        return False
    return (src.endpoint or "").rstrip("/") != (tgt.endpoint or "").rstrip("/")


def _ensure_arm_metadata(
    ctx: _SideCtx,
    *,
    side_flag: str,
    subscription_id: str | None,
) -> _SideCtx:
    """Resolve a profile-derived endpoint within its authoritative subscription.

    An explicit side subscription takes precedence; otherwise
    :func:`resolve_resource` uses the active Azure CLI subscription. Discovery
    never fans out to other subscriptions. Direct resource selectors already
    carry metadata and are returned unchanged.
    """
    if ctx.resource is not None:
        return ctx
    if not ctx.endpoint:
        raise CuCliError(
            f"cannot resolve an Azure resource for {ctx.source_label} because "
            "no endpoint is configured on that side.",
            hint=f"pass {side_flag} with a Foundry endpoint URL, an account name, or a full ARM ID.",
        )
    from ..core.azure_resources import resolve_resource
    scope = (
        f"subscription '{subscription_id}'"
        if subscription_id
        else "the active Azure CLI subscription"
    )
    try:
        resolved = resolve_resource(ctx.endpoint, subscription_id=subscription_id)
    except CuCliError as exc:
        selector_hint = (
            f"Pass {side_flag} explicitly with a URL, name, or ARM ID "
            "(the CU profile does not need to carry ARM ID / region)."
        )
        raise CuCliError(
            f"could not resolve {ctx.source_label} endpoint '{ctx.endpoint}' in "
            f"{scope}: {exc.message}",
            hint=((exc.hint.rstrip() + " ") if exc.hint else "") + selector_hint,
        ) from exc
    return _SideCtx(client=ctx.client, endpoint=resolved.endpoint,
                    resource=resolved, source_label=ctx.source_label,
                    profile_name=ctx.profile_name, force_entra=ctx.force_entra,
                    api_version=ctx.api_version)


def _print_copy_runtime_context(src: _SideCtx, tgt: _SideCtx, *, cross_resource: bool) -> None:
    console.print("[bold]resolved copy sides:[/bold]")
    console.print(f"  source: {src.source_label} -> {src.endpoint}")
    console.print(f"          api-version: {src.api_version}")
    if src.resource is not None:
        console.print(f"          arm-id: {src.resource.arm_id}")
        console.print(f"          region: {src.resource.region}")
    console.print(f"  destination: {tgt.source_label} -> {tgt.endpoint}")
    console.print(f"          api-version: {tgt.api_version}")
    if tgt.resource is not None:
        console.print(f"          arm-id: {tgt.resource.arm_id}")
        console.print(f"          region: {tgt.resource.region}")
    console.print(f"  mode:   {'cross-resource' if cross_resource else 'same-resource'}")


def _copy_side_cli_option(
    ctx: _SideCtx,
    *,
    side: str,
    subscription_id: str | None = None,
) -> str:
    """Return shell-safe options that preserve a copy side's provenance."""
    if ctx.profile_name:
        options = f"--{side}-profile {shlex.quote(ctx.profile_name)}"
        if subscription_id:
            options += f" --{side}-subscription {shlex.quote(subscription_id)}"
        return options
    if ctx.resource is not None:
        return f"--{side}-resource {shlex.quote(ctx.resource.arm_id)}"
    return f"--{side}-resource {shlex.quote(ctx.endpoint or ctx.source_label)}"


def _dependency_copy_cli_command(
    analyzer_id: str,
    src_ctx: _SideCtx,
    tgt_ctx: _SideCtx,
    *,
    source_subscription: str | None,
    destination_subscription: str | None,
    api_version: str | None,
) -> str:
    """Build a shell-safe dependency-copy command without authentication data."""
    command = (
        f"cu analyzer copy --source {shlex.quote(analyzer_id)} "
        f"--destination {shlex.quote(analyzer_id)} "
        f"{_copy_side_cli_option(src_ctx, side='source', subscription_id=source_subscription)} "
        f"{_copy_side_cli_option(tgt_ctx, side='destination', subscription_id=destination_subscription)}"
    )
    if api_version:
        command += f" --api-version {shlex.quote(api_version)}"
    return command


def _target_cli_options(ctx: _SideCtx) -> str:
    """Return non-secret options that qualify a follow-up command to ``ctx``."""
    options: list[str] = []
    if ctx.profile_name:
        options.extend(("--profile", shlex.quote(ctx.profile_name)))
        if ctx.endpoint:
            options.extend(("--endpoint", shlex.quote(ctx.endpoint)))
        if ctx.force_entra:
            mode = ctx.force_entra if isinstance(ctx.force_entra, str) else "login"
            options.extend(("--auth-mode", mode))
    elif ctx.resource is not None:
        options.extend(("--endpoint", shlex.quote(ctx.endpoint), "--auth-mode", "login"))
    elif ctx.endpoint:
        options.extend(("--endpoint", shlex.quote(ctx.endpoint)))
        if ctx.force_entra:
            mode = ctx.force_entra if isinstance(ctx.force_entra, str) else "login"
            options.extend(("--auth-mode", mode))
    return " ".join(options)


def _target_cli_command(action: str, analyzer_id: str, ctx: _SideCtx) -> str:
    """Build a destination-qualified analyzer follow-up command without secrets."""
    options = _target_cli_options(ctx)
    suffix = f" {options}" if options else ""
    return f"cu analyzer {action} {shlex.quote(analyzer_id)}{suffix}"


# --- Authoring: schema creation -------------------------------------------


@analyzer_group.group(
    "schema",
    help="Create custom-analyzer schemas.",
    epilog=common_commands(
        (
            "cu analyzer schema create --output-file SCHEMA.json",
            "Write an editable starter schema.",
        ),
        (
            "cu analyzer schema create --from-sample SAMPLE_FILE "
            "--output-file SCHEMA.json",
            "Create a schema from one document sample.",
        ),
    ),
)
def schema_group() -> None:
    pass


def suggest_schema_payload_from_sample(
    *,
    sample_path: Path,
    analyzer_id: str,
    api_version: str,
    profile_name: str | None = None,
    endpoint: str | None = None,
    api_key: str | None = None,
    force_entra: bool | str = False,
) -> dict[str, Any]:
    """Build an extraction schema from one sample via prebuilt-documentFieldSchema.

    Command-layer wrapper: validates the sample, resolves profile/auth, builds a
    client, and delegates the analyze + field extraction to
    :func:`cu_cli.core.schema.suggest_schema_from_sample`. MVP behavior
    intentionally supports exactly one local document sample.
    """
    from cu_cli_core.contracts import AnalyzerSchemaCreateRequest

    validate_document_sample(sample_path)
    profile = Profile.load(profile_name=profile_name)
    client = _client(endpoint, api_key, api_version, force_entra, profile_name, False)
    request = AnalyzerSchemaCreateRequest(
        from_sample=sample_path,
        name=analyzer_id,
    )
    payload, found = resolve_identifier(ANALYZER_SCHEMA_CREATE.operation)(
        request,
        api_version=api_version,
        completion_model=template_completion_model(profile),
        client=client,
    )
    if not found:
        console.print(
            "[yellow]warn:[/yellow] no suggested fields were returned; wrote the default extraction template."
        )
    return payload


@schema_group.command(
    "create",
    help=ANALYZER_SCHEMA_CREATE.help,
    epilog=common_commands(
        (
            "cu analyzer schema create --output-file SCHEMA.json",
            "Write a document extraction schema.",
        ),
        (
            "cu analyzer schema create --type classification "
            "--output-file SCHEMA.json",
            "Write a classification schema.",
        ),
        (
            "cu analyzer schema create --from-sample SAMPLE_FILE "
            "--output-file SCHEMA.json",
            "Derive an extraction schema from one sample.",
        ),
    ),
)
@with_command_arguments(ANALYZER_SCHEMA_CREATE)
@with_auth_options
@friendly_errors
def cmd_schema_create(
    from_template,
    sample_path,
    analyzer_id,
    base,
    modality,
    out_path,
    force,
    template_type,
    api_version,
    endpoint,
    api_key,
    entra,
    profile_name,
    show_runtime_context,
    show_calling_time,
) -> None:
    try:
        request = build_request(
            ANALYZER_SCHEMA_CREATE,
            {
                "from_template": from_template,
                "sample_path": sample_path,
                "analyzer_id": analyzer_id,
                "base": base,
                "modality": modality,
                "out_path": out_path,
                "force": force,
                "template_type": template_type,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    _require_custom_analyzer_id(request.name)
    _require_output_available(
        request.output_file,
        force=request.force,
        description="schema output",
    )
    profile = Profile.load(profile_name=profile_name)
    resolved = resolve_api_version(flag=api_version, profile=profile.api_version)

    with calling_time(show_calling_time) as calling_timer:
        if request.from_sample is None:
            payload, _ = resolve_identifier(ANALYZER_SCHEMA_CREATE.operation)(
                request,
                api_version=resolved,
                completion_model=_template_completion_model(profile),
            )
            source = "starter"
        else:
            if show_runtime_context:
                auth = resolve(
                    profile,
                    endpoint_override=endpoint,
                    api_key_override=api_key,
                    api_version_override=api_version,
                    force_entra=entra,
                )
                print_runtime_context(auth, profile)
            payload = suggest_schema_payload_from_sample(
                sample_path=request.from_sample,
                analyzer_id=request.name,
                api_version=resolved,
                profile_name=profile_name,
                endpoint=endpoint,
                api_key=api_key,
                force_entra=entra,
            )
            source = "sample-derived"
    _write_json_output(
        payload,
        request.output_file,
        force=request.force,
        description="schema output",
    )
    if request.output_file:
        console.print(
            f"[green]ok[/green] wrote {source} schema "
            f"(apiVersion {resolved}) -> {request.output_file}"
        )
        console.print(
            "[dim]next:[/dim] review fields, then run "
            f"[cyan]cu analyzer validate {out_path}[/cyan]"
        )
    calling_timer.print()


# --- Authoring: validate (offline, exit 2 on error) ------------------------


@analyzer_group.command("validate",
                        help=ANALYZER_VALIDATE.help,
                        epilog=common_commands(
                            ("cu analyzer validate SCHEMA.json", "Validate a schema offline."),
                            (
                                "cu analyzer validate SCHEMA.json --strict --spec",
                                "Treat warnings as errors and check the service contract.",
                            ),
                        ))
@with_command_arguments(ANALYZER_VALIDATE)
@click.option("--api-version", "api_version", default=None,
              help=API_VERSION_HELP)
@friendly_errors
def cmd_validate(
    named_schema_path: Path | None,
    positional_schema_path: Path | None,
    json_output: bool,
    strict: bool,
    use_spec: bool,
    api_version: str | None,
) -> None:
    try:
        request = build_request(
            ANALYZER_VALIDATE,
            {
                "named_schema_path": named_schema_path,
                "positional_schema_path": positional_schema_path,
                "json_output": json_output,
                "strict": strict,
                "use_spec": use_spec,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    schema_path = request.schema
    strict = request.strict
    profile = Profile.load()
    try:
        text = schema_path.read_text(encoding="utf-8")
        pinned = schema_pinned_version(json.loads(text))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        pinned = None

    resolved = resolve_api_version(
        flag=api_version,
        schema_pinned=pinned,
        profile=profile.api_version,
    )

    result = resolve_identifier(ANALYZER_VALIDATE.operation)(
        request,
        api_version=resolved,
    )
    ok = result.ok and (not strict or not result.warnings)

    if json_output:
        payload = result.as_dict()
        payload["ok"] = ok
        payload["strict"] = strict
        dump_json(payload)
        raise SystemExit(SUCCESS if ok else VALIDATION_FAILURE)

    if not result.errors and not result.warnings:
        console.print(f"[green]ok[/green]  {schema_path}  is a valid analyzer schema "
                      f"(apiVersion {resolved}).")
        return

    if result.errors:
        console.print(f"[bold red]{len(result.errors)} error(s)[/bold red]  {_esc(str(schema_path))}")
        for e in result.errors:
            console.print(f"  [red]error[/red]  [cyan]{_esc(e.path)}[/cyan]  {_esc(e.msg)}")
    if result.warnings:
        console.print(f"[bold yellow]{len(result.warnings)} warning(s)[/bold yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]warn[/yellow]   [cyan]{_esc(w.path)}[/cyan]  {_esc(w.msg)}")
    if not result.errors:
        if strict and result.warnings:
            console.print(f"[bold red]validation failed under --strict[/bold red] "
                          f"({len(result.warnings)} warning(s) treated as errors).")
        else:
            console.print("[dim]validation passed (warnings only). Use --strict to fail on warnings.[/dim]")

    raise SystemExit(SUCCESS if ok else VALIDATION_FAILURE)


# --- Authoring: test (per-field coverage + confidence) ---------------------


@analyzer_group.command("test",
                        help=ANALYZER_TEST.help,
                        epilog=common_commands(
                            (
                                "cu analyzer test ANALYZER_NAME SAMPLE_DIR",
                                "Test an analyzer across local samples.",
                            ),
                            (
                                "cu analyzer test --name ANALYZER_NAME --source SAMPLE_DIR "
                                "--json --output-file REPORT.json",
                                "Write a machine-readable quality report.",
                            ),
                        ))
@with_command_arguments(ANALYZER_TEST)
@with_auth_options
@friendly_errors
def cmd_test(
    positional_analyzer_name,
    analyzer_name,
    inputs,
    files,
    sources,
    pattern,
    recursive,
    dry_run,
    json_output,
    out_path,
    force,
    assume_yes,
    concurrency,
    endpoint,
    api_key,
    api_version,
    entra,
    profile_name,
    show_runtime_context,
    show_calling_time,
) -> None:
    from .analyze import _print_discovery, _run_one
    from cu_cli_core.contracts import InputOrigin
    from cu_cli_core.input_planning import plan_inputs

    if dry_run and assume_yes:
        raise CuCliError(
            "--dry-run and --yes cannot be combined.",
            exit_code=VALIDATION_FAILURE,
        )
    try:
        request = build_request(
            ANALYZER_TEST,
            {
                "positional_analyzer_name": positional_analyzer_name,
                "analyzer_name": analyzer_name,
                "inputs": inputs,
                "files": files,
                "sources": sources,
                "pattern": pattern,
                "recursive": recursive,
                "dry_run": dry_run,
                "json_output": json_output,
                "out_path": out_path,
                "force": force,
                "assume_yes": assume_yes,
                "concurrency": concurrency,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    if not request.dry_run:
        _require_output_available(
            request.output_file,
            force=request.force,
            description="analyzer test report",
        )
    input_plan = plan_inputs(
        positional=request.positional_inputs,
        files=request.files,
        sources=request.sources,
        pattern=request.pattern,
        recursive=request.recursive,
    )
    refs = [str(item.path) for item in input_plan.inputs]
    analyzer_id = request.name
    if request.dry_run:
        console.print("[bold cyan]Dry run[/bold cyan]")
        _print_discovery(input_plan, analyzer_id=analyzer_id)
        console.print(
            "[dim]No service calls or files were written. Analyzer existence, "
            "service-side format acceptance, usage, and cost were not validated.[/dim]"
        )
        return

    discovered = any(
        item.origin in {InputOrigin.POSITIONAL_SOURCE, InputOrigin.NAMED_SOURCE}
        for item in input_plan.inputs
    )
    if not assume_yes and discovered and len(refs) > 1 and sys.stdin.isatty():
        _print_discovery(input_plan, analyzer_id=analyzer_id)
        if not click.confirm("proceed?", default=False):
            raise CuCliError("aborted by user.", hint="narrow the inputs or pass --yes.")

    client = _client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context)

    if not json_output:
        console.print(f"[bold]testing[/bold] [magenta]{analyzer_id}[/magenta] against "
                      f"[cyan]{len(refs)}[/cyan] sample(s)…")

    with calling_time(show_calling_time) as calling_timer:
        report = resolve_identifier(ANALYZER_TEST.operation)(
            client,
            request,
            input_plan=input_plan,
            run=lambda c, j: _run_one(c, j)[1],
        )
    any_failed = report["summary"]["samplesFailed"] > 0

    if request.output_file is not None:
        _write_json_output(
            report,
            request.output_file,
            force=request.force,
            description="analyzer test report",
        )

    if json_output:
        if request.output_file is None:
            dump_json(report)
        else:
            console.print(f"[green]ok[/green] wrote report -> {request.output_file}")
        calling_timer.print()
        if any_failed:
            sys.exit(GENERIC_ERROR)
        return

    s = report["summary"]
    console.print(f"\n[bold]Summary[/bold]  [green]{s['samplesOk']} ok[/green] / "
                  f"[red]{s['samplesFailed']} failed[/red] / [dim]{s['samplesTotal']} total[/dim]")
    console.print(f"[dim]Note: {_esc(s['disclaimer'])}[/dim]")
    if s["fields"]:
        t = Table(show_lines=False)
        t.add_column("Field", style="bold")
        t.add_column("Populated", justify="right")
        t.add_column("Mean conf.", justify="right")
        t.add_column("Low-conf hits", justify="right")
        for fname, fstat in s["fields"].items():
            mean = fstat["meanConfidence"]
            mean_str = f"{mean:.2f}" if mean is not None else "—"
            t.add_row(fname,
                      f"{fstat['populated']}/{s['samplesTotal']} "
                      f"[dim]({fstat['populatedPct']}%)[/dim]",
                      mean_str, str(fstat["lowConfidenceCount"]))
        console.print(t)
        console.print(f"[dim]Low-confidence threshold: {s['lowConfidenceThreshold']}. "
                      "Re-run with --json for the full per-sample report.[/dim]")
    fails = [r for r in report["samples"] if r["status"] != "ok"]
    if fails:
        console.print(f"\n[bold red]{len(fails)} failed[/bold red]:")
        for f in fails[:10]:
            console.print(f"  [red]x[/red] {f['input']}  [dim]{f.get('error', '')[:120]}[/dim]")
    if request.output_file is not None:
        console.print(f"\n[dim]wrote full report -> {request.output_file}[/dim]")
    calling_timer.print()
    if any_failed:
        sys.exit(GENERIC_ERROR)
