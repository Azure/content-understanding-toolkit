# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cu_cli_core.command_spec import resolve_identifier
from support.command_catalog import invoke_cli
from support.recording import copy_sample_invoice

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_resolved_operations():
    resolve_identifier.cache_clear()
    yield
    resolve_identifier.cache_clear()


def _run(*args: str, comment: str | None = None):
    return invoke_cli(args, comment=comment)


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

    result = _run(
        "analyzer", "create", *selector,
        "-s" if selector == ("-n", "invoice_v1") else "--schema", "schema.json",
    )

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

    result = _run(
        "analyzer", "delete", *selector,
        "-y" if selector == ("-n", "invoice_v1") else "--yes",
    )

    assert result.exit_code == 0, result.output
    assert deleted == ["invoice_v1"]


def test_analyzer_test_dry_run_uses_shared_input_contract(monkeypatch):
    samples = Path("samples")
    samples.mkdir()
    copy_sample_invoice(samples / "sample_invoice.pdf")
    copy_sample_invoice(samples / "nested" / "sample_invoice.pdf")
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
    assert "Found 1 inputs:" in result.output
    assert "sample_invoice.pdf" not in result.output
    assert "No service calls or files were written" in result.output


def test_analyzer_test_positional_name_and_inputs_are_unambiguous(monkeypatch):
    copy_sample_invoice("first.pdf")
    copy_sample_invoice("second.pdf")
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
    copy_sample_invoice("sample.pdf")
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


def test_analyzer_inspection_commands_preserve_analyzer_id(monkeypatch):
    analyzer = SimpleNamespace(
        analyzer_id="invoice_v1", created_at=None, last_modified_at=None,
        as_dict=lambda: {"analyzerId": "invoice_v1"},
    )
    requested = []
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: SimpleNamespace(
            get_analyzer=lambda name: requested.append(name) or analyzer,
            list_analyzers=lambda: [analyzer],
        ),
    )
    result = _run("analyzer", "list")
    assert "invoice_v1" in result.stderr
    result = _run("analyzer", "show", "invoice_v1")
    assert json.loads(result.stdout)["analyzerId"] == "invoice_v1"
    assert requested == ["invoice_v1"]


@pytest.mark.parametrize("short_options", [False, True], ids=["long", "short"])
def test_analyzer_test_file_and_recursive_report_options(monkeypatch, short_options):
    from cu_cli_core import input_planning

    copy_sample_invoice()
    copy_sample_invoice("my_sample_dir/sample_invoice.pdf")
    copy_sample_invoice("my_sample_dir/nested/sample_invoice.pdf")
    seen = []
    selected_inputs = []
    built_clients = []
    original_plan_inputs = input_planning.plan_inputs

    def capture_inputs(**kwargs):
        plan = original_plan_inputs(**kwargs)
        selected_inputs.append({item.path for item in plan.inputs})
        return plan

    def build_client(*args, **kwargs):
        built_clients.append(object())
        return built_clients[-1]

    monkeypatch.setattr(input_planning, "plan_inputs", capture_inputs)
    monkeypatch.setattr("cu_cli.commands.analyzer._client", build_client)
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (
            seen.append(Path(job.input_ref).relative_to(Path.cwd()).as_posix())
            or (job, SimpleNamespace(contents=[]))
        ),
    )
    _run(
        "analyzer", "test", "invoice_v1", "sample_invoice.pdf",
    )
    assert seen == ["sample_invoice.pdf"]
    seen.clear()
    selection = (
        "analyzer", "test", "--name", "invoice_v1", "--source", "my_sample_dir",
        "--pattern", "*.pdf", "-r" if short_options else "--recursive",
    )
    if short_options:
        preview = _run(*selection, "--dry-run")
    else:
        # region Snippet:analyzer_test_preview
        preview = _run(
            *selection, "--dry-run", comment="Preview the matching samples without making service calls.",
        )
        # endregion
    assert preview.exit_code == 0, preview.output
    assert "Found 2 inputs:" in preview.output
    assert "No service calls or files were written" in preview.output
    assert seen == []
    assert len(built_clients) == 1
    assert not Path("test-report.json").exists()

    arguments = (
        *selection,
        "-j" if short_options else "--concurrency", "2", "-y" if short_options else "--yes",
        "--json", "--output-file", "test-report.json",
    )
    if short_options:
        _run(*arguments)
    else:
        # region Snippet:analyzer_test_batch
        _run(
            *arguments,
            comment=(
                "Test every matching sample in my_sample_dir, including nested PDFs,\n"
                "and save one aggregate JSON report."
            ),
        )
        # endregion
    assert set(seen) == {"my_sample_dir/sample_invoice.pdf", "my_sample_dir/nested/sample_invoice.pdf"}
    assert selected_inputs[-2] == selected_inputs[-1] == {Path(name).resolve() for name in seen}
    assert len(built_clients) == 2
    assert json.loads(Path("test-report.json").read_text())["analyzerId"] == "invoice_v1"


@pytest.mark.parametrize("concurrency", ["0", "33", "invalid"])
def test_analyzer_test_concurrency_rejects_invalid_values_before_service(monkeypatch, concurrency):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("client must not be built"),
    )
    result = _run("analyzer", "test", "invoice_v1", "--concurrency", concurrency)
    assert result.exit_code == 2


@pytest.mark.parametrize("name_option", ["--name", "-n", "-a"])
@pytest.mark.parametrize("schema_option", ["--schema", "-s"])
def test_schema_name_and_validation_alias_combinations(name_option, schema_option):
    result = _run(
        "analyzer", "schema", "create", name_option, "invoice_v1",
        "--output-file", "schema.json",
    )
    assert result.exit_code == 0, result.output
    assert json.loads(Path("schema.json").read_text())["analyzerId"] == "invoice_v1"
    result = _run("analyzer", "validate", schema_option, "schema.json", "--spec")
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("name_option", ["--name", "-n", "-a"])
def test_analyzer_test_name_aliases_with_named_file_input(monkeypatch, name_option):
    copy_sample_invoice("sample.pdf")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("dry-run must not create a client"),
    )
    result = _run(
        "analyzer", "test", name_option, "invoice_v1", "--file", "sample.pdf", "--dry-run",
    )
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output


def test_replaced_analyzer_surfaces_are_not_registered():
    for args in (
        ("analyzer", "schema", "template"),
        ("analyzer", "schema", "suggest"),
        ("analyzer", "test", "invoice_v1", "--samples", "samples"),
    ):
        result = _run(*args)
        assert result.exit_code == 2
