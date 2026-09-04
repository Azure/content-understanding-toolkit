from __future__ import annotations

import sys
import types

import pytest
from cu_cli_core.contracts import OutcomeStatus

from cu_cli.output import EmptyMarkdownOutputError, render_markdown

pytestmark = pytest.mark.unit


def _install_fake_sdk(monkeypatch: pytest.MonkeyPatch, *, fn) -> None:
    fake = types.ModuleType("azure.ai.contentunderstanding")
    fake.to_llm_input = fn
    monkeypatch.setitem(sys.modules, "azure.ai.contentunderstanding", fake)


def test_render_markdown_uses_to_llm_input_only(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Result:
        pass

    _install_fake_sdk(monkeypatch, fn=lambda _r: "hello")
    assert render_markdown(_Result()) == "hello"


def test_render_markdown_requires_to_llm_input(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("azure.ai.contentunderstanding")
    monkeypatch.setitem(sys.modules, "azure.ai.contentunderstanding", fake)
    with pytest.raises(RuntimeError, match="to_llm_input"):
        render_markdown(object())


def test_render_markdown_rejects_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_sdk(monkeypatch, fn=lambda _r: "   \n")
    with pytest.raises(EmptyMarkdownOutputError, match="empty markdown"):
        render_markdown(object())


def test_markdown_table_is_valid_gfm() -> None:
    # Regression: --output markdown must emit a real pipe/---- table, not a Rich grid.
    from cu_cli.output import markdown_table

    out = markdown_table([["gpt-4.1", "dep-a"], ["emb", "dep|b"]], ["Model", "Deployment"])
    lines = out.splitlines()
    assert lines[0] == "| Model | Deployment |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| gpt-4.1 | dep-a |"
    # A literal pipe inside a cell is escaped so the table stays valid.
    assert lines[3] == r"| emb | dep\|b |"


def test_json_conversion_uses_shared_recursive_serializer() -> None:
    from datetime import datetime, timezone
    from pathlib import Path

    from cu_cli.output import to_jsonable

    assert to_jsonable(
        {
            "status": OutcomeStatus.SUCCEEDED,
            "path": Path("result.json"),
            "timestamp": datetime(2026, 8, 29, tzinfo=timezone.utc),
        }
    ) == {
        "status": "succeeded",
        "path": "result.json",
        "timestamp": "2026-08-29T00:00:00+00:00",
    }


def test_analyzer_table_renders_enum_status_value() -> None:
    # Regression: status should show `ready`, not `ContentAnalyzerStatus.READY`.
    import enum
    import io
    from types import SimpleNamespace

    from rich.console import Console

    from cu_cli.output import analyzer_table

    class _Status(enum.Enum):
        READY = "ready"

    row = SimpleNamespace(analyzer_id="a1", base_analyzer_id="prebuilt-document",
                          status=_Status.READY, last_modified_at="t", description="d")
    console = Console(file=io.StringIO(), width=140)
    console.print(analyzer_table([row]))
    rendered = console.file.getvalue()
    assert "ready" in rendered
    assert "READY" not in rendered


@pytest.mark.parametrize("width", [80, 100, 120])
def test_analyzer_table_folds_long_id_without_truncating(width: int) -> None:
    import io
    from types import SimpleNamespace

    from rich.console import Console

    from cu_cli.output import analyzer_table

    analyzer_id = "analyzer_identifier_" + "0123456789abcdef" * 2 + "0123456789ab"
    assert len(analyzer_id) == 64
    row = SimpleNamespace(
        analyzer_id=analyzer_id,
        base_analyzer_id="base",
        status="ready",
        last_modified_at="time",
        description="description",
    )
    output = io.StringIO()
    console = Console(file=output, width=width, color_system=None)
    console.print(analyzer_table([row]))
    rendered = output.getvalue()

    assert "…" not in rendered
    data_lines = [line for line in rendered.splitlines() if "│" in line]
    first_column = "".join(line.split("│")[1].strip() for line in data_lines)
    assert analyzer_id in first_column


def test_result_console_writes_to_stdout_not_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    # CUCONFIG-001 regression: `result_console` (used by `cu profile list` /
    # `cu profile show` for actual result tables) must resolve to the live
    # sys.stdout, unlike `console` which is pinned to stderr.
    import io

    from cu_cli.output import console, result_console

    fake_stdout = io.StringIO()
    fake_stderr = io.StringIO()
    monkeypatch.setattr("sys.stdout", fake_stdout)
    monkeypatch.setattr("sys.stderr", fake_stderr)

    result_console.print("result-payload")
    console.print("status-message")

    assert "result-payload" in fake_stdout.getvalue()
    assert "result-payload" not in fake_stderr.getvalue()
    assert "status-message" in fake_stderr.getvalue()
    assert "status-message" not in fake_stdout.getvalue()
