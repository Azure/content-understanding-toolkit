# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import pytest

from cu_cli_core.environment import (
    ENVIRONMENT_VARIABLES,
    REDACTED_VALUE,
    list_set_environment_variables,
)

pytestmark = pytest.mark.unit


def test_environment_registry_matches_preview_contract():
    by_name = {spec.name: spec for spec in ENVIRONMENT_VARIABLES}

    assert set(by_name) == {
        "CU_ENDPOINT",
        "CU_API_KEY",
        "CU_AUTH_MODE",
        "CU_API_VERSION",
        "CU_TELEMETRY",
        "CU_NO_UPDATE_CHECK",
        "CU_ON_EXISTS",
    }
    assert by_name["CU_API_KEY"].sensitive
    assert by_name["CU_ON_EXISTS"].accepted_values == "error | skip | reanalyze"
    for name in ("CU_ENDPOINT", "CU_API_KEY", "CU_AUTH_MODE", "CU_API_VERSION"):
        assert "selected CU CLI profile" in by_name[name].precedence
        assert "selected config" not in by_name[name].precedence


def test_list_set_environment_variables_redacts_secrets():
    rows = list_set_environment_variables(
        {
            "CU_ENDPOINT": "https://example.cognitiveservices.azure.com",
            "CU_API_KEY": "secret",
            "UNRECOGNIZED": "ignored",
        }
    )

    assert rows == [
        {
            "name": "CU_ENDPOINT",
            "value": "https://example.cognitiveservices.azure.com",
            "scope": "service commands",
            "sensitive": False,
        },
        {
            "name": "CU_API_KEY",
            "value": REDACTED_VALUE,
            "scope": "authentication",
            "sensitive": True,
        },
    ]
