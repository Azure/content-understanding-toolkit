# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path

import pytest

from cu_cli_core.contracts import (
    AnalyzerShowRequest,
    AnalyzerUpdateRequest,
    BatchReport,
    FileOutcome,
    OutcomeStatus,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", ["", " ", "\t\n"])
def test_analyzer_show_rejects_empty_name(name):
    with pytest.raises(ValueError, match="cannot be empty"):
        AnalyzerShowRequest(name)


def test_analyzer_update_parses_repeated_tags_without_losing_equals():
    request = AnalyzerUpdateRequest(
        " invoice_v1 ",
        tag_assignments=("owner=cu-cli", "query=a=b"),
    )

    assert request.name == "invoice_v1"
    assert request.tags == {"owner": "cu-cli", "query": "a=b"}


@pytest.mark.parametrize(
    ("tag_assignments", "message"),
    [
        (("owner",), "expected KEY=VALUE"),
        (("=cu-cli",), "non-empty key"),
        ((" owner=cu-cli",), "cannot start or end with whitespace"),
        (("owner =cu-cli",), "cannot start or end with whitespace"),
        (("owner=one", "owner=two"), "duplicate tag key 'owner'"),
    ],
)
def test_analyzer_update_rejects_invalid_tags(tag_assignments, message):
    with pytest.raises(ValueError, match=message):
        AnalyzerUpdateRequest("invoice_v1", tag_assignments=tag_assignments)


def test_analyzer_update_requires_a_metadata_change():
    with pytest.raises(ValueError, match="at least one metadata change"):
        AnalyzerUpdateRequest("invoice_v1")


def test_analyzer_update_allows_clearing_description_and_empty_tag_values():
    request = AnalyzerUpdateRequest(
        "invoice_v1",
        description="",
        tag_assignments=("owner=",),
    )

    assert request.description == ""
    assert request.tags == {"owner": ""}


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
