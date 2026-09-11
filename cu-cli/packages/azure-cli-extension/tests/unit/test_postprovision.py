# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from types import SimpleNamespace

import pytest

from azext_content_understanding import _postprovision
from cu_cli_core.postprovision import PostprovisionResult

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
