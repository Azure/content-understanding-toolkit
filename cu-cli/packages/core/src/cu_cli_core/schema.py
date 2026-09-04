# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Custom-analyzer schema authoring (Click-free).

Pure helpers to generate a starter analyzer schema and to pick a template
completion model, plus a client-injected ``suggest_schema_from_sample`` that
derives a field schema from one local document via ``prebuilt-documentFieldSchema``.

Nothing here prints or resolves auth — callers pass a built client and the
resolved completion model; the command layer handles config, client
construction, and any user-facing warnings.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Mapping, Protocol

from .defaults import COMPLETION_MODEL_PREFERENCE, PREFERRED_EMBEDDING_MODEL
from .errors import ValidationError
DOCUMENT_SAMPLE_EXTS = frozenset(
    {
        ".pdf",
        ".tiff",
        ".docx",
        ".xlsx",
        ".pptx",
        ".docm",
        ".xlsm",
        ".pptm",
        ".doc",
        ".xls",
        ".ppt",
        ".odt",
        ".ods",
        ".odp",
        ".epub",
        ".txt",
        ".html",
        ".md",
        ".rtf",
        ".xml",
        ".json",
        ".csv",
        ".tsv",
        ".kml",
        ".eml",
        ".msg",
    }
)

MODALITY_BASE: dict[str, str] = {
    "document": "prebuilt-document",
    "image": "prebuilt-image",
    "audio": "prebuilt-audio",
    "video": "prebuilt-video",
}

FIELD_SCHEMA_SUGGEST_ANALYZER_ID = "prebuilt-documentFieldSchema"


class _ModelDeploymentConfig(Protocol):
    @property
    def model_deployments(self) -> Mapping[str, str]: ...


