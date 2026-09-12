# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI analysis orchestration over shared CU core contracts."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from typing import Any, Callable

from azure.cli.core.util import user_confirmation

from cu_cli_core.analysis import (
    CONFIRM_THRESHOLD,
    AnalyzeJob,
    AnalyzeResponse,
    analyze_one,
    analyze_one_inline,
    analyze_one_inline_with_usage,
    analyze_one_with_usage,
)
from cu_cli_core.command_spec import ANALYZE, build_request, resolve_identifier
from cu_cli_core.contracts import ExistingResultPolicy, ResultView
from cu_cli_core.errors import ConflictError, ServiceError, UsageError, ValidationError
from cu_cli_core.input_planning import (
    plan_inputs,
    plan_outputs,
    redact_input_reference,
    redact_sensitive_urls,
)
from cu_cli_core.profiles import Profile
from cu_cli_core.reporting import build_analysis_report
from cu_cli_core.serialization import to_plain_value

from ._client_factory import create_content_understanding_client
from ._io import write_json, write_text


def _runner(request: Any) -> Callable[[Any, AnalyzeJob], Any]:
    if request.inline and request.usage:
        return analyze_one_inline_with_usage
    if request.inline:
        return analyze_one_inline
    if request.usage:
        return analyze_one_with_usage
    return analyze_one


def _report(
    path: Path,
    analyzer: str,
    result_view: str,
    records: list[dict[str, Any]],
) -> None:
    report = build_analysis_report(
        analyzer=analyzer,
        result_view=result_view,
        results=records,
    )
    write_json(
        path,
        report.to_dict(),
        overwrite=False,
    )


def analyze(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZE, values)
    if request.dry_run and request.yes:
        raise UsageError("--dry-run and --yes cannot be combined.")
    profile = Profile.load(profile_name=values.get("profile_name"))
    analyzer = request.analyzer or profile.default_analyzer
    if not analyzer:
        raise UsageError(
            "no analyzer was specified and no default_analyzer is configured.",
            hint="Pass --analyzer or configure default_analyzer in a CU profile.",
        )
    policy = request.on_existing
    if policy is None:
        try:
            policy = ExistingResultPolicy(
                os.getenv("CU_ON_EXISTS", ExistingResultPolicy.ERROR.value)
            )
        except ValueError as exc:
            raise ValidationError("CU_ON_EXISTS must be error, skip, or reanalyze.") from exc
    request = replace(request, analyzer=analyzer, on_existing=policy)
    inputs = plan_inputs(
        files=request.files,
        sources=request.sources,
        urls=request.urls,
        pattern=request.pattern,
        recursive=request.recursive,
    )
    execution = plan_outputs(
        inputs,
        view=ResultView.LLM_INPUT if request.llm_input else ResultView.FULL,
        output_file=request.output_file,
        output_dir=request.output_dir,
        on_existing=policy,
        dry_run=request.dry_run,
    )
    existing = [output for output in execution.outputs if output.exists]
    if existing and policy is ExistingResultPolicy.ERROR:
        raise ConflictError(
            f"{len(existing)} result file(s) already exist.",
            hint="Use --on-existing skip or --on-existing reanalyze.",
        )
    report_path = Path(values["report_path"]) if values.get("report_path") else None
    if report_path is not None and report_path.exists():
        raise ConflictError("--report-file already exists; reports are never overwritten.")
    if request.dry_run:
        return {
            "dryRun": True,
            "analyzerId": analyzer,
            "outputs": [
                {
                    "input": redact_input_reference(output.source.reference),
                    "output": str(output.path) if output.path else None,
                    "exists": output.exists,
                    "skipped": output.skipped,
                }
                for output in execution.outputs
            ],
        }
    if len(inputs.inputs) > CONFIRM_THRESHOLD:
        user_confirmation(
            f"Analyze {len(inputs.inputs)} inputs with '{analyzer}'? This may incur cost.",
            yes=request.yes,
        )

    jobs = [
        AnalyzeJob(
            input_ref=redact_input_reference(output.source.reference),
            input_url=output.source.url,
            analyzer_id=analyzer,
            out_path=output.path,
            output_format="markdown" if request.llm_input else "json",
        )
        for output in execution.outputs
        if not output.skipped
    ]
    records = [
        {
            "input": redact_input_reference(output.source.reference),
            "status": "skipped",
            "reason": "result file already exists",
            "output": str(output.path) if output.path else None,
        }
        for output in execution.outputs
        if output.skipped
    ]
    streamed: Any = None

    def persist(outcome: Any) -> None:
        nonlocal streamed
        job = outcome.job
        if not outcome.ok:
            records.append(
                {
                    "input": job.input_ref,
                    "status": "failed",
                    "error": redact_sensitive_urls(str(outcome.error)),
                    "output": str(job.out_path) if job.out_path else None,
                }
            )
            return
        response = outcome.result
        usage = response.usage if isinstance(response, AnalyzeResponse) else None
        result = response.result if isinstance(response, AnalyzeResponse) else response
        if request.llm_input:
            from azure.ai.contentunderstanding import to_llm_input

            payload = to_llm_input(result)
            if not isinstance(payload, str) or not payload.strip():
                raise ServiceError("analysis succeeded, but the model-input result was empty.")
        else:
            payload = to_plain_value(result)
        if job.out_path is None:
            streamed = (
                {"result": payload, "usage": to_plain_value(usage)}
                if request.usage
                else payload
            )
        elif request.llm_input:
            write_text(
                job.out_path,
                str(payload),
                overwrite=policy is ExistingResultPolicy.REANALYZE,
            )
        else:
            write_json(
                job.out_path,
                payload,
                overwrite=policy is ExistingResultPolicy.REANALYZE,
            )
        records.append(
            {
                "input": job.input_ref,
                "status": "succeeded",
                "analyzerId": analyzer,
                "output": str(job.out_path) if job.out_path else None,
                "usage": to_plain_value(usage) if request.usage else None,
            }
        )

    batch = resolve_identifier(ANALYZE.operation)(
        create_content_understanding_client(
            cmd,
            endpoint=values.get("endpoint"),
            api_version=values.get("api_version"),
            profile_name=values.get("profile_name"),
            auth_mode=values.get("auth_mode"),
            api_key=values.get("api_key"),
        ),
        request,
        input_plan=inputs,
        jobs=jobs,
        on_result=persist,
        run=_runner(request),
    )
    if report_path is not None:
        _report(
            report_path,
            analyzer,
            "llm-input" if request.llm_input else "full",
            records,
        )
    if batch.failures:
        raise ServiceError(
            f"{len(batch.failures)} analysis job(s) failed.",
            hint="Use --report-file to retain per-input status without exposing SAS tokens.",
        )
    return streamed if len(jobs) == 1 and jobs[0].out_path is None else records