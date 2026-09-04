# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the Click-free analyze engine in :mod:`cu_cli_core.analysis`.

These prove the engine is usable and testable **without** the CLI or a cloud
endpoint: a fake client (and the ``run=`` injection point) stands in for the
SDK, so concurrency, per-job error isolation, and the ``on_result`` callback
can be exercised in isolation.

Also covers :func:`~cu_cli_core.analysis.disambiguate_collisions` — the
result-filename deduplication helper.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cu_cli_core.analysis import (
    AnalyzeJob,
    AnalyzeOutcome,
    AnalyzeResponse,
    BatchResult,
    analyze_bytes,
    analyze_bytes_inline,
    analyze_bytes_inline_with_usage,
    analyze_bytes_with_usage,
    analyze_many,
    analyze_one,
    analyze_one_inline,
    dedupe_same_file,
    disambiguate_collisions,
    plan_jobs,
)

pytestmark = pytest.mark.unit


class _FakePoller:
    def __init__(self, result):
        self._result = result
        self.usage = {"documentPagesStandard": 1}

    def result(self):
        return self._result


class _FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakePipelineResponse:
    def __init__(self, payload):
        self.http_response = _FakeHttpResponse(payload)


class _FakeClient:
    """Records calls and echoes a deterministic result per analyzer/bytes."""

    def __init__(self):
        self.calls: list[tuple[str, int]] = []

    def begin_analyze_binary(self, *, analyzer_id, binary_input, cls=None):
        self.calls.append((analyzer_id, len(binary_input)))
        deserialized = {"analyzer_id": analyzer_id, "size": len(binary_input)}
        raw = {
            "id": "operation-id",
            "status": "Succeeded",
            "result": {
                "analyzerId": analyzer_id,
                "size": len(binary_input),
                "serviceOnly": True,
            },
            "usage": {"documentPagesStandard": 1},
        }
        result = (
            cls(_FakePipelineResponse(raw), deserialized, {})
            if cls is not None
            else deserialized
        )
        return _FakePoller(result)

    def analyze_binary_inline(self, *, analyzer_id, binary_input, cls=None):
        self.calls.append((analyzer_id, len(binary_input)))
        response = type("InlineResponse", (), {
            "result": {"analyzer_id": analyzer_id, "size": len(binary_input)},
            "usage": {"documentPagesMinimalInline": 1},
        })()
        raw = {
            "status": "Succeeded",
            "result": {
                "analyzerId": analyzer_id,
                "size": len(binary_input),
                "serviceOnly": True,
            },
        }
        return (
            cls(_FakePipelineResponse(raw), response, {})
            if cls is not None
            else response
        )


def test_analyze_bytes_and_one_use_the_client(tmp_path):
    client = _FakeClient()
    assert analyze_bytes(client, "prebuilt-layout", b"abc") == {
        "analyzer_id": "prebuilt-layout", "size": 3
    }

    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 hello")
    job = AnalyzeJob(input_ref=str(f), analyzer_id="prebuilt-invoice")
    assert analyze_one(client, job)["analyzer_id"] == "prebuilt-invoice"


def test_analyze_bytes_and_one_inline_use_the_synchronous_client_method(tmp_path):
    client = _FakeClient()
    assert analyze_bytes_inline(client, "prebuilt-layout", b"abc") == {
        "analyzer_id": "prebuilt-layout", "size": 3
    }

    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 hello")
    job = AnalyzeJob(input_ref=str(path), analyzer_id="prebuilt-invoice")
    assert analyze_one_inline(client, job)["analyzer_id"] == "prebuilt-invoice"


def test_json_jobs_return_raw_lro_and_inline_service_payloads(tmp_path):
    client = _FakeClient()
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 hello")
    job = AnalyzeJob(
        input_ref=str(path),
        analyzer_id="prebuilt-layout",
        output_format="json",
    )

    lro = analyze_one(client, job)
    inline = analyze_one_inline(client, job)

    assert lro["status"] == "Succeeded"
    assert lro["result"]["analyzerId"] == "prebuilt-layout"
    assert lro["result"]["serviceOnly"] is True
    assert inline["status"] == "Succeeded"
    assert inline["result"]["analyzerId"] == "prebuilt-layout"
    assert inline["result"]["serviceOnly"] is True


