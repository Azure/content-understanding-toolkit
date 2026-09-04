# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Discover and inspect supported CU CLI environment variables."""

from __future__ import annotations

import rich_click as click
from rich.table import Table

from cu_cli_core.command_spec import ENV_VAR_LIST, build_request, resolve_identifier
from cu_cli_core.environment import ENVIRONMENT_VARIABLES

from ..output import dump_json, result_console
from ._command_spec import with_command_arguments
from ._help import common_commands


def _environment_help() -> str:
    blocks = ["[bold cyan]Supported environment variables:[/bold cyan]"]
    for spec in ENVIRONMENT_VARIABLES:
        sensitivity = " (sensitive; always redacted)" if spec.sensitive else ""
        blocks.append(
            f"[bold green]{spec.name}[/bold green]{sensitivity}\n"
            f"  {spec.description}\n"
            f"  Values: {spec.accepted_values}. Default: {spec.default}.\n"
            f"  Scope: {spec.scope}. {spec.precedence}"
        )
    return "\n\n[white] [/white]\n\n".join(blocks)


@click.group(
    "env-var",
    help="Show help for supported environment variables and inspect values that are set.",
    epilog=_environment_help()
    + "\n\n"
    + common_commands(
        ("cu env-var list --json", "Print the set variables as redacted JSON."),
    ),
)
def env_var_group() -> None:
    pass


@env_var_group.command(
    "list",
    help=ENV_VAR_LIST.help,
    epilog=common_commands(
        ("cu env-var list", "List set variables as a table."),
        ("cu env-var list --json", "Print set variables as redacted JSON."),
    ),
)
@with_command_arguments(ENV_VAR_LIST)
def cmd_list(json_output: bool) -> None:
    build_request(ENV_VAR_LIST, {"json_output": json_output})
    rows = resolve_identifier(ENV_VAR_LIST.operation)()
    if json_output:
        dump_json(rows)
        return

    table = Table(title="Set CU environment variables", show_lines=False)
    table.add_column("Name", style="bold")
    table.add_column("Value")
    table.add_column("Scope")
    for row in rows:
        table.add_row(str(row["name"]), str(row["value"]), str(row["scope"]))
    result_console.print(table)
