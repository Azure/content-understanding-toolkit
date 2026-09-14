# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Structured diagnostics for the Azure CLI frontend."""

from __future__ import annotations

from typing import Any

from cu_cli_core.command_spec import ENV_VAR_LIST, build_request, resolve_identifier
from cu_cli_core.doctor import assess_doctor, resolve_doctor_request
from cu_cli_core.profiles import Profile
from cu_cli_core.errors import ServiceError

from ._client_factory import create_content_understanding_client


def doctor(cmd: Any, **values: Any) -> dict[str, Any]:
    profile = Profile.load(profile_name=values.get("profile_name"))
    request = resolve_doctor_request(
        profile,
        endpoint=values.get("endpoint"),
        api_version=values.get("api_version"),
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
        fix_defaults=bool(values.get("fix_defaults")),
    )
    result = assess_doctor(
        request,
        lambda resolved: create_content_understanding_client(
            cmd,
            endpoint=resolved.endpoint,
            api_version=resolved.api_version,
            profile_name=values.get("profile_name"),
            auth_mode="key" if resolved.authentication == "resource key" else "login",
            api_key=resolved.api_key,
        ),
    )
    if result.failures:
        raise ServiceError(result.failures[0].message)
    return result.to_dict()


def list_environment_variables(_cmd: Any, **values: Any) -> Any:
    request = build_request(ENV_VAR_LIST, values)
    del request
    return resolve_identifier(ENV_VAR_LIST.operation)()