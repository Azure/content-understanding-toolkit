# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Internal model setup used by generated azd post-provision hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
from azure.cli.core.util import get_az_user_agent
from azure.mgmt.cognitiveservices.models import Deployment, DeploymentModel, DeploymentProperties, Sku
from knack.prompting import prompt

from cu_cli_core.errors import ConflictError, ServiceError, UsageError
from cu_cli_core.defaults import apply_defaults
from cu_cli_core.infra_models import (
    DeployableModel,
    deployable_models,
    recommended_models,
    select_requested_models,
    supported_model_names,
    write_models_file,
)

from . import __version__
from ._client_factory import (
    create_content_understanding_client,
    get_subscription_id,
    resolve_service_settings,
)
from ._resources import _management_client

def _value(value: Any, snake: str, camel: str | None = None) -> Any:
    if isinstance(value, dict):
        return value.get(snake, value.get(camel or snake))
    return getattr(value, snake, getattr(value, camel or snake, None))


def _supported_models(analyzer: Any) -> dict[str, set[str]]:
    return supported_model_names(analyzer)


def _candidates(models: Iterable[Any], supported: dict[str, set[str]]) -> list[DeployableModel]:
    return deployable_models(models, supported)


def _select(candidates: list[DeployableModel], requested: Iterable[str]) -> list[DeployableModel]:
    return select_requested_models(candidates, requested)


def _recommended(candidates: list[DeployableModel]) -> list[DeployableModel]:
    return recommended_models(candidates)


def _prompt_models(candidates: list[DeployableModel]) -> list[DeployableModel]:
    choices = ["0: no models"] + [f"{index}: {item.selector} ({item.kind})" for index, item in enumerate(candidates, 1)]
    raw = prompt("Select model numbers, comma-separated\n" + "\n".join(choices), default="0")
    try:
        indices = [int(value.strip()) for value in raw.split(",")]
    except ValueError as exc:
        raise UsageError("model selections must be comma-separated numbers.") from exc
    if 0 in indices:
        if len(indices) != 1:
            raise UsageError("0 cannot be combined with model selections.")
        return []
    if any(index < 1 or index > len(candidates) for index in indices):
        raise UsageError("a model selection is out of range.")
    return _select(candidates, [candidates[index - 1].selector for index in indices])


def _write(path: Path, models: Iterable[DeployableModel]) -> None:
    write_models_file(path, models)


def _deploy(client: Any, resource_group: str, account: str, models: Iterable[DeployableModel]) -> None:
    existing = {str(item.name).casefold(): item for item in client.deployments.list(resource_group, account)}
    for model in models:
        current = existing.get(model.name.casefold())
        if current is not None:
            deployed = _value(_value(current, "properties"), "model")
            if (
                str(_value(deployed, "name") or "").casefold(),
                str(_value(deployed, "version") or ""),
            ) == (model.name.casefold(), model.version):
                continue
            raise ConflictError(f"deployment '{model.name}' already exists with a different model version.")
        payload = Deployment(
            sku=Sku(name=model.sku_name, capacity=model.sku_capacity),
            properties=DeploymentProperties(
                model=DeploymentModel(format=model.format, name=model.name, version=model.version)
            ),
        )
        client.deployments.begin_create_or_update(resource_group, account, model.name, payload).result()


def setup_models(cmd: Any, **values: Any) -> dict[str, Any]:
    """Discover, optionally deploy, and persist CU-supported model definitions."""

    selection = str(values.get("selection") or "recommended").strip()
    output = Path(values.get("out_path") or "infra/models.json")
    if selection.casefold() == "none":
        _write(output, [])
        return {"models": [], "outputFile": str(output), "deployed": False}
    subscription = get_subscription_id(cmd.cli_ctx)
    management = _management_client(cmd, subscription)
    if values.get("use_key"):
        endpoint, api_version = resolve_service_settings(
            endpoint=values.get("endpoint"), api_version=values.get("api_version"), profile_name=None
        )
        keys = management.accounts.list_keys(values["resource_group"], values["account_name"])
        key = str(keys.key1 or keys.key2 or "")
        if not key:
            raise ServiceError("the Microsoft Foundry resource returned no account key.")
        cu_client = ContentUnderstandingClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
            api_version=api_version,
            user_agent=f"{get_az_user_agent()} content-understanding/{__version__}",
        )
    else:
        cu_client = create_content_understanding_client(
            cmd,
            endpoint=values.get("endpoint"),
            api_version=values.get("api_version"),
            profile_name=None,
            auth_mode=values.get("auth_mode"),
            api_key=values.get("api_key"),
            subscription_id=subscription,
        )
    supported = _supported_models(cu_client.get_analyzer("prebuilt-document"))
    candidates = _candidates(
        management.accounts.list_models(values["resource_group"], values["account_name"]),
        supported,
    )
    if not candidates:
        raise ServiceError("no live CU-supported models are deployable on this account.")
    if selection.casefold() == "recommended":
        selected = _recommended(candidates)
    elif selection.casefold() == "prompt":
        selected = _prompt_models(candidates)
    else:
        selected = _select(candidates, selection.split(","))
    if values.get("deploy", True):
        _deploy(management, values["resource_group"], values["account_name"], selected)
        if values.get("configure_defaults", True):
            apply_defaults(cu_client, {item.name: item.name for item in selected}, replace=False)
    _write(output, selected)
    return {
        "models": [item.template_entry() for item in selected],
        "outputFile": str(output),
        "deployed": bool(values.get("deploy", True)),
        "defaultsConfigured": bool(
            values.get("deploy", True) and values.get("configure_defaults", True) and selected
        ),
    }
