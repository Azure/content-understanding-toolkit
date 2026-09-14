# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Versioned, frontend-neutral analysis report contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ANALYSIS_REPORT_SCHEMA_V1 = "cu-cli/analyze-report/v1"
_ANALYSIS_STATUSES = ("succeeded", "failed", "skipped")


@dataclass(frozen=True)
class AnalysisReportV1:
    """Stable machine-readable report produced by both CU CLI frontends."""

    analyzer: str
    result_view: str
    results: tuple[Mapping[str, Any], ...]
    schema: str = ANALYSIS_REPORT_SCHEMA_V1

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report using the public v1 field names."""

        counts = {
            status: sum(result.get("status") == status for result in self.results)
            for status in _ANALYSIS_STATUSES
        }
        return {
            "schema": self.schema,
            "analyzer": self.analyzer,
            "result_view": self.result_view,
            "counts": {**counts, "total": len(self.results)},
            "results": [dict(result) for result in self.results],
        }


def build_analysis_report(
    *,
    analyzer: str,
    result_view: str,
    results: Sequence[Mapping[str, Any]],
) -> AnalysisReportV1:
    """Validate per-input statuses and construct the shared v1 report."""

    if result_view not in {"full", "llm-input"}:
        raise ValueError("analysis report result_view must be full or llm-input")
    normalized: list[dict[str, Any]] = []
    for result in results:
        record = dict(result)
        status = record.get("status")
        if status not in _ANALYSIS_STATUSES:
            raise ValueError(
                "analysis report status must be succeeded, failed, or skipped"
            )
        if "analyzerId" in record and "analyzer" not in record:
            record["analyzer"] = record.pop("analyzerId")
        normalized.append(record)
    return AnalysisReportV1(
        analyzer=analyzer,
        result_view=result_view,
        results=tuple(normalized),
    )
