# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for Azure CLI credential and CU setting adaptation."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from azure.cli.core.azclierror import ArgumentUsageError, AzureConnectionError
from knack.parser import CLICommandParser

from azext_content_understanding import _client_factory
from azext_content_understanding._params import _argument_kwargs
from cu_cli_core.service_options import API_KEY, API_VERSION, AUTH_MODE, ENDPOINT, PROFILE


def _service_parser() -> CLICommandParser:
    parser = CLICommandParser()
    for option in (ENDPOINT, API_VERSION, AUTH_MODE, API_KEY, PROFILE):
        kwargs = _argument_kwargs(option)
        options = kwargs.pop("options_list")
        arg_type = kwargs.pop("arg_type", None)
        if arg_type is not None:
            kwargs.update(arg_type.settings)
        parser.add_argument(*options, dest=option.parser_name, **kwargs)
    return parser


@pytest.mark.unit
def test_resolve_service_settings_prefers_explicit_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.example")
    monkeypatch.setenv("CU_API_VERSION", "environment-version")

    endpoint, api_version = _client_factory.resolve_service_settings(
        endpoint="https://explicit.example",
        api_version="explicit-version",
        profile_name=None,
    )

    assert endpoint == "https://explicit.example"
    assert api_version == "explicit-version"


@pytest.mark.unit
def test_resolve_service_settings_requires_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("CU_ENDPOINT", raising=False)
    monkeypatch.delenv("CONTENTUNDERSTANDING_ENDPOINT", raising=False)

    with pytest.raises(ArgumentUsageError, match="--endpoint"):
        _client_factory.resolve_service_settings(
            endpoint=None,
            api_version=None,
            profile_name=None,
        )


@pytest.mark.unit
def test_get_cli_credential_uses_active_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    credential = object()
    calls: dict[str, Any] = {}

    class FakeProfile:
        def __init__(self, cli_ctx: Any) -> None:
            calls["cli_ctx"] = cli_ctx

        def get_subscription_id(self) -> str:
            return "subscription-id"

        def get_login_credentials(self, *, subscription_id: str) -> tuple[Any, None, None]:
            calls["subscription_id"] = subscription_id
            return credential, None, None

    monkeypatch.setattr(_client_factory, "AzureCliProfile", FakeProfile)
    cli_ctx = SimpleNamespace()

    assert _client_factory.get_cli_credential(cli_ctx) is credential
    assert calls == {"cli_ctx": cli_ctx, "subscription_id": "subscription-id"}


@pytest.mark.unit
def test_create_client_rejects_unsupported_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _client_factory,
        "resolve_service_settings",
        lambda **kwargs: ("https://example", "2025-11-01"),
    )
    cmd = SimpleNamespace(cli_ctx=SimpleNamespace(cloud=SimpleNamespace(name="AzureUSGovernment")))

    with pytest.raises(AzureConnectionError, match="AzureUSGovernment"):
        _client_factory.create_content_understanding_client(
            cmd,
            endpoint=None,
            api_version=None,
            profile_name=None,
        )


@pytest.mark.unit
def test_create_client_uses_explicit_api_key_without_azure_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        _client_factory.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(auth_mode="login", api_key=None),
    )
    monkeypatch.setattr(
        _client_factory,
        "get_cli_credential",
        lambda *_args: pytest.fail("Azure login must not be requested for key auth"),
    )
    monkeypatch.setattr(
        _client_factory,
        "build_content_understanding_client",
        lambda **kwargs: captured.update(kwargs) or object(),
    )

    _client_factory.create_content_understanding_client(
        SimpleNamespace(cli_ctx=SimpleNamespace()),
        endpoint="https://example",
        api_version="2025-11-01",
        auth_mode="key",
        api_key="secret",
    )

    assert captured["credential"].key == "secret"


@pytest.mark.unit
def test_real_azure_parser_preserves_profile_api_version_and_passes_key_to_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    profile = SimpleNamespace(
        endpoint="https://profile.example",
        api_version="2026-06-01-preview",
        auth_mode="login",
        api_key=None,
    )
    monkeypatch.setattr(_client_factory.CuProfile, "load", lambda **kwargs: profile)
    monkeypatch.setattr(
        _client_factory,
        "get_cli_credential",
        lambda *_args: pytest.fail("Azure login must not be requested for parsed key auth"),
    )
    monkeypatch.setattr(
        _client_factory,
        "build_content_understanding_client",
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    parsed = _service_parser().parse_args(
        ["--profile", "preview", "--auth-mode", "key", "--api-key", "secret"]
    )

    assert parsed.api_version is None
    _client_factory.create_content_understanding_client(
        SimpleNamespace(cli_ctx=SimpleNamespace()), **vars(parsed)
    )

    assert captured["api_version"] == "2026-06-01-preview"
    assert captured["credential"].key == "secret"


@pytest.mark.unit
def test_create_client_uses_key_from_selected_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        _client_factory.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(auth_mode="key", api_key="profile-secret"),
    )
    monkeypatch.setattr(
        _client_factory,
        "get_cli_credential",
        lambda *_args: pytest.fail("Azure login must not be requested for profile key auth"),
    )
    monkeypatch.setattr(
        _client_factory,
        "build_content_understanding_client",
        lambda **kwargs: captured.update(kwargs) or object(),
    )

    _client_factory.create_content_understanding_client(
        SimpleNamespace(cli_ctx=SimpleNamespace()),
        endpoint="https://example",
        api_version="2025-11-01",
        profile_name="key-profile",
    )

    assert captured["credential"].key == "profile-secret"


@pytest.mark.unit
def test_explicit_login_overrides_profile_key(monkeypatch: pytest.MonkeyPatch) -> None:
    cli_credential = object()
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        _client_factory.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(auth_mode="key", api_key="profile-secret"),
    )
    monkeypatch.setattr(_client_factory, "get_cli_credential", lambda *_args: cli_credential)
    monkeypatch.setattr(
        _client_factory,
        "build_content_understanding_client",
        lambda **kwargs: captured.update(kwargs) or object(),
    )

    _client_factory.create_content_understanding_client(
        SimpleNamespace(cli_ctx=SimpleNamespace()),
        endpoint="https://example",
        api_version="2025-11-01",
        auth_mode="login",
    )

    assert captured["credential"] is cli_credential


@pytest.mark.unit
def test_key_auth_requires_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _client_factory.CuProfile,
        "load",
        lambda **kwargs: SimpleNamespace(auth_mode="login", api_key=None),
    )

    with pytest.raises(ArgumentUsageError, match="requires an API key"):
        _client_factory.create_content_understanding_client(
            SimpleNamespace(cli_ctx=SimpleNamespace()),
            endpoint="https://example",
            api_version="2025-11-01",
            auth_mode="key",
        )