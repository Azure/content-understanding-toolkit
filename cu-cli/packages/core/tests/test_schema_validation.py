"""Schema validation: exact messages, exit-2 semantics, warnings."""

from __future__ import annotations

import json

from cu_cli_core.schema_validation import (ALLOWED_TYPES, parse_and_validate,

                                    schema_pinned_version, validate_schema)



import pytest

pytestmark = pytest.mark.unit

def _base_schema():
    return {
        "analyzerId": "my_analyzer_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {
            "fields": {
                "vendor": {"type": "string", "method": "extract",
                           "description": "Full legal vendor name from the header."},
            }
        },
    }


def test_valid_schema_ok():
    assert validate_schema(_base_schema()).ok


def test_bad_field_type_exact_message():
    body = _base_schema()
    body["fieldSchema"]["fields"]["dob"] = {
        "type": "datetime", "method": "extract",
        "description": "date of birth as printed on the form",
    }
    res = validate_schema(body)
    assert not res.ok
    msgs = {(e.path, e.msg) for e in res.errors}
    expected_types = "[" + ", ".join(ALLOWED_TYPES) + "]"
    assert ("fieldSchema.fields.dob.type",
            f"must be one of {expected_types}, got 'datetime'.") in msgs


def test_allowed_types_match_design_doc():
    assert ALLOWED_TYPES == ["array", "boolean", "date", "integer", "json",
                             "number", "object", "string", "time"]


def test_classify_requires_enum():
    body = _base_schema()
    body["fieldSchema"]["fields"]["kind"] = {
        "type": "string", "method": "classify",
        "description": "the document category from a closed set",
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.kind.enum" for e in res.errors)


def test_bad_analyzer_id_rejected():
    body = _base_schema()
    body["analyzerId"] = "has-dash"
    res = validate_schema(body)
    finding = next(e for e in res.errors if e.path == "analyzerId")
    assert "Hyphens are reserved for service-provided prebuilt analyzer IDs" in finding.msg
    assert "prebuilt-invoice" in finding.msg


def test_parse_and_validate_reports_bad_json():
    res, body = parse_and_validate("{not json")
    assert not res.ok
    assert body is None
    assert res.errors[0].path == "$"


@pytest.mark.parametrize("payload", [[], None, "schema", 42, True])
def test_parse_and_validate_rejects_non_object_roots(payload):
    res, body = parse_and_validate(json.dumps(payload))
    assert not res.ok
    assert body is None
    assert res.errors[0].path == "$"
    assert res.errors[0].msg == "schema root must be a JSON object."


def test_schema_pinned_version():
    assert schema_pinned_version({"apiVersion": "2025-11-01"}) == "2025-11-01"
    assert schema_pinned_version({}) is None


def test_missing_type_is_error():
    body = _base_schema()
    body["fieldSchema"]["fields"]["x"] = {"method": "extract", "description": "some field value here"}
    res = validate_schema(body)
    assert any(e.path == "fieldSchema.fields.x.type" for e in res.errors)


def test_missing_method_is_allowed():
    body = _base_schema()
    body["fieldSchema"]["fields"]["invoice_total"] = {
        "type": "number",
        "description": "Total invoice amount extracted from the summary section.",
    }
    res = validate_schema(body)
    assert res.ok


def test_classification_schema_with_content_categories_is_valid_without_field_schema():
    body = {
        "analyzerId": "classifier_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "config": {
            "enableSegment": True,
            "contentCategories": {
                "invoice": {
                    "description": "Invoices that should be routed to an invoice analyzer.",
                    "analyzerId": "invoice_extractor_v1",
                },
                "other": {
                    "description": "Fallback category when no specific category matches.",
                },
            },
        },
    }
    res = validate_schema(body)
    assert res.ok
    assert not any(w.path == "fieldSchema" for w in res.warnings)


def test_2025_11_01_json_field_type_is_valid():
    body = _base_schema()
    body["fieldSchema"]["fields"]["metadata"] = {
        "type": "json",
        "method": "extract",
        "description": "Structured metadata object from the form footer as raw JSON.",
    }
    res = validate_schema(body)
    assert res.ok


def test_field_examples_and_enum_descriptions_are_accepted():
    body = _base_schema()
    body["fieldSchema"]["fields"]["document_type"] = {
        "type": "string",
        "method": "classify",
        "description": "Classify document into a stable processing type.",
        "enum": ["invoice", "receipt", "other"],
        "enumDescriptions": {
            "invoice": "Supplier invoice requesting payment.",
            "receipt": "Point-of-sale receipt.",
            "other": "Anything that does not match invoice or receipt.",
        },
        "examples": ["invoice"],
    }
    res = validate_schema(body)
    assert res.ok


@pytest.mark.parametrize("api_version", ["2025-11-01", "2026-06-01-preview"])
def test_ref_definition_is_rejected_for_supported_api_versions(api_version):
    body = _base_schema()
    body["fieldSchema"]["fields"]["line_item"] = {
        "$ref": "#/fieldSchema/definitions/line_item",
        "description": "Reference a reusable line item definition.",
    }
    body["fieldSchema"]["definitions"] = {
        "line_item": {
            "type": "object",
            "description": "A line item object with amount and description.",
            "properties": {
                "description": {
                    "type": "string",
                    "method": "extract",
                    "description": "Line item description text.",
                },
                "amount": {
                    "type": "number",
                    "method": "extract",
                    "description": "Line item amount value.",
                },
            },
        }
    }
    res = validate_schema(body, api_version=api_version)
    assert not res.ok
    assert (
        "fieldSchema.fields.line_item.$ref",
        "`$ref` is not currently supported in analyzer field schemas; "
        "inline the field definition.",
    ) in {(error.path, error.msg) for error in res.errors}


