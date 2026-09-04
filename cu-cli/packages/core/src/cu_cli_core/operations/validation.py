# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Frontend-neutral schema validation."""

from __future__ import annotations

from ..contracts import AnalyzerValidateRequest
from ..schema_validation import Finding, ValidationResult, parse_and_validate
from ..spec_validation import validate_against_spec


def validate_schema(
    request: AnalyzerValidateRequest,
    *,
    api_version: str,
) -> ValidationResult:
    """Validate a schema with curated rules and the optional service contract."""

    try:
        text = request.schema.read_text(encoding="utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        return ValidationResult(
            ok=False,
            errors=[
                Finding(
                    "$",
                    f"{request.schema.name} is not a UTF-8 JSON schema file "
                    f"({exc.__class__.__name__}); it looks like a binary or non-text file. "
                    "Pass a JSON analyzer schema.",
                )
            ],
        )

    result, body = parse_and_validate(text, api_version=api_version)
    if request.spec and body is not None:
        spec_result = validate_against_spec(body, api_version=api_version)
        result.errors.extend(spec_result.errors)
        result.warnings.extend(spec_result.warnings)
        result.ok = not result.errors
    return result
