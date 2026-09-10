# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Internal model setup used by generated azd post-provision hooks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
from azure.cli.core.util import get_az_user_agent
from azure.mgmt.cognitiveservices.models import Deployment, DeploymentModel, DeploymentProperties, Sku
from knack.prompting import prompt

from cu_cli_core.errors import ConflictError, ServiceError, UsageError, ValidationError
from cu_cli_core.defaults import apply_defaults

from . import __version__
from ._client_factory import (
    create_content_understanding_client,
    get_subscription_id,
    resolve_service_settings,
)
from ._resources import _management_client

_SKU_ORDER = ("GlobalStandard", "DataZoneStandard", "Standard")
_COMPLETION_ORDER = ("gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini")
_EMBEDDING_ORDER = ("text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002")


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

    def template_entry(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.name,
            "version": self.version,
            "format": self.format,
            "skuName": self.sku_name,
            "skuCapacity": self.sku_capacity,
        }


def _value(value: Any, snake: str, camel: str | None = None) -> Any:
    if isinstance(value, dict):
        return value.get(snake, value.get(camel or snake))
    return getattr(value, snake, getattr(value, camel or snake, None))


def _supported_models(analyzer: Any) -> dict[str, set[str]]:
    supported = _value(analyzer, "supported_models", "supportedModels")
    if supported is None:
        raise ServiceError("prebuilt-document did not return supportedModels.")
    result: dict[str, set[str]] = {}
    for kind in ("completion", "embedding"):
        raw = _value(supported, kind) or []
        result[kind] = {str(item).strip().lower() for item in raw if str(item).strip()}
    if not any(result.values()):
        raise ServiceError("prebuilt-document returned an empty supportedModels catalog.")
    return result


def _sku(model: Any) -> tuple[str, int] | None:
    available: dict[str, tuple[str, int]] = {}
    for sku in _value(model, "skus") or []:
        name = str(_value(sku, "name") or "").strip()
        capacity = _value(sku, "capacity")
        default = _value(capacity, "default") if capacity is not None else None
        if name:
            try:
                parsed = max(int(default or 1), 1)
            except (TypeError, ValueError):
                parsed = 1
            available[name.casefold()] = (name, parsed)
    for name in _SKU_ORDER:
        if name.casefold() in available:
            return available[name.casefold()]
    return next(iter(sorted(available.values())), None)


def _candidates(models: Iterable[Any], supported: dict[str, set[str]]) -> list[DeployableModel]:
    kind_by_name = {name: kind for kind, names in supported.items() for name in names}
    result = []
    for model in models:
        name = str(_value(model, "name") or "").strip()
        version = str(_value(model, "version") or "").strip()
        model_format = str(_value(model, "format") or "").strip()
        sku = _sku(model)
        kind = kind_by_name.get(name.casefold())
        if name and version and model_format and sku and kind:
            result.append(
                DeployableModel(
                    name,
                    version,
                    model_format,
                    kind,
                    sku[0],
                    sku[1],
                    bool(_value(model, "is_default_version", "isDefaultVersion")),
                )
            )
    return sorted(result, key=lambda item: (item.kind, item.name.casefold(), item.version))


def _select(candidates: list[DeployableModel], requested: Iterable[str]) -> list[DeployableModel]:
    by_selector = {item.selector.casefold(): item for item in candidates}
    by_name: dict[str, list[DeployableModel]] = {}
    for item in candidates:
        by_name.setdefault(item.name.casefold(), []).append(item)
    selected: list[DeployableModel] = []
    for raw in requested:
        value = raw.strip().casefold()
        matches = [by_selector[value]] if "@" in value and value in by_selector else by_name.get(value, [])
        if not matches:
            raise ValidationError(f"model '{raw}' is not supported and deployable on this account.")
        if len(matches) != 1:
            raise ValidationError(
                f"model '{raw}' has multiple deployable versions.",
                hint="Select one explicitly: " + ", ".join(item.selector for item in matches),
            )
        if any(item.name.casefold() == matches[0].name.casefold() for item in selected):
            raise ValidationError(f"model family '{matches[0].name}' was selected more than once.")
        selected.append(matches[0])
    return selected


def _recommended(candidates: list[DeployableModel]) -> list[DeployableModel]:
    selected = []
    for kind, names in (("completion", _COMPLETION_ORDER), ("embedding", _EMBEDDING_ORDER)):
        options = [item for item in candidates if item.kind == kind]
        chosen = None
        for name in names:
            family = [item for item in options if item.name.casefold() == name]
            defaults = [item for item in family if item.is_default_version]
            if len(defaults) == 1:
                chosen = defaults[0]
            elif len(family) == 1:
                chosen = family[0]
            if chosen:
                break
        if chosen:
            selected.append(chosen)
    if not selected:
        raise ServiceError("no unambiguous recommended CU-supported models are deployable.")
    return selected


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
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps([item.template_entry() for item in models], indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


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
        apply_defaults(cu_client, {item.name: item.name for item in selected}, replace=False)
    _write(output, selected)
    return {
        "models": [item.template_entry() for item in selected],
        "outputFile": str(output),
        "deployed": bool(values.get("deploy", True)),
        "defaultsConfigured": bool(values.get("deploy", True) and selected),
    }
