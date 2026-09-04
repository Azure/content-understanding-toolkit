"""Compatibility exports for schema validation now owned by ``cu-cli-core``."""

from cu_cli_core.schema_validation import (
    ALLOWED_METHODS,
    ALLOWED_TYPES,
    Finding,
    ValidationResult,
    custom_analyzer_id_error,
    first_error_line,
    parse_and_validate,
    schema_pinned_version,
    validate_schema,
)

__all__ = [
    "ALLOWED_METHODS",
    "ALLOWED_TYPES",
    "Finding",
    "ValidationResult",
    "custom_analyzer_id_error",
    "first_error_line",
    "parse_and_validate",
    "schema_pinned_version",
    "validate_schema",
]
