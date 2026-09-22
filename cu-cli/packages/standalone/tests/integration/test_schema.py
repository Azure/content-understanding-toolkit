# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Integration tests for starter-schema generation and validation commands.

Covers offline and sample-derived ``analyzer schema create`` plus the
create -> validate -> analyzer lifecycle roundtrip.

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from support.command_catalog import invoke_cli
from support.recording import copy_sample_invoice, mode, use_cassette

pytestmark = pytest.mark.integration


def _run(*args):
    return invoke_cli(args)


def _resolved_completion_model() -> str:
    if mode() not in {"live", "record"}:
        return "gpt-4.1"
    res = _run("defaults", "show")
    if res.exit_code != 0:
        return "gpt-4.1"
    try:
        payload = json.loads(res.output[res.output.find("{"):])
    except Exception:  # noqa: BLE001
        return "gpt-4.1"
    mappings = payload.get("modelDeployments") or {}
    for key in (
        "prebuilt-analyzer-completion",
        "gpt-5.2",
        "gpt-4.1",
    ):
        if key in mappings:
            if key == "prebuilt-analyzer-completion" and "gpt-5.2" in mappings:
                return "gpt-5.2"
            if key == "prebuilt-analyzer-completion" and "gpt-4.1" in mappings:
                return "gpt-4.1"
            return key
    return "gpt-4.1"


def _rewrite_schema_completion(path: Path, model_name: str) -> None:
    body = json.loads(path.read_text(encoding="utf-8"))
    models = body.get("models")
    if not isinstance(models, dict):
        models = {}
        body["models"] = models
    models["completion"] = model_name
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")


def _require_create_success(res):
    if res.exit_code == 0:
        return
    if "DefaultDeploymentModelNotFound" in res.output:
        pytest.skip(
            "live endpoint defaults are not configured for required completion model; "
            "run `cu defaults set --from-profile` after configuring model_deployments."
        )
    assert res.exit_code == 0, res.output


def test_scenario_2_schema_template_validate_then_create_show_delete(cloud_project):
    res = _run(
        "analyzer", "schema", "create",
        "--name", "cu_cli_test_v1",
        "--output-file", "schema.json",
    )
    assert res.exit_code == 0, res.output

    if mode() in {"live", "record"}:
        _rewrite_schema_completion(Path("schema.json"), _resolved_completion_model())

    res = _run("analyzer", "validate", "schema.json")
    assert res.exit_code == 0, res.output

    with use_cassette("analyzer_create"):
        res = _run("analyzer", "create", "cu_cli_test_v1", "--schema", "schema.json")
    _require_create_success(res)

    with use_cassette("analyzer_show"):
        res = _run("analyzer", "show", "cu_cli_test_v1")
    assert res.exit_code == 0, res.output

    with use_cassette("analyzer_delete"):
        res = _run("analyzer", "delete", "cu_cli_test_v1", "--yes")
    assert res.exit_code == 0, res.output


def test_scenario_2_schema_create_from_sample(cloud_project, monkeypatch):
    """`cu analyzer schema create --from-sample <file>`."""
    copy_sample_invoice()
    with use_cassette("schema_suggest"):
        # region Snippet:schema_from_sample
        res = _run(
            "analyzer", "schema", "create",
            "--name", "invoice_v1",
            "--from-sample", "sample_invoice.pdf",
            "--output-file", "schema.json",
        )
        # endregion
    assert res.exit_code == 0, res.output
    body = json.loads(Path("schema.json").read_text(encoding="utf-8"))
    assert body["analyzerId"] == "invoice_v1"
    assert "fieldSchema" in body and body["fieldSchema"].get("fields")
    remote = {}
    analyzed = []

    def get_analyzer(name):
        assert name in remote, "commands must use the analyzer created earlier in this workflow"
        return SimpleNamespace(analyzer_id=name, as_dict=lambda: {"analyzerId": name, **remote[name]})

    def create_analyzer(name, definition):
        assert name not in remote
        assert definition["fieldSchema"] == body["fieldSchema"]
        assert definition["baseAnalyzerId"] == body["baseAnalyzerId"]
        remote[name] = definition
        return SimpleNamespace(result=lambda: get_analyzer(name))

    client = SimpleNamespace(
        begin_create_analyzer=create_analyzer, get_analyzer=get_analyzer,
        delete_analyzer=lambda name: remote.pop(name),
    )
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_args, **_kwargs: client)

    def analyze(_client, job):
        assert job.analyzer_id in remote
        assert Path(job.input_ref).read_bytes() == Path("sample_invoice.pdf").read_bytes()
        analyzed.append(job.analyzer_id)
        return job, {"analyzerId": job.analyzer_id, "contents": []}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", analyze)
    # region Snippet:analyzer_create
    _run("analyzer", "create", "--name", "invoice_v1", "--schema", "schema.json")
    # endregion
    assert remote["invoice_v1"]["fieldSchema"] == body["fieldSchema"]
    # region Snippet:analyzer_test_single
    _run("analyzer", "test", "invoice_v1", "sample_invoice.pdf")
    # endregion
    # region Snippet:analyze_custom
    result = _run(
        "analyze", "sample_invoice.pdf", "-a", "invoice_v1", "--json",
    )
    # endregion
    assert analyzed == ["invoice_v1", "invoice_v1"]
    assert json.loads(result.stdout)["analyzerId"] == "invoice_v1"
    # region Snippet:analyzer_show
    result = _run("analyzer", "show", "invoice_v1")
    # endregion
    assert json.loads(result.stdout)["fieldSchema"] == body["fieldSchema"]
    result = invoke_cli(("analyzer", "delete", "invoice_v1"), input="n\n")
    assert result.exit_code != 0
    assert "invoice_v1" in remote
    # region Snippet:analyzer_delete
    result = invoke_cli(
        ("analyzer", "delete", "invoice_v1"), input="y\n",
    )
    # endregion
    assert "Delete analyzer 'invoice_v1'?" in result.output
    assert remote == {}