def starter_schema(
    analyzer_id: str,
    base: str,
    modality: str,
    api_version: str,
    *,
    completion_model: str,
    template_type: str,
) -> dict[str, Any]:
    """A minimal, valid analyzer schema for an agent/human to fill in.

    The resolved ``apiVersion`` is stamped so authored schemas are
    self-describing.
    """
    extraction_fields = {
        "example_string_field": {
            "type": "string",
            "method": "extract",
            "description": (
                "TODO: replace this field. Describe specifically what to extract, "
                "where it appears in the document, and any formatting expectations. "
                "Example: 'Full legal name of the vendor as printed in the invoice header.'"
            ),
            "estimateSourceAndConfidence": True,
        },
        "example_number_field": {
            "type": "number",
            "method": "extract",
            "description": (
                "TODO: replace this field. Use for amounts, totals, rates, or "
                "other numeric values. Example: 'Invoice total amount before tax.'"
            ),
            "estimateSourceAndConfidence": True,
        },
        "example_summary": {
            "type": "string",
            "method": "generate",
            "description": (
                "Provide a one-line summary of the document's main purpose and "
                "key outcome. Keep it concise and factual."
            ),
        },
        "example_classify_field": {
            "type": "string",
            "method": "classify",
            "description": (
                "TODO: replace this field. Use `classify` only when the value comes "
                "from a closed set. Always include `enum`."
            ),
            "enum": ["option_a", "option_b", "other"],
            "enumDescriptions": {
                "option_a": "Primary category when the content strongly matches pattern A.",
                "option_b": "Secondary category when the content matches pattern B.",
                "other": "Fallback category when neither option_a nor option_b applies.",
            },
        },
        "example_table_field": {
            "type": "array",
            "method": "extract",
            "description": (
                "TODO: replace this field. Use for repeating table rows such as "
                "line items, transactions, or schedule entries."
            ),
            "items": {
                "type": "object",
                "description": "One extracted table row.",
                "properties": {
                    "column_description": {
                        "type": "string",
                        "method": "extract",
                        "description": "Text content for the description column.",
                    },
                    "column_amount": {
                        "type": "number",
                        "method": "extract",
                        "description": "Numeric value in the amount column.",
                    },
                    "column_category": {
                        "type": "string",
                        "method": "classify",
                        "description": (
                            "Classify the column value into a stable category used by "
                            "downstream business logic."
                        ),
                        "enum": ["product", "service", "fee", "tax", "other"],
                        "enumDescriptions": {
                            "product": "Physical good or inventory item.",
                            "service": "Labor or service charge.",
                            "fee": "Non-tax fee such as handling or processing.",
                            "tax": "Tax line item.",
                            "other": "Row does not fit the predefined categories.",
                        },
                    },
                },
            },
        },
    }

    # Categories are description-only by default so the emitted template can be
    # created immediately. Routing a category to another analyzer is optional and
    # requires that analyzer (prebuilt or custom) to already exist — otherwise the
    # service rejects create with InvalidAnalyzerId. See the description below.
    classification_categories = {
        "invoice": {
            "description": (
                "Vendor invoices requesting payment for goods or services, typically "
                "including vendor details, line items, totals, and payment terms."
            ),
        },
        "purchase_order": {
            "description": (
                "Purchase orders that authorize a purchase, typically including a PO "
                "number, buyer/supplier details, ordered items, quantities, and prices."
            ),
        },
        "receipt": {
            "description": (
                "Retail or expense receipts confirming a completed payment, typically "
                "including merchant, date, purchased items, and total paid."
            ),
        },
        "other": {
            "description": (
                "Fallback category for content that does not match any category above."
            ),
        },
    }

    if template_type == "classification":
        return {
            "apiVersion": api_version,
            "analyzerId": analyzer_id,
            "description": (
                "TODO: classify inputs into the categories below; give each a clear "
                "description. Optional: add \"analyzerId\": \"<existing-analyzer-id>\" to a "
                "category to route matching content to that analyzer for extraction "
                "(the analyzer — prebuilt like prebuilt-invoice or a custom one — must "
                "already exist, otherwise create fails with InvalidAnalyzerId)."
            ),
            "baseAnalyzerId": base,
            "config": {
                "estimateFieldSourceAndConfidence": True,
                "enableSegment": True,
                "contentCategories": classification_categories,
            },
            "models": {"completion": completion_model, "embedding": PREFERRED_EMBEDDING_MODEL},
        }

    return {
        "apiVersion": api_version,
        "analyzerId": analyzer_id,
        "description": f"TODO: one-sentence description of what this {modality} analyzer extracts.",
        "baseAnalyzerId": base,
        "fieldSchema": {
            "name": f"{analyzer_id.replace('-', '_')}_schema",
            "description": "TODO: one-sentence summary of the extraction.",
            "fields": extraction_fields,
        },
        "config": {"estimateFieldSourceAndConfidence": True},
        "models": {"completion": completion_model, "embedding": PREFERRED_EMBEDDING_MODEL},
    }


def suggested_fields_from_result(result: Any) -> dict[str, Any]:
    """Extract the ``schema.valueJson`` field map from a suggestion result."""
    contents = getattr(result, "contents", None) or []
    if not contents:
        return {}
    for content in contents:
        fields = getattr(content, "fields", None)
        if fields is None and isinstance(content, dict):
            fields = content.get("fields")
        if not isinstance(fields, dict):
            if fields is not None and hasattr(fields, "as_dict"):
                fields = fields.as_dict()
            else:
                continue
        schema_field = fields.get("schema")
        if schema_field is None:
            continue
        if hasattr(schema_field, "as_dict"):
            schema_field = schema_field.as_dict()
        if not isinstance(schema_field, dict):
            continue

        value_json = schema_field.get("valueJson")
        if isinstance(value_json, dict) and value_json:
            return value_json
    return {}


