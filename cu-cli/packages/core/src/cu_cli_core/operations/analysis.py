# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared orchestration for analyze and analyzer-test commands."""

from __future__ import annotations

from typing import Any, Callable

from ..analysis import AnalyzeJob, AnalyzeOutcome, BatchResult, analyze_many
from ..contracts import AnalyzeRequest, AnalyzerTestRequest, InputPlan
from ..input_planning import plan_inputs

_TEST_DISCLAIMER = (
    "This is not a real accuracy benchmark. It only checks whether a value was "
    "extracted or generated, and reports confidence when the service returns it."
)


def _input_plan(request: AnalyzeRequest | AnalyzerTestRequest) -> InputPlan:
    return plan_inputs(
        positional=request.positional_inputs,
        files=request.files,
        sources=request.sources,
        pattern=request.pattern,
        recursive=request.recursive,
    )


def execute_analyze(
    client: Any,
    request: AnalyzeRequest,
    *,
    input_plan: InputPlan | None = None,
    jobs: list[AnalyzeJob] | None = None,
    on_result: Callable[[AnalyzeOutcome], None] | None = None,
    run: Callable[[Any, AnalyzeJob], Any] | None = None,
) -> BatchResult:
    """Execute a normalized analyze request against an injected client."""

    planned = input_plan or _input_plan(request)
    selected_jobs = jobs or [
        AnalyzeJob(
            input_ref=str(item.path),
            analyzer_id=request.analyzer or "",
            out_path=None,
        )
        for item in planned.inputs
    ]
    return analyze_many(
        client,
        selected_jobs,
        concurrency=request.concurrency,
        on_result=on_result,
        run=run,
    )


def _field_as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if hasattr(value, "as_dict"):
        mapped = value.as_dict()
        return mapped if isinstance(mapped, dict) else None
    return None


def _coerce_field_value(field: Any) -> Any:
    if field is None or isinstance(field, (str, int, float, bool)):
        return field
    mapped = _field_as_dict(field)
    if mapped is None:
        return str(field)
    for key in (
        "valueString",
        "valueNumber",
        "valueInteger",
        "valueBoolean",
        "valueDate",
        "valueTime",
        "valueJson",
    ):
        if mapped.get(key) is not None:
            return mapped[key]
    if mapped.get("valueArray") is not None:
        return [_coerce_field_value(value) for value in mapped["valueArray"]]
    if isinstance(mapped.get("valueObject"), dict):
        return {
            key: _coerce_field_value(value)
            for key, value in mapped["valueObject"].items()
        }
    for key in ("value", "content"):
        if mapped.get(key) is not None:
            return mapped[key]
    return None


def _coerce_field_confidence(field: Any) -> float | None:
    confidence = (
        field.get("confidence")
        if isinstance(field, dict)
        else getattr(field, "confidence", None)
    )
    if confidence is None:
        mapped = _field_as_dict(field)
        confidence = mapped.get("confidence") if mapped else None
    try:
        return float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        return None


def _child_field_entries(
    field_name: str,
    field: Any,
) -> dict[str, dict[str, Any]]:
    mapped = _field_as_dict(field)
    if mapped is None:
        return {}
    value_object = mapped.get("valueObject")
    if isinstance(value_object, dict):
        return {
            f"{field_name}.{name}": {
                "value": _coerce_field_value(value),
                "confidence": _coerce_field_confidence(value),
            }
            for name, value in value_object.items()
        }

    value_array = mapped.get("valueArray")
    if not isinstance(value_array, list):
        return {}
    child_values: dict[str, list[Any]] = {}
    child_confidences: dict[str, list[float]] = {}
    for item in value_array:
        item_mapping = _field_as_dict(item)
        item_object = item_mapping.get("valueObject") if item_mapping else None
        if not isinstance(item_object, dict):
            continue
        for name, value in item_object.items():
            child_values.setdefault(name, []).append(_coerce_field_value(value))
            confidence = _coerce_field_confidence(value)
            if confidence is not None:
                child_confidences.setdefault(name, []).append(confidence)
    return {
        f"{field_name}[].{name}": {
            "value": values,
            "confidence": (
                round(sum(child_confidences[name]) / len(child_confidences[name]), 3)
                if child_confidences.get(name)
                else None
            ),
        }
        for name, values in child_values.items()
    }


