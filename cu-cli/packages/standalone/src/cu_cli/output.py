"""Output helpers: JSON / markdown / pretty tables.

``console`` is routed to stderr so the stdout pipe contract for
``cu analyze ... --json | jq`` is never broken by status output. Data
payloads use ``sys.stdout.write`` / explicit file writes, or ``result_console``
for Rich-rendered result content (e.g. ``cu profile list`` / ``cu profile show``)
that still needs to be redirectable/pipeable via stdout.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

from cu_cli_core.serialization import to_plain_value
from rich.console import Console
from rich.table import Table

console = Console(stderr=True)
result_console = Console()


class EmptyMarkdownOutputError(RuntimeError):
    """The service succeeded, but its result has no Markdown projection."""


def to_jsonable(obj: Any) -> Any:
    """Convert Azure SDK model objects to frontend-neutral plain values."""
    return to_plain_value(obj)


def dumps_json(obj: Any) -> str:
    return json.dumps(to_jsonable(obj), indent=2, default=str)


def _enum_value(obj: Any) -> Any:
    """Return an enum's ``.value`` so tables show ``ready`` not ``Status.READY``."""
    return getattr(obj, "value", obj)


def _md_cell(value: Any) -> str:
    """Escape a value for a GitHub-flavored-markdown table cell."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def markdown_table(rows: "Iterable[Iterable[Any]]", headers: "list[str]") -> str:
    """Render *rows* as a valid GitHub-flavored-markdown table string."""
    lines = [
        "| " + " | ".join(_md_cell(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_cell(c) for c in row) + " |")
    return "\n".join(lines)


def dump_markdown_kv(pairs: dict, headers: "tuple[str, str]" = ("Key", "Value"),
                     out: "Path | None" = None) -> None:
    """Write a two-column mapping as a real markdown table (stdout by default).

    Unlike the Rich tables (which go to stderr and aren't valid markdown), this
    goes to stdout so ``... --output markdown >> report.md`` produces valid GFM.
    """
    body = markdown_table([[k, v] for k, v in pairs.items()], list(headers)) + "\n"
    if out is None:
        sys.stdout.write(body)
        sys.stdout.flush()
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")


def dump_json(
    obj: Any,
    out: "Path | None" = None,
    *,
    overwrite: bool = True,
) -> None:
    payload = dumps_json(obj)
    if out is None:
        sys.stdout.write(payload)
        if not payload.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    elif not overwrite:
        out.parent.mkdir(parents=True, exist_ok=True)
        created = False
        try:
            with out.open("x", encoding="utf-8") as stream:
                created = True
                stream.write(payload)
        except OSError:
            if created:
                out.unlink(missing_ok=True)
            raise
    else:
        import tempfile

        out.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=out.parent,
                prefix=f".{out.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                stream.write(payload)
                temporary = Path(stream.name)
            os.replace(temporary, out)
        except OSError:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise


def render_markdown(result: Any) -> str:
    """Render an analysis result as LLM-friendly markdown via SDK helper only."""
    try:
        from azure.ai.contentunderstanding import to_llm_input
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Markdown output requires SDK support for to_llm_input(). "
            "Install azure-ai-contentunderstanding>=1.2.0b3."
        ) from exc

    rendered = to_llm_input(result)
    if not isinstance(rendered, str) or not rendered.strip():
        raise EmptyMarkdownOutputError("to_llm_input() returned empty markdown output.")
    return rendered


def dump_markdown(result: Any, out: "Path | None" = None) -> None:
    body = render_markdown(result)
    if out is None:
        sys.stdout.write(body)
        if not body.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")


def analyzer_table(rows: Iterable[Any]) -> Table:
    t = Table(title="Analyzers", show_lines=False)
    t.add_column("Analyzer ID", style="bold", overflow="fold", max_width=36)
    t.add_column("Base")
    t.add_column("Status")
    t.add_column("Modified")
    t.add_column("Description")
    for a in rows:
        t.add_row(
            str(getattr(a, "analyzer_id", "") or ""),
            str(getattr(a, "base_analyzer_id", "") or "—"),
            str(_enum_value(getattr(a, "status", "")) or "—"),
            str(getattr(a, "last_modified_at", "") or "—"),
            (str(getattr(a, "description", "") or "")[:60]),
        )
    return t


def kv_table(pairs: dict, title: str = "") -> Table:
    t = Table(title=title or None, title_justify="left", show_header=False, box=None)
    t.add_column("key", style="dim")
    t.add_column("value")
    for k, v in pairs.items():
        t.add_row(str(k), str(v) if not isinstance(v, dict)
                  else json.dumps(v, indent=2, default=str))
    return t