def test_ref_is_rejected_recursively_in_fields_items_properties_and_definitions():
    body = _base_schema()
    body["fieldSchema"]["fields"].update({
        "direct": {
            "type": "string",
            "$ref": "#/fieldSchema/definitions/text",
        },
        "rows": {
            "type": "array",
            "items": {"$ref": "#/fieldSchema/definitions/row"},
        },
        "container": {
            "type": "object",
            "properties": {
                "nested": {"$ref": "#/fieldSchema/definitions/text"},
            },
        },
    })
    body["fieldSchema"]["definitions"] = {
        "alias": {"$ref": "#/fieldSchema/definitions/text"},
    }

    res = validate_schema(body)

    assert not res.ok
    assert {
        error.path for error in res.errors if error.path.endswith(".$ref")
    } == {
        "fieldSchema.fields.direct.$ref",
        "fieldSchema.fields.rows.items.$ref",
        "fieldSchema.fields.container.properties.nested.$ref",
        "fieldSchema.definitions.alias.$ref",
    }


def test_classify_requires_two_distinct_enum_values():
    body = _base_schema()
    body["fieldSchema"]["fields"]["kind"] = {
        "type": "string",
        "method": "classify",
        "description": "Document type category from closed set.",
        "enum": ["invoice", "invoice"],
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.kind.enum" for e in res.errors)


def test_array_field_requires_items_object():
    body = _base_schema()
    body["fieldSchema"]["fields"]["rows"] = {
        "type": "array",
        "method": "extract",
        "description": "Extract table rows.",
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.rows.items" for e in res.errors)


def test_array_field_valid_with_string_items():
    body = _base_schema()
    body["fieldSchema"]["fields"]["tags"] = {
        "type": "array",
        "method": "extract",
        "description": "List of tags extracted from the document.",
        "items": {
            "type": "string",
            "method": "extract",
            "description": "A single tag value.",
        },
    }
    res = validate_schema(body)
    assert res.ok


def test_array_field_valid_with_object_items_table_like():
    body = _base_schema()
    body["fieldSchema"]["fields"]["line_items"] = {
        "type": "array",
        "method": "extract",
        "description": "Table rows represented as an array of objects.",
        "items": {
            "type": "object",
            "description": "One table row.",
            "properties": {
                "description": {
                    "type": "string",
                    "method": "extract",
                    "description": "Line-item description text.",
                },
                "amount": {
                    "type": "number",
                    "method": "extract",
                    "description": "Line-item amount.",
                },
            },
        },
    }
    res = validate_schema(body)
    assert res.ok


def test_tables_with_same_columns_are_valid_when_row_schema_is_inlined():
    body = _base_schema()
    for field_name, description in (
        ("purchased_items", "Items purchased on the invoice."),
        ("returned_items", "Items returned on the invoice."),
    ):
        body["fieldSchema"]["fields"][field_name] = {
            "type": "array",
            "method": "extract",
            "description": description,
            "items": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "method": "extract",
                        "description": "Description of the line item.",
                    },
                    "amount": {
                        "type": "number",
                        "method": "extract",
                        "description": "Amount for the line item.",
                    },
                },
            },
        }

    assert validate_schema(body).ok


def test_array_items_missing_type_is_error():
    body = _base_schema()
    body["fieldSchema"]["fields"]["rows"] = {
        "type": "array",
        "method": "extract",
        "description": "Rows with malformed item definition.",
        "items": {
            "method": "extract",
            "description": "Missing item type should be rejected.",
        },
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.rows.items.type" for e in res.errors)


def test_array_items_object_without_properties_is_error():
    body = _base_schema()
    body["fieldSchema"]["fields"]["rows"] = {
        "type": "array",
        "method": "extract",
        "description": "Rows where item object is missing properties.",
        "items": {
            "type": "object",
            "description": "Object item missing properties should fail.",
        },
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.rows.items.properties" for e in res.errors)


def test_object_field_requires_properties_or_ref():
    body = _base_schema()
    body["fieldSchema"]["fields"]["party"] = {
        "type": "object",
        "method": "extract",
        "description": "An object field without properties should fail.",
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "fieldSchema.fields.party.properties" for e in res.errors)


def test_content_categories_must_be_non_empty_object():
    body = {
        "analyzerId": "classifier_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "config": {"enableSegment": True, "contentCategories": {}},
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "config.contentCategories" for e in res.errors)


def test_content_category_analyzer_id_pattern_enforced():
    body = {
        "analyzerId": "classifier_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "config": {
            "enableSegment": True,
            "contentCategories": {
                "invoice": {
                    "description": "Invoice category.",
                    "analyzerId": "bad analyzer id",
                }
            },
        },
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "config.contentCategories.invoice.analyzerId" for e in res.errors)


def test_config_boolean_fields_must_be_boolean():
    body = _base_schema()
    body["config"] = {
        "enableSegment": "yes",
        "segmentPerPage": 1,
        "estimateFieldSourceAndConfidence": "false",
    }
    res = validate_schema(body)
    assert not res.ok
    assert any(e.path == "config.enableSegment" for e in res.errors)
    assert any(e.path == "config.segmentPerPage" for e in res.errors)
    assert any(e.path == "config.estimateFieldSourceAndConfidence" for e in res.errors)
