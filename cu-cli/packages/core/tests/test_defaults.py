# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from io import BytesIO
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from cu_cli_core.defaults import (
    apply_defaults,
    extract_model_deployments,
    parse_model_kv,
    with_prebuilt_default_mappings,
)
from cu_cli_core.errors import ValidationError

pytestmark = pytest.mark.unit


def test_parse_model_kv_validates_and_normalizes_values():
    assert parse_model_kv((" gpt-5.2 = deployment ",)) == {
        "gpt-5.2": "deployment"
    }
    with pytest.raises(ValidationError, match="invalid --model mapping"):
        parse_model_kv(("missing-separator",))


def test_with_prebuilt_default_mappings_adds_service_aliases():
    mappings = with_prebuilt_default_mappings(
        {
            "gpt-5.2": "completion",
            "text-embedding-3-large": "embedding",
        }
    )

    assert mappings["prebuilt-analyzer-completion"] == "completion"
    assert mappings["prebuilt-analyzer-completion-mini"] == "completion"
    assert mappings["prebuilt-analyzer-embedding"] == "embedding"


@pytest.mark.parametrize("replace", [False, True], ids=["merge", "replace"])
def test_apply_defaults_merges_or_replaces_existing_values(replace):
    existing = {
        "existing": "old",
        "text-embedding-3-large": "old-embedding",
        "prebuilt-analyzer-completion": "old-completion",
        "prebuilt-analyzer-completion-mini": "old-mini",
        "prebuilt-analyzer-embedding": "old-embedding",
    }
    requests = []
    calls = []

    class Client:
        def get_defaults(self):
            calls.append("get")
            return SimpleNamespace(model_deployments=dict(existing))

        def update_defaults(self, *, model_deployments):
            calls.append("update")
            requests.append(dict(model_deployments))
            for model, deployment in model_deployments.items():
                if deployment is None:
                    existing.pop(model, None)
                else:
                    existing[model] = deployment
            return SimpleNamespace(model_deployments=dict(existing))

    updated, merged = apply_defaults(
        Client(),
        {"gpt-5.2": "completion"},
        replace=replace,
    )

    assert ("existing" in merged) == (not replace)
    assert extract_model_deployments(updated) == merged
    assert calls == ["get", "update"]
    assert merged["prebuilt-analyzer-completion"] == "completion"
    assert merged["prebuilt-analyzer-completion-mini"] == "completion"
    assert all(isinstance(deployment, str) for deployment in merged.values())
    if replace:
        for model in ("existing", "text-embedding-3-large", "prebuilt-analyzer-embedding"):
            assert requests[0][model] is None
            assert model not in merged
    else:
        assert merged["existing"] == "old"
        assert merged["prebuilt-analyzer-embedding"] == "old-embedding"
        assert requests[0] == merged


@pytest.mark.parametrize("replace", [False, True], ids=["merge", "replace"])
@pytest.mark.parametrize(
    "message",
    ["DefaultsNotSet", "Defaults have not yet been set"],
    ids=["error-code", "message"],
)
def test_apply_defaults_accepts_unconfigured_resource(replace, message):
    from azure.core.exceptions import HttpResponseError

    requests = []

    def get_defaults():
        raise HttpResponseError(message=message)

    def update_defaults(*, model_deployments):
        requests.append(dict(model_deployments))
        return SimpleNamespace(model_deployments=dict(model_deployments))

    updated, merged = apply_defaults(
        SimpleNamespace(get_defaults=get_defaults, update_defaults=update_defaults),
        {"gpt-5.2": "completion"},
        replace=replace,
    )

    assert requests == [merged]
    assert extract_model_deployments(updated) == merged
    assert all(isinstance(deployment, str) for deployment in merged.values())


@pytest.mark.parametrize("replace", [False, True], ids=["merge", "replace"])
def test_apply_defaults_read_failure_does_not_update(replace):
    from azure.core.exceptions import HttpResponseError

    error = HttpResponseError(message="defaults read denied")

    def get_defaults():
        raise error

    def update_defaults(**kwargs):
        pytest.fail("defaults must not be updated after a failed read")

    with pytest.raises(HttpResponseError, match="defaults read denied") as caught:
        apply_defaults(
            SimpleNamespace(get_defaults=get_defaults, update_defaults=update_defaults),
            {"gpt-5.2": "completion"},
            replace=replace,
        )

    assert caught.value is error


@pytest.mark.parametrize("replace", [False, True], ids=["merge", "replace"])
@pytest.mark.parametrize(
    "api_version", ["2025-11-01", "2026-06-01-preview"], ids=["ga", "preview"]
)
def test_apply_defaults_sdk_merge_patch_round_trip(monkeypatch, replace, api_version):
    from azure.ai.contentunderstanding import ContentUnderstandingClient
    from azure.core.credentials import AzureKeyCredential
    from requests import Response
    from urllib3.response import HTTPResponse

    server_mappings = {
        "gpt-4.1": "old-completion",
        "text-embedding-3-large": "old-embedding",
        "prebuilt-analyzer-embedding": "old-embedding",
    }
    calls = []
    patches = []

    def request(session, method, url, **kwargs):
        parsed = urlsplit(url)
        assert parsed.path == "/contentunderstanding/defaults"
        assert parse_qs(parsed.query) == {"api-version": [api_version]}
        calls.append(method)
        if method == "PATCH":
            assert kwargs["headers"]["Content-Type"] == "application/merge-patch+json"
            body = json.loads(kwargs["data"])
            mappings = body["modelDeployments"]
            patches.append(mappings)
            for model, deployment in mappings.items():
                if deployment is None:
                    server_mappings.pop(model, None)
                else:
                    server_mappings[model] = deployment
        else:
            assert method == "GET"
        response = Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps({"modelDeployments": server_mappings}).encode("utf-8")
        response.raw = HTTPResponse(body=BytesIO(response.content), preload_content=False)
        return response

    monkeypatch.setattr("requests.sessions.Session.request", request)

    with ContentUnderstandingClient(
        endpoint="https://defaults-test.invalid",
        credential=AzureKeyCredential("offline-test-key"),
        api_version=api_version,
    ) as client:
        updated, merged = apply_defaults(client, {"gpt-5.2": "completion"}, replace=replace)
        read_back = extract_model_deployments(client.get_defaults())

    assert calls == ["GET", "PATCH", "GET"]
    assert read_back == extract_model_deployments(updated) == merged
    assert merged["gpt-5.2"] == "completion"
    assert merged["prebuilt-analyzer-completion"] == "completion"
    assert merged["prebuilt-analyzer-completion-mini"] == "completion"
    assert all(isinstance(deployment, str) for deployment in merged.values())
    if replace:
        assert patches[0]["gpt-4.1"] is None
        assert patches[0]["text-embedding-3-large"] is None
        assert patches[0]["prebuilt-analyzer-embedding"] is None
        assert set(merged) == {
            "gpt-5.2", "prebuilt-analyzer-completion", "prebuilt-analyzer-completion-mini",
        }
    else:
        assert merged["gpt-4.1"] == "old-completion"
        assert merged["prebuilt-analyzer-embedding"] == "old-embedding"
        assert patches[0] == merged
