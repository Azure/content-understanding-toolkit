# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from types import SimpleNamespace

import pytest

from azext_content_understanding import _postprovision
from cu_cli_core.postprovision import PostprovisionResult, execute_postprovision

pytestmark = pytest.mark.unit


def test_azure_adapter_returns_shared_postprovision_result(monkeypatch):
    monkeypatch.setattr(_postprovision, "_request_from_environment", lambda: object())
    monkeypatch.setattr(
        _postprovision,
        "execute_postprovision",
        lambda request, capabilities: PostprovisionResult(
            succeeded=True,
            profile_configured=True,
            model_setup="completed",
            messages=("shared policy reached",),
        ),
    )

    result = _postprovision.postprovision_v1(SimpleNamespace(cli_ctx=object()))

    assert result["succeeded"] is True
    assert result["profileConfigured"] is True
    assert result["modelSetup"] == "completed"
    assert result["messages"] == ["shared policy reached"]


def test_completed_model_state_from_azd_skips_azure_model_setup(monkeypatch):
    monkeypatch.setattr(
        _postprovision,
        "_azd_values",
        lambda: {
            "FOUNDRY_ENDPOINT": "https://example.services.ai.azure.com/",
            "FOUNDRY_RESOURCE_NAME": "account",
            "AZURE_RESOURCE_GROUP": "rg",
            "AZURE_SUBSCRIPTION_ID": "sub",
            "CU_MODEL_SETUP_COMPLETE": "true",
        },
    )
    request = _postprovision._request_from_environment()
    capabilities = SimpleNamespace(
        setup_models=lambda _request: pytest.fail("model setup must be skipped"),
        mark_model_setup_complete=lambda: pytest.fail("state must not be rewritten"),
        profile_has_values=lambda _name: True,
    )

    result = execute_postprovision(request, capabilities)

    assert request.model_setup_complete is True
    assert result.model_setup == "skipped"


def test_azure_adapter_rejects_empty_account_key(monkeypatch):
    management = SimpleNamespace(
        accounts=SimpleNamespace(
            list_keys=lambda _rg, _account: SimpleNamespace(key1=None, key2="")
        )
    )
    capabilities = _postprovision._AzureCapabilities(
        SimpleNamespace(cli_ctx=object())
    )
    monkeypatch.setattr(capabilities, "_management_client", lambda _request: management)

    with pytest.raises(RuntimeError, match="returned no account key"):
        capabilities.get_account_key(
            SimpleNamespace(resource_group="rg", account_name="account")
        )
