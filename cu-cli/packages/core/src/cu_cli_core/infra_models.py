# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Framework-neutral model discovery and selection policy for CU infrastructure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .errors import ServiceError, ValidationError

SKU_PREFERENCE_ORDER = ("GlobalStandard", "DataZoneStandard", "Standard")
DEFAULT_COMPLETION_PREFERENCE = ("gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini")
DEFAULT_EMBEDDING_PREFERENCE = (
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
)


@dataclass(frozen=True)
class DeployableModel:
    """A CU-supported model that can be deployed to a Foundry account."""

    name: str
    version: str
    format: str
    kind: str
    sku_name: str
    sku_capacity: int
    is_default_version: bool = False

    @property
    def selector(self) -> str:
        """Return the unambiguous model selector."""

        return f"{self.name}@{self.version}"

    def to_template_entry(self) -> dict[str, Any]:
        """Return the Bicep model-file representation."""

        return {
            "name": self.name,
            "model": self.name,
            "version": self.version,
            "format": self.format,
            "skuName": self.sku_name,
            "skuCapacity": self.sku_capacity,
        }

    def template_entry(self) -> dict[str, Any]:
        """Return the legacy frontend name for the Bicep representation."""

        return self.to_template_entry()


def _value(value: Any, snake: str, camel: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(snake, value.get(camel))
    return getattr(value, snake, getattr(value, camel, None))


def supported_model_names(analyzer: Any) -> dict[str, set[str]]:
    """Return completion and embedding model families from a CU analyzer response."""

    supported = _value(analyzer, "supported_models", "supportedModels")
    if supported is None:
        raise ServiceError("prebuilt-document did not return supportedModels.")

    result: dict[str, set[str]] = {}
    for kind in ("completion", "embedding"):
        raw = _value(supported, kind, kind)
        if raw is None:
            raw = []
        if not isinstance(raw, (list, tuple, set)):
            raise ServiceError(f"prebuilt-document returned invalid supportedModels.{kind}.")
        result[kind] = {str(name).strip().lower() for name in raw if str(name).strip()}
    if not result["completion"] and not result["embedding"]:
        raise ServiceError("prebuilt-document returned an empty supportedModels catalog.")
    return result


def _choose_sku(skus: Iterable[Any]) -> tuple[str, int] | None:
    parsed: dict[str, tuple[str, int]] = {}
    for sku in skus:
        name = str(_value(sku, "name", "name") or "").strip()
        if not name:
            continue
        capacity = _value(sku, "capacity", "capacity")
        raw_default = _value(capacity, "default", "default") if capacity is not None else _value(
            sku, "default_capacity", "defaultCapacity"
        )
        try:
            default_capacity = int(str(raw_default))
        except (TypeError, ValueError):
            default_capacity = 1
        parsed[name.casefold()] = (name, max(default_capacity, 1))
    for preferred in SKU_PREFERENCE_ORDER:
        match = parsed.get(preferred.casefold())
        if match:
            return match
    return sorted(parsed.values(), key=lambda item: item[0].casefold())[0] if parsed else None


def deployable_models(arm_models: Iterable[Any], supported: Mapping[str, set[str]]) -> list[DeployableModel]:
    """Intersect live ARM model metadata with CU-supported model families."""

    kind_by_name = {name: kind for kind, names in supported.items() for name in names}
    result: list[DeployableModel] = []
    for row in arm_models:
        name = str(_value(row, "name", "name") or "").strip()
        version = str(_value(row, "version", "version") or "").strip()
        model_format = str(_value(row, "format", "format") or "").strip()
        kind = kind_by_name.get(name.casefold())
        skus = _value(row, "skus", "skus") or []
        sku = _choose_sku(skus)
        if name and version and model_format and kind and sku:
            result.append(
                DeployableModel(
                    name=name,
                    version=version,
                    format=model_format,
                    kind=kind,
                    sku_name=sku[0],
                    sku_capacity=sku[1],
                    is_default_version=bool(_value(row, "is_default_version", "isDefaultVersion")),
                )
            )
    return sorted(result, key=lambda model: (model.kind, model.name.casefold(), model.version))


def select_requested_models(
    candidates: Iterable[DeployableModel], requested: Iterable[str]
) -> list[DeployableModel]:
    """Resolve explicit selectors without guessing between multiple versions."""

    candidates = list(candidates)
    by_selector = {model.selector.casefold(): model for model in candidates}
    by_name: dict[str, list[DeployableModel]] = {}
    for model in candidates:
        by_name.setdefault(model.name.casefold(), []).append(model)

    selected: list[DeployableModel] = []
    for raw in requested:
        selector = raw.strip().casefold()
        if not selector:
            continue
        if "@" in selector:
            selected_model = by_selector.get(selector)
            if selected_model is None:
                raise ValidationError(f"model '{raw}' is not supported and deployable on this account.")
        else:
            versions = by_name.get(selector, [])
            if not versions:
                raise ValidationError(f"model '{raw}' is not supported and deployable on this account.")
            if len(versions) > 1:
                raise ValidationError(
                    f"model '{raw}' has multiple deployable versions.",
                    hint=f"select one explicitly: {', '.join(model.selector for model in versions)}",
                )
            selected_model = versions[0]
        if any(existing.name.casefold() == selected_model.name.casefold() for existing in selected):
            raise ValidationError(f"model family '{selected_model.name}' was selected more than once.")
        selected.append(selected_model)
    return selected


def recommended_models(candidates: Iterable[DeployableModel]) -> list[DeployableModel]:
    """Choose deterministic completion and embedding models from live candidates."""

    candidates = list(candidates)
    selected: list[DeployableModel] = []
    for kind, preference in (
        ("completion", DEFAULT_COMPLETION_PREFERENCE),
        ("embedding", DEFAULT_EMBEDDING_PREFERENCE),
    ):
        options = [model for model in candidates if model.kind == kind]
        chosen = None
        for name in preference:
            family = [model for model in options if model.name.casefold() == name]
            if not family:
                continue
            defaults = [model for model in family if model.is_default_version]
            if len(defaults) == 1:
                chosen = defaults[0]
            elif len(family) == 1:
                chosen = family[0]
            else:
                raise ValidationError(
                    f"recommended model '{name}' has multiple deployable versions.",
                    hint=f"select one explicitly: {', '.join(model.selector for model in family)}",
                )
            break
        if chosen is None and options:
            if len(options) > 1:
                raise ValidationError(
                    f"no unambiguous recommended {kind} model is available.",
                    hint="select an explicit model@version.",
                )
            chosen = options[0]
        if chosen is not None:
            selected.append(chosen)
    if not selected:
        raise ServiceError("no CU-supported models are deployable on this account.")
    return selected


def write_models_file(path: Path, models: Iterable[DeployableModel]) -> None:
    """Persist selected model definitions atomically in the Bicep input shape."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps([model.to_template_entry() for model in models], indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
