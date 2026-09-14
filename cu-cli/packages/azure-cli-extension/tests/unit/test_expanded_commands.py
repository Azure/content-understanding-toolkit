# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Focused tests for Preview 2 and Preview 3 adapters."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from azure.core.exceptions import HttpResponseError
from cu_cli_core.errors import ServiceError, UsageError, ValidationError

from azext_content_understanding import _analysis, _analyzers, _diagnostics, _profiles


@pytest.mark.unit
def test_analyze_llm_input_preserves_sdk_result_for_formatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"pdf")
    sdk_result = object()
    formatted = "---\nmimeType: application/pdf\n---\ninvoice"
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        _analysis.Profile,
        "load",
        lambda **_kwargs: SimpleNamespace(default_analyzer=None),
    )
    monkeypatch.setattr(
        _analysis, "create_content_understanding_client", lambda *_args, **_kwargs: object()
    )

    def execute(_client, _request, *, jobs, on_result, **_kwargs):
        captured["output_format"] = jobs[0].output_format
        on_result(SimpleNamespace(job=jobs[0], ok=True, result=sdk_result))
        return SimpleNamespace(failures=[])

    monkeypatch.setattr(_analysis, "resolve_identifier", lambda _operation: execute)
    import azure.ai.contentunderstanding as content_understanding

    monkeypatch.setattr(
        content_understanding,
        "to_llm_input",
        lambda result: captured.setdefault("result", result) and formatted,
    )

    result = _analysis.analyze(
        SimpleNamespace(cli_ctx=object()),
        files=[source],
        analyzer_id="prebuilt-layout",
        llm_input=True,
        yes=True,
    )

    assert result == formatted
    assert captured == {"output_format": "markdown", "result": sdk_result}


@pytest.mark.unit
def test_analyzer_create_rejects_schema_pin_that_differs_from_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps({"analyzerId": "invoice", "apiVersion": "2025-11-01"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        _analyzers.Profile,
        "load",
        lambda **_kwargs: SimpleNamespace(api_version="2026-06-01-preview"),
    )
    monkeypatch.setattr(
        _analyzers,
        "create_content_understanding_client",
        lambda *_args, **_kwargs: pytest.fail("client must not target the schema's GA namespace"),
    )

    with pytest.raises(ValidationError, match="selected profile.*2026-06-01-preview"):
        _analyzers.create_analyzer(
            SimpleNamespace(),
            analyzer_name="invoice",
            schema_path=schema,
            profile_name="preview",
        )


@pytest.mark.unit
def test_profile_get_redacts_saved_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    config = tmp_path / "config"
    config.write_text("[cu]\ndefault.api_key = top-secret\n", encoding="utf-8")

    result = _profiles.get_profile(
        SimpleNamespace(), profile_key="api_key", profile_name="default"
    )

    assert result["value"] == "***redacted***"
    assert "top-secret" not in str(result)


@pytest.mark.unit
def test_profile_delete_uses_native_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path))
    config = tmp_path / "config"
    config.write_text("[cu]\ntest._created = true\n", encoding="utf-8")
    confirmations: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        _profiles,
        "user_confirmation",
        lambda message, yes: confirmations.append((message, yes)),
    )

    result = _profiles.delete_profile(SimpleNamespace(), profile_name="test", yes=True)

    assert result["deleted"] is True
    assert confirmations == [("Delete CU profile 'test'?", True)]


