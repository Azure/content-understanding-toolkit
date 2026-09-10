# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI adapters for shared CU profile operations."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from urllib.parse import urlparse

from azure.cli.core.util import user_confirmation

from cu_cli_core.command_spec import (
    PROFILE_COPY,
    PROFILE_CREATE,
    PROFILE_DELETE,
    PROFILE_GET,
    PROFILE_LIST,
    PROFILE_RENAME,
    PROFILE_SET,
    PROFILE_SET_ACTIVE,
    PROFILE_SHOW,
    PROFILE_SYNC_DEFAULTS,
    PROFILE_UNSET,
    build_request,
    resolve_identifier,
)
from cu_cli_core.defaults import extract_model_deployments, with_prebuilt_default_mappings
from cu_cli_core.errors import NotFoundError, ValidationError
from cu_cli_core.profiles import Profile, ProfileStore

from ._client_factory import create_content_understanding_client


def _request(spec: Any, values: dict[str, Any]) -> Any:
    return build_request(spec, values)


def show_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_SHOW, values)
    profile = resolve_identifier(PROFILE_SHOW.operation)(request)
    result = profile.to_public_dict()
    result["isActive"] = profile.profile_name == ProfileStore.load().get_active_name()
    return result


def list_profiles(_cmd: Any, **values: Any) -> list[dict[str, Any]]:
    active, names = resolve_identifier(PROFILE_LIST.operation)(_request(PROFILE_LIST, values))
    return [{"name": name, "active": name == active} for name in names]


def get_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_GET, values)
    value = resolve_identifier(PROFILE_GET.operation)(request)
    if request.key == "api_key" and value:
        value = "***redacted***"
    return {"name": request.name, "key": request.key, "value": value}


def _normalize_endpoint(value: str) -> str:
    candidate = value.strip()
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValidationError("endpoint must be an absolute HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError("endpoint must not contain user credentials.")
    host = parsed.hostname.lower()
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return f"https://{host}/"


def set_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_SET, values)
    if request.key == "endpoint":
        request = replace(request, value=_normalize_endpoint(request.value))
    path = resolve_identifier(PROFILE_SET.operation)(request)
    target = request.name or ProfileStore.load().get_active_name()
    return {"saved": True, "name": target, "key": request.key, "path": str(path)}


def unset_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_UNSET, values)
    path = resolve_identifier(PROFILE_UNSET.operation)(request)
    target = request.name or ProfileStore.load().get_active_name()
    return {"unset": True, "name": target, "key": request.key, "path": str(path)}


def create_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_CREATE, values)
    path = resolve_identifier(PROFILE_CREATE.operation)(request)
    return {"created": True, "name": request.name, "path": str(path)}


def delete_profile(_cmd: Any, yes: bool = False, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_DELETE, values)
    user_confirmation(f"Delete CU profile '{request.name}'?", yes=yes)
    path = resolve_identifier(PROFILE_DELETE.operation)(request)
    return {"deleted": True, "name": request.name, "path": str(path)}


def copy_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_COPY, values)
    path, source = resolve_identifier(PROFILE_COPY.operation)(request)
    return {
        "copied": True,
        "source": source,
        "destination": request.destination,
        "path": str(path),
    }


def rename_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_RENAME, values)
    path = resolve_identifier(PROFILE_RENAME.operation)(request)
    return {
        "renamed": True,
        "source": request.source,
        "destination": request.destination,
        "path": str(path),
    }


def set_active_profile(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_SET_ACTIVE, values)
    path = resolve_identifier(PROFILE_SET_ACTIVE.operation)(request)
    return {"active": request.name, "path": str(path)}


def sync_profile_defaults(cmd: Any, **values: Any) -> dict[str, Any]:
    request = _request(PROFILE_SYNC_DEFAULTS, values)
    saved = Profile.load_saved(profile_name=request.name)
    if not saved.endpoint:
        raise ValidationError(f"no endpoint is saved in CU profile '{saved.profile_name}'.")
    client = create_content_understanding_client(
        cmd,
        endpoint=saved.endpoint,
        api_version=values.get("api_version") or saved.api_version,
        profile_name=request.name,
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
    )
    defaults = client.get_defaults()
    models = with_prebuilt_default_mappings(extract_model_deployments(defaults))
    if not models:
        raise NotFoundError("Content Understanding defaults contain no model mappings.")
    path, target = resolve_identifier(PROFILE_SYNC_DEFAULTS.operation)(request, models)
    return {
        "synchronized": len(models),
        "name": target,
        "path": str(path),
        "modelDeployments": models,
    }