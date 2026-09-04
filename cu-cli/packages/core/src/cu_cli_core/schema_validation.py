# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Local, structural schema validation against the bundled rules for an
api-version.

Deterministic and offline — **no service call**. ``validate`` produces detailed,
actionable messages: on a bad field ``type`` it names the field and lists the
accepted types, and returns exit code ``2`` on any error (so agents can branch).

The accepted types/methods are shared by both MVP api-versions; the
``api_version`` argument is threaded through so future versions can diverge
without changing call sites.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources as ir
from typing import Any, List, Optional, Tuple

from .service_options import DEFAULT_API_VERSION

# Accepted field types/methods come from the bundled CU OpenAPI spec (the service
# contract) so they never drift from the API. A hardcoded fallback keeps the
# validator working if the bundled spec is unavailable.
_FALLBACK_TYPES = ["array", "boolean", "date", "integer", "json", "number",
                   "object", "string", "time"]
_FALLBACK_METHODS = ["classify", "extract", "generate"]


def _spec_enums(api_version: str) -> Tuple[List[str], List[str]]:
    try:
        text = (ir.files("cu_cli_core")
                .joinpath(f"resources/openapi/{api_version}/ContentUnderstanding.json")
                .read_text(encoding="utf-8"))
        defs = json.loads(text).get("definitions", {})
        types = defs.get("ContentFieldType", {}).get("enum")
        methods = defs.get("GenerationMethod", {}).get("enum")
        return (sorted(types) if isinstance(types, list) and types else _FALLBACK_TYPES,
                sorted(methods) if isinstance(methods, list) and methods else _FALLBACK_METHODS)
    except Exception:
        return _FALLBACK_TYPES, _FALLBACK_METHODS


ALLOWED_TYPES, ALLOWED_METHODS = _spec_enums(DEFAULT_API_VERSION)

_CUSTOM_ANALYZER_ID_RE = re.compile(r"^[a-zA-Z0-9_]{1,64}$")
_BASE_ANALYZER_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")
_MAX_NESTING = 4
_MIN_DESCRIPTION_LEN = 15


@dataclass
class Finding:
    path: str
    msg: str


@dataclass
class ValidationResult:
    ok: bool
    errors: List[Finding] = field(default_factory=list)
    warnings: List[Finding] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [{"path": e.path, "msg": e.msg} for e in self.errors],
            "warnings": [{"path": w.path, "msg": w.msg} for w in self.warnings],
        }


def _types_list() -> str:
    return "[" + ", ".join(ALLOWED_TYPES) + "]"


def custom_analyzer_id_error(value: Any) -> str | None:
    """Return the user-facing validation error for a custom analyzer ID."""
    if isinstance(value, str) and _CUSTOM_ANALYZER_ID_RE.fullmatch(value):
        return None
    return (
        "must contain 1-64 ASCII letters, numbers, or underscores. "
        "Hyphens are reserved for service-provided prebuilt analyzer IDs "
        "(for example, 'prebuilt-invoice')."
    )


