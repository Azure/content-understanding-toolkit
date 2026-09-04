# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for spec-backed validation against the bundled CU OpenAPI spec."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from cu_cli.apiversion import DEFAULT_API_VERSION
from cu_cli.cli import main
from cu_cli.schema_validate import ALLOWED_METHODS, ALLOWED_TYPES
from cu_cli.spec_validate import (
    spec_allowed_methods,
    spec_allowed_types,
    spec_available,
    validate_against_spec,
)

import pytest

pytestmark = pytest.mark.unit

PREVIEW_VERSION = "2026-06-01-preview"


def _run(*args, **kwargs):
    return CliRunner().invoke(main, list(args), **kwargs)


def _valid_body():
    return {
        "apiVersion": DEFAULT_API_VERSION,
        "analyzerId": "spec_test_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-5.2", "embedding": "text-embedding-3-large"},
        "fieldSchema": {
            "fields": {
                "vendor": {
                    "type": "string",
                    "method": "extract",
                    "description": "Full legal vendor name from the invoice header.",
                }
            }
        },
    }


def test_spec_is_bundled_and_available():
    assert spec_available(DEFAULT_API_VERSION) is True
    assert spec_available(PREVIEW_VERSION) is True


def test_allowed_lists_are_derived_from_the_spec():
    # schema_validate derives its lists from the bundled spec's enums.
    assert ALLOWED_TYPES == spec_allowed_types(DEFAULT_API_VERSION)
    assert ALLOWED_METHODS == spec_allowed_methods(DEFAULT_API_VERSION)
    assert "string" in ALLOWED_TYPES and "datetime" not in ALLOWED_TYPES
    assert ALLOWED_METHODS == ["classify", "extract", "generate"]


def test_validate_against_spec_accepts_valid_create_body():
    res = validate_against_spec(_valid_body())
    assert res.ok, [(e.path, e.msg) for e in res.errors]


def test_preview_spec_accepts_valid_create_body():
    body = _valid_body()
    body["apiVersion"] = PREVIEW_VERSION
    res = validate_against_spec(body, api_version=PREVIEW_VERSION)
    assert res.ok, [(e.path, e.msg) for e in res.errors]


def test_validate_against_spec_flags_bad_field_type():
    body = _valid_body()
    body["fieldSchema"]["fields"]["vendor"]["type"] = "datetime"
    res = validate_against_spec(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.vendor.type" for e in res.errors)


def test_validate_against_spec_flags_bad_method():
    body = _valid_body()
    body["fieldSchema"]["fields"]["vendor"]["method"] = "conjure"
    res = validate_against_spec(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.vendor.method" for e in res.errors)


def test_validate_against_spec_catches_config_type_beyond_curated_rules():
    # `config.enableOcr` must be a boolean per the spec; the curated validator
    # doesn't check this key, so the spec pass adds real coverage.
    body = _valid_body()
    body["config"] = {"enableOcr": "yes"}
    res = validate_against_spec(body)
    assert not res.ok
    assert any(e.path == "config.enableOcr" for e in res.errors)


def test_validate_against_spec_non_object_root():
    res = validate_against_spec(["not", "an", "object"])
    assert not res.ok


def test_cli_validate_spec_flag_accepts_valid(tmp_path: Path):
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(_valid_body()), encoding="utf-8")
    res = _run("analyzer", "validate", str(p), "--spec")
    assert res.exit_code == 0, res.output


def test_cli_validate_spec_flag_catches_spec_only_violation(tmp_path: Path):
    body = _valid_body()
    body["config"] = {"enableOcr": "yes"}  # passes curated checks, fails the spec
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(body), encoding="utf-8")

    # Without --spec the curated validator does not check enableOcr -> exit 0.
    assert _run("analyzer", "validate", str(p)).exit_code == 0
    # With --spec the bundled contract rejects it -> exit 2.
    res = _run("analyzer", "validate", str(p), "--spec")
    assert res.exit_code == 2, res.output
    assert "enableOcr" in res.output
