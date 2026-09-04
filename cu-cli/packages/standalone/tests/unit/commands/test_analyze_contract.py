# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from cu_cli.cli import main

pytestmark = pytest.mark.unit


def _run(*args: str):
    return CliRunner().invoke(main, list(args))


@pytest.fixture
def analyze_runtime(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (
            job,
            {"status": "Succeeded", "result": {"analyzerId": job.analyzer_id}},
        ),
    )


def test_help_exposes_preview_contract_and_removes_replaced_options():
    result = _run("analyze", "--help")

    assert result.exit_code == 0
    for option in (
        "--file",
        "--source",
        "--pattern",
        "--recursive",
        "--llm-input",
        "--json",
        "--output-file",
        "--output-dir",
        "--on-existing",
        "--dry-run",
        "--report-file",
        "--auth-mode",
    ):
        assert option in result.output
    for replaced in ("--out ", "--output ", "--force", "--skip-existing", "--report "):
        assert replaced not in result.output


@pytest.mark.parametrize(
    "args",
    [
        ("input.pdf", "--file", "other.pdf"),
        ("input.pdf", "--source", "documents"),
        ("--file", "input.pdf", "--source", "documents"),
        ("--file", "input.pdf", "--pattern", "*.pdf"),
    ],
)
def test_invalid_selection_modes_fail_before_config_or_client(monkeypatch, args):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run("analyze", *args)

    assert result.exit_code == 2


def test_positional_wildcard_is_not_interpreted_by_cu(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )

    result = _run("analyze", "*.pdf")

    assert result.exit_code == 2
    assert "wildcard patterns aren't accepted" in result.output
    assert "--source" in result.output
    assert "--pattern" in result.output


