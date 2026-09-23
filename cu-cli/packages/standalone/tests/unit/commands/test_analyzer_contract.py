# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from cu_cli.cli import main
from cu_cli_core.command_spec import resolve_identifier

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_resolved_operations():
    resolve_identifier.cache_clear()
    yield
    resolve_identifier.cache_clear()


def _run(*args: str):
    return CliRunner().invoke(main, list(args))


def test_analyzer_create_help_describes_valid_custom_id():
    result = _run("analyzer", "create", "--help")

    assert result.exit_code == 0, result.output
    compact_output = "".join(result.output.replace("│", "").split())
    assert (
        "CustomanalyzerID:1-64ASCIIletters,numbers,orunderscores."
        in compact_output
    )


def test_analyzer_list_uses_json_shortcut(monkeypatch):
    analyzer = SimpleNamespace(
        analyzer_id="custom_v1",
        created_at="2026-01-01",
        last_modified_at="2026-01-02",
        as_dict=lambda: {"analyzerId": "custom_v1"},
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: SimpleNamespace(
            list_analyzers=lambda: [analyzer],
        ),
    )

    result = _run("analyzer", "list", "--kind", "custom", "--json")

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [{"analyzerId": "custom_v1"}]


@pytest.mark.parametrize(
    "selector",
    [
        ("invoice_v1",),
        ("--name", "invoice_v1"),
        ("-n", "invoice_v1"),
        ("-a", "invoice_v1"),
    ],
)
def test_analyzer_create_accepts_canonical_and_positional_names(monkeypatch, selector):
    Path("schema.json").write_text(
        json.dumps(
            {
                "analyzerId": "invoice_v1",
                "baseAnalyzerId": "prebuilt-document",
                "fieldSchema": {"fields": {}},
            }
        )
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.Profile.load",
        lambda **_kwargs: SimpleNamespace(api_version="2025-11-01"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: object(),
    )
    captured = {}

    def create(_client, analyzer_id, body):
        captured["id"] = analyzer_id
        captured["body"] = body
        return SimpleNamespace(analyzer_id=analyzer_id)

    monkeypatch.setattr("cu_cli_core.operations.analyzers.create_analyzer", create)

    result = _run("analyzer", "create", *selector, "--schema", "schema.json")

    assert result.exit_code == 0, result.output
    assert captured["id"] == "invoice_v1"


def test_analyzer_create_rejects_duplicate_name_before_client(monkeypatch):
    Path("schema.json").write_text("{}")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyzer",
        "create",
        "invoice_v1",
        "--name",
        "invoice_v2",
        "--schema",
        "schema.json",
    )

    assert result.exit_code == 2
    assert "provide name only once" in result.output


@pytest.mark.parametrize(
    "selector",
    [
        ("invoice_v1",),
        ("--name", "invoice_v1"),
        ("-n", "invoice_v1"),
        ("-a", "invoice_v1"),
    ],
)
def test_analyzer_delete_accepts_canonical_and_positional_names(monkeypatch, selector):
    client = SimpleNamespace(
        get_analyzer=lambda _name: object(),
        delete_analyzer=lambda name: deleted.append(name),
    )
    deleted = []
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: client,
    )

    result = _run("analyzer", "delete", *selector, "--yes")

    assert result.exit_code == 0, result.output
    assert deleted == ["invoice_v1"]


def test_analyzer_test_dry_run_uses_shared_input_contract(monkeypatch):
    samples = Path("samples")
    samples.mkdir()
    (samples / "invoice.pdf").write_text("invoice")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyzer",
        "test",
        "--name",
        "invoice_v1",
        "--source",
        "samples",
        "--pattern",
        "*.pdf",
        "--dry-run",
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert "invoice.pdf" not in result.output
    assert "No service calls or files were written" in result.output


def test_analyzer_test_positional_name_and_inputs_are_unambiguous(monkeypatch):
    first = Path("first.pdf")
    second = Path("second.pdf")
    first.write_text("first")
    second.write_text("second")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: object(),
    )
    seen = []

    def run_one(_client, job):
        seen.append(Path(job.input_ref).name)
        return job, SimpleNamespace(contents=[])

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)

    result = _run(
        "analyzer",
        "test",
        "invoice_v1",
        "first.pdf",
        "second.pdf",
        "--json",
    )

    assert result.exit_code == 0, result.output
    assert seen == ["first.pdf", "second.pdf"]
    assert json.loads(result.output)["analyzerId"] == "invoice_v1"


def test_analyzer_test_rejects_mixed_input_modes_before_client(monkeypatch):
    Path("first.pdf").write_text("first")
    Path("second.pdf").write_text("second")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyzer",
        "test",
        "invoice_v1",
        "first.pdf",
        "--file",
        "second.pdf",
    )

    assert result.exit_code == 2
    assert "positional inputs cannot be combined with --file" in result.output


def test_schema_create_defaults_to_offline_template(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            api_version="2025-11-01",
            model_deployments={},
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyzer",
        "schema",
        "create",
        "--name",
        "invoice_v1",
        "--output-file",
        "schema.json",
    )

    assert result.exit_code == 0, result.output
    assert json.loads(Path("schema.json").read_text())["analyzerId"] == "invoice_v1"


def test_schema_create_from_sample_uses_suggestion_path(monkeypatch):
    Path("sample.pdf").write_text("sample")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            api_version="2025-11-01",
            model_deployments={},
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.suggest_schema_payload_from_sample",
        lambda **kwargs: {
            "analyzerId": kwargs["analyzer_id"],
            "fieldSchema": {"fields": {"InvoiceNumber": {"type": "string"}}},
        },
    )

    result = _run(
        "analyzer",
        "schema",
        "create",
        "--name",
        "invoice_v1",
        "--from-sample",
        "sample.pdf",
        "--output-file",
        "schema.json",
    )

    assert result.exit_code == 0, result.output
    fields = json.loads(Path("schema.json").read_text())["fieldSchema"]["fields"]
    assert "InvoiceNumber" in fields


def test_schema_create_modes_are_mutually_exclusive():
    Path("sample.pdf").write_text("sample")

    result = _run(
        "analyzer",
        "schema",
        "create",
        "--from-template",
        "--from-sample",
        "sample.pdf",
    )

    assert result.exit_code == 2
    assert "cannot be combined" in result.output


def test_replaced_analyzer_surfaces_are_not_registered():
    for args in (
        ("analyzer", "schema", "template"),
        ("analyzer", "schema", "suggest"),
        ("analyzer", "test", "invoice_v1", "--samples", "samples"),
    ):
        result = _run(*args)
        assert result.exit_code == 2
