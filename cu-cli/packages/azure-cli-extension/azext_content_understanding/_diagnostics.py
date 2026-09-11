# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Structured diagnostics for the Azure CLI frontend."""

from __future__ import annotations

from typing import Any

from cu_cli_core.command_spec import ENV_VAR_LIST, build_request, resolve_identifier
from cu_cli_core.defaults import (
    PREBUILT_COMPLETION_KEY,
    PREBUILT_COMPLETION_MINI_KEY,
    PREBUILT_EMBEDDING_KEY,
    apply_defaults,
    extract_model_deployments,
    is_defaults_not_set,
)
from cu_cli_core.profiles import Profile
from cu_cli_core.errors import UsageError

from ._client_factory import create_content_understanding_client, resolve_service_settings


def _missing_model_requirements(mapped: dict[str, str]) -> list[str]:
    """Return model requirements not satisfied by a defaults mapping."""

    missing: list[str] = []
    has_embedding = bool(mapped.get(PREBUILT_EMBEDDING_KEY)) or any(
        name.startswith("text-embedding-") for name in mapped
    )
    if not has_embedding:
        missing.append("an embeddings model (for example text-embedding-3-large)")
    has_completion = bool(mapped.get(PREBUILT_COMPLETION_KEY)) or any(
        not name.startswith(("prebuilt-analyzer-", "text-embedding-")) for name in mapped
    )
    if not has_completion:
        missing.append("a supported large language model (LLM) deployment")
    if not mapped.get(PREBUILT_COMPLETION_MINI_KEY):
        missing.append("Content Understanding's prebuilt analyzer mapping for the selected LLM")
    return missing


def doctor(cmd: Any, **values: Any) -> dict[str, Any]:
    profile = Profile.load(profile_name=values.get("profile_name"))
    auth_mode = values.get("auth_mode") or (
        "key" if values.get("api_key") else profile.auth_mode
    )
    endpoint, api_version = resolve_service_settings(
        endpoint=values.get("endpoint"),
        api_version=values.get("api_version"),
        profile_name=values.get("profile_name"),
    )
    client = create_content_understanding_client(
        cmd,
        endpoint=endpoint,
        api_version=api_version,
        profile_name=values.get("profile_name"),
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
    )
    from azure.core.exceptions import HttpResponseError

    try:
        mappings = extract_model_deployments(client.get_defaults())
    except HttpResponseError as exc:
        if not is_defaults_not_set(exc):
            raise
        mappings = {}
    missing = _missing_model_requirements(mappings)
    if values.get("fix_defaults"):
        if not mappings and not profile.model_deployments:
            raise UsageError(
                "cannot set defaults: no model deployment mapping is configured",
                hint=(
                    "Set model mappings first, for example with "
                    "'az cu profile set --key model_deployments.gpt-5.2 "
                    "--value <deployment-name>', then rerun 'az cu doctor --fix-defaults'."
                ),
            )
        _, mappings = apply_defaults(client, profile.model_deployments, replace=False)
        missing = _missing_model_requirements(mappings)
    return {
        "ready": not missing,
        "endpoint": endpoint,
        "apiVersion": api_version,
        "authentication": (
            "resource key" if auth_mode == "key" else "Microsoft Entra ID (Azure CLI)"
        ),
        "profile": profile.profile_name,
        "defaultAnalyzer": profile.default_analyzer,
        "modelDeployments": mappings,
        "missingRequirements": missing,
    }


def list_environment_variables(_cmd: Any, **values: Any) -> Any:
    request = build_request(ENV_VAR_LIST, values)
    del request
    return resolve_identifier(ENV_VAR_LIST.operation)()