def test_usage_aware_helpers_retain_lro_and_inline_usage():
    client = _FakeClient()

    lro = analyze_bytes_with_usage(client, "prebuilt-layout", b"abc")
    inline = analyze_bytes_inline_with_usage(client, "prebuilt-layout", b"abc")

    assert isinstance(lro, AnalyzeResponse)
    assert lro.result["size"] == 3
    assert lro.usage == {"documentPagesStandard": 1}
    assert inline.result["size"] == 3
    assert inline.usage == {"documentPagesMinimalInline": 1}


def test_analyze_many_collects_all_successes():
    jobs = [AnalyzeJob(input_ref=f"f{i}", analyzer_id="a") for i in range(10)]
    result = analyze_many(
        None, jobs, concurrency=4, run=lambda _c, j: {"ref": j.input_ref}
    )
    assert isinstance(result, BatchResult)
    assert len(result.successes) == 10
    assert result.failures == []
    assert {o.result["ref"] for o in result.successes} == {j.input_ref for j in jobs}


def test_analyze_many_isolates_per_job_failures():
    jobs = [AnalyzeJob(input_ref=f"f{i}", analyzer_id="a") for i in range(6)]

    def _run(_client, job):
        if job.input_ref in {"f1", "f4"}:
            raise RuntimeError(f"boom {job.input_ref}")
        return {"ref": job.input_ref}

    result = analyze_many(None, jobs, concurrency=3, run=_run)
    assert len(result.successes) == 4
    assert {o.job.input_ref for o in result.failures} == {"f1", "f4"}
    assert all(isinstance(o.error, RuntimeError) for o in result.failures)


def test_analyze_many_invokes_on_result_for_every_job():
    jobs = [AnalyzeJob(input_ref=f"f{i}", analyzer_id="a") for i in range(5)]
    seen: list[AnalyzeOutcome] = []
    result = analyze_many(
        None, jobs, concurrency=2, run=lambda _c, j: j.input_ref, on_result=seen.append
    )
    assert len(seen) == 5
    assert {o.job.input_ref for o in seen} == {j.input_ref for j in jobs}
    assert len(result.successes) == 5


def test_analyze_many_default_runner_reads_files(tmp_path):
    client = _FakeClient()
    files = []
    for i in range(3):
        f = tmp_path / f"doc{i}.pdf"
        f.write_bytes(b"%PDF-1.4 " + bytes([65 + i]) * (i + 1))
        files.append(f)
    jobs = [AnalyzeJob(input_ref=str(f), analyzer_id="prebuilt-layout") for f in files]
    result = analyze_many(client, jobs, concurrency=2)
    assert len(result.successes) == 3
    assert len(client.calls) == 3


def test_plan_jobs_stdout_uses_no_out_path():
    jobs = plan_jobs(["only.pdf"], analyzer_id="custom-analyzer", out_dir=None, fmt="markdown",
                     to_stdout=True)
    assert len(jobs) == 1
    assert jobs[0].out_path is None
    assert jobs[0].analyzer_id == "custom-analyzer"


def test_plan_jobs_out_dir_uses_direct_file_basename(tmp_path):
    jobs = plan_jobs(["a/x.pdf", "b/y.pdf"], analyzer_id="prebuilt-invoice",
                     out_dir=tmp_path, fmt="json", to_stdout=False)
    assert [j.out_path for j in jobs] == [
        tmp_path / "x.pdf.result.json",
        tmp_path / "y.pdf.result.json",
    ]
    assert all(j.analyzer_id == "prebuilt-invoice" for j in jobs)
    assert all(j.output_format == "json" for j in jobs)