def test_source_pattern_is_nonrecursive_and_accepts_unknown_extensions(
    analyze_runtime,
):
    source = Path("documents")
    source.mkdir()
    nested = source / "nested"
    nested.mkdir()
    (source / "immediate.new").write_text("immediate")
    (source / "ignored.pdf").write_text("ignored")
    (nested / "nested.new").write_text("nested")

    result = _run(
        "analyze",
        "--source",
        str(source),
        "--pattern",
        "*.new",
        "--json",
        "--output-dir",
        "results",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    assert Path("results/immediate.new.result.json").exists()
    assert not Path("results/nested/nested.new.result.json").exists()


def test_recursive_source_preserves_relative_output_path(analyze_runtime):
    nested = Path("documents/nested")
    nested.mkdir(parents=True)
    (nested / "input.pdf").write_text("input")

    result = _run(
        "analyze",
        "--source",
        "documents",
        "--recursive",
        "--json",
        "--output-dir",
        "results",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    assert Path("results/nested/input.pdf.result.json").exists()


def test_output_file_writes_single_primary_payload(analyze_runtime):
    Path("input.pdf").write_text("input")

    result = _run(
        "analyze",
        "--file",
        "input.pdf",
        "--json",
        "--output-file",
        "custom.json",
    )

    assert result.exit_code == 0, result.output
    assert json.loads(Path("custom.json").read_text())["status"] == "Succeeded"


@pytest.mark.parametrize(
    ("output_args", "directory"),
    [
        (("--output-dir", "results"), "results"),
        (("--report-file", "reports/report.json"), "reports"),
    ],
)
def test_output_write_preflight_prevents_service_call(
    analyze_runtime,
    monkeypatch,
    output_args,
    directory,
):
    Path("input.pdf").write_text("input")
    checked_directories = []

    def reject_write_check(*_args, **kwargs):
        checked_directories.append(Path(kwargs["dir"]))
        raise PermissionError("read-only output directory")

    monkeypatch.setattr(
        "cu_cli.commands.analyze.tempfile.NamedTemporaryFile",
        reject_write_check,
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run("analyze", "input.pdf", "--json", *output_args)

    assert result.exit_code == 1
    assert "permission denied" in result.output
    assert checked_directories == [Path(directory).resolve()]


def test_single_stdout_analysis_uses_registered_core_operation(
    analyze_runtime,
    monkeypatch,
):
    from cu_cli_core.operations.analysis import execute_analyze

    Path("input.pdf").write_text("input")
    resolved = []

    def resolve(identifier):
        resolved.append(identifier)
        return execute_analyze

    monkeypatch.setattr("cu_cli.commands.analyze.resolve_identifier", resolve)

    result = _run("analyze", "input.pdf", "--json")

    assert result.exit_code == 0, result.output
    assert resolved == ["cu_cli_core.operations.analysis#execute_analyze"]


def test_output_file_rejects_multiple_inputs_before_client(monkeypatch):
    Path("first.pdf").write_text("first")
    Path("second.pdf").write_text("second")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyze",
        "--file",
        "first.pdf",
        "--file",
        "second.pdf",
        "--output-file",
        "custom.json",
    )

    assert result.exit_code == 2
    assert "exactly one file" in result.output


def test_dry_run_makes_no_client_call_or_file_write(monkeypatch):
    source = Path("documents")
    source.mkdir()
    (source / "input.pdf").write_text("input")
    (source / ".DS_Store").write_text("metadata")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyze",
        "--source",
        str(source),
        "--json",
        "--output-dir",
        "results",
        "--report-file",
        "report.json",
        "--dry-run",
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert "Skipped during discovery: 1" in result.output
    rendered = "".join(result.output.split())
    assert ".DS_Store:hiddenfileskipped" in rendered
    assert "No service calls or files were written" in result.output
    assert not Path("results").exists()
    assert not Path("report.json").exists()


def test_discovery_skips_are_in_batch_report(analyze_runtime):
    source = Path("documents")
    source.mkdir()
    (source / "input.pdf").write_text("input")
    (source / ".DS_Store").write_text("metadata")

    result = _run(
        "analyze",
        "--source",
        str(source),
        "--json",
        "--output-dir",
        "results",
        "--report-file",
        "report.json",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    assert "1 skipped (discovery)" in result.output
    report = json.loads(Path("report.json").read_text())
    assert report["counts"] == {
        "succeeded": 1,
        "failed": 0,
        "skipped": 1,
        "total": 2,
    }
    skipped = next(item for item in report["results"] if item["status"] == "skipped")
    assert Path(skipped["input"]).name == ".DS_Store"
    assert skipped["reason"] == "hidden file skipped"


def test_dry_run_and_yes_are_mutually_exclusive():
    Path("input.pdf").write_text("input")

    result = _run("analyze", "input.pdf", "--dry-run", "--yes")

    assert result.exit_code == 2
    assert "--dry-run and --yes cannot be combined" in result.output


@pytest.mark.parametrize(
    ("policy", "expected_calls", "expected_code"),
    [("error", 0, 2), ("skip", 0, 0), ("reanalyze", 1, 0)],
)
def test_on_existing_policy(analyze_runtime, monkeypatch, policy, expected_calls, expected_code):
    Path("input.pdf").write_text("input")
    output = Path("result.json")
    output.write_text("existing")
    calls = {"count": 0}

    def run_one(_client, job):
        calls["count"] += 1
        return job, {"status": "Succeeded"}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)

    result = _run(
        "analyze",
        "input.pdf",
        "--json",
        "--output-file",
        str(output),
        "--on-existing",
        policy,
    )

    assert result.exit_code == expected_code, result.output
    assert calls["count"] == expected_calls


def test_report_uses_stable_statuses_and_is_written_after_success(analyze_runtime):
    Path("input.pdf").write_text("input")

    result = _run(
        "analyze",
        "input.pdf",
        "--json",
        "--report-file",
        "report.json",
    )

    assert result.exit_code == 0, result.output
    report = json.loads(Path("report.json").read_text())
    assert report["counts"] == {
        "succeeded": 1,
        "failed": 0,
        "skipped": 0,
        "total": 1,
    }
    assert report["results"][0]["status"] == "succeeded"


def test_auth_mode_is_forwarded_to_client_builder(monkeypatch):
    Path("input.pdf").write_text("input")
    captured = {}
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )

    def build_client(*_args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", build_client)
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"status": "Succeeded"}),
    )

    result = _run("analyze", "input.pdf", "--json", "--auth-mode", "login")

    assert result.exit_code == 0, result.output
    assert captured["auth_mode_override"] == "login"
