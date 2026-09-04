"""Spec-backed structural validation against the bundled CU OpenAPI (Swagger 2.0).

The CU service contract is published as ``ContentUnderstanding.json`` (Swagger
2.0, whose ``definitions`` are JSON Schema Draft 4). We bundle that JSON per
api-version and validate an analyzer body against the ``ContentAnalyzer``
definition with ``jsonschema`` — so the structural rules come straight from the
service contract instead of a hand-maintained list.

Two adaptations are applied:

* **Create-view** — the ``ContentAnalyzer`` model marks server-generated fields
  (``status``, ``createdAt``, ``lastModifiedAt``, ``analyzerId``) as ``readOnly``
  yet lists them in ``required``. Those don't exist in an authoring/create body,
  so we drop ``readOnly`` properties from every object's ``required`` list.
* **Graceful degradation** — if the bundled spec or ``jsonschema`` is
  unavailable, ``validate_against_spec`` returns an OK result with no findings so
  the primary (rule-based) validator is never blocked.

This module is an *additional* structural gate (opt-in via ``cu analyzer
validate --spec``); the curated, message-friendly checks in ``schema_validate``
remain the default.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources as ir
from typing import Any, List

from .schema_validation import Finding, ValidationResult
from .service_options import DEFAULT_API_VERSION

_ANALYZER_DEF = "ContentAnalyzer"
_SPEC_URI = "urn:cu-spec"


def _spec_resource(api_version: str) -> str:
    return f"openapi/{api_version}/ContentUnderstanding.json"


@lru_cache(maxsize=None)
def _load_spec(api_version: str) -> dict | None:
    try:
        text = (ir.files("cu_cli_core")
                .joinpath(f"resources/{_spec_resource(api_version)}")
                .read_text(encoding="utf-8"))
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def spec_available(api_version: str = DEFAULT_API_VERSION) -> bool:
    """True when the bundled OpenAPI spec exists and has the analyzer definition."""
    spec = _load_spec(api_version)
    return bool(spec and isinstance(spec.get("definitions"), dict)
                and _ANALYZER_DEF in spec["definitions"])


def spec_allowed_types(api_version: str = DEFAULT_API_VERSION) -> List[str]:
    spec = _load_spec(api_version) or {}
    enum = (spec.get("definitions", {}).get("ContentFieldType", {}) or {}).get("enum") or []
    return sorted(str(v) for v in enum)


def spec_allowed_methods(api_version: str = DEFAULT_API_VERSION) -> List[str]:
    spec = _load_spec(api_version) or {}
    enum = (spec.get("definitions", {}).get("GenerationMethod", {}) or {}).get("enum") or []
    return sorted(str(v) for v in enum)


def _create_view_defs(defs: dict) -> dict:
    """Return a copy of *defs* with ``readOnly`` props removed from ``required``."""
    out = copy.deepcopy(defs)
    for d in out.values():
        if isinstance(d, dict) and d.get("type") == "object" and isinstance(d.get("required"), list):
            props = d.get("properties") or {}
            d["required"] = [
                r for r in d["required"]
                if not (isinstance(props.get(r), dict) and props[r].get("readOnly"))
            ]
    return out


@lru_cache(maxsize=None)
def _build_validator(api_version: str):
    spec = _load_spec(api_version)
    if not spec:
        return None
    defs = spec.get("definitions")
    if not isinstance(defs, dict) or _ANALYZER_DEF not in defs:
        return None
    try:
        from jsonschema import Draft4Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT4
    except Exception:  # pragma: no cover - deps are declared, defensive only
        return None

    create_view = {"definitions": _create_view_defs(defs)}
    resource = Resource.from_contents(create_view, default_specification=DRAFT4)
    registry = Registry().with_resource(uri=_SPEC_URI, resource=resource)
    return Draft4Validator(
        {"$ref": f"{_SPEC_URI}#/definitions/{_ANALYZER_DEF}"},
        registry=registry,
    )


def _dotted(parts: list) -> str:
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += f".{p}" if out else str(p)
    return out or "$"


def validate_against_spec(body: Any, *, api_version: str = DEFAULT_API_VERSION) -> ValidationResult:
    """Validate *body* against the bundled CU ``ContentAnalyzer`` (create-view).

    Returns an OK result with no findings when the spec or ``jsonschema`` are
    unavailable, so it never blocks the primary validator.
    """
    validator = _build_validator(api_version)
    if validator is None:
        return ValidationResult(ok=True)
    if not isinstance(body, dict):
        return ValidationResult(
            ok=False, errors=[Finding("$", "schema root must be a JSON object.")]
        )
    errors: List[Finding] = []
    for err in sorted(validator.iter_errors(body), key=lambda e: list(e.absolute_path)):
        path = _dotted(list(err.absolute_path))
        errors.append(Finding(path, f"{err.message} (per CU {api_version} spec)"))
    return ValidationResult(ok=not errors, errors=errors)
