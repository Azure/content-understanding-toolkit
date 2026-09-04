"""Credential-hygiene warnings emitted by ``build_client``.

Regression coverage for an ``--api-key`` value on argv leaking via
``ps``/shell history, and ``--api-key`` being silently ignored when
``--entra`` also given).
"""

from __future__ import annotations

from cu_cli.client import build_client
from cu_cli.profile import Profile



import pytest
from cu_cli.errors import CuCliError

pytestmark = pytest.mark.unit

def test_build_client_warns_on_argv_api_key(capsys):
    profile = Profile(endpoint="https://x.services.ai.azure.com/")
    build_client(profile, api_key_override="leaky-key-value")
    err = capsys.readouterr().err
    assert "--api-key" in err
    assert "ps" in err or "history" in err


def test_build_client_warns_when_api_key_combined_with_entra(capsys):
    profile = Profile(endpoint="https://x.services.ai.azure.com/")
    build_client(profile, api_key_override="leaky-key-value", force_entra=True)
    err = capsys.readouterr().err
    assert "--auth-mode login overrides" in err


def test_build_client_silent_without_argv_api_key(capsys):
    # A key sourced from config (not argv) must not trigger the warning.
    profile = Profile(endpoint="https://x.services.ai.azure.com/", auth_mode="key",
                      api_key="from-profile")
    build_client(profile)
    err = capsys.readouterr().err
    assert "--api-key" not in err


def test_build_client_rejects_non_https_login_endpoint_before_sdk_construction(
    monkeypatch,
):
    monkeypatch.setattr(
        "azure.ai.contentunderstanding.ContentUnderstandingClient",
        lambda **_kwargs: pytest.fail("SDK client must not be constructed"),
    )

    with pytest.raises(CuCliError) as exc_info:
        build_client(
            Profile(endpoint="http://not-https.example.invalid/"),
            force_entra=True,
        )

    rendered = exc_info.value.format_message()
    assert "authentication mode 'login' requires an HTTPS endpoint" in rendered
    assert "******" not in rendered


def test_build_client_rejects_malformed_endpoint_before_sdk_construction(monkeypatch):
    monkeypatch.setattr(
        "azure.ai.contentunderstanding.ContentUnderstandingClient",
        lambda **_kwargs: pytest.fail("SDK client must not be constructed"),
    )

    with pytest.raises(CuCliError, match="invalid foundry endpoint"):
        build_client(Profile(endpoint="not-a-url"))


def test_build_client_honors_telemetry_opt_out(monkeypatch):
    # Opt-out flows all the way to the SDK client as an empty User-Agent prefix
    # (azure-core then sends only its standard azsdk moniker, no cu-cli marker).
    captured: dict = {}

    class _FakeSdkClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "azure.ai.contentunderstanding.ContentUnderstandingClient", _FakeSdkClient
    )
    monkeypatch.setenv("CU_TELEMETRY", "off")
    build_client(Profile(endpoint="https://x.services.ai.azure.com/"))
    assert captured["user_agent"] == ""
    assert "cu-cli" not in captured["user_agent"]


def test_build_client_sends_marker_when_telemetry_on(monkeypatch):
    captured: dict = {}

    class _FakeSdkClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "azure.ai.contentunderstanding.ContentUnderstandingClient", _FakeSdkClient
    )
    # CU_* env is stripped by the isolate fixture -> telemetry on by default.
    build_client(Profile(endpoint="https://x.services.ai.azure.com/"))
    assert captured["user_agent"].startswith("cu-cli/")


def test_build_client_polls_long_running_operations_every_second(monkeypatch):
    captured: dict = {}

    class _FakeSdkClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "azure.ai.contentunderstanding.ContentUnderstandingClient", _FakeSdkClient
    )

    build_client(Profile(endpoint="https://x.services.ai.azure.com/"))

    assert captured["polling_interval"] == 1
