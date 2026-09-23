# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Integration tests for analyzer lifecycle commands.

Covers ``analyzer list/show/create/delete/test`` and the schema create ->
create → show → delete roundtrip, including classifier routing with prebuilt
and custom analyzers.

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import json
import os
import time
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


def _write_schema(path: str = "schema.json", analyzer_id: str = "cu_cli_test_v1") -> Path:
    body = {
        "apiVersion": "2025-11-01",
        "analyzerId": analyzer_id,
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": _resolved_completion_model()},
        "fieldSchema": {"fields": {
            "vendor_name": {"type": "string", "method": "extract",
                            "description": "Full legal vendor name from the invoice header."},
        }},
    }
    p = Path.cwd() / path
    p.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return p


# Analyzer/classifier IDs used by the schema-template lifecycle tests. Distinct
# from the other scenarios so their cassettes never collide.
_TEMPLATE_ANALYZER_ID = "cu_cli_tmpl_analyzer_v1"
_ROUTE_TARGET_ID = "cu_cli_route_target_v1"
_TEMPLATE_CLASSIFIER_ID = "cu_cli_tmpl_classifier_v1"
_COPY_TARGET_ID = "cu_cli_copy_target_v1"


def _build_classifier_schema_with_routing(path: str, route_target_id: str) -> Path:
    """Emit a classification template and route two categories to real analyzers.

    One category routes to a prebuilt analyzer (``prebuilt-invoice``) and another
    to a custom analyzer that the test creates first. The remaining categories are
    left description-only. This proves both prebuilt and custom routing work.
    """
    res = _run(
        "analyzer", "schema", "create",
        "--name", _TEMPLATE_CLASSIFIER_ID,
        "--type", "classification",
        "--output-file", path,
    )
    assert res.exit_code == 0, res.output
    p = Path.cwd() / path
    body = json.loads(p.read_text(encoding="utf-8"))
    body.setdefault("models", {})["completion"] = _resolved_completion_model()
    categories = body["config"]["contentCategories"]
    categories["invoice"]["analyzerId"] = "prebuilt-invoice"
    categories["purchase_order"]["analyzerId"] = route_target_id
    p.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return p


def test_scenario_3_analyzer_list_json(cloud_project):
    with use_cassette("analyzer_list"):
        res = _run("analyzer", "list", "--json")
    assert res.exit_code == 0, res.output
    json.loads(res.output[res.output.find("["):])  # output includes context lines


def test_scenario_3_analyzer_list_custom_sorted(cloud_project):
    with use_cassette("analyzer_list"):
        res = _run(
            "analyzer", "list", "--json", "--kind", "custom",
            "--sort-by", "analyzerId",
        )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output[res.output.find("["):])
    ids = [item["analyzerId"] for item in payload]
    assert all(not aid.startswith("prebuilt-") for aid in ids)
    assert ids == sorted(ids)


def test_scenario_3_analyzer_list_sorted_by_created_at(cloud_project):
    with use_cassette("analyzer_list"):
        res = _run("analyzer", "list", "--json", "--sort-by", "createdAt")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output[res.output.find("["):])
    created = [item.get("createdAt", "") for item in payload]
    assert created == sorted(created)


def test_scenario_3_analyzer_lifecycle_create_show_delete(cloud_project):
    _write_schema()
    with use_cassette("analyzer_create"):
        res = _run("analyzer", "create", "cu_cli_test_v1", "--schema", "schema.json")
    _require_create_success(res)

    with use_cassette("analyzer_show"):
        res = _run("analyzer", "show", "cu_cli_test_v1")
    assert res.exit_code == 0, res.output

    with use_cassette("analyzer_delete"):
        res = _run("analyzer", "delete", "cu_cli_test_v1", "--yes")
    assert res.exit_code == 0, res.output


@pytest.mark.skipif(
    mode() == "playback",
    reason="copy lifecycle requires a live custom source analyzer",
)
def test_analyzer_copy_same_resource_live(cloud_project):
    """Copy a ready custom analyzer, verify it, and clean up only the target.

    Record/live mode requires ``CU_TEST_REC_COPY_SOURCE_ID`` to name a stable,
    ready custom analyzer that the test never modifies.
    """
    source_id = os.getenv("CU_TEST_REC_COPY_SOURCE_ID")
    if not source_id:
        pytest.skip("CU_TEST_REC_COPY_SOURCE_ID is required for record/live mode")
    target_created = False
    try:
        res = _run("analyzer", "copy", source_id, _COPY_TARGET_ID)
        assert res.exit_code == 0, res.output
        target_created = True

        res = _run("analyzer", "show", _COPY_TARGET_ID)
        assert res.exit_code == 0, res.output
        payload = json.loads(res.output[res.output.find("{"):])
        assert payload["analyzerId"] == _COPY_TARGET_ID
    finally:
        if target_created:
            res = _run("analyzer", "delete", _COPY_TARGET_ID, "--yes")
            assert res.exit_code == 0, res.output


