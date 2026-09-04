# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Live CU model discovery and deployment helpers for generated infrastructure."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..errors import CuCliError

SKU_PREFERENCE_ORDER = ("GlobalStandard", "DataZoneStandard", "Standard")
DEFAULT_COMPLETION_PREFERENCE = (
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
)
DEFAULT_EMBEDDING_PREFERENCE = (
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
)


@dataclass(frozen=True)
class DeployableModel:
    name: str
    version: str
    format: str
    kind: str
    sku_name: str
    sku_capacity: int
    is_default_version: bool = False

    @property
    def selector(self) -> str:
        return f"{self.name}@{self.version}"

    def to_template_entry(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.name,
            "version": self.version,
            "format": self.format,
            "skuName": self.sku_name,
            "skuCapacity": self.sku_capacity,
        }


def _value(value: Any, snake: str, camel: str) -> Any:
    if isinstance(value, dict):
        return value.get(snake, value.get(camel))
    return getattr(value, snake, getattr(value, camel, None))


def supported_model_names(analyzer: Any) -> dict[str, set[str]]:
    """Return completion/embedding model names from an analyzer response."""
    supported = _value(analyzer, "supported_models", "supportedModels")
    if supported is None:
        raise CuCliError(
            "prebuilt-document did not return supportedModels.",
            hint="verify that the selected CU API version exposes analyzer model metadata.",
        )

    result: dict[str, set[str]] = {}
    for kind in ("completion", "embedding"):
        raw = _value(supported, kind, kind)
        if raw is None:
            raw = []
        if not isinstance(raw, (list, tuple, set)):
            raise CuCliError(f"prebuilt-document returned invalid supportedModels.{kind}.")
        result[kind] = {
            str(name).strip().lower()
            for name in raw
            if str(name).strip()
        }
    if not result["completion"] and not result["embedding"]:
        raise CuCliError("prebuilt-document returned an empty supportedModels catalog.")
    return result


def _choose_sku(skus: Iterable[dict[str, Any]]) -> tuple[str, int] | None:
    parsed: dict[str, tuple[str, int]] = {}
    for sku in skus:
        if not isinstance(sku, dict):
            continue
        name = str(sku.get("name") or "").strip()
        if not name:
            continue
        capacity = sku.get("capacity")
        if isinstance(capacity, dict):
            raw_default = capacity.get("default")
        else:
            raw_default = sku.get("defaultCapacity")
        try:
            default_capacity = int(str(raw_default))
        except (TypeError, ValueError):
            default_capacity = 1
        parsed[name.lower()] = (name, max(default_capacity, 1))

    for preferred in SKU_PREFERENCE_ORDER:
        match = parsed.get(preferred.lower())
        if match:
            return match
    if not parsed:
        return None
    return sorted(parsed.values(), key=lambda item: item[0].lower())[0]


def deployable_models(
    arm_payload: Any,
    supported: dict[str, set[str]],
) -> list[DeployableModel]:
    """Intersect live ARM model metadata with CU-supported model names."""
    if not isinstance(arm_payload, list):
        raise CuCliError("Azure returned an invalid model catalog.")

    kind_by_name = {
        name: kind
        for kind, names in supported.items()
        for name in names
    }
    result: list[DeployableModel] = []
    for row in arm_payload:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        version = str(row.get("version") or "").strip()
        model_format = str(row.get("format") or "").strip()
        kind = kind_by_name.get(name.lower())
        sku = _choose_sku(row.get("skus") or [])
        if not name or not version or not model_format or not kind or sku is None:
            continue
        result.append(
            DeployableModel(
                name=name,
                version=version,
                format=model_format,
                kind=kind,
                sku_name=sku[0],
                sku_capacity=sku[1],
                is_default_version=bool(
                    row.get("isDefaultVersion", row.get("is_default_version", False))
                ),
            )
        )
    return sorted(result, key=lambda model: (model.kind, model.name.lower(), model.version))