def extract_fields_from_result(result: Any) -> dict[str, dict[str, Any]]:
    """Flatten result fields for analyzer-test coverage reporting."""

    extracted: dict[str, dict[str, Any]] = {}
    for content in getattr(result, "contents", None) or []:
        fields = getattr(content, "fields", None)
        if fields is None:
            continue
        if hasattr(fields, "items"):
            items = fields.items()
        elif hasattr(fields, "as_dict"):
            items = fields.as_dict().items()
        else:
            continue
        for name, value in items:
            if name in extracted and extracted[name].get("value") not in (
                None,
                "",
                [],
                {},
            ):
                continue
            extracted[name] = {
                "value": _coerce_field_value(value),
                "confidence": _coerce_field_confidence(value),
            }
            extracted.update(_child_field_entries(name, value))
    return extracted


def _is_populated_value(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, dict):
        return any(_is_populated_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_is_populated_value(item) for item in value)
    return True


def analyzer_test_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic field-coverage and confidence statistics."""

    low_threshold = 0.6
    total = len(samples)
    succeeded = sum(sample.get("status") == "ok" for sample in samples)
    field_names = {
        name
        for sample in samples
        for name in (sample.get("fields") or {})
    }
    per_field: dict[str, dict[str, Any]] = {}
    for name in sorted(field_names):
        populated = 0
        low = 0
        confidences: list[float] = []
        for sample in samples:
            field = (sample.get("fields") or {}).get(name)
            if field is None or field.get("value") is None:
                continue
            if _is_populated_value(field["value"]):
                populated += 1
            confidence = field.get("confidence")
            if isinstance(confidence, (int, float)):
                confidences.append(float(confidence))
                if confidence < low_threshold:
                    low += 1
        per_field[name] = {
            "populated": populated,
            "populatedPct": round(populated / total * 100, 1) if total else 0.0,
            "meanConfidence": (
                round(sum(confidences) / len(confidences), 3)
                if confidences
                else None
            ),
            "lowConfidenceCount": low,
        }
    return {
        "samplesTotal": total,
        "samplesOk": succeeded,
        "samplesFailed": total - succeeded,
        "disclaimer": _TEST_DISCLAIMER,
        "fields": per_field,
        "lowConfidenceThreshold": low_threshold,
    }


def execute_analyzer_test(
    client: Any,
    request: AnalyzerTestRequest,
    *,
    input_plan: InputPlan | None = None,
    run: Callable[[Any, AnalyzeJob], Any] | None = None,
) -> dict[str, Any]:
    """Execute analyzer test samples and return a frontend-neutral report."""

    planned = input_plan or _input_plan(request)
    refs = [str(item.path) for item in planned.inputs]
    jobs = [
        AnalyzeJob(input_ref=ref, analyzer_id=request.name, out_path=None)
        for ref in refs
    ]
    samples: list[dict[str, Any]] = []

    def collect(outcome: AnalyzeOutcome) -> None:
        if outcome.ok:
            samples.append(
                {
                    "input": outcome.job.input_ref,
                    "status": "ok",
                    "fields": extract_fields_from_result(outcome.result),
                }
            )
        else:
            samples.append(
                {
                    "input": outcome.job.input_ref,
                    "status": "error",
                    "error": str(outcome.error)[:500],
                    "fields": {},
                }
            )

    analyze_many(
        client,
        jobs,
        concurrency=request.concurrency,
        on_result=collect,
        run=run,
    )
    order = {ref: index for index, ref in enumerate(refs)}
    samples.sort(key=lambda sample: order.get(sample["input"], 0))
    return {
        "analyzerId": request.name,
        "summary": analyzer_test_summary(samples),
        "samples": samples,
    }
