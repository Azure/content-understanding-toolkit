"""Unit tests for :mod:`cu_cli.core.foundry` endpoint helpers."""

from __future__ import annotations

import pytest

from cu_cli.core.foundry import normalize_foundry_endpoint
from cu_cli.errors import CuCliError

pytestmark = pytest.mark.unit


def test_normalize_foundry_endpoint_accepts_standard_foundry_host():
    assert (
        normalize_foundry_endpoint("myservice.services.ai.azure.com")
        == "https://myservice.services.ai.azure.com/"
    )


def test_normalize_foundry_endpoint_accepts_custom_domain_host():
    assert (
        normalize_foundry_endpoint("https://cu.contoso.example.com")
        == "https://cu.contoso.example.com/"
    )


def test_normalize_foundry_endpoint_preserves_explicit_port():
    assert (
        normalize_foundry_endpoint("https://cu.contoso.example.com:8443")
        == "https://cu.contoso.example.com:8443/"
    )


@pytest.mark.parametrize(
    ("endpoint", "username", "password"),
    [
        ("https://demo-user@cu.contoso.example.com/", "demo-user", None),
        (
            "https://demo-user:demo-password@cu.contoso.example.com/",
            "demo-user",
            "demo-password",
        ),
        ("demo-user@cu.contoso.example.com", "demo-user", None),
        (
            "demo-user:demo-password@cu.contoso.example.com",
            "demo-user",
            "demo-password",
        ),
    ],
)
def test_normalize_foundry_endpoint_rejects_user_information_without_echoing_it(
    endpoint, username, password
):
    with pytest.raises(CuCliError) as exc_info:
        normalize_foundry_endpoint(endpoint)

    error = str(exc_info.value)
    assert "must not include username or password information" in error
    assert username not in error
    if password is not None:
        assert password not in error


def test_normalize_foundry_endpoint_rejects_non_https_scheme():
    with pytest.raises(CuCliError, match="must use https"):
        normalize_foundry_endpoint("http://cu.contoso.example.com")


def test_normalize_foundry_endpoint_names_login_auth_for_non_https_endpoint():
    with pytest.raises(CuCliError, match="authentication mode 'login' requires"):
        normalize_foundry_endpoint(
            "http://cu.contoso.example.com",
            auth_mode="login",
        )


def test_normalize_foundry_endpoint_rejects_invalid_host():
    with pytest.raises(CuCliError, match="invalid foundry endpoint"):
        normalize_foundry_endpoint("not-a-host")