def fetch_account_models(
    resource_group: str,
    account_name: str,
    subscription_id: str,
) -> list[dict[str, Any]]:
    """Read live deployable model metadata for an existing Microsoft Foundry resource."""
    result = subprocess.run(
        [
            "az",
            "cognitiveservices",
            "account",
            "list-models",
            "--resource-group",
            resource_group,
            "--name",
            account_name,
            "--subscription",
            subscription_id,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "Azure CLI returned no error detail."
        raise CuCliError(f"could not read the Foundry model catalog: {detail}")
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CuCliError("Azure CLI returned invalid JSON for the Foundry model catalog.") from exc
    if not isinstance(payload, list):
        raise CuCliError("Azure CLI returned an invalid Foundry model catalog.")
    return payload


def select_requested_models(
    candidates: list[DeployableModel],
    requested: Iterable[str],
) -> list[DeployableModel]:
    """Resolve model or model@version selectors without guessing versions."""
    by_name: dict[str, list[DeployableModel]] = {}
    by_selector = {model.selector.lower(): model for model in candidates}
    for candidate in candidates:
        by_name.setdefault(candidate.name.lower(), []).append(candidate)

    selected: list[DeployableModel] = []
    for raw in requested:
        selector = raw.strip().lower()
        if not selector:
            continue
        if "@" in selector:
            selected_model = by_selector.get(selector)
            if selected_model is None:
                raise CuCliError(f"model '{raw}' is not supported and deployable on this account.")
        else:
            versions = by_name.get(selector, [])
            if not versions:
                raise CuCliError(f"model '{raw}' is not supported and deployable on this account.")
            if len(versions) > 1:
                choices = ", ".join(model.selector for model in versions)
                raise CuCliError(
                    f"model '{raw}' has multiple deployable versions.",
                    hint=f"select one explicitly: {choices}",
                )
            selected_model = versions[0]
        if any(existing.name.lower() == selected_model.name.lower() for existing in selected):
            raise CuCliError(f"model family '{selected_model.name}' was selected more than once.")
        selected.append(selected_model)
    return selected


def recommended_models(candidates: list[DeployableModel]) -> list[DeployableModel]:
    """Choose one completion and embedding model from live candidates."""
    selected: list[DeployableModel] = []
    for kind, preference in (
        ("completion", DEFAULT_COMPLETION_PREFERENCE),
        ("embedding", DEFAULT_EMBEDDING_PREFERENCE),
    ):
        options = [model for model in candidates if model.kind == kind]
        chosen = None
        for name in preference:
            family = [model for model in options if model.name.lower() == name]
            if not family:
                continue
            defaults = [model for model in family if model.is_default_version]
            if len(defaults) == 1:
                chosen = defaults[0]
            elif len(family) == 1:
                chosen = family[0]
            else:
                choices = ", ".join(model.selector for model in family)
                raise CuCliError(
                    f"recommended model '{name}' has multiple deployable versions.",
                    hint=f"select one explicitly: {choices}",
                )
            break
        if chosen is None and options:
            if len(options) > 1:
                raise CuCliError(
                    f"no unambiguous recommended {kind} model is available.",
                    hint="select an explicit model@version.",
                )
            chosen = options[0]
        if chosen is not None:
            selected.append(chosen)
    if not selected:
        raise CuCliError("no CU-supported models are deployable on this account.")
    return selected


def write_models_file(path: Path, models: Iterable[DeployableModel]) -> None:
    """Persist selected models atomically for future azd/Bicep runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps([model.to_template_entry() for model in models], indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def deploy_models(
    resource_group: str,
    account_name: str,
    subscription_id: str,
    models: Iterable[DeployableModel],
) -> None:
    """Deploy selected models sequentially through Azure CLI."""
    existing_result = subprocess.run(
        [
            "az",
            "cognitiveservices",
            "account",
            "deployment",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            account_name,
            "--subscription",
            subscription_id,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if existing_result.returncode != 0:
        detail = existing_result.stderr.strip() or "Azure CLI returned no error detail."
        raise CuCliError(f"could not inspect existing model deployments: {detail}")
    try:
        existing_payload = json.loads(existing_result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CuCliError("Azure CLI returned invalid model deployment JSON.") from exc
    existing: dict[str, tuple[str, str]] = {}
    for deployment in existing_payload if isinstance(existing_payload, list) else []:
        if not isinstance(deployment, dict):
            continue
        deployment_name = str(deployment.get("name") or "").strip().lower()
        properties = deployment.get("properties") or {}
        model = properties.get("model") if isinstance(properties, dict) else {}
        if deployment_name and isinstance(model, dict):
            existing[deployment_name] = (
                str(model.get("name") or "").strip().lower(),
                str(model.get("version") or "").strip(),
            )

    for model in models:
        deployed = existing.get(model.name.lower())
        requested = (model.name.lower(), model.version)
        if deployed == requested:
            continue
        if deployed is not None:
            raise CuCliError(
                f"deployment '{model.name}' already exists with model "
                f"'{deployed[0]}@{deployed[1]}'.",
                hint="choose another model version or delete the existing deployment explicitly; "
                     "live setup never replaces deployments.",
            )
        result = subprocess.run(
            [
                "az",
                "cognitiveservices",
                "account",
                "deployment",
                "create",
                "--resource-group",
                resource_group,
                "--name",
                account_name,
                "--subscription",
                subscription_id,
                "--deployment-name",
                model.name,
                "--model-name",
                model.name,
                "--model-version",
                model.version,
                "--model-format",
                model.format,
                "--sku-name",
                model.sku_name,
                "--sku-capacity",
                str(model.sku_capacity),
                "--only-show-errors",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "Azure CLI returned no error detail."
            raise CuCliError(f"could not deploy model '{model.selector}': {detail}")
