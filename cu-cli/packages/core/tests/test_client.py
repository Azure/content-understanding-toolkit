import builtins

import pytest

from cu_cli_core.client import build_content_understanding_client
from cu_cli_core.errors import ValidationError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "kwargs, message",
    [
        (
            {"endpoint": " ", "credential": object(), "api_version": "2025-11-01"},
            "endpoint cannot be empty",
        ),
        (
            {"endpoint": "https://example", "credential": None, "api_version": "2025-11-01"},
            "credential cannot be empty",
        ),
        (
            {"endpoint": "https://example", "credential": object(), "api_version": " "},
            "API version cannot be empty",
        ),
    ],
)
def test_client_factory_validates_inputs_before_sdk_import(monkeypatch, kwargs, message):
    original_import = builtins.__import__

    def fail_sdk_import(name, *args, **options):
        if name.startswith("azure"):
            raise AssertionError("SDK must not be imported for invalid input")
        return original_import(name, *args, **options)

    monkeypatch.setattr(builtins, "__import__", fail_sdk_import)

    with pytest.raises(ValidationError, match=message):
        build_content_understanding_client(**kwargs)


def test_client_factory_injects_credential_and_normalizes_endpoint(monkeypatch):
    captured: dict = {}
    credential = object()

    class _FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "azure.ai.contentunderstanding.ContentUnderstandingClient",
        _FakeClient,
    )

    client = build_content_understanding_client(
        endpoint=" https://example.services.ai.azure.com/ ",
        credential=credential,
        api_version="2025-11-01",
        user_agent="cu-cli/0.2.0",
    )

    assert isinstance(client, _FakeClient)
    assert captured == {
        "endpoint": "https://example.services.ai.azure.com",
        "credential": credential,
        "api_version": "2025-11-01",
        "user_agent": "cu-cli/0.2.0",
        "polling_interval": 1,
    }
