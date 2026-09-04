# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared schema-create operation."""

from __future__ import annotations

from typing import Any

from ..contracts import AnalyzerSchemaCreateRequest
from ..errors import UsageError
from ..schema import (
    MODALITY_BASE,
    starter_schema,
    suggest_schema_from_sample,
)


def create_schema(
    request: AnalyzerSchemaCreateRequest,
    *,
    api_version: str,
    completion_model: str,
    client: Any | None = None,
) -> tuple[dict[str, Any], bool]:
    """Create a starter or sample-derived schema from a normalized request."""

    if request.from_sample is not None:
        if client is None:
            raise UsageError("sample-derived schema creation requires a CU client.")
        return suggest_schema_from_sample(
            client,
            sample_path=request.from_sample,
            analyzer_id=request.name,
            api_version=api_version,
            completion_model=completion_model,
        )
    return (
        starter_schema(
            request.name,
            request.base or MODALITY_BASE[request.modality],
            request.modality,
            api_version,
            completion_model=completion_model,
            template_type=request.template_type,
        ),
        True,
    )
