# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI adapters for Content Understanding defaults."""

from __future__ import annotations

from typing import Any

from cu_cli_core.command_spec import DEFAULTS_SET, DEFAULTS_SHOW, build_request, resolve_identifier
from cu_cli_core.defaults import parse_model_kv
from cu_cli_core.errors import UsageError

from ._client_factory import create_content_understanding_client


def _client(cmd: Any, values: dict[str, Any]) -> Any:
    return create_content_understanding_client(
        cmd,
        endpoint=values.get("endpoint"),
        api_version=values.get("api_version"),
        profile_name=values.get("profile_name"),
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
    )


def show_defaults(cmd: Any, **values: Any) -> Any:
    build_request(DEFAULTS_SHOW, values)
    return resolve_identifier(DEFAULTS_SHOW.operation)(_client(cmd, values))


def set_defaults(cmd: Any, **values: Any) -> Any:
    request = build_request(DEFAULTS_SET, values)
    desired = parse_model_kv(request.models)
    if not desired:
        raise UsageError("provide --model MODEL=DEPLOYMENT at least once.")
    updated, _ = resolve_identifier(DEFAULTS_SET.operation)(
        _client(cmd, values), desired, replace=request.replace
    )
    return updated