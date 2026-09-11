# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Static service-option metadata shared by command frontends."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .command_spec import ArgumentValueType, SurfaceClassification

DEFAULT_API_VERSION = "2025-11-01"
SUPPORTED_API_VERSIONS = (DEFAULT_API_VERSION, "2026-06-01-preview")
_PREVIEW_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-preview$")


def is_supported_api_version(version: str | None) -> bool:
    """Return whether an API version follows the CLI's shared support policy."""

    return bool(
        version in SUPPORTED_API_VERSIONS
        or (version and _PREVIEW_VERSION_PATTERN.fullmatch(version))
    )


@dataclass(frozen=True)
class ServiceOptionSpec:
    key: str
    name: str
    parser_name: str
    help: str
    value_type: ArgumentValueType = ArgumentValueType.STRING
    aliases: tuple[str, ...] = ()
    required: bool = False
    default: object = None
    choices: tuple[str, ...] = ()
    sensitive: bool = False
    classification: SurfaceClassification = SurfaceClassification.COMMON


ENDPOINT = ServiceOptionSpec(
    key="endpoint",
    name="--endpoint",
    parser_name="endpoint",
    help="Microsoft Foundry resource endpoint for Content Understanding.",
)
API_VERSION = ServiceOptionSpec(
    key="api-version",
    name="--api-version",
    parser_name="api_version",
    help="Content Understanding service API version.",
)
AUTH_MODE = ServiceOptionSpec(
    key="auth-mode",
    name="--auth-mode",
    parser_name="auth_mode",
    help="Authentication mode.",
    choices=("login", "key"),
)
API_KEY = ServiceOptionSpec(
    key="api-key",
    name="--api-key",
    parser_name="api_key",
    help="Microsoft Foundry resource API key.",
    sensitive=True,
)
PROFILE = ServiceOptionSpec(
    key="profile",
    name="--profile",
    parser_name="profile_name",
    help="CU CLI profile used to resolve endpoint and API-version defaults.",
)

SERVICE_OPTIONS = (ENDPOINT, API_VERSION, AUTH_MODE, API_KEY, PROFILE)
_SERVICE_OPTIONS_BY_KEY = {option.key: option for option in SERVICE_OPTIONS}

if len(_SERVICE_OPTIONS_BY_KEY) != len(SERVICE_OPTIONS):
    raise RuntimeError("duplicate service option key")


def get_service_option(key: str) -> ServiceOptionSpec:
    return _SERVICE_OPTIONS_BY_KEY[key]


def service_options_for(keys: tuple[str, ...]) -> tuple[ServiceOptionSpec, ...]:
    return tuple(get_service_option(key) for key in keys)
