from pathlib import Path

import pytest

from cu_cli_core.contracts import (
    AnalyzerShowRequest,
    BatchReport,
    FileOutcome,
    OutcomeStatus,
)

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
