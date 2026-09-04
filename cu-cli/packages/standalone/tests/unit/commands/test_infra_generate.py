# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cu_cli.cli import main
from cu_cli.commands.infra import AzureAccount

pytestmark = pytest.mark.unit

_runner = CliRunner()
_ACCOUNT = AzureAccount(
    subscription_id="sub-id",
    subscription_name="Development",
    tenant_id="tenant-id",
)


def _run(*args: str):
    return _runner.invoke(main, list(args), color=False)


def test_infra_generate_defaults_to_noninteractive_provision_directory(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda subscription=None: _ACCOUNT,
    )

    def _run_wizard(target: Path, **kwargs):
        captured["target"] = target
        captured.update(kwargs)

    monkeypatch.setattr("cu_cli.commands.infra.run_wizard", _run_wizard)

    result = _run("infra", "generate")

    assert result.exit_code == 0, result.output
    assert captured["target"] == Path("provision").resolve()
    assert captured["interactive"] is False
    assert captured["api_version"] == "2025-11-01"
    assert captured["models"] is None
    assert captured["subscription_id"] == "sub-id"
    assert "cu infra generate" in result.output


def test_infra_generate_passes_custom_output_and_new_resource_options(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}
    checked: list[str | None] = []
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda subscription=None: checked.append(subscription) or _ACCOUNT,
    )
    monkeypatch.setattr(
        "cu_cli.commands.infra.run_wizard",
        lambda target, **kwargs: captured.update(target=target, **kwargs),
    )

    result = _run(
        "infra",
        "generate",
        "--output-dir",
        "infra",
        "--environment",
        "dev-01",
        "--location",
        "westus3",
        "--subscription",
        "Development",
        "--api-version",
        "2026-06-01-preview",
        "--models",
        "gpt-5.2, text-embedding-3-large",
        "--foundry-prefix",
        "contoso-cu",
        "--force",
    )

    assert result.exit_code == 0, result.output
    assert checked == ["Development"]
    assert captured["target"] == Path("infra").resolve()
    assert captured["env"] == "dev-01"
    assert captured["location"] == "westus3"
    assert captured["api_version"] == "2026-06-01-preview"
    assert captured["models"] == ["gpt-5.2", "text-embedding-3-large"]
    assert captured["foundry_account_prefix"] == "contoso-cu"
    assert captured["force"] is True


@pytest.mark.parametrize(
    "models",
    [
        "",
        " ",
        ",",
        "gpt-5.2,",
        ",gpt-5.2",
        "gpt-5.2,,text-embedding-3-large",
    ],
)
def test_infra_generate_rejects_empty_model_entries_before_side_effects(
    models: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda *_args: pytest.fail("Azure must not be queried for invalid models"),
    )
    output_dir = tmp_path / "generated" / "provision"

    result = _run(
        "infra",
        "generate",
        "--models",
        models,
        "--output-dir",
        str(output_dir),
    )

    assert result.exit_code == 2, result.output
    assert "empty" in result.output
    assert "entries are not allowed" in result.output
    assert "--models none" in result.output
    assert not output_dir.parent.exists()


@pytest.mark.parametrize(
    "models",
    [
        "none,gpt-5.2",
        "gpt-5.2,none",
        "recommended,text-embedding-3-large",
        "text-embedding-3-large,recommended",
    ],
)
def test_infra_generate_rejects_special_model_values_in_lists_before_side_effects(
    models: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda *_args: pytest.fail("Azure must not be queried for invalid models"),
    )
    output_dir = tmp_path / "generated" / "provision"

    result = _run(
        "infra",
        "generate",
        "--models",
        models,
        "--output-dir",
        str(output_dir),
    )

    assert result.exit_code == 2, result.output
    assert "'none' and 'recommended' must each be used alone" in result.output
    assert not output_dir.parent.exists()


def test_infra_generate_existing_foundry_uses_resolved_resource_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}
    resolve_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda subscription=None: _ACCOUNT,
    )

    def _resolve(endpoint: str, subscription_id: str):
        resolve_calls.append((endpoint, subscription_id))
        return "foundry-dev", "rg-foundry", "eastus2"

    monkeypatch.setattr(
        "cu_cli.commands.infra._resolve_existing_foundry_account",
        _resolve,
    )
    monkeypatch.setattr(
        "cu_cli.commands.infra.run_wizard",
        lambda target, **kwargs: captured.update(target=target, **kwargs),
    )

    result = _run(
        "infra",
        "generate",
        "--foundry-endpoint",
        "https://foundry-dev.services.ai.azure.com",
        "--models",
        "none",
    )

    assert result.exit_code == 0, result.output
    endpoint = "https://foundry-dev.services.ai.azure.com/"
    assert resolve_calls == [(endpoint, "sub-id")]
    assert captured["foundry_endpoint"] == endpoint
    assert captured["foundry_resource_group"] == "rg-foundry"
    assert captured["location"] == "eastus2"
    assert captured["models"] == ["none"]


def test_infra_generate_explicit_location_overrides_existing_resource_location(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda subscription=None: _ACCOUNT,
    )
    monkeypatch.setattr(
        "cu_cli.commands.infra._resolve_existing_foundry_account",
        lambda *_args: ("foundry-dev", "rg-foundry", "eastus2"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.infra.run_wizard",
        lambda target, **kwargs: captured.update(target=target, **kwargs),
    )

    result = _run(
        "infra",
        "generate",
        "--foundry-endpoint",
        "https://foundry-dev.services.ai.azure.com/",
        "--location",
        "westus3",
    )

    assert result.exit_code == 0, result.output
    assert captured["location"] == "westus3"


def test_infra_generate_rejects_endpoint_with_new_resource_prefix_before_azure_check(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda *_args: pytest.fail("Azure must not be queried for invalid options"),
    )

    result = _run(
        "infra",
        "generate",
        "--foundry-endpoint",
        "https://foundry-dev.services.ai.azure.com/",
        "--foundry-prefix",
        "new-account",
    )

    assert result.exit_code == 1, result.output
    assert "--foundry-prefix cannot be used with --foundry-endpoint" in result.output
    assert not Path("provision").exists()


def test_infra_generate_rejects_malformed_endpoint_before_azure_check(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda *_args: pytest.fail("Azure must not be queried for an invalid endpoint"),
    )

    result = _run(
        "infra",
        "generate",
        "--foundry-endpoint",
        "not-a-url",
        "--models",
        "none",
    )

    assert result.exit_code == 1
    assert "invalid foundry endpoint" in result.output
    assert not Path("provision").exists()


def test_infra_generate_rejects_unsafe_environment_before_azure_check(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda *_args: pytest.fail("Azure must not be queried for an invalid environment"),
    )

    result = _run("infra", "generate", "--environment", "../escape")

    assert result.exit_code == 1, result.output
    assert "invalid azd environment name" in result.output
    assert not Path("escape").exists()


def test_infra_group_exposes_generate_and_removed_commands_are_rejected():
    help_result = _run("--help")
    infra_help_result = _run("infra", "--help")

    assert help_result.exit_code == 0, help_result.output
    assert "infra" in help_result.output
    assert infra_help_result.exit_code == 0, infra_help_result.output
    assert "generate" in infra_help_result.output
    assert "provision" in infra_help_result.output
    assert "│ init " not in help_result.output
    assert _run("init", "--help").exit_code == 2
    assert _run("provision", "--help").exit_code == 2
