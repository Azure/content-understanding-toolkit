from pathlib import Path
from types import SimpleNamespace

import pytest

from cu_cli_core.errors import ValidationError
from cu_cli_core.schema import suggest_schema_from_sample, validate_document_sample
from cu_cli_core.schema_validation import validate_schema

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("extension", [".pdf", ".docx", ".csv", ".json", ".eml"])
def test_validate_document_sample_accepts_documented_formats(
    tmp_path: Path,
    extension: str,
) -> None:
    sample = tmp_path / f"sample{extension}"
    sample.write_bytes(b"sample")

    validate_document_sample(sample)


@pytest.mark.parametrize("extension", [".jpg", ".mp3", ".mp4", ".zip"])
def test_validate_document_sample_rejects_non_document_and_unknown_formats(
    tmp_path: Path,
    extension: str,
) -> None:
    sample = tmp_path / f"sample{extension}"
    sample.write_bytes(b"sample")

    with pytest.raises(ValidationError, match="expects a document file"):
        validate_document_sample(sample)


def test_sample_suggestion_adds_placeholder_descriptions_and_passes_strict_validation(
    tmp_path: Path,
) -> None:
    existing_description = "Line items extracted from the invoice table."
    suggested_fields = {
        "InvoiceNumber": {
            "type": "string",
            "method": "extract",
        },
        "LineItems": {
            "type": "array",
            "method": "generate",
            "description": existing_description,
            "items": {
                "type": "object",
                "method": "generate",
                "properties": {
                    "Description": {
                        "type": "string",
                        "method": "extract",
                        "description": " ",
                    },
                },
            },
        },
    }
    result = SimpleNamespace(
        contents=[
            SimpleNamespace(
                fields={"schema": {"valueJson": suggested_fields}},
            ),
        ],
    )
    client = SimpleNamespace(
        begin_analyze=lambda *_args, **_kwargs: SimpleNamespace(result=lambda: result),
    )
    sample = tmp_path / "invoice.pdf"
    sample.write_bytes(b"%PDF-1.4 sample")

    payload, found_fields = suggest_schema_from_sample(
        client,
        sample_path=sample,
        analyzer_id="invoice_v1",
        api_version="2025-11-01",
        completion_model="gpt-5.2",
    )

    fields = payload["fieldSchema"]["fields"]
    assert found_fields is True
    assert fields["InvoiceNumber"]["description"] == "TODO: describe the 'InvoiceNumber' field."
    assert fields["LineItems"]["description"] == existing_description
    assert fields["LineItems"]["items"]["description"] == (
        "TODO: describe one item in this array."
    )
    assert fields["LineItems"]["items"]["properties"]["Description"]["description"] == (
        "TODO: describe the 'Description' field."
    )
    assert validate_schema(payload, api_version="2025-11-01").warnings == []
