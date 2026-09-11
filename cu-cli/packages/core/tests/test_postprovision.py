# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from dataclasses import replace

import pytest

from cu_cli_core.postprovision import (
    DeploymentState,
    PostprovisionRequest,
    execute_postprovision,
)

pytestmark = pytest.mark.unit


class Capabilities:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.populated = False
        self.deployments = (
            DeploymentState("gpt", "gpt-5.2", True),
            DeploymentState("embedding", "text-embedding-3-large", True),
        )
        self.fail: str | None = None

    def _call(self, *values: object) -> None:
        self.calls.append(values)
        if self.fail and self.fail in ":".join(str(value) for value in values):
            raise RuntimeError("injected failure")

    def setup_models(self, request: PostprovisionRequest) -> None:
        self._call("models", request.model_selection)

    def mark_model_setup_complete(self) -> None:
        self._call("complete")

    def profile_has_values(self, name: str) -> bool:
        self._call("has-values", name)
        return self.populated

    def set_profile_value(self, name: str, key: str, value: str) -> None:
        self._call("set", name, key, value)

    def get_account_key(self, request: PostprovisionRequest) -> str:
        self._call("key", request.account_name)
        return "secret"

    def list_deployments(self, request: PostprovisionRequest):
        self._call("deployments", request.account_name)
        return self.deployments

    def configure_defaults(self, request: PostprovisionRequest, mappings: dict[str, str]) -> None:
        self._call("defaults", request.endpoint, tuple(sorted(mappings)))


REQUEST = PostprovisionRequest(
    endpoint="https://example.services.ai.azure.com/",
    resource_group="rg",
    account_name="account",
    subscription_id="sub",
    model_selection="recommended",
)


def test_key_auth_precedes_endpoint_analyzer_and_defaults() -> None:
    capabilities = Capabilities()
    result = execute_postprovision(REQUEST, capabilities)

    names = [call[2] if call[0] == "set" else call[0] for call in capabilities.calls]
    assert result.succeeded and result.generative_ready
    assert names.index("api_key") < names.index("endpoint") < names.index("default_analyzer")
    assert names.index("default_analyzer") < names.index("defaults")
    assert "secret" not in repr(result)


def test_role_enabled_uses_login_without_fetching_key() -> None:
    capabilities = Capabilities()
    result = execute_postprovision(replace(REQUEST, assign_roles=True), capabilities)

    assert result.succeeded
    assert ("set", "default", "auth_mode", "login") in capabilities.calls
    assert not any(call[0] == "key" for call in capabilities.calls)


def test_completed_state_skips_model_setup() -> None:
    capabilities = Capabilities()
    result = execute_postprovision(replace(REQUEST, model_setup_complete=True), capabilities)

    assert result.model_setup == "skipped"
    assert not any(call[0] in {"models", "complete"} for call in capabilities.calls)


@pytest.mark.parametrize("legacy", [False, True])
def test_profile_opt_out_prevents_inspection_and_mutation(legacy: bool) -> None:
    capabilities = Capabilities()
    request = replace(REQUEST, disable_profile_setup=True)
    result = execute_postprovision(request, capabilities)

    assert result.succeeded and result.profile_setup_disabled
    assert not any(call[0] in {"has-values", "set", "key", "deployments", "defaults"} for call in capabilities.calls)
    assert legacy in {False, True}  # Both environment spellings resolve to this request contract.


def test_populated_profile_is_preserved_unless_forced() -> None:
    capabilities = Capabilities()
    capabilities.populated = True
    preserved = execute_postprovision(REQUEST, capabilities)
    assert preserved.profile_preserved
    assert not any(call[0] == "set" for call in capabilities.calls)

    forced = Capabilities()
    forced.populated = True
    result = execute_postprovision(replace(REQUEST, force_profile_setup=True), forced)
    assert result.profile_configured
    assert any(call[0] == "set" for call in forced.calls)


def test_optional_model_and_defaults_failures_preserve_basic_success() -> None:
    model_failure = Capabilities()
    model_failure.fail = "models"
    model_result = execute_postprovision(REQUEST, model_failure)
    assert model_result.succeeded and model_result.profile_configured
    assert model_result.model_setup == "failed"
    assert any("Optional model setup failed" in warning for warning in model_result.warnings)

    defaults_failure = Capabilities()
    defaults_failure.fail = "defaults"
    defaults_result = execute_postprovision(REQUEST, defaults_failure)
    assert defaults_result.succeeded and not defaults_result.defaults_configured
    assert any("defaults" in warning for warning in defaults_result.warnings)


def test_optional_model_failure_does_not_mark_setup_complete() -> None:
    capabilities = Capabilities()
    capabilities.fail = "models"

    result = execute_postprovision(REQUEST, capabilities)

    assert result.model_setup == "failed"
    assert not any(call[0] == "complete" for call in capabilities.calls)


@pytest.mark.parametrize(
    ("deployments", "expected_ready"),
    [
        ((), False),
        ((DeploymentState("gpt", "gpt-5.2", True),), False),
        (
            (
                DeploymentState("gpt", "gpt-5.2", True),
                DeploymentState("embedding", "text-embedding-3-large", False),
            ),
            False,
        ),
        (
            (
                DeploymentState("gpt", "gpt-5.2", True),
                DeploymentState("embedding", "text-embedding-3-large", True),
            ),
            True,
        ),
    ],
)
def test_readiness_requires_succeeded_completion_and_embedding_deployments(
    deployments: tuple[DeploymentState, ...], expected_ready: bool
) -> None:
    capabilities = Capabilities()
    capabilities.deployments = deployments

    result = execute_postprovision(REQUEST, capabilities)

    assert result.generative_ready is expected_ready


def test_adapter_exception_text_cannot_leak_into_result() -> None:
    capabilities = Capabilities()
    capabilities.fail = "api_key"
    secret = capabilities.get_account_key(REQUEST)

    result = execute_postprovision(REQUEST, capabilities)

    assert secret not in repr(result)
    assert "injected failure" not in repr(result)


@pytest.mark.parametrize("failure", ["api_key", "endpoint", "default_analyzer"])
def test_required_profile_write_failure_is_nonzero(failure: str) -> None:
    capabilities = Capabilities()
    capabilities.fail = failure
    result = execute_postprovision(REQUEST, capabilities)

    assert not result.succeeded
    expected = {
        "api_key": "key authentication",
        "endpoint": "endpoint",
        "default_analyzer": "default analyzer",
    }[failure]
    assert any(expected in message.casefold() for message in result.messages)