def _validate_field(name: str, defn: Any, path: str, depth: int,
                    errors: List[Finding], warnings: List[Finding]) -> None:
    if not isinstance(defn, dict):
        errors.append(Finding(path, f"field '{name}' must be an object."))
        return

    if "$ref" in defn:
        errors.append(Finding(
            f"{path}.$ref",
            "`$ref` is not currently supported in analyzer field schemas; "
            "inline the field definition.",
        ))
        return

    ftype = defn.get("type")

    if ftype is None:
        errors.append(Finding(
            f"{path}.type",
            "missing `type`; every field definition requires an explicit type.",
        ))
    elif ftype is not None and ftype not in ALLOWED_TYPES:
        errors.append(Finding(
            f"{path}.type",
            f"must be one of {_types_list()}, got '{ftype}'.",
        ))

    desc = defn.get("description")
    if desc is None or (isinstance(desc, str) and not desc.strip()):
        warnings.append(Finding(f"{path}.description",
                                "no `description` — the model uses this as a per-field prompt."))
    elif not isinstance(desc, str):
        errors.append(Finding(f"{path}.description", "must be a string."))
    elif len(desc.strip()) < _MIN_DESCRIPTION_LEN:
        warnings.append(Finding(f"{path}.description",
                                f"description is very short ({len(desc.strip())} chars); be specific."))

    method = defn.get("method")
    if method is not None and method not in ALLOWED_METHODS:
        errors.append(Finding(f"{path}.method",
                              f"must be one of [{', '.join(ALLOWED_METHODS)}], got '{method}'."))
    if method == "classify":
        enum = defn.get("enum")
        if not isinstance(enum, list) or len({str(e) for e in enum}) < 2:
            errors.append(Finding(f"{path}.enum",
                                  "`classify` fields require `enum` with >=2 distinct values."))

    if ftype == "array":
        items = defn.get("items")
        if not isinstance(items, dict):
            errors.append(Finding(f"{path}.items", "`array` fields require an `items` object."))
        else:
            _depth_check(depth + 1, f"{path}.items", errors, warnings)
            _validate_field(f"{name}[]", items, f"{path}.items", depth + 1, errors, warnings)

    if ftype == "object":
        props = defn.get("properties")
        if not isinstance(props, dict) or not props:
            errors.append(Finding(
                f"{path}.properties",
                "`object` fields require a non-empty `properties` map.",
            ))
        else:
            _depth_check(depth + 1, f"{path}.properties", errors, warnings)
            for sub_name, sub_def in props.items():
                _validate_field(sub_name, sub_def, f"{path}.properties.{sub_name}",
                                depth + 1, errors, warnings)

    esc = defn.get("estimateSourceAndConfidence")
    if esc is not None and not isinstance(esc, bool):
        errors.append(Finding(f"{path}.estimateSourceAndConfidence", "must be a boolean."))


def _depth_check(depth: int, path: str, errors: List[Finding], warnings: List[Finding]) -> None:
    if depth > _MAX_NESTING:
        warnings.append(Finding(path,
                                f"nesting depth {depth}; accuracy drops past depth "
                                f"{_MAX_NESTING}. Consider flattening."))


