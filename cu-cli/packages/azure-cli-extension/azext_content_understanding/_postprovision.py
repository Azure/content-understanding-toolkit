# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI adapter for the versioned generated-project postprovision contract."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Sequence

from cu_cli_core.defaults import apply_defaults
from cu_cli_core.postprovision import (
    DeploymentState,
    PostprovisionCapabilities,
    PostprovisionRequest,
    execute_postprovision,
)
from cu_cli_core.profiles import ProfileStore

from ._client_factory import create_content_understanding_client, get_subscription_id
from ._infra_models import setup_models
from ._resources import _management_client


def _azd_values() -> dict[str, str]:
    result = subprocess.run(
        ["azd", "env", "get-values"], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "azd env get-values failed").strip())
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator:
            values[name] = value.strip().strip('"')
    return values


def _true(value: str | None) -> bool:
    return str(value or "").casefold() == "true"


def _request_from_environment() -> PostprovisionRequest:
    values = _azd_values()
    return PostprovisionRequest(
        endpoint=values.get("FOUNDRY_ENDPOINT", ""),
        project_name=values.get("FOUNDRY_PROJECT_NAME", ""),
        account_name=values.get("FOUNDRY_RESOURCE_NAME", ""),
        resource_group=values.get("AZURE_RESOURCE_GROUP", ""),
        subscription_id=values.get("AZURE_SUBSCRIPTION_ID", ""),
        existing_endpoint=values.get("FOUNDRY_EXISTING_ENDPOINT", ""),
        api_version=values.get("CU_API_VERSION") or "2025-11-01",
        model_selection=values.get("CU_MODEL_SELECTION") or "prompt",
        model_setup_complete=_true(values.get("CU_MODEL_SETUP_COMPLETE")),
        assign_roles=_true(values.get("AZD_ASSIGN_ROLES")),
        force_profile_setup=_true(values.get("CU_PROFILE_SETUP_FORCE")),
        disable_profile_setup=(
            _true(os.getenv("CU_DISABLE_AUTO_PROFILE_SETUP"))
            or str(os.getenv("CU_AUTOCONFIG", "")).casefold() == "false"
        ),
    )


class _AzureCapabilities(PostprovisionCapabilities):
    def __init__(self, cmd: Any) -> None:
        self._cmd = cmd
        self._management: Any | None = None

    def _management_client(self, request: PostprovisionRequest) -> Any:
        if self._management is None:
            subscription = request.subscription_id or get_subscription_id(self._cmd.cli_ctx)
            self._management = _management_client(self._cmd, subscription)
        return self._management

    def setup_models(self, request: PostprovisionRequest) -> None:
        setup_models(
            self._cmd,
            resource_group=request.resource_group,
            account_name=request.account_name,
            selection=request.model_selection,
            out_path="infra/models.json",
            deploy=True,
            endpoint=request.endpoint,
            api_version=request.api_version,
            use_key=not request.assign_roles,
            auth_mode="login" if request.assign_roles else "key",
            configure_defaults=False,
        )

    def mark_model_setup_complete(self) -> None:
        result = subprocess.run(
            ["azd", "env", "set", "CU_MODEL_SETUP_COMPLETE", "true"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "could not save model setup state").strip())

    def profile_has_values(self, name: str) -> bool:
        return bool(ProfileStore.load().get_profile(name))

    def set_profile_value(self, name: str, key: str, value: str) -> None:
        store = ProfileStore.load()
        store.set(key, value, name=name)
        store.save()

    def get_account_key(self, request: PostprovisionRequest) -> str:
        keys = self._management_client(request).accounts.list_keys(
            request.resource_group, request.account_name
        )
        key = str(keys.key1 or keys.key2 or "")
        if not key:
            raise RuntimeError("the Microsoft Foundry resource returned no account key")
        return key

    def list_deployments(self, request: PostprovisionRequest) -> Sequence[DeploymentState]:
        rows = self._management_client(request).deployments.list(
            request.resource_group, request.account_name
        )
        result = []
        for item in rows:
            properties = getattr(item, "properties", None)
            model = getattr(properties, "model", None)
            name = str(getattr(item, "name", "") or "")
            model_name = str(getattr(model, "name", "") or "")
            if name and model_name:
                result.append(
                    DeploymentState(
                        name=name,
                        model_name=model_name,
                        succeeded=getattr(properties, "provisioning_state", None) == "Succeeded",
                    )
                )
        return tuple(result)

    def configure_defaults(self, request: PostprovisionRequest, mappings: dict[str, str]) -> None:
        client = create_content_understanding_client(
            self._cmd,
            endpoint=request.endpoint,
            api_version=request.api_version,
            profile_name="default",
            subscription_id=request.subscription_id,
        )
        apply_defaults(client, mappings, replace=False)


def postprovision_v1(cmd: Any, **_values: Any) -> dict[str, Any]:
    """Execute and return the shared v1 postprovision result."""

    result = execute_postprovision(_request_from_environment(), _AzureCapabilities(cmd))
    if not result.succeeded:
        raise RuntimeError("; ".join(result.messages[-3:]))
    return {
        "succeeded": result.succeeded,
        "profileConfigured": result.profile_configured,
        "profilePreserved": result.profile_preserved,
        "profileSetupDisabled": result.profile_setup_disabled,
        "modelSetup": result.model_setup,
        "defaultsConfigured": result.defaults_configured,
        "generativeReady": result.generative_ready,
        "warnings": list(result.warnings),
        "messages": list(result.messages),
    }