def test_plan_jobs_uses_expanded_direct_file_relative_path(tmp_path):
    ref = "/data/invoices/q1.pdf"
    jobs = plan_jobs(
        [ref],
        analyzer_id="prebuilt-invoice",
        out_dir=tmp_path,
        fmt="json",
        to_stdout=False,
        source_relative_paths={ref: Path("q1.pdf")},
    )

    assert jobs[0].out_path == tmp_path / "q1.pdf.result.json"


def test_plan_jobs_out_dir_preserves_source_relative_structure(tmp_path):
    refs = ["/data/invoices/a/report.pdf", "/data/invoices/b/report.pdf"]
    jobs = plan_jobs(
        refs,
        analyzer_id="test-analyzer",
        out_dir=tmp_path,
        fmt="markdown",
        to_stdout=False,
        source_relative_paths={
            refs[0]: Path("a/report.pdf"),
            refs[1]: Path("b/report.pdf"),
        },
    )
    assert jobs[0].out_path == tmp_path / "a" / "report.pdf.result.md"
    assert jobs[1].out_path == tmp_path / "b" / "report.pdf.result.md"


def test_plan_jobs_out_dir_uses_absolute_file_basename(tmp_path):
    jobs = plan_jobs(["/data/reports/q1.pdf"], analyzer_id="test-analyzer",
                     out_dir=tmp_path, fmt="markdown", to_stdout=False)
    out = jobs[0].out_path
    assert out == tmp_path / "q1.pdf.result.md"
    assert tmp_path in out.parents


def test_plan_jobs_out_dir_rejects_unsafe_source_relative_path(tmp_path):
    with pytest.raises(ValueError, match="must be source-relative"):
        plan_jobs(
            ["/data/reports/q1.pdf"],
            analyzer_id="test-analyzer",
            out_dir=tmp_path,
            fmt="json",
            to_stdout=False,
            source_relative_paths={"/data/reports/q1.pdf": Path("../q1.pdf")},
        )


# --- disambiguate_collisions ------------------------------------------------


def test_disambiguate_collisions_makes_out_paths_unique():
    # Regression: distinct inputs that resolve to the same result path under --out
    # (e.g. different roots collapsing once anchors are stripped).
    out = Path("out")
    jobs = [
        AnalyzeJob("a/foo.pdf", "prebuilt-layout", out / "foo.pdf.result.md"),
        AnalyzeJob("b/foo.pdf", "prebuilt-layout", out / "foo.pdf.result.md"),
    ]
    adjusted = disambiguate_collisions(jobs)
    assert adjusted == 2
    assert jobs[0].out_path != jobs[1].out_path
    assert all(str(j.out_path).endswith(".result.md") for j in jobs)


def test_disambiguate_collisions_noop_when_unique():
    out = Path("out")
    jobs = [
        AnalyzeJob("x.pdf", "prebuilt-layout", out / "x.pdf.result.md"),
        AnalyzeJob("y.pdf", "prebuilt-layout", out / "y.pdf.result.md"),
    ]
    assert disambiguate_collisions(jobs) == 0


# --- collisions across source roots -----------------------------------------


def test_plan_jobs_same_relative_path_from_multiple_roots_collides(tmp_path):
    refs = ["/first/x/a.pdf", "/second/x/a.pdf"]
    jobs = plan_jobs(
        refs,
        analyzer_id="test-analyzer",
        out_dir=tmp_path,
        fmt="json",
        to_stdout=False,
        source_relative_paths={ref: Path("x/a.pdf") for ref in refs},
    )
    assert jobs[0].out_path == jobs[1].out_path == tmp_path / "x" / "a.pdf.result.json"

    adjusted = disambiguate_collisions(jobs)
    assert adjusted == 2
    assert jobs[0].out_path != jobs[1].out_path
    assert jobs[0].out_path.parent == jobs[1].out_path.parent == tmp_path / "x"
    assert all(str(j.out_path).endswith(".result.json") for j in jobs)


def test_plan_jobs_direct_files_with_same_basename_collide(tmp_path):
    jobs = plan_jobs(["../x/a.pdf", "x/a.pdf"], analyzer_id="test-analyzer",
                     out_dir=tmp_path, fmt="markdown", to_stdout=False)
    assert jobs[0].out_path == jobs[1].out_path == tmp_path / "a.pdf.result.md"

    adjusted = disambiguate_collisions(jobs)
    assert adjusted == 2
    assert jobs[0].out_path != jobs[1].out_path
    assert all(tmp_path in j.out_path.parents for j in jobs)  # stayed inside --out


