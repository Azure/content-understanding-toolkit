"""Integration tests for starter-schema generation and validation commands.

Covers offline and sample-derived ``analyzer schema create`` plus the
create -> validate -> analyzer lifecycle roundtrip.

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from cu_cli.cli import main

from support.recording import mode, use_cassette

pytestmark = pytest.mark.integration


def _run(*args):
    return CliRunner().invoke(main, list(args))


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


def _copy_sample(name: str = "sample_invoice.pdf") -> Path:
    dest = Path.cwd() / name
    dest.write_bytes((Path(__file__).parent / "fixtures" / name).read_bytes())
    return dest


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


def test_scenario_2_schema_create_from_sample(cloud_project):
    """`cu analyzer schema create --from-sample <file>`."""
    _copy_sample()
    with use_cassette("schema_suggest"):
        res = _run(
            "analyzer", "schema", "create",
            "--from-sample", "sample_invoice.pdf",
            "--output-file", "suggested.json",
        )
    assert res.exit_code == 0, res.output
    body = json.loads(Path("suggested.json").read_text(encoding="utf-8"))
    assert "fieldSchema" in body and body["fieldSchema"].get("fields")