@pytest.mark.skipif(
    mode() != "live",
    reason="cross-resource lifecycle requires two live Azure resources",
)
def test_analyzer_copy_cross_resource_live(cloud_project):
    """Live-only grant/copy lifecycle with unique IDs and scoped cleanup.

    Required environment variables are deliberately recording-harness-prefixed
    so the test isolation fixture preserves them:

    * ``CU_TEST_REC_ENDPOINT`` — source Foundry endpoint
    * ``CU_TEST_REC_SOURCE_ARM_ID`` — source account ARM ID
    * ``CU_TEST_REC_TARGET_ENDPOINT`` — target Foundry endpoint
    * ``CU_TEST_REC_TARGET_ARM_ID`` — target account ARM ID
    """
    source_endpoint = os.getenv("CU_TEST_REC_ENDPOINT")
    source_arm = os.getenv("CU_TEST_REC_SOURCE_ARM_ID")
    target_endpoint = os.getenv("CU_TEST_REC_TARGET_ENDPOINT")
    target_arm = os.getenv("CU_TEST_REC_TARGET_ARM_ID")
    if not all((source_endpoint, source_arm, target_endpoint, target_arm)):
        pytest.skip("cross-resource live-test environment is incomplete")

    unique = f"{int(time.time())}"
    source_id = f"cu_cli_xcopy_source_{unique}"
    target_id = f"cu_cli_xcopy_target_{unique}"
    _write_schema("cross_copy_source.json", analyzer_id=source_id)
    source_created = False
    target_created = False
    try:
        res = _run(
            "analyzer",
            "create",
            source_id,
            "--schema",
            "cross_copy_source.json",
            "--endpoint",
            source_endpoint,
            "--auth-mode",
            "login",
        )
        _require_create_success(res)
        source_created = True

        res = _run(
            "analyzer",
            "copy",
            source_id,
            target_id,
            "--source-resource",
            source_arm,
            "--destination-resource",
            target_arm,
        )
        assert res.exit_code == 0, res.output
        target_created = True
        assert "granting temporary copy authorization" in res.output

        res = _run(
            "analyzer",
            "show",
            target_id,
            "--endpoint",
            target_endpoint,
            "--auth-mode",
            "login",
        )
        assert res.exit_code == 0, res.output
    finally:
        # IDs are unique to this invocation; never delete a pre-existing target.
        if target_created:
            res = _run(
                "analyzer",
                "delete",
                target_id,
                "--endpoint",
                target_endpoint,
                "--auth-mode",
                "login",
                "--yes",
            )
            assert res.exit_code == 0, res.output
        if source_created:
            res = _run(
                "analyzer",
                "delete",
                source_id,
                "--endpoint",
                source_endpoint,
                "--auth-mode",
                "login",
                "--yes",
            )
            assert res.exit_code == 0, res.output

def test_scenario_3_analyzer_test_reports_fields(cloud_project):
    _copy_sample()
    with use_cassette("analyzer_test"):
        res = _run(
            "analyzer", "test", "prebuilt-invoice", "sample_invoice.pdf", "--json"
        )
    assert res.exit_code == 0, res.output
    report = json.loads(res.output[res.output.find("{"):])
    assert "summary" in report and "samples" in report
    assert report["summary"]["disclaimer"].startswith("This is not a real accuracy benchmark")
    assert "AmountDue.Amount" in report["summary"]["fields"]
    assert "LineItems[].Description" in report["summary"]["fields"]
    assert not any(name.endswith(".confidence") or name.endswith(".type")
                   for name in report["summary"]["fields"])
    assert report["summary"]["fields"]["AmountDue.Amount"]["meanConfidence"] is not None


def test_schema_create_template_creates_extraction_analyzer(cloud_project):
    """Offline ``schema create`` output must create a working analyzer."""
    res = _run(
        "analyzer", "schema", "create",
        "--name", _TEMPLATE_ANALYZER_ID,
        "--output-file", "tmpl_analyzer.json",
    )
    assert res.exit_code == 0, res.output

    if mode() in {"live", "record"}:
        _rewrite_schema_completion(Path("tmpl_analyzer.json"), _resolved_completion_model())

    res = _run("analyzer", "validate", "tmpl_analyzer.json")
    assert res.exit_code == 0, res.output

    with use_cassette("template_analyzer_create"):
        res = _run(
            "analyzer", "create", _TEMPLATE_ANALYZER_ID,
            "--schema", "tmpl_analyzer.json",
        )
    _require_create_success(res)

    with use_cassette("template_analyzer_show"):
        res = _run("analyzer", "show", _TEMPLATE_ANALYZER_ID)
    assert res.exit_code == 0, res.output

    with use_cassette("template_analyzer_delete"):
        res = _run("analyzer", "delete", _TEMPLATE_ANALYZER_ID, "--yes")
    assert res.exit_code == 0, res.output


def test_schema_create_template_creates_classifier_with_prebuilt_and_custom_routing(
    cloud_project,
):
    """``schema create --type classification`` must create a working
    classifier, including routing to a prebuilt analyzer and a custom analyzer."""
    # 1) Create a custom analyzer to serve as a routing target.
    _write_schema("route_target.json", analyzer_id=_ROUTE_TARGET_ID)
    with use_cassette("route_target_create"):
        res = _run(
            "analyzer", "create", _ROUTE_TARGET_ID, "--schema", "route_target.json"
        )
    _require_create_success(res)

    # 2) Build a classifier from the template, routing one category to a prebuilt
    #    analyzer and another to the custom analyzer created above.
    _build_classifier_schema_with_routing("classifier.json", _ROUTE_TARGET_ID)
    res = _run("analyzer", "validate", "classifier.json")
    assert res.exit_code == 0, res.output

    with use_cassette("classifier_route_create"):
        res = _run(
            "analyzer", "create", _TEMPLATE_CLASSIFIER_ID,
            "--schema", "classifier.json",
        )
    _require_create_success(res)

    with use_cassette("classifier_route_show"):
        res = _run("analyzer", "show", _TEMPLATE_CLASSIFIER_ID)
    assert res.exit_code == 0, res.output
    assert "prebuilt-invoice" in res.output
    assert _ROUTE_TARGET_ID in res.output

    with use_cassette("classifier_route_delete"):
        res = _run("analyzer", "delete", _TEMPLATE_CLASSIFIER_ID, "--yes")
    assert res.exit_code == 0, res.output

    with use_cassette("route_target_delete"):
        res = _run("analyzer", "delete", _ROUTE_TARGET_ID, "--yes")
    assert res.exit_code == 0, res.output
