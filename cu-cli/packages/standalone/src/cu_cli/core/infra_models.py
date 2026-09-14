# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Live CU model discovery and deployment helpers for generated infrastructure."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

from cu_cli_core.errors import CuCoreError
from cu_cli_core.infra_models import (
    DeployableModel,
    deployable_models as _shared_deployable_models,
    recommended_models as _shared_recommended_models,
    select_requested_models as _shared_select_requested_models,
    supported_model_names as _shared_supported_model_names,
    write_models_file as _shared_write_models_file,
)

from ..errors import CuCliError


def _value(value: Any, snake: str, camel: str) -> Any:
    if isinstance(value, dict):
        return value.get(snake, value.get(camel))
    return getattr(value, snake, getattr(value, camel, None))


def _translate(action):
    try:
        return action()
    except CuCoreError as exc:
        raise CuCliError(exc.message, hint=exc.hint) from exc


def supported_model_names(analyzer: Any) -> dict[str, set[str]]:
    """Return CU-supported model families through the shared policy."""

    return _translate(lambda: _shared_supported_model_names(analyzer))


def deployable_models(arm_payload: Any, supported: dict[str, set[str]]) -> list[DeployableModel]:
    """Intersect an Azure CLI catalog with CU-supported model families."""

    if not isinstance(arm_payload, list):
        raise CuCliError("Azure returned an invalid model catalog.")
    return _translate(lambda: _shared_deployable_models(arm_payload, supported))


def select_requested_models(
    candidates: list[DeployableModel], requested: Iterable[str]
) -> list[DeployableModel]:
    """Resolve explicit model selectors through the shared policy."""

    return _translate(lambda: _shared_select_requested_models(candidates, requested))


def recommended_models(candidates: list[DeployableModel]) -> list[DeployableModel]:
    """Choose live recommended models through the shared policy."""

    return _translate(lambda: _shared_recommended_models(candidates))


def write_models_file(path: Path, models: Iterable[DeployableModel]) -> None:
    """Write shared Bicep model serialization atomically."""

    _shared_write_models_file(path, models)


def fetch_account_models(
    resource_group: str, account_name: str, subscription_id: str
) -> list[dict[str, Any]]:
    """Read live Foundry model metadata through the standalone Azure CLI host."""

    result = subprocess.run(
        [
            "az", "cognitiveservices", "account", "list-models", "--resource-group",
            resource_group, "--name", account_name, "--subscription", subscription_id,
            "--output", "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise CuCliError(
            f"could not read the Foundry model catalog: {result.stderr.strip() or 'Azure CLI returned no error detail.'}"
        )
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CuCliError("Azure CLI returned invalid JSON for the Foundry model catalog.") from exc
    if not isinstance(payload, list):
        raise CuCliError("Azure CLI returned an invalid Foundry model catalog.")
    return payload


def deploy_models(
    resource_group: str, account_name: str, subscription_id: str, models: Iterable[DeployableModel]
) -> None:
    """Deploy selected models sequentially through the standalone Azure CLI host."""

    existing_result = subprocess.run(
        [
            "az", "cognitiveservices", "account", "deployment", "list", "--resource-group",
            resource_group, "--name", account_name, "--subscription", subscription_id,
            "--output", "json",
        ], capture_output=True, text=True,
    )
    if existing_result.returncode != 0:
        raise CuCliError(
            f"could not inspect existing model deployments: {existing_result.stderr.strip() or 'Azure CLI returned no error detail.'}"
        )
    try:
        payload = json.loads(existing_result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CuCliError("Azure CLI returned invalid model deployment JSON.") from exc
    existing: dict[str, tuple[str, str]] = {}
    for deployment in payload if isinstance(payload, list) else []:
        if not isinstance(deployment, dict):
            continue
        properties = deployment.get("properties") or {}
        model = properties.get("model") if isinstance(properties, dict) else {}
        name = str(deployment.get("name") or "").strip().casefold()
        if name and isinstance(model, dict):
            existing[name] = (
                str(model.get("name") or "").strip().casefold(),
                str(model.get("version") or "").strip(),
            )
    for model in models:
        deployed = existing.get(model.name.casefold())
        if deployed == (model.name.casefold(), model.version):
            continue
        if deployed is not None:
            raise CuCliError(
                f"deployment '{model.name}' already exists with model '{deployed[0]}@{deployed[1]}'.",
                hint="choose another model version or delete the existing deployment explicitly; live setup never replaces deployments.",
            )
        result = subprocess.run(
            [
                "az", "cognitiveservices", "account", "deployment", "create", "--resource-group",
                resource_group, "--name", account_name, "--subscription", subscription_id,
                "--deployment-name", model.name, "--model-name", model.name, "--model-version",
                model.version, "--model-format", model.format, "--sku-name", model.sku_name,
                "--sku-capacity", str(model.sku_capacity), "--only-show-errors",
            ], capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise CuCliError(
                f"could not deploy model '{model.selector}': {result.stderr.strip() or 'Azure CLI returned no error detail.'}"
            )
