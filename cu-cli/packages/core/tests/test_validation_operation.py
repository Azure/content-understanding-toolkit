# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the complete core schema-validation operation."""

from __future__ import annotations

import json

import pytest

from cu_cli_core.contracts import AnalyzerValidateRequest
from cu_cli_core.operations.validation import validate_schema

pytestmark = pytest.mark.unit


def _valid_schema() -> dict:
    return {
        "apiVersion": "2025-11-01",
        "analyzerId": "invoice_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-5.2"},
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


def test_validate_schema_accepts_valid_utf8_json(tmp_path):
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps(_valid_schema()), encoding="utf-8")

    result = validate_schema(
        AnalyzerValidateRequest(schema=schema),
        api_version="2025-11-01",
    )

    assert result.ok
    assert result.errors == []


def test_validate_schema_reports_binary_input_as_validation_error(tmp_path):
    schema = tmp_path / "schema.pdf"
    schema.write_bytes(b"%PDF-1.4 \xff\xfe")

    result = validate_schema(
        AnalyzerValidateRequest(schema=schema),
        api_version="2025-11-01",
    )

    assert not result.ok
    assert result.errors[0].path == "$"
    assert "not a UTF-8 JSON schema file" in result.errors[0].msg


def test_validate_schema_applies_optional_service_contract(tmp_path):
    body = _valid_schema()
    body["config"] = {"enableOcr": "yes"}
    schema = tmp_path / "schema.json"
    schema.write_text(json.dumps(body), encoding="utf-8")

    curated = validate_schema(
        AnalyzerValidateRequest(schema=schema),
        api_version="2025-11-01",
    )
    spec_backed = validate_schema(
        AnalyzerValidateRequest(schema=schema, spec=True),
        api_version="2025-11-01",
    )

    assert curated.ok
    assert not spec_backed.ok
    assert any(error.path == "config.enableOcr" for error in spec_backed.errors)
