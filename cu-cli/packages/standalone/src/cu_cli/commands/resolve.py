# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu resolve`` — turn rich-markdown anchors into page, bounding box and context.

Purely local: reads the ``--json`` result written by ``cu analyze`` and never
calls the service.
"""

from __future__ import annotations

import json
from pathlib import Path

import rich_click as click

from cu_cli_core.rich_markdown import RichMarkdownError, resolve_ids

from ..errors import CuCliError, friendly_errors
from ..exit_codes import VALIDATION_FAILURE
from ..output import dump_json


@click.command(
    "resolve",
    help="Resolve rich-markdown anchors (s3, t0, f2, p30) to page + bounding box (+ context).",
    epilog="Ids come from `cu analyze FILE` (s3 = section, t0 = table, f2 = figure) or "
           "`cu analyze FILE --level paragraph` (p30 = paragraph). RESULT is the matching "
           "--json output. Coordinates are in inches on the page; bbox = {page, x, y, w, h}.\n\n"
           "[white] [/white]\n\n"
           "[bold cyan]Common commands:[/bold cyan]\n\n"
           "[bold green]cu resolve[/bold green] [bold yellow]doc.json p30[/bold yellow]\n\n"
           "[white]\u00a0\u00a0Page, bbox and text of paragraph 30.[/white]\n\n"
           "[bold green]cu resolve[/bold green] [bold yellow]doc.json t0 f2[/bold yellow] "
           "[bold cyan]--around 1[/bold cyan]\n\n"
           "[white]\u00a0\u00a0Also the block (paragraph, table or figure) before and after each.[/white]",
)
@click.argument("result", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("ids", nargs=-1, required=True, metavar="ID...")
@click.option("--around", type=click.IntRange(0, 50), default=0, metavar="N",
              help="Include N blocks (paragraphs, tables, figures) before and after (markdown order).")
@click.option("--text-chars", type=click.IntRange(0), default=400, metavar="N",
              help="Truncate returned text to N characters (0 = full text).")
@friendly_errors
def cmd_resolve(result: Path, ids: tuple[str, ...], around: int, text_chars: int) -> None:
    try:
        payload = json.loads(result.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CuCliError(f"cannot read {result}: {exc}", exit_code=VALIDATION_FAILURE) from exc
    if not isinstance(payload, dict):
        raise CuCliError(
            f"{result} is not a cu analyze result.",
            hint="pass the file written by `cu analyze FILE --json --output-file PATH`.",
            exit_code=VALIDATION_FAILURE,
        )
    try:
        resolved = resolve_ids(
            payload, ids, around=around, text_chars=None if text_chars == 0 else text_chars,
        )
    except RichMarkdownError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc
    resolved["source"] = str(result)
    dump_json(resolved)
