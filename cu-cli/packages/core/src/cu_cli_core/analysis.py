# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""The reusable analyze engine (Click-free, concurrent).

This module owns everything about *running* analyze jobs: planning where each
result goes, calling the SDK, and submitting many jobs concurrently. Nothing
here prints, writes result files, or exits — callers decide how to render,
persist, and report.

:func:`analyze_many` is the reusable concurrency primitive: hand it a built
client and a list of :class:`AnalyzeJob`, and it fans them out across a thread
pool, isolating per-job failures and invoking an optional ``on_result``
callback as each job completes (so callers can stream writes/progress without
buffering every result in memory).
"""

from __future__ import annotations

import hashlib
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

RESULT_SUFFIXES = (".result.md", ".result.json")


def result_path(path: str, fmt: str) -> Path:
    suffix = ".result.json" if fmt == "json" else ".result.md"
    return Path(f"{path}{suffix}")

# Prompt before very large batches (interactive TTY only) as a cost safety net.
# The engine never enforces this — the command layer decides when to confirm.
CONFIRM_THRESHOLD = 50


@dataclass
class AnalyzeJob:
    """A single unit of work: analyze *input_ref* and (maybe) write a result."""

    input_ref: str
    analyzer_id: str
    out_path: Optional[Path] = None  # None => caller streams to stdout
    output_format: str = "markdown"


@dataclass
class AnalyzeOutcome:
    """The result of running one :class:`AnalyzeJob` (success xor error)."""

    job: AnalyzeJob
    result: Any = None
    error: Optional[BaseException] = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class AnalyzeResponse:
    """Completed analysis result plus request usage metadata."""

    result: Any
    usage: Any = None


@dataclass
class BatchResult:
    """Aggregate outcome of :func:`analyze_many`."""

    successes: list[AnalyzeOutcome] = field(default_factory=list)
    failures: list[AnalyzeOutcome] = field(default_factory=list)


def _result_under(out_dir: Path, relative_ref: str | Path, fmt: str) -> Path:
    """Place a source-relative result path beneath *out_dir*."""
    relative = Path(relative_ref)
    if relative.is_absolute() or relative.anchor or ".." in relative.parts:
        raise ValueError(f"result path must be source-relative: {relative_ref}")
    return out_dir / result_path(str(relative), fmt)


def plan_jobs(
    refs: Sequence[str],
    *,
    analyzer_id: str,
    out_dir: Optional[Path],
    fmt: str,
    to_stdout: bool,
    source_relative_paths: Optional[Mapping[str, Path]] = None,
) -> list[AnalyzeJob]:
    """Build one :class:`AnalyzeJob` per input reference.

    :param refs: Input file paths to analyze (already expanded and deduped).
    :param analyzer_id: Analyzer to use for every job.
    :param out_dir: When set, every result file is written under this directory,
        relative to the source file or directory that selected it.
    :param fmt: Output format (``"markdown"`` or ``"json"``); selects the
        result-file extension (``.result.md`` vs ``.result.json``).
    :param to_stdout: When ``True`` (single input, no ``--out``) no result
        path is assigned — the caller streams the result to stdout instead.
    :param source_relative_paths: Per-input paths relative to their selecting
        source roots. Direct files default to their basename.
    """
    jobs: list[AnalyzeJob] = []
    for ref in refs:
        if to_stdout:
            out_path: Optional[Path] = None
        elif out_dir is not None:
            relative_ref = (
                source_relative_paths.get(ref, Path(ref).name)
                if source_relative_paths is not None
                else Path(ref).name
            )
            out_path = _result_under(out_dir, relative_ref, fmt)
        else:
            out_path = result_path(ref, fmt)
        jobs.append(
            AnalyzeJob(
                input_ref=ref,
                analyzer_id=analyzer_id,
                out_path=out_path,
                output_format=fmt,
            )
        )
    return jobs


def _file_identity(ref: str) -> object:
    """A stable key for the *physical* file *ref* points to.

    Prefers the OS device+inode pair, which collapses different spellings of
    the same file (``report.pdf`` vs ``../dir/report.pdf``), symlinks, and
    hardlinks onto one identity. Falls back to the resolved absolute path when
    ``stat`` fails (missing file) or the inode is unavailable (``0`` on some
    Windows/filesystems).
    """
    try:
        st = os.stat(ref)
    except OSError:
        return os.path.realpath(ref)
    if st.st_ino:
        return (st.st_dev, st.st_ino)
    return os.path.realpath(ref)


def dedupe_same_file(jobs: list[AnalyzeJob]) -> list[tuple[AnalyzeJob, AnalyzeJob]]:
    """Drop jobs whose input is the *same physical file* as an earlier job.

    Two inputs can point at one file via different path spellings (``a.pdf``
    and ``../dir/a.pdf``), a symlink and its target, or a hardlink. Analyzing
    it twice would double the billed API calls and write duplicate results, so
    this keeps the first occurrence in planned order and removes the rest.

    *jobs* is mutated in place. Returns ``(dropped, kept)`` pairs so the caller
    can warn — the engine never prints. Identity is decided by
    :func:`_file_identity` (device+inode, resolved-path fallback).
    """
    seen: dict[object, AnalyzeJob] = {}
    kept: list[AnalyzeJob] = []
    dropped: list[tuple[AnalyzeJob, AnalyzeJob]] = []
    for j in jobs:
        key = _file_identity(j.input_ref)
        original = seen.get(key)
        if original is not None:
            dropped.append((j, original))
        else:
            seen[key] = j
            kept.append(j)
    jobs[:] = kept
    return dropped


def disambiguate_collisions(jobs: list[AnalyzeJob]) -> int:
    """Ensure distinct inputs never share a result path.

    Direct files with the same basename, or files from different source roots
    with the same relative path, can map to one output. Returns the number
    adjusted.
    """
    counts = Counter(j.out_path for j in jobs if j.out_path is not None)
    collided = {p for p, n in counts.items() if n > 1}
    if not collided:
        return 0
    adjusted = 0
    for j in jobs:
        if j.out_path is None or j.out_path not in collided:
            continue
        digest = hashlib.sha1(j.input_ref.encode("utf-8")).hexdigest()[:8]
        name = j.out_path.name
        for suffix in RESULT_SUFFIXES:
            if name.endswith(suffix):
                base = name[: -len(suffix)]
                j.out_path = j.out_path.with_name(f"{base}.{digest}{suffix}")
                adjusted += 1
                break
    return adjusted


def _capture_raw_response(
    pipeline_response: Any,
    deserialized: Any,
    _response_headers: dict[str, Any],
) -> tuple[Any, Any]:
    """Retain the SDK model and raw HTTP response from an SDK ``cls`` callback."""
    return deserialized, pipeline_response.http_response


def analyze_bytes(
    client: Any,
    analyzer_id: str,
    data: bytes,
    *,
    raw_json: bool = False,
) -> Any:
    """Analyze raw *data* with *analyzer_id* and return the completed result."""
    return analyze_bytes_with_usage(
        client,
        analyzer_id,
        data,
        raw_json=raw_json,
    ).result


def analyze_bytes_with_usage(
    client: Any,
    analyzer_id: str,
    data: bytes,
    *,
    raw_json: bool = False,
) -> AnalyzeResponse:
    """Analyze raw *data* and retain usage metadata from the completed poller."""
    kwargs = {"cls": _capture_raw_response} if raw_json else {}
    poller = client.begin_analyze_binary(
        analyzer_id=analyzer_id,
        binary_input=data,
        **kwargs,
    )
    completed = poller.result()
    if raw_json:
        _, raw_response = completed
        result = raw_response.json()
    else:
        result = completed
    return AnalyzeResponse(result=result, usage=getattr(poller, "usage", None))


def analyze_bytes_inline(
    client: Any,
    analyzer_id: str,
    data: bytes,
    *,
    raw_json: bool = False,
) -> Any:
    """Analyze raw *data* synchronously and return the inline result."""
    return analyze_bytes_inline_with_usage(
        client,
        analyzer_id,
        data,
        raw_json=raw_json,
    ).result


def analyze_bytes_inline_with_usage(
    client: Any,
    analyzer_id: str,
    data: bytes,
    *,
    raw_json: bool = False,
) -> AnalyzeResponse:
    """Analyze raw *data* synchronously and retain inline usage metadata."""
    kwargs = {"cls": _capture_raw_response} if raw_json else {}
    completed = client.analyze_binary_inline(
        analyzer_id=analyzer_id,
        binary_input=data,
        **kwargs,
    )
    if raw_json:
        response, raw_response = completed
        result = raw_response.json()
    else:
        response = completed
        result = response.result
    return AnalyzeResponse(result=result, usage=getattr(response, "usage", None))


def analyze_one(client: Any, job: AnalyzeJob) -> Any:
    """Run a single :class:`AnalyzeJob`, returning the completed SDK result."""
    data = Path(job.input_ref).read_bytes()
    return analyze_bytes(
        client,
        job.analyzer_id,
        data,
        raw_json=job.output_format == "json",
    )


def analyze_one_inline(client: Any, job: AnalyzeJob) -> Any:
    """Run a single job synchronously through the inline analyze API."""
    data = Path(job.input_ref).read_bytes()
    return analyze_bytes_inline(
        client,
        job.analyzer_id,
        data,
        raw_json=job.output_format == "json",
    )


def analyze_one_with_usage(client: Any, job: AnalyzeJob) -> AnalyzeResponse:
    """Run one long-running analysis and retain its usage metadata."""
    data = Path(job.input_ref).read_bytes()
    return analyze_bytes_with_usage(
        client,
        job.analyzer_id,
        data,
        raw_json=job.output_format == "json",
    )


def analyze_one_inline_with_usage(client: Any, job: AnalyzeJob) -> AnalyzeResponse:
    """Run one inline analysis and retain its usage metadata."""
    data = Path(job.input_ref).read_bytes()
    return analyze_bytes_inline_with_usage(
        client,
        job.analyzer_id,
        data,
        raw_json=job.output_format == "json",
    )


def analyze_many(
    client: Any,
    jobs: Sequence[AnalyzeJob],
    *,
    concurrency: int = 4,
    on_result: Optional[Callable[[AnalyzeOutcome], None]] = None,
    run: Optional[Callable[[Any, AnalyzeJob], Any]] = None,
) -> BatchResult:
    """Run *jobs* concurrently, isolating per-job failures.

    Each job is submitted to a :class:`~concurrent.futures.ThreadPoolExecutor`
    with up to *concurrency* workers. As each completes, an
    :class:`AnalyzeOutcome` is produced (result on success, ``error`` on
    failure) and, if given, ``on_result`` is invoked with it on the calling
    thread — so callers can persist/print incrementally in a single-threaded,
    deterministic-enough order without buffering results.

    *run* is the per-job runner (dependency injection point); it defaults to
    :func:`analyze_one` and must have the signature ``run(client, job) ->
    result``. Callers can inject a custom runner (e.g. a caching or dry-run
    variant) without touching the concurrency machinery.

    Exceptions raised by *on_result* propagate to the caller (the callback is
    the caller's own code); analyze failures never do — they surface as
    ``outcome.error``.
    """
    runner = run or analyze_one
    result = BatchResult()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(runner, client, j): j for j in jobs}
        for fut in as_completed(futs):
            job = futs[fut]
            try:
                outcome = AnalyzeOutcome(job=job, result=fut.result())
            except Exception as exc:  # noqa: BLE001 — per-job isolation
                outcome = AnalyzeOutcome(job=job, error=exc)
            (result.successes if outcome.ok else result.failures).append(outcome)
            if on_result is not None:
                on_result(outcome)
    return result