def test_disambiguate_collisions_embeds_input_path_hash(tmp_path):
    # The disambiguated filename carries a short sha1 of the *input path*, so it
    # is deterministic and unique per distinct input while keeping its dir.
    jobs = plan_jobs(["/x/a.pdf", "x/a.pdf"], analyzer_id="test-analyzer",
                     out_dir=tmp_path, fmt="json", to_stdout=False)
    disambiguate_collisions(jobs)

    for job in jobs:
        digest = hashlib.sha1(job.input_ref.encode("utf-8")).hexdigest()[:8]
        assert job.out_path == tmp_path / f"a.pdf.{digest}.result.json"


def test_disambiguate_collisions_is_stable_across_runs(tmp_path):
    # Re-planning + re-disambiguating the same inputs yields the same names.
    def _names():
        jobs = plan_jobs(["/x/a.pdf", "x/a.pdf"], analyzer_id="test-analyzer",
                         out_dir=tmp_path, fmt="json", to_stdout=False)
        disambiguate_collisions(jobs)
        return sorted(j.out_path.name for j in jobs)

    assert _names() == _names()


# --- dedupe_same_file (physical-file identity) ------------------------------
# Distinct input strings can point at one physical file (different spellings,
# symlinks, hardlinks). dedupe_same_file collapses them so we analyze once
# instead of double-billing, keeping the first occurrence in planned order.


def test_dedupe_same_file_collapses_path_spellings(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_bytes(b"%PDF-1.4 x")
    (tmp_path / "sub").mkdir()
    alt = tmp_path / "sub" / ".." / "report.pdf"  # same file, different spelling
    jobs = [
        AnalyzeJob(str(f), "prebuilt-layout"),
        AnalyzeJob(str(alt), "prebuilt-layout"),
    ]
    dropped = dedupe_same_file(jobs)
    assert [j.input_ref for j in jobs] == [str(f)]  # first occurrence kept
    assert len(dropped) == 1
    dup, orig = dropped[0]
    assert dup.input_ref == str(alt)
    assert orig.input_ref == str(f)


def test_dedupe_same_file_collapses_symlink(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_bytes(b"%PDF-1.4 x")
    link = tmp_path / "link.pdf"
    try:
        link.symlink_to(f)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    jobs = [AnalyzeJob(str(f), "a"), AnalyzeJob(str(link), "a")]
    dropped = dedupe_same_file(jobs)
    assert len(jobs) == 1
    assert len(dropped) == 1


def test_dedupe_same_file_keeps_distinct_files(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_bytes(b"a")
    b = tmp_path / "b.pdf"
    b.write_bytes(b"b")
    jobs = [AnalyzeJob(str(a), "x"), AnalyzeJob(str(b), "x")]
    assert dedupe_same_file(jobs) == []
    assert len(jobs) == 2


def test_dedupe_same_file_keeps_first_in_planned_order(tmp_path):
    f = tmp_path / "report.pdf"
    f.write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    alt = tmp_path / "sub" / ".." / "report.pdf"
    jobs = [AnalyzeJob(str(alt), "x"), AnalyzeJob(str(f), "x")]  # alt planned first
    dedupe_same_file(jobs)
    assert [j.input_ref for j in jobs] == [str(alt)]


def test_dedupe_same_file_missing_files_fall_back_to_realpath(tmp_path, monkeypatch):
    # stat() fails for missing files, so identity falls back to realpath, which
    # still collapses two spellings of the same (nonexistent) path.
    monkeypatch.chdir(tmp_path)
    jobs = [AnalyzeJob("ghost.pdf", "x"), AnalyzeJob("./ghost.pdf", "x")]
    dropped = dedupe_same_file(jobs)
    assert len(jobs) == 1
    assert len(dropped) == 1
