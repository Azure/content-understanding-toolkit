# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path

import pytest

from cu_cli_core.contracts import (
    AnalyzerShowRequest,
    BatchReport,
    FileOutcome,
    OutcomeStatus,
)
from cu_cli_core.reporting import ANALYSIS_REPORT_SCHEMA_V1, build_analysis_report

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", ["", " ", "\t\n"])
def test_analyzer_show_rejects_empty_name(name):
    with pytest.raises(ValueError, match="cannot be empty"):
        AnalyzerShowRequest(name)


def test_batch_report_counts_each_outcome_status():
    report = BatchReport(
        (
            FileOutcome(Path("a.pdf"), OutcomeStatus.SUCCEEDED, "layout"),
            FileOutcome(Path("b.pdf"), OutcomeStatus.FAILED, "layout"),
            FileOutcome(Path("c.pdf"), OutcomeStatus.SKIPPED, "layout"),
            FileOutcome(Path("d.pdf"), OutcomeStatus.SUCCEEDED, "layout"),
        )
    )

    assert report.succeeded == 2
    assert report.failed == 1
    assert report.skipped == 1


def test_analysis_report_v1_has_stable_fields_statuses_and_counts():
    report = build_analysis_report(
        analyzer="layout",
        result_view="full",
        results=(
            {"input": "a.pdf", "status": "succeeded", "analyzerId": "layout"},
            {"input": "b.pdf", "status": "failed", "error": "bad input"},
            {"input": "c.pdf", "status": "skipped", "reason": "exists"},
        ),
    ).to_dict()

    assert report == {
        "schema": ANALYSIS_REPORT_SCHEMA_V1,
        "analyzer": "layout",
        "result_view": "full",
        "counts": {"succeeded": 1, "failed": 1, "skipped": 1, "total": 3},
        "results": [
            {"input": "a.pdf", "status": "succeeded", "analyzer": "layout"},
            {"input": "b.pdf", "status": "failed", "error": "bad input"},
            {"input": "c.pdf", "status": "skipped", "reason": "exists"},
        ],
    }


def test_analysis_report_rejects_unknown_status():
    with pytest.raises(ValueError, match="status must be"):
        build_analysis_report(
            analyzer="layout",
            result_view="full",
            results=({"input": "a.pdf", "status": "pending"},),
        )


def test_analysis_report_rejects_unknown_result_view():
    with pytest.raises(ValueError, match="result_view must be"):
        build_analysis_report(analyzer="layout", result_view="markdown", results=())
