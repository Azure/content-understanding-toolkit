# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu analyze`` standalone adapter."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from azure.core.exceptions import HttpResponseError
from cu_cli_core.command_spec import (
    ANALYZE,
    CommandBindingError,
    build_request,
    resolve_identifier,
)
import rich_click as click
from rich.markup import escape as _esc

from ..apiversion import API_VERSION_HELP, ensure_supported, supports_api_feature
from ..client import build_client
from ..profile import Profile
from cu_cli_core.analysis import (
    AnalyzeJob,
    AnalyzeOutcome,
    AnalyzeResponse,
    analyze_one,
    analyze_one_inline,
    analyze_one_inline_with_usage,
    analyze_one_with_usage,
)
from ..errors import CuCliError, _format_service_error, friendly_errors
from ..exit_codes import GENERIC_ERROR, VALIDATION_FAILURE
from ..output import (
    EmptyMarkdownOutputError,
    console,
    dump_json,
    dump_markdown,
    dumps_json,
    render_markdown,
    to_jsonable,
)
from ._options import CALLING_TIME_OPTION, calling_time
from ._command_spec import with_command_arguments

if TYPE_CHECKING:
    from cu_cli_core.contracts import ExecutionPlan, ExistingResultPolicy, InputPlan


def _run_one(client, job: AnalyzeJob):
    """Thin, patchable seam around :func:`cu_cli.core.analyze.analyze_one`.

    Kept as a module-level indirection so tests can inject a fake analyzer and
    so callers that want the originating job alongside the result get the
    familiar ``(job, result)`` tuple. All real work lives in ``core``.
    """
    return job, analyze_one(client, job)


def _run_one_inline(client, job: AnalyzeJob):
    """Run one job through the synchronous inline analyze API."""
    return job, analyze_one_inline(client, job)


def _run_one_with_usage(client, job: AnalyzeJob):
    """Run one long-running analysis while retaining usage metadata."""
    return job, analyze_one_with_usage(client, job)


def _run_one_inline_with_usage(client, job: AnalyzeJob):
    """Run one inline analysis while retaining usage metadata."""
    return job, analyze_one_inline_with_usage(client, job)


def _print_usage(usage, *, input_ref: str) -> None:
    """Render request usage to stderr without changing data written to stdout."""
    console.print("\n")
    console.print(f"[bold cyan]Usage:[/bold cyan] {_esc(input_ref)}")
    if usage is None:
        console.print("[dim]usage details were not returned by the service.[/dim]")
        return
    console.print_json(data=to_jsonable(usage))


_ON_EXISTS_ENV = "CU_ON_EXISTS"
_ON_EXISTS_CHOICES = ("error", "skip", "reanalyze")


def _friendly_analyze_error(exc: BaseException) -> str:
    """Return a user-facing error string for per-input analyze failures."""
    msg = str(exc)
    if isinstance(exc, EmptyMarkdownOutputError) or (
        "to_llm_input() returned empty markdown output" in msg
    ):
        return (
            "Analysis succeeded, but the Markdown view was empty. "
            "Retry with --json to inspect the complete result."
        )
    if isinstance(exc, HttpResponseError):
        return _format_service_error(exc)
    return msg


def _resolve_on_exists(explicit: str | None) -> ExistingResultPolicy:
    """Resolve the explicit or environment-selected existing-result policy."""
    from cu_cli_core.contracts import ExistingResultPolicy

    raw = explicit or os.environ.get(_ON_EXISTS_ENV, "").strip().lower() or "error"
    if not raw:
        raw = "error"
    if raw not in _ON_EXISTS_CHOICES:
        raise CuCliError(
            f"{_ON_EXISTS_ENV} must be one of {'|'.join(_ON_EXISTS_CHOICES)} "
            f"(got {os.environ.get(_ON_EXISTS_ENV)!r}).",
            exit_code=VALIDATION_FAILURE,
        )
    return ExistingResultPolicy(raw)


def _validate_report_path(report_path: Path | None, jobs: list[AnalyzeJob]) -> None:
    """Reject a report path that would overwrite a finalized analysis result."""
    if report_path is None:
        return
    resolved_report_path = report_path.resolve(strict=False)
    for job in jobs:
        if (
            job.out_path is not None
            and job.out_path.resolve(strict=False) == resolved_report_path
        ):
            raise CuCliError(
                f"--report-file conflicts with an analysis result file: {report_path}",
                hint=(
                    "choose a different --report-file path; planned result path: "
                    f"{job.out_path}."
                ),
                exit_code=VALIDATION_FAILURE,
            )