def validate_schema(body: Any, *, api_version: Optional[str] = None) -> ValidationResult:
    errors: List[Finding] = []
    warnings: List[Finding] = []

    if not isinstance(body, dict):
        errors.append(Finding("$", "schema root must be a JSON object."))
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    aid = body.get("analyzerId") or body.get("analyzer_id")
    if aid is not None:
        aid_error = custom_analyzer_id_error(aid)
        if aid_error:
            errors.append(Finding("analyzerId", aid_error))

    base = body.get("baseAnalyzerId") or body.get("base_analyzer_id")
    if base is not None and (not isinstance(base, str) or not _BASE_ANALYZER_ID_RE.match(base)):
        errors.append(Finding("baseAnalyzerId", "must match ^[a-zA-Z0-9._-]{1,64}$."))
    elif base is None:
        warnings.append(Finding("baseAnalyzerId",
                                "no `baseAnalyzerId`; recommend `prebuilt-document`."))

    pinned = body.get("apiVersion")
    if pinned is not None and api_version is not None and pinned != api_version:
        # Callers pass the already-reconciled api_version; a residual mismatch
        # here is surfaced so the schema and resolved version never diverge.
        errors.append(Finding("apiVersion",
                              f"schema pins '{pinned}' but resolved api-version is '{api_version}'."))

    models = body.get("models")
    if models is not None and not isinstance(models, dict):
        errors.append(Finding("models", "must be an object mapping role -> model name."))

    has_content_categories = False
    cfg = body.get("config")
    if cfg is not None:
        if not isinstance(cfg, dict):
            errors.append(Finding("config", "must be an object."))
        else:
            for bool_key in ("enableSegment", "segmentPerPage", "estimateFieldSourceAndConfidence"):
                val = cfg.get(bool_key)
                if val is not None and not isinstance(val, bool):
                    errors.append(Finding(f"config.{bool_key}", "must be a boolean."))

            cats = cfg.get("contentCategories")
            if cats is not None:
                if not isinstance(cats, dict) or not cats:
                    errors.append(Finding("config.contentCategories",
                                          "must be a non-empty object when provided."))
                else:
                    has_content_categories = True
                    for cat_name, cat_def in cats.items():
                        if not isinstance(cat_def, dict):
                            errors.append(Finding(
                                f"config.contentCategories.{cat_name}",
                                "must be an object with category definition fields.",
                            ))
                            continue

                        desc = cat_def.get("description")
                        if desc is None or (isinstance(desc, str) and not desc.strip()):
                            warnings.append(Finding(
                                f"config.contentCategories.{cat_name}.description",
                                "no `description` — classification quality improves with clear category intent.",
                            ))
                        elif not isinstance(desc, str):
                            errors.append(Finding(
                                f"config.contentCategories.{cat_name}.description",
                                "must be a string.",
                            ))

                        analyzer_id = cat_def.get("analyzerId")
                        if analyzer_id is not None:
                            if not isinstance(analyzer_id, str) or not _BASE_ANALYZER_ID_RE.match(analyzer_id):
                                errors.append(Finding(
                                    f"config.contentCategories.{cat_name}.analyzerId",
                                    "must match ^[a-zA-Z0-9._-]{1,64}$.",
                                ))

    fs = body.get("fieldSchema") or body.get("field_schema")
    if fs is None:
        if not has_content_categories:
            warnings.append(Finding("fieldSchema", "no `fieldSchema`; layout/markdown only."))
    elif not isinstance(fs, dict):
        errors.append(Finding("fieldSchema", "must be an object."))
    else:
        fields = fs.get("fields")
        if fields is None:
            warnings.append(Finding("fieldSchema.fields", "no `fields`; layout only."))
        elif not isinstance(fields, dict):
            errors.append(Finding("fieldSchema.fields", "must be an object."))
        elif fields:
            models_map = models if isinstance(models, dict) else {}
            if not models_map.get("completion"):
                warnings.append(Finding("models.completion",
                                        "field extraction needs a completion model, e.g. "
                                        "`\"models\": {\"completion\": \"gpt-5.2\"}`."))
            for name, defn in fields.items():
                _validate_field(name, defn, f"fieldSchema.fields.{name}", 1, errors, warnings)

        defs = fs.get("definitions")
        if defs is not None:
            if not isinstance(defs, dict):
                errors.append(Finding("fieldSchema.definitions", "must be an object."))
            else:
                for name, defn in defs.items():
                    _validate_field(name, defn, f"fieldSchema.definitions.{name}", 1,
                                    errors, warnings)

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def schema_pinned_version(body: Any) -> Optional[str]:
    if isinstance(body, dict):
        v = body.get("apiVersion")
        return v if isinstance(v, str) else None
    return None


def first_error_line(result: ValidationResult, schema_path: str) -> str:
    """The design-doc 'Invalid schema (structural)' one-liner for the first error."""
    e = result.errors[0]
    return (
        f"Schema invalid: {schema_path} — {e.path}: {e.msg} "
        "Run `cu analyzer validate --help` for validation guidance."
    )


def parse_and_validate(text: str, *, api_version: Optional[str] = None
                       ) -> Tuple[ValidationResult, Optional[dict]]:
    """Parse JSON text, then validate. JSON errors are returned as a validation
    error (exit-2 territory) rather than raised."""
    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        res = ValidationResult(
            ok=False,
            errors=[Finding("$", f"file is not valid JSON: {exc.msg} "
                                 f"at line {exc.lineno} col {exc.colno}.")],
        )
        return res, None
    result = validate_schema(body, api_version=api_version)
    return result, body if isinstance(body, dict) else None