def _add_placeholder_descriptions(fields: dict[str, Any]) -> None:
    """Fill description gaps in service-suggested field definitions."""

    def visit(definition: Any, placeholder: str) -> None:
        if not isinstance(definition, dict):
            return

        description = definition.get("description")
        if description is None or (isinstance(description, str) and not description.strip()):
            definition["description"] = placeholder

        properties = definition.get("properties")
        if isinstance(properties, dict):
            for property_name, property_definition in properties.items():
                visit(
                    property_definition,
                    f"TODO: describe the '{property_name}' field.",
                )

        items = definition.get("items")
        if isinstance(items, dict):
            visit(
                items,
                "TODO: describe one item in this array.",
            )

    for field_name, field_definition in fields.items():
        visit(
            field_definition,
            f"TODO: describe the '{field_name}' field.",
        )


def template_completion_model(cfg: _ModelDeploymentConfig) -> str:
    """Pick a completion model to stamp into a generated schema template."""
    for model in COMPLETION_MODEL_PREFERENCE:
        if model in cfg.model_deployments:
            return model

    for model in cfg.model_deployments:
        if model.startswith("prebuilt-analyzer-"):
            continue
        if model == PREFERRED_EMBEDDING_MODEL or model.endswith("-mini"):
            continue
        return model

    # Default completion model when none is configured (recommended: gpt-5.2).
    return COMPLETION_MODEL_PREFERENCE[0]


def validate_document_sample(sample_path: Path) -> None:
    """Raise a validation error if *sample_path* is unusable."""
    if not sample_path.exists() or not sample_path.is_file():
        raise ValidationError(f"sample file not found: {sample_path}")
    if sample_path.suffix.lower() not in DOCUMENT_SAMPLE_EXTS:
        raise ValidationError(
            f"--from-sample expects a document file, got '{sample_path.suffix}'.",
            hint="supported document formats include pdf/docx/pptx/xlsx/txt/html.",
        )


def suggest_schema_from_sample(
    client: Any,
    *,
    sample_path: Path,
    analyzer_id: str,
    api_version: str,
    completion_model: str,
) -> tuple[dict[str, Any], bool]:
    """Suggest an extraction schema from one document sample via *client*.

    Returns ``(payload, found_fields)`` where ``found_fields`` is ``True`` when
    the service returned a non-empty field schema (otherwise ``payload`` is the
    default extraction template). MVP behavior intentionally supports exactly
    one local document sample.
    """
    validate_document_sample(sample_path)

    payload = starter_schema(
        analyzer_id,
        base=MODALITY_BASE["document"],
        modality="document",
        api_version=api_version,
        completion_model=completion_model,
        template_type="extraction",
    )

    sample_bytes = sample_path.read_bytes()
    sample_mime = mimetypes.guess_type(sample_path.name)[0] or "application/octet-stream"

    input_payload: Any
    try:
        from azure.ai.contentunderstanding import models as _cu_models

        input_cls = getattr(_cu_models, "AnalyzeInput", None) or getattr(
            _cu_models, "AnalysisInput", None
        )
        if input_cls is None:
            raise AttributeError("AnalyzeInput/AnalysisInput model is not available")

        input_payload = input_cls(
            name=sample_path.name,
            mime_type=sample_mime,
            data=sample_bytes,
        )
    except (ImportError, AttributeError, TypeError):
        # SDK compatibility: older wheels may not expose AnalyzeInput.
        input_payload = {
            "name": sample_path.name,
            "mime_type": sample_mime,
            "data": sample_bytes,
        }

    poller = client.begin_analyze(
        FIELD_SCHEMA_SUGGEST_ANALYZER_ID,
        inputs=[input_payload],
    )
    result = poller.result()
    suggested_fields = suggested_fields_from_result(result)
    if suggested_fields:
        _add_placeholder_descriptions(suggested_fields)
        payload["fieldSchema"]["fields"] = suggested_fields
        payload["description"] = (
            f"Suggested from sample '{sample_path.name}' using prebuilt-documentFieldSchema."
        )
        payload["fieldSchema"]["description"] = (
            "Suggested extraction schema derived from one sample document."
        )
        return payload, True
    return payload, False