@pytest.mark.unit
def test_profile_show_lists_live_deployments(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = SimpleNamespace(
        profile_name="dev",
        endpoint="https://dev.services.ai.azure.com/",
        to_public_dict=lambda: {"profile": "dev"},
    )
    monkeypatch.setattr(_profiles, "resolve_identifier", lambda _operation: lambda _request: profile)
    monkeypatch.setattr(
        _profiles.ProfileStore,
        "load",
        lambda: SimpleNamespace(get_active_name=lambda: "default"),
    )
    monkeypatch.setattr(
        _profiles,
        "list_model_deployments",
        lambda cmd, endpoint: [{"name": "gpt", "model": "gpt-5.2"}],
    )

    result = _profiles.show_profile(
        SimpleNamespace(), profile_name="dev", deployments=True
    )

    assert result["deployments"] == [{"name": "gpt", "model": "gpt-5.2"}]


@pytest.mark.unit
def test_doctor_fix_defaults_applies_profile_mappings(monkeypatch: pytest.MonkeyPatch) -> None:
    reads = 0
    captured: dict[str, Any] = {}

    def get_defaults():
        nonlocal reads
        reads += 1
        return SimpleNamespace(model_deployments={"unrelated": "preserved"})

    client = SimpleNamespace(
        get_defaults=get_defaults,
        update_defaults=lambda *, model_deployments: captured.update(model_deployments),
    )
    profile = SimpleNamespace(
        profile_name="dev",
        endpoint="https://dev.example",
        api_version="2026-06-01-preview",
        auth_mode="login",
        api_key=None,
        default_analyzer=None,
        model_deployments={"gpt-5.2": "gpt-prod", "text-embedding-3-large": "emb-prod"},
    )
    monkeypatch.setattr(_diagnostics.Profile, "load", lambda **kwargs: profile)
    monkeypatch.setattr(
        _diagnostics, "create_content_understanding_client", lambda *args, **kwargs: client
    )

    result = _diagnostics.doctor(SimpleNamespace(), fix_defaults=True)

    assert reads == 1
    assert captured["unrelated"] == "preserved"
    assert captured["gpt-5.2"] == "gpt-prod"
    assert captured["prebuilt-analyzer-completion-mini"] == "gpt-prod"
    assert result["ready"] is True


def _doctor_profile(**overrides: Any) -> SimpleNamespace:
    values = {
        "profile_name": "dev",
        "endpoint": "https://saved.example",
        "api_version": "2025-11-01",
        "auth_mode": "login",
        "api_key": None,
        "default_analyzer": None,
        "model_deployments": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.unit
def test_doctor_unsupported_version_fails_before_client_creation(monkeypatch):
    monkeypatch.setattr(_diagnostics.Profile, "load", lambda **kwargs: _doctor_profile())
    called = False

    def client_factory(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(_diagnostics, "create_content_understanding_client", client_factory)

    with pytest.raises(ValidationError):
        _diagnostics.doctor(SimpleNamespace(), api_version="1999-01-01")
    assert called is False


@pytest.mark.unit
def test_doctor_defaults_not_set_is_successful_partial_readiness(monkeypatch):
    monkeypatch.setattr(_diagnostics.Profile, "load", lambda **kwargs: _doctor_profile())

    def get_defaults():
        raise HttpResponseError(message="DefaultsNotSet")

    monkeypatch.setattr(
        _diagnostics,
        "create_content_understanding_client",
        lambda *args, **kwargs: SimpleNamespace(get_defaults=get_defaults),
    )

    result = _diagnostics.doctor(SimpleNamespace())

    assert result["ready"] is False
    assert result["failures"] == []
    assert result["modelDeployments"] == {}


@pytest.mark.unit
def test_doctor_connectivity_failure_is_nonzero_and_redacts_key(monkeypatch):
    secret = "top-secret"
    monkeypatch.setattr(
        _diagnostics.Profile,
        "load",
        lambda **kwargs: _doctor_profile(auth_mode="key", api_key=secret),
    )

    def get_defaults():
        raise RuntimeError(f"login failed using {secret}")

    monkeypatch.setattr(
        _diagnostics,
        "create_content_understanding_client",
        lambda *args, **kwargs: SimpleNamespace(get_defaults=get_defaults),
    )

    with pytest.raises(ServiceError) as exc_info:
        _diagnostics.doctor(SimpleNamespace())
    assert secret not in str(exc_info.value)
    assert "***redacted***" in str(exc_info.value)


@pytest.mark.unit
def test_doctor_explicit_overrides_and_key_result_are_secret_free(monkeypatch):
    secret = "top-secret"
    monkeypatch.setattr(_diagnostics.Profile, "load", lambda **kwargs: _doctor_profile())
    captured = {}
    client = SimpleNamespace(
        get_defaults=lambda: SimpleNamespace(
            model_deployments={
                "text-embedding-3-large": "emb",
                "gpt-5.2": "gpt",
                "prebuilt-analyzer-completion-mini": "gpt",
            }
        )
    )

    def client_factory(*args, **kwargs):
        captured.update(kwargs)
        return client

    monkeypatch.setattr(_diagnostics, "create_content_understanding_client", client_factory)
    result = _diagnostics.doctor(
        SimpleNamespace(),
        endpoint="https://override.example",
        api_version="2026-06-01-preview",
        auth_mode="key",
        api_key=secret,
        profile_name="dev",
    )

    assert result["endpoint"] == "https://override.example"
    assert result["apiVersion"] == "2026-06-01-preview"
    assert result["authentication"] == "resource key"
    assert captured["api_key"] == secret
    assert secret not in str(result)


@pytest.mark.unit
def test_doctor_loads_named_profile_without_changing_active_profile(monkeypatch):
    loaded = []
    profile = _doctor_profile(profile_name="named")
    monkeypatch.setattr(
        _diagnostics.Profile,
        "load",
        lambda **kwargs: loaded.append(kwargs) or profile,
    )
    monkeypatch.setattr(
        _diagnostics,
        "create_content_understanding_client",
        lambda *args, **kwargs: SimpleNamespace(
            get_defaults=lambda: SimpleNamespace(model_deployments={})
        ),
    )

    result = _diagnostics.doctor(SimpleNamespace(), profile_name="named")

    assert loaded == [{"profile_name": "named"}]
    assert result["profile"] == "named"


@pytest.mark.unit
def test_doctor_fix_without_service_or_profile_mappings_is_nonzero(monkeypatch):
    monkeypatch.setattr(_diagnostics.Profile, "load", lambda **kwargs: _doctor_profile())
    monkeypatch.setattr(
        _diagnostics,
        "create_content_understanding_client",
        lambda *args, **kwargs: SimpleNamespace(
            get_defaults=lambda: SimpleNamespace(model_deployments={})
        ),
    )

    with pytest.raises(UsageError, match="no model deployment mapping"):
        _diagnostics.doctor(SimpleNamespace(), fix_defaults=True)


@pytest.mark.unit
def test_frontends_emit_identical_analysis_report_contract(tmp_path: Path) -> None:
    from cu_cli.commands.analyze import _write_analyze_report

    records = [
        {"input": "a.pdf", "status": "succeeded", "analyzerId": "layout"},
        {"input": "b.pdf", "status": "skipped", "reason": "exists"},
    ]
    standalone_path = tmp_path / "standalone.json"
    azure_path = tmp_path / "azure.json"

    _write_analyze_report(standalone_path, analyzer_id="layout", fmt="json", results=records)
    _analysis._report(azure_path, "layout", "full", records)

    import json

    assert json.loads(standalone_path.read_text()) == json.loads(azure_path.read_text())


@pytest.mark.unit
def test_env_var_list_redacts_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CU_API_KEY", "top-secret")
    monkeypatch.setenv("CU_ENDPOINT", "https://example.test")

    result = _diagnostics.list_environment_variables(SimpleNamespace())

    keyed = {item["name"]: item for item in result}
    assert keyed["CU_API_KEY"]["value"] == "********"
    assert "top-secret" not in str(result)


@pytest.mark.unit
def test_analyzer_copy_uses_host_resolved_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_client = SimpleNamespace()
    destination_client = SimpleNamespace()
    source_resource = SimpleNamespace(
        arm_id="/subscriptions/s/resourceGroups/r/providers/Microsoft.CognitiveServices/accounts/a",
        endpoint="https://a.services.ai.azure.com/",
        subscription_id="s",
        resource_group="r",
        account_name="a",
        region="eastus",
    )
    destination_resource = SimpleNamespace(
        arm_id="/subscriptions/d/resourceGroups/r/providers/Microsoft.CognitiveServices/accounts/b",
        endpoint="https://b.services.ai.azure.com/",
        subscription_id="d",
        resource_group="r",
        account_name="b",
        region="westus",
    )
    resources = {"a": source_resource, "b": destination_resource}
    clients = {
        source_resource.endpoint: source_client,
        destination_resource.endpoint: destination_client,
    }
    monkeypatch.setattr(
        _analyzers,
        "resolve_resource",
        lambda cmd, selector, **kwargs: resources[selector],
    )
    monkeypatch.setattr(
        _analyzers,
        "create_content_understanding_client",
        lambda cmd, endpoint, **kwargs: clients[endpoint],
    )
    monkeypatch.setattr(
        _analyzers,
        "resources_equal",
        lambda left, right: left.arm_id == right.arm_id,
    )
    operations = __import__(
        "cu_cli_core.operations.analyzer_copy", fromlist=["copy_analyzer"]
    )
    monkeypatch.setattr(operations, "get_copy_source_analyzer", lambda *args: object())
    monkeypatch.setattr(operations, "collect_custom_dependencies", lambda value: [])
    monkeypatch.setattr(operations, "preflight_dependencies_on_target", lambda *args: [])
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        operations,
        "copy_analyzer",
        lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs) or {"copied": True},
    )
    from cu_cli_core.command_spec import resolve_identifier

    resolve_identifier.cache_clear()

    result = _analyzers.copy_analyzer(
        SimpleNamespace(),
        named_source="source",
        named_destination="destination",
        source_resource="a",
        destination_resource="b",
    )

    assert result == {"copied": True}
    assert captured["args"][0] is source_client
    assert captured["kwargs"]["target_client"] is destination_client
    assert captured["kwargs"]["source_azure_resource_id"] == source_resource.arm_id
    assert captured["kwargs"]["target_azure_resource_id"] == destination_resource.arm_id
