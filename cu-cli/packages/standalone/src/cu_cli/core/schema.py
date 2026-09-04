"""Compatibility imports for schema operations now provided by cu-cli-core."""

from cu_cli_core.schema import (
    FIELD_SCHEMA_SUGGEST_ANALYZER_ID,
    MODALITY_BASE,
    starter_schema,
    suggest_schema_from_sample,
    suggested_fields_from_result,
    template_completion_model,
    validate_document_sample,
)

__all__ = [
    "FIELD_SCHEMA_SUGGEST_ANALYZER_ID",
    "MODALITY_BASE",
    "starter_schema",
    "suggest_schema_from_sample",
    "suggested_fields_from_result",
    "template_completion_model",
    "validate_document_sample",
]
