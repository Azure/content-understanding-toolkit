# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Static environment-variable metadata and redacted process inspection."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

REDACTED_VALUE = "********"


@dataclass(frozen=True)
class EnvironmentVariableSpec:
    name: str
    description: str
    accepted_values: str
    default: str
    scope: str
    precedence: str
    sensitive: bool = False


ENVIRONMENT_VARIABLES = (
    EnvironmentVariableSpec(
        name="CU_ENDPOINT",
        description="Microsoft Foundry resource endpoint for Content Understanding.",
        accepted_values="HTTPS URL",
        default="not set",
        scope="service commands",
        precedence="Overrides the endpoint in the selected CU CLI profile.",
    ),
    EnvironmentVariableSpec(
        name="CU_API_KEY",
        description="API key used for key authentication.",
        accepted_values="secret string",
        default="not set",
        scope="authentication",
        precedence="Overrides the selected CU CLI profile and implies key authentication.",
        sensitive=True,
    ),
    EnvironmentVariableSpec(
        name="CU_AUTH_MODE",
        description="Authentication mode.",
        accepted_values="login | key",
        default="login",
        scope="authentication",
        precedence="Overrides authentication in the selected CU CLI profile.",
    ),
    EnvironmentVariableSpec(
        name="CU_API_VERSION",
        description="Content Understanding API version.",
        accepted_values="supported API version",
        default="2025-11-01",
        scope="service commands",
        precedence="Overrides the API version in the selected CU CLI profile.",
    ),
    EnvironmentVariableSpec(
        name="CU_TELEMETRY",
        description="Controls the cu-cli User-Agent adoption marker.",
        accepted_values="off | 0 | false | no to disable",
        default="on",
        scope="service commands",
        precedence="Controls CLI telemetry behavior directly.",
    ),
    EnvironmentVariableSpec(
        name="CU_NO_UPDATE_CHECK",
        description="Disables the daily package update check.",
        accepted_values="1 | true | yes | on to disable",
        default="off",
        scope="update check",
        precedence="Controls update-check behavior directly.",
    ),
    EnvironmentVariableSpec(
        name="CU_ON_EXISTS",
        description="Chooses how analyze handles an existing result file.",
        accepted_values="error | skip | reanalyze",
        default="error",
        scope="analyze",
        precedence="Used when --on-existing is not specified.",
    ),
)


def list_set_environment_variables(
    environ: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    """Return recognized variables currently set, redacting sensitive values."""

    values = os.environ if environ is None else environ
    return [
        {
            "name": spec.name,
            "value": REDACTED_VALUE if spec.sensitive else values[spec.name],
            "scope": spec.scope,
            "sensitive": spec.sensitive,
        }
        for spec in ENVIRONMENT_VARIABLES
        if spec.name in values
    ]
