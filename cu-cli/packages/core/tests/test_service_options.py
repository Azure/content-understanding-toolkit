# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import pytest

from cu_cli_core.command_spec import ANALYZER_SHOW
from cu_cli_core.service_options import (
    API_KEY,
    API_VERSION,
    AUTH_MODE,
    DEFAULT_API_VERSION,
    ENDPOINT,
    SERVICE_OPTIONS,
    get_service_option,
    service_options_for,
)

pytestmark = pytest.mark.unit


def test_service_option_keys_are_unique_and_resolvable():
    assert len({option.key for option in SERVICE_OPTIONS}) == len(SERVICE_OPTIONS)
    assert get_service_option("endpoint") is ENDPOINT
    assert get_service_option("api-version") is API_VERSION


def test_analyzer_show_composes_expected_service_options_in_order():
    assert service_options_for(ANALYZER_SHOW.service_options) == (
        ENDPOINT,
        API_VERSION,
        AUTH_MODE,
        API_KEY,
    )


def test_service_option_security_and_defaults():
    assert API_KEY.sensitive is True
    assert API_VERSION.default == DEFAULT_API_VERSION
    assert AUTH_MODE.choices == ("login", "key")
    assert AUTH_MODE.default == "login"
