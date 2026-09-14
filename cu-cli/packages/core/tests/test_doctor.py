# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from types import SimpleNamespace

import pytest

from cu_cli_core.doctor import assess_doctor, resolve_doctor_request
from cu_cli_core.errors import UsageError, ValidationError


class FakeClient:
    def __init__(self, mappings=None, error=None):
        self.mappings = mappings or {}
        self.error = error
        self.reads = 0
        self.updated = None

    def get_defaults(self):
        self.reads += 1
        if self.error:
            raise self.error
        return SimpleNamespace(model_deployments=self.mappings)

    def update_defaults(self, *, model_deployments):
        self.updated = model_deployments


def profile(**overrides):
    values = {
        "endpoint": "https://saved.example",
        "api_version": "2025-11-01",
        "auth_mode": "login",
        "api_key": None,
        "default_analyzer": "saved-analyzer",
        "model_deployments": {"gpt-5.2": "saved-gpt"},
        "profile_name": "named",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.unit
def test_request_resolves_all_explicit_overrides_without_exposing_key():
    request = resolve_doctor_request(
        profile(),
        endpoint="https://override.example",
        api_version="2026-06-01-preview",
        auth_mode="key",
        api_key="top-secret",
    )

    assert request.endpoint == "https://override.example"
    assert request.api_version == "2026-06-01-preview"
    assert request.authentication == "resource key"
    assert request.profile == "named"
    assert "top-secret" not in repr(request)


@pytest.mark.unit
def test_unsupported_version_fails_before_client_creation():
    request_factory_calls = []
    with pytest.raises(ValidationError):
        resolve_doctor_request(profile(), api_version="1999-01-01")
    assert request_factory_calls == []


@pytest.mark.unit
def test_defaults_not_set_is_reachable_partial_readiness():
    request = resolve_doctor_request(profile(model_deployments={}))
    client = FakeClient(error=RuntimeError("DefaultsNotSet"))

    result = assess_doctor(request, lambda _: client)

    assert result.required_checks_passed is True
    assert result.ready is False
    assert result.defaults_configured is False
    assert result.model_deployments == {}


@pytest.mark.unit
def test_connectivity_failure_is_required_and_redacts_key():
    request = resolve_doctor_request(
        profile(auth_mode="key", api_key="top-secret")
    )
    result = assess_doctor(
        request,
        lambda _: FakeClient(error=RuntimeError("failed with top-secret")),
    )

    assert result.required_checks_passed is False
    assert result.ready is False
    assert "top-secret" not in str(result.to_dict())
    assert "***redacted***" in result.failures[0].message


@pytest.mark.unit
@pytest.mark.parametrize(
    "failure",
    (
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature",
        "api_key=another-secret",
        "token: token-value",
        "https://example.test/file?sig=sas-signature&other=safe",
    ),
)
def test_connectivity_failure_redacts_common_credential_formats(failure):
    request = resolve_doctor_request(profile())

    result = assess_doctor(request, lambda _: FakeClient(error=RuntimeError(failure)))

    message = result.failures[0].message
    assert "eyJhbGciOiJIUzI1NiJ9" not in message
    assert "another-secret" not in message
    assert "token-value" not in message
    assert "sas-signature" not in message
    assert "***redacted***" in message


@pytest.mark.unit
def test_fix_reads_once_preserves_mappings_and_adds_aliases():
    request = resolve_doctor_request(
        profile(
            model_deployments={
                "gpt-5.2": "new-gpt",
                "text-embedding-3-large": "new-embedding",
            }
        ),
        fix_defaults=True,
    )
    client = FakeClient({"unrelated-model": "keep-me", "gpt-5.2": "old-gpt"})

    result = assess_doctor(request, lambda _: client)

    assert client.reads == 1
    assert client.updated["unrelated-model"] == "keep-me"
    assert client.updated["gpt-5.2"] == "new-gpt"
    assert client.updated["prebuilt-analyzer-completion"] == "new-gpt"
    assert client.updated["prebuilt-analyzer-completion-mini"] == "new-gpt"
    assert client.updated["prebuilt-analyzer-embedding"] == "new-embedding"
    assert result.ready is True
    assert result.defaults_updated is True


@pytest.mark.unit
def test_fix_without_any_mapping_is_usage_failure():
    request = resolve_doctor_request(profile(model_deployments={}), fix_defaults=True)
    with pytest.raises(UsageError):
        assess_doctor(request, lambda _: FakeClient())