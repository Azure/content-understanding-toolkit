# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from cu_cli.cli import main
from cu_cli.profile import ProfileStore, azure_config_path

pytestmark = pytest.mark.unit

_runner = CliRunner()


def _run(*args: str):
    return _runner.invoke(main, list(args), color=False)


@pytest.mark.parametrize(
    "args",
    [
        ("profile", "get"),
        ("profile", "set"),
        ("profile", "unset"),
        ("profile", "create"),
        ("profile", "delete"),
        ("profile", "copy"),
        ("profile", "rename"),
        ("profile", "set-active"),
    ],
)
def test_profile_missing_required_arguments_exit_two(args):
    result = _run(*args)

    assert result.exit_code == 2, result.output
    assert "missing required argument" in result.output


@pytest.mark.parametrize(
    ("command", "expected_help"),
    [
        ("create", "New profile name."),
        ("delete", "Existing inactive profile to delete."),
        ("set-active", "Existing profile to activate."),
    ],
)
def test_profile_name_help_matches_command(command: str, expected_help: str):
    result = _run("profile", command, "--help")

    assert result.exit_code == 0, result.output
    compact_output = "".join(result.output.replace("│", "").split())
    assert "".join(expected_help.split()) in compact_output


def test_removed_config_group_is_not_exposed():
    result = _run("--help")

    assert result.exit_code == 0, result.output
    assert "profile" in result.output
    assert "│ config " not in result.output
    assert _run("config", "--help").exit_code == 2


def test_set_get_and_show_default_profile():
    set_result = _run("profile", "set", "api_version", "2026-06-01-preview")

    assert set_result.exit_code == 0, set_result.output
    assert "profile 'default'" in set_result.output
    get_result = _run("profile", "get", "api_version")
    assert get_result.exit_code == 0, get_result.output
    assert get_result.output.strip() == "2026-06-01-preview"
    show_result = _run("profile", "show")
    assert show_result.exit_code == 0, show_result.output
    assert "CU CLI profile: default (active)" in show_result.output
    assert "2026-06-01-preview" in show_result.output


def test_hidden_has_values_reports_saved_default_profile_state():
    empty_result = _run("profile", "_has-values", "--name", "default")
    assert empty_result.exit_code == 3

    assert _run("profile", "set", "endpoint", "https://example.services.ai.azure.com/").exit_code == 0
    populated_result = _run("profile", "_has-values", "--name", "default")
    assert populated_result.exit_code == 0


def test_api_key_is_redacted_by_get_and_show():
    secret = "test-secret-value"

    assert _run("profile", "set", "api_key", secret).exit_code == 0

    get_result = _run("profile", "get", "api_key")
    show_result = _run("profile", "show")
    assert get_result.exit_code == 0, get_result.output
    assert get_result.output.strip() == "***redacted***"
    assert show_result.exit_code == 0, show_result.output
    assert "***redacted***" in show_result.output
    assert secret not in get_result.output
    assert secret not in show_result.output


def test_create_set_active_and_list_named_profile():
    create_result = _run("profile", "create", "dev")

    assert create_result.exit_code == 0, create_result.output
    assert ProfileStore.load().get_active_name() == "default"
    assert _run(
        "profile",
        "set",
        "endpoint",
        "https://dev.services.ai.azure.com",
        "--name",
        "dev",
    ).exit_code == 0

    set_active_result = _run("profile", "set-active", "dev")
    assert set_active_result.exit_code == 0, set_active_result.output
    assert ProfileStore.load().get_active_name() == "dev"
    list_result = _run("profile", "list")
    assert list_result.exit_code == 0, list_result.output
    assert "default" in list_result.output
    assert "dev" in list_result.output
    assert "(active)" in list_result.output


def test_show_named_profile_does_not_change_active_profile():
    assert _run("profile", "create", "dev").exit_code == 0
    assert _run("profile", "set", "api_version", "2026-06-01-preview", "--name", "dev").exit_code == 0

    result = _run("profile", "show", "--name", "dev")

    assert result.exit_code == 0, result.output
    assert "view only; active CU CLI profile remains: default" in result.output
    assert "CU CLI profile: dev" in result.output
    assert ProfileStore.load().get_active_name() == "default"


def test_endpoint_is_normalized_and_credentials_are_rejected_atomically():
    assert _run(
        "profile",
        "set",
        "endpoint",
        "https://existing.services.ai.azure.com/",
    ).exit_code == 0
    path = azure_config_path()
    original = path.read_bytes()

    invalid = _run(
        "profile",
        "set",
        "endpoint",
        "https://demo-user:demo-password@x.services.ai.azure.com/",
    )

    assert invalid.exit_code == 1, invalid.output
    assert "must not include username or password information" in invalid.output
    assert "demo-password" not in invalid.output
    assert path.read_bytes() == original
    assert ProfileStore.load().get("endpoint") == (
        "https://existing.services.ai.azure.com/"
    )


@pytest.mark.parametrize(
    "name",
    ["default", "-dev", "dev-", "contains space", "x" * 65],
)
def test_invalid_profile_names_do_not_modify_azure_config(name: str):
    path = azure_config_path()

    result = _run("profile", "create", name)

    assert result.exit_code == 2, result.output
    assert not path.exists()


