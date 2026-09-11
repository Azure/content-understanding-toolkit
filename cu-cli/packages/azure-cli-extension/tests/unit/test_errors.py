# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for CU-to-Azure-CLI error translation."""

from types import SimpleNamespace

import pytest
from azure.cli.core.azclierror import (
    ArgumentUsageError,
    AuthenticationError as AzureCliAuthenticationError,
    AzureConnectionError,
    InvalidArgumentValueError,
    ResourceNotFoundError,
)
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError, ServiceRequestError
from knack.util import CLIError

from azext_content_understanding._errors import azure_cli_error
from cu_cli_core.errors import (
    AuthenticationError,
    NotFoundError,
    ServiceError,
    UsageError,
    ValidationError,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("core_error", "expected_type"),
    [
        (UsageError("bad usage"), ArgumentUsageError),
        (ValidationError("bad value"), InvalidArgumentValueError),
        (AuthenticationError("login failed"), AzureCliAuthenticationError),
        (NotFoundError("missing"), ResourceNotFoundError),
        (ServiceError("service failed"), CLIError),
    ],
)
def test_azure_cli_error_maps_categories(core_error: Exception, expected_type: type[Exception]) -> None:
    translated = azure_cli_error(core_error)

    assert isinstance(translated, expected_type)


@pytest.mark.unit
def test_azure_cli_error_preserves_hint() -> None:
    translated = azure_cli_error(ValidationError("bad value.", hint="Use a valid value."))

    assert "bad value. Use a valid value." in str(translated)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("sdk_error", "expected_type"),
    [
        (ClientAuthenticationError("login failed"), AzureCliAuthenticationError),
        (ServiceRequestError("network failed"), AzureConnectionError),
        (
            HttpResponseError(
                "bad request",
                response=SimpleNamespace(status_code=400, reason="Bad Request", headers={}),
            ),
            InvalidArgumentValueError,
        ),
    ],
)
def test_azure_cli_error_maps_sdk_failures(
    sdk_error: Exception,
    expected_type: type[Exception],
) -> None:
    assert isinstance(azure_cli_error(sdk_error), expected_type)