def _preflight_output_writes(
    jobs: list[AnalyzeJob],
    *,
    report_path: Path | None,
) -> None:
    output_paths = [job.out_path for job in jobs if job.out_path is not None]
    if report_path is not None:
        output_paths.append(report_path)

    directories = {path.parent.resolve(strict=False) for path in output_paths}
    for directory in sorted(directories, key=str):
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=directory,
            prefix=".cu-write-check-",
        ) as handle:
            handle.write(b"\0")
            handle.flush()


def _write_analyze_report(path: Path, *, analyzer_id, fmt: str, results: list[dict]) -> None:
    """Write a machine-readable per-input status report (regression).

    ``results`` is a flat list of ``{"input", "status", ...}`` records where
    ``status`` is ``succeeded`` / ``failed`` / ``skipped``. The stable ``schema`` key
    lets agents parse the summary without scraping human-formatted stderr.
    """
    counts = {"succeeded": 0, "failed": 0, "skipped": 0}
    for r in results:
        status = r.get("status")
        if status in counts:
            counts[status] += 1
    counts["total"] = len(results)
    payload = dumps_json(
        {
            "schema": "cu-cli/analyze-report/v1",
            "analyzer": analyzer_id,
            "result_view": "full" if fmt == "json" else "llm-input",
            "counts": counts,
            "results": results,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def _print_extension_counts(input_plan: InputPlan) -> None:
    for extension, count in input_plan.extension_counts.items():
        console.print(f"  {extension:<10} {count}")


def _print_discovery_skips(input_plan: InputPlan) -> None:
    if not input_plan.skipped:
        return
    console.print(f"Skipped during discovery: {len(input_plan.skipped)}")
    for item in input_plan.skipped:
        console.print(f"  [dim]- {_esc(str(item.path))}: {_esc(item.reason)}[/dim]")


def _print_discovery(input_plan: InputPlan, *, analyzer_id: str) -> None:
    console.print(f"[yellow]Found {len(input_plan.inputs)} files:[/yellow]")
    _print_extension_counts(input_plan)
    _print_discovery_skips(input_plan)
    console.print(f"\nAnalyzer: {analyzer_id}")
    console.print(f"Recursive: {'yes' if input_plan.recursive else 'no'}")


def _print_dry_run(plan: ExecutionPlan, *, analyzer_id: str) -> None:
    input_plan = plan.input_plan
    console.print("[bold cyan]Dry run[/bold cyan]")
    console.print(
        f"Selected: {len(input_plan.inputs)} file(s), {input_plan.total_bytes} byte(s)"
    )
    _print_extension_counts(input_plan)
    _print_discovery_skips(input_plan)
    console.print(f"Analyzer: {analyzer_id}")
    console.print(f"Recursive: {'yes' if input_plan.recursive else 'no'}")
    console.print(f"On existing: {plan.on_existing.value}")
    for output in plan.outputs:
        if output.path is None:
            destination = "stdout"
        else:
            destination = str(output.path)
        if output.exists:
            action = (
                "skip"
                if plan.on_existing.value == "skip"
                else plan.on_existing.value
            )
            console.print(
                f"  {_esc(str(output.source.path))} -> {_esc(destination)} "
                f"[dim](exists: {action})[/dim]"
            )
        else:
            console.print(f"  {_esc(str(output.source.path))} -> {_esc(destination)}")
    console.print(
        "[dim]No service calls or files were written. Analyzer existence, "
        "service-side format acceptance, usage, and cost were not validated.[/dim]"
    )


@click.command("analyze",
               help=ANALYZE.help,
               epilog="When a result file already exists, analyze stops unless "
                      "--on-existing skip or --on-existing reanalyze is selected. "
                      "Set CU_ON_EXISTS=error|skip|reanalyze to change the default.\n\n"
                      "[white] [/white]\n\n"
                      "[bold cyan]Common commands:[/bold cyan]\n\n"
                      "[bold green]cu analyze[/bold green] [bold yellow]FILE[/bold yellow]\n\n"
                      "[white]\u00a0\u00a0Analyze one file with the configured default "
                      "analyzer.[/white]\n\n"
                      "[bold green]cu analyze[/bold green] [bold yellow]FILE[/bold yellow] "
                      "[bold cyan]-a[/bold cyan] [bold magenta]prebuilt-invoice[/bold magenta] "
                      "[bold cyan]--json[/bold cyan]\n\n"
                      "[white]\u00a0\u00a0Extract invoice fields as JSON.[/white]\n\n"
                      "[bold green]cu analyze[/bold green] "
                      "[bold cyan]--source[/bold cyan] [bold yellow]DIRECTORY[/bold yellow] "
                      "[bold cyan]--output-dir[/bold cyan] [bold yellow]TARGET_DIR[/bold yellow]\n\n"
                      "[white]\u00a0\u00a0Analyze immediate files in DIRECTORY and write all "
                      "result files to TARGET_DIR instead of beside each input.[/white]")
@with_command_arguments(ANALYZE)
@CALLING_TIME_OPTION
@click.option("-p", "--profile", "profile_name", default=None,
              help="Named CU CLI profile to use (from cu profile).")
@click.option("--endpoint", default=None, help="Override configured endpoint.")
@click.option("--auth-mode", type=click.Choice(["login", "key"]), default=None,
              help="Authentication mode; defaults to the selected CU CLI profile.")
@click.option("--api-key", default=None, help="Override configured API key.")
@click.option("--api-version", "api_version", default=None,
              help=API_VERSION_HELP)
@friendly_errors
def cmd_analyze(
    inputs,
    files,
    sources,
    pattern,
    recursive,
    analyzer_id,
    out_dir,
    output_file,
    llm_input,
    json_output,
    report_path,
    concurrency,
    on_existing,
    dry_run,
    assume_yes,
    endpoint,
    api_key,
    api_version,
    auth_mode,
    profile_name,
    inline,
    show_usage,
    show_calling_time,
) -> None:
    from cu_cli_core.contracts import ExistingResultPolicy, InputOrigin, ResultView
    from cu_cli_core.input_planning import plan_inputs, plan_outputs

    try:
        request = build_request(
            ANALYZE,
            {
                "inputs": inputs,
                "files": files,
                "sources": sources,
                "pattern": pattern,
                "recursive": recursive,
                "analyzer_id": analyzer_id,
                "inline": inline,
                "show_usage": show_usage,
                "llm_input": llm_input,
                "json_output": json_output,
                "output_file": output_file,
                "out_dir": out_dir,
                "on_existing": on_existing,
                "dry_run": dry_run,
                "assume_yes": assume_yes,
                "report_path": report_path,
                "concurrency": concurrency,
            },
        )
    except CommandBindingError as exc:
        raise CuCliError(str(exc), exit_code=VALIDATION_FAILURE) from exc

    # Fail fast, before any input discovery, CU service call, or result-file
    # write: an existing report is never overwritten.
    if dry_run and assume_yes:
        raise CuCliError(
            "--dry-run and --yes cannot be combined.",
            exit_code=VALIDATION_FAILURE,
        )
    if llm_input and json_output:
        raise CuCliError(
            "--llm-input and --json cannot be combined.",
            exit_code=VALIDATION_FAILURE,
        )
    if not dry_run and report_path is not None and report_path.exists():
        raise CuCliError(
            f"--report-file already exists: {report_path}",
            hint="choose a new --report-file path; existing reports are never overwritten.",
            exit_code=VALIDATION_FAILURE,
        )
    input_plan = plan_inputs(
        positional=request.positional_inputs,
        files=request.files,
        sources=request.sources,
        pattern=request.pattern,
        recursive=request.recursive,
    )
    policy = _resolve_on_exists(request.on_existing)
    view = ResultView.FULL if json_output else ResultView.LLM_INPUT
    fmt = "json" if view is ResultView.FULL else "markdown"
    execution_plan = plan_outputs(
        input_plan,
        view=view,
        output_file=request.output_file,
        output_dir=request.output_dir,
        on_existing=policy,
        dry_run=dry_run,
    )
    profile = Profile.load(profile_name=profile_name)
    effective_analyzer = request.analyzer or profile.default_analyzer
    if not effective_analyzer:
        raise CuCliError(
            "no analyzer was specified and no default_analyzer is configured.",
            hint="pass --analyzer ANALYZER_ID or run "
                 "`cu profile set default_analyzer ANALYZER_ID`.",
            exit_code=VALIDATION_FAILURE,
        )
    skipped_report = [
        {
            "input": str(item.path),
            "status": "skipped",
            "reason": item.reason,
            "output": None,
        }
        for item in input_plan.skipped
    ]

    jobs = [
        AnalyzeJob(
            input_ref=str(output.source.path),
            analyzer_id=effective_analyzer,
            out_path=output.path,
            output_format=fmt,
        )
        for output in execution_plan.outputs
    ]
    to_stdout = len(jobs) == 1 and jobs[0].out_path is None

    effective_api_version = ensure_supported(api_version or profile.api_version)
    if inline:
        if not supports_api_feature(effective_api_version, "inline-analysis"):
            raise CuCliError(
                "--inline requires API version 2026-06-01-preview.",
                hint="pass `--api-version 2026-06-01-preview` or save it with "
                     "`cu profile set api_version 2026-06-01-preview`.",
            )

    skipped: list[Path] = []
    if not to_stdout:
        if not dry_run:
            _validate_report_path(report_path, jobs)
        existing = [j for j in jobs if j.out_path is not None and j.out_path.exists()]
        if dry_run:
            _print_dry_run(execution_plan, analyzer_id=effective_analyzer)
            return
        if existing:
            where = f"under {out_dir}" if out_dir is not None else "next to the inputs"
            if policy is ExistingResultPolicy.ERROR:
                raise CuCliError(
                    f"{len(existing)} of {len(jobs)} result file(s) already exist {where}.",
                    hint="choose --on-existing skip to keep them or "
                         "--on-existing reanalyze to replace them (re-bills).",
                    exit_code=VALIDATION_FAILURE,
                )
            if policy is ExistingResultPolicy.SKIP:
                skipped = [j.out_path for j in existing if j.out_path is not None]
                for j in existing:
                    skipped_report.append({
                        "input": j.input_ref,
                        "status": "skipped",
                        "reason": "result file already exists",
                        "output": str(j.out_path) if j.out_path is not None else None,
                    })
                existing_ids = {id(j) for j in existing}
                jobs = [j for j in jobs if id(j) not in existing_ids]
            elif policy is ExistingResultPolicy.REANALYZE:
                console.print(
                    "[yellow]Warning:[/yellow] Reanalysis sends the input to "
                    "Content Understanding again and may incur additional charges. "
                    "Existing result files will be replaced."
                )
        if not jobs:
            message = (
                f"[green]nothing to do:[/green] {len(skipped)} result file(s) already exist "
                "(skipped)."
            )
            if input_plan.skipped:
                message += f" {len(input_plan.skipped)} source entry(s) skipped during discovery."
            console.print(message)
            if report_path is not None:
                _write_analyze_report(report_path, analyzer_id=effective_analyzer, fmt=fmt,
                                      results=skipped_report)
                console.print(f"[dim]report:[/dim] wrote {report_path}")
            return
        discovered = any(
            item.origin in {InputOrigin.POSITIONAL_SOURCE, InputOrigin.NAMED_SOURCE}
            for item in input_plan.inputs
        )
        if not assume_yes and discovered and len(jobs) > 1 and sys.stdin.isatty():
            _print_discovery(input_plan, analyzer_id=effective_analyzer)
            if not click.confirm("proceed?", default=False):
                raise CuCliError("aborted by user.", hint="narrow the inputs or pass --yes.")
    elif dry_run:
        _print_dry_run(execution_plan, analyzer_id=effective_analyzer)
        return

    _preflight_output_writes(jobs, report_path=report_path)
    client = build_client(profile, endpoint_override=endpoint, api_key_override=api_key,
                          api_version_override=api_version,
                          auth_mode_override=auth_mode)
    if show_usage:
        run_one = _run_one_inline_with_usage if inline else _run_one_with_usage
    else:
        run_one = _run_one_inline if inline else _run_one

    if to_stdout:
        job = jobs[0]
        with calling_time(show_calling_time) as calling_timer:
            batch_result = resolve_identifier(ANALYZE.operation)(
                client,
                request,
                input_plan=input_plan,
                jobs=[job],
                run=lambda c, j: run_one(c, j)[1],
            )
        if batch_result.failures:
            failure = batch_result.failures[0].error
            assert failure is not None
            # Match the batch path: a failed single-input run still emits the
            # --report file (one "failed" entry) before the friendly error exits
            # 1, so a scripted single-file caller never gets a missing report
            # (regression). Re-raise the captured core outcome so @friendly_errors
            # renders the same message and exit code as before.
            if report_path is not None:
                _write_analyze_report(
                    report_path, analyzer_id=effective_analyzer, fmt=fmt,
                    results=[{"input": job.input_ref, "status": "failed",
                              "analyzer": job.analyzer_id,
                              "error": _friendly_analyze_error(failure)}] + skipped_report,
                )
                console.print(f"[dim]report:[/dim] wrote {report_path}")
            raise failure
        response = batch_result.successes[0].result
        if show_usage:
            assert isinstance(response, AnalyzeResponse)
            result = response.result
        else:
            result = response
        if fmt == "json":
            dump_json(result)
        else:
            try:
                dump_markdown(result)
            except EmptyMarkdownOutputError as exc:
                error = _friendly_analyze_error(exc)
                if report_path is not None:
                    _write_analyze_report(
                        report_path,
                        analyzer_id=effective_analyzer,
                        fmt=fmt,
                        results=[
                            {
                                "input": job.input_ref,
                                "status": "failed",
                                "analyzer": job.analyzer_id,
                                "error": error,
                            }
                        ] + skipped_report,
                    )
                    console.print(f"[dim]report:[/dim] wrote {report_path}")
                raise CuCliError(error) from exc
        if report_path is not None:
            _write_analyze_report(
                report_path, analyzer_id=effective_analyzer, fmt=fmt,
                results=[{"input": job.input_ref, "status": "succeeded",
                          "analyzer": job.analyzer_id, "output": None}] + skipped_report,
            )
            console.print(f"[dim]report:[/dim] wrote {report_path}")
        if show_usage:
            assert isinstance(response, AnalyzeResponse)
            _print_usage(response.usage, input_ref=job.input_ref)
        calling_timer.print()
        return

    failures: list[tuple[str, str]] = []
    written: list[Path] = []
    results_report: list[dict] = []
    usage_results: list[tuple[str, object]] = []
    console.print(f"[bold]analyze[/bold] {len(jobs)} file(s) -> "
                  f"{out_dir or 'alongside inputs'}")

    def _persist(outcome: AnalyzeOutcome) -> None:
        job = outcome.job
        if not outcome.ok:
            assert outcome.error is not None
            err = _friendly_analyze_error(outcome.error)
            failures.append((job.input_ref, err))
            results_report.append({"input": job.input_ref, "status": "failed",
                                   "analyzer": job.analyzer_id, "error": err})
            return
        try:
            assert job.out_path is not None
            if show_usage:
                assert isinstance(outcome.result, AnalyzeResponse)
                result = outcome.result.result
                usage_results.append((job.input_ref, outcome.result.usage))
            else:
                result = outcome.result
            if fmt == "json":
                dump_json(result, out=job.out_path)
            else:
                job.out_path.parent.mkdir(parents=True, exist_ok=True)
                job.out_path.write_text(render_markdown(result), encoding="utf-8")
            written.append(job.out_path)
            results_report.append({"input": job.input_ref, "status": "succeeded",
                                   "analyzer": job.analyzer_id, "output": str(job.out_path)})
        except Exception as exc:  # noqa: BLE001 — per-file isolation on write
            err = _friendly_analyze_error(exc)
            failures.append((job.input_ref, err))
            results_report.append({"input": job.input_ref, "status": "failed",
                                   "analyzer": job.analyzer_id, "error": err})

    with calling_time(show_calling_time) as calling_timer:
        resolve_identifier(ANALYZE.operation)(
            client,
            request,
            input_plan=input_plan,
            jobs=jobs,
            on_result=_persist,
            run=lambda c, j: run_one(c, j)[1],
        )

    # Write the report before the failure exit so agents always get it (regression).
    if report_path is not None:
        _write_analyze_report(report_path, analyzer_id=effective_analyzer, fmt=fmt,
                              results=results_report + skipped_report)
        console.print(f"[dim]report:[/dim] wrote {report_path}")
    summary = [f"[green]{len(written)} ok[/green]", f"[red]{len(failures)} failed[/red]"]
    if skipped:
        summary.append(f"[dim]{len(skipped)} skipped (existing)[/dim]")
    if input_plan.skipped:
        summary.append(f"[dim]{len(input_plan.skipped)} skipped (discovery)[/dim]")
    console.print(", ".join(summary))
    for path in written:
        console.print(f"  [green]->[/green] {path}")
    if failures:
        # List every failed input and its full reason — never truncate the file
        # list or the per-file service message, so an agent can act on each one
        # (regression).
        console.print(f"[red]{len(failures)} failed input(s):[/red]")
        for ref, err in failures:
            console.print(f"  [red]x[/red] {_esc(ref)}")
            for line in (err.splitlines() or [""]):
                console.print(f"      [dim]{_esc(line)}[/dim]")
    for input_ref, usage in usage_results:
        _print_usage(usage, input_ref=input_ref)
    calling_timer.print()
    if failures:
        sys.exit(GENERIC_ERROR)