def test_copy_and_rename_preserve_values_and_active_profile():
    assert _run("profile", "create", "dev").exit_code == 0
    assert _run("profile", "set", "default_analyzer", "invoice_v1", "--name", "dev").exit_code == 0
    assert _run("profile", "copy", "dev", "test").exit_code == 0
    assert _run("profile", "set-active", "test").exit_code == 0

    rename_result = _run("profile", "rename", "test", "prod")

    assert rename_result.exit_code == 0, rename_result.output
    store = ProfileStore.load()
    assert store.get_active_name() == "prod"
    assert store.get("default_analyzer", name="prod") == "invoice_v1"
    assert not store.has_name("test")


def test_copy_rejects_mixed_positional_and_named_selectors():
    assert _run("profile", "create", "dev").exit_code == 0

    result = _run(
        "profile",
        "copy",
        "dev",
        "test",
        "--source",
        "dev",
        "--destination",
        "prod",
    )

    assert result.exit_code == 2, result.output
    assert "cannot be combined" in result.output
    assert not ProfileStore.load().has_name("test")
    assert not ProfileStore.load().has_name("prod")


def test_delete_active_profile_is_blocked():
    assert _run("profile", "create", "dev").exit_code == 0
    assert _run("profile", "set-active", "dev").exit_code == 0

    result = _run("profile", "delete", "dev")

    assert result.exit_code == 1, result.output
    assert "cannot delete active CU CLI profile" in result.output
    assert ProfileStore.load().has_name("dev")


def test_unset_last_value_keeps_empty_named_profile():
    assert _run("profile", "create", "dev").exit_code == 0
    assert _run("profile", "set", "api_version", "2026-06-01-preview", "--name", "dev").exit_code == 0

    result = _run("profile", "unset", "api_version", "--name", "dev")

    assert result.exit_code == 0, result.output
    store = ProfileStore.load()
    assert store.has_name("dev")
    assert store.get_explicit_profile("dev") == {}


def test_sync_defaults_uses_saved_endpoint_not_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    saved_endpoint = "https://saved.services.ai.azure.com/"
    assert _run("profile", "create", "dev").exit_code == 0
    assert _run("profile", "set", "endpoint", saved_endpoint, "--name", "dev").exit_code == 0
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.services.ai.azure.com/")
    captured: dict[str, str | None] = {}

    class _Client:
        def get_defaults(self):
            return SimpleNamespace(
                model_deployments={
                    "gpt-5.2": "gpt-prod",
                    "text-embedding-3-large": "embedding-prod",
                }
            )

    def _build_client(profile, **_kwargs):
        captured["endpoint"] = profile.endpoint
        return _Client()

    monkeypatch.setattr("cu_cli.commands.profile_cmd.build_client", _build_client)

    result = _run("profile", "sync-defaults", "--name", "dev")

    assert result.exit_code == 0, result.output
    assert captured["endpoint"] == saved_endpoint
    store = ProfileStore.load()
    assert store.get("model_deployments.gpt-5.2", name="dev") == "gpt-prod"
    assert store.get(
        "model_deployments.text-embedding-3-large",
        name="dev",
    ) == "embedding-prod"


def test_sync_defaults_requires_saved_endpoint(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.services.ai.azure.com/")

    result = _run("profile", "sync-defaults")

    assert result.exit_code == 1, result.output
    assert "no endpoint is saved in CU CLI profile 'default'" in result.output
    assert "cu profile set endpoint URL" in result.output


@pytest.mark.parametrize("service_returns_empty", [False, True])
def test_sync_defaults_not_configured_reuses_model_setup_guidance(
    monkeypatch: pytest.MonkeyPatch,
    service_returns_empty: bool,
):
    from azure.core.exceptions import HttpResponseError

    endpoint = "https://saved.services.ai.azure.com/"
    assert _run("profile", "create", "dev").exit_code == 0
    assert _run("profile", "set", "endpoint", endpoint, "--name", "dev").exit_code == 0

    class _Client:
        def get_defaults(self):
            if service_returns_empty:
                return SimpleNamespace(model_deployments={})
            raise HttpResponseError(
                message="DefaultsNotSet: Call 'PATCH /contentunderstanding/defaults' first."
            )

    monkeypatch.setattr(
        "cu_cli.commands.profile_cmd.build_client",
        lambda *_args, **_kwargs: _Client(),
    )

    result = _run("profile", "sync-defaults", "--name", "dev")

    assert result.exit_code == 1, result.output
    assert "Content Understanding defaults are not configured" in result.output
    assert "No changes were made to CU CLI profile 'dev'" in result.output
    assert "prebuilt-digitalParse, prebuilt-read, prebuilt-layout" in result.output
    assert result.output.index("--models recommended") < result.output.index(
        "cu defaults set"
    )
    assert "cu profile sync-defaults --name dev" in result.output
    assert "PATCH /contentunderstanding/defaults" not in result.output
    assert ProfileStore.load().get_explicit_profile("dev") == {
        "endpoint": endpoint,
    }
