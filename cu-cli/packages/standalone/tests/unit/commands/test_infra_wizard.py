# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import sys

import pytest

from cu_cli.commands._infra_wizard import (
    CU_REGION_SUPPORT_URL,
    InfraChoices,
    _merge_azd_env,
    _prompt_location,
    _print_next_steps,
    _resolve_choices,
    _render_azd_env,
    _resolve_model_selection,
    _safe_env_directory,
    _validate_azd_environment_name,
    _validate_foundry_account_prefix,
    _write_template,
)
from cu_cli.errors import CuCliError
from cu_cli.output import console



pytestmark = pytest.mark.unit


def _choices(model_selection: str = "prompt") -> InfraChoices:
    return InfraChoices(
        env="dev",
        location="westus",
        api_version="2025-11-01",
        subscription_id="00000000-0000-0000-0000-000000000001",
        subscription_name="CU Test",
        tenant_id="00000000-0000-0000-0000-000000000002",
        foundry_account_prefix=None,
        foundry_endpoint="https://mmi-sample-foundry-west-us.services.ai.azure.com/",
        foundry_resource_group="mmi-sample-vendors",
        model_selection=model_selection,
        assign_roles=False,
        force_profile_setup=False,
    )


def test_prompt_location_includes_region_support_link(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands._infra_wizard.click.prompt",
        lambda *_args, **_kwargs: "westus3",
    )

    with console.capture() as capture:
        location = _prompt_location()

    assert location == "westus3"
    assert CU_REGION_SUPPORT_URL in "".join(capture.get().split())


def test_invalid_location_error_includes_region_support_link():
    with pytest.raises(CuCliError) as exc_info:
        _resolve_choices(
            interactive=False,
            env="dev",
            location="westus2",
            api_version="2025-11-01",
            subscription_id="sub-id",
            subscription_name="Development",
            tenant_id="tenant-id",
            foundry_account_prefix=None,
            foundry_endpoint=None,
            foundry_resource_group=None,
            models=["none"],
            assign_roles=False,
            force_profile_setup=False,
        )

    assert CU_REGION_SUPPORT_URL in (exc_info.value.hint or "")


def test_write_template_reuses_existing_template_for_new_env(tmp_path):
    target = tmp_path / "provision"
    (target / "infra").mkdir(parents=True)
    (target / "azure.yaml").write_text("name: test\n", encoding="utf-8")
    (target / "infra" / "main.bicep").write_text("targetScope = 'subscription'\n", encoding="utf-8")
    (target / "keep.txt").write_text("do not touch\n", encoding="utf-8")

    choices = _choices("recommended")
    choices.env = "westus"
    _write_template(target, choices, force=False)

    assert (target / ".azure" / "westus" / ".env").exists()
    assert (target / "keep.txt").read_text(encoding="utf-8") == "do not touch\n"


def test_generated_template_assigns_only_cognitive_services_user(tmp_path):
    target = tmp_path / "provision"

    _write_template(target, _choices("none"), force=False)

    foundry_bicep = (target / "infra" / "modules" / "foundry.bicep").read_text(
        encoding="utf-8"
    )
    assert "a97b65f3-24c7-4388-baec-2e87135dc908" in foundry_bicep
    assert "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd" not in foundry_bicep
    assert "64702f94-c441-49e6-a78b-ef80e0188fee" not in foundry_bicep


def test_write_template_preserves_existing_azd_state_without_force(tmp_path):
    target = tmp_path / "provision"
    (target / "infra").mkdir(parents=True)
    (target / "azure.yaml").write_text("name: test\n", encoding="utf-8")
    (target / "infra" / "main.bicep").write_text(
        "targetScope = 'subscription'\n", encoding="utf-8"
    )
    env_dir = target / ".azure" / "dev"
    env_dir.mkdir(parents=True)
    (env_dir / ".env").write_text(
        '# azd state\n'
        'AZURE_ENV_NAME="old"\n'
        'AZURE_LOCATION="old-location"\n'
        'FOUNDRY_RESOURCE_PREFIX="old-prefix"\n'
        'FOUNDRY_EXISTING_ENDPOINT="https://old.example.com/"\n'
        'FOUNDRY_EXISTING_RESOURCE_GROUP="old-rg"\n'
        'AZD_ASSIGN_ROLES="true"\n'
        'CU_AUTOCONFIG="false"\n'
        'CU_MODEL_SETUP_COMPLETE="true"\n'
        'AZURE_SUBSCRIPTION_ID="old-sub-id"\n'
        'AZURE_TENANT_ID="old-tenant-id"\n'
        'CUSTOM_VALUE="left=right"\n',
        encoding="utf-8",
    )
    config_path = target / ".azure" / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": 1,
                "defaultEnvironment": "old",
                "customProperty": {"keep": True},
            }
        ),
        encoding="utf-8",
    )
    choices = _choices("recommended")
    choices.location = "eastus2"

    _write_template(target, choices, force=False)

    env_text = (env_dir / ".env").read_text(encoding="utf-8")
    assert "# azd state\n" in env_text
    assert f'AZURE_SUBSCRIPTION_ID="{choices.subscription_id}"\n' in env_text
    assert f'AZURE_TENANT_ID="{choices.tenant_id}"\n' in env_text
    assert 'CUSTOM_VALUE="left=right"\n' in env_text
    assert 'CU_MODEL_SETUP_COMPLETE="true"\n' in env_text
    for assignment in _render_azd_env(choices).splitlines():
        if assignment.startswith("CU_MODEL_SETUP_COMPLETE="):
            continue
        assert env_text.count(assignment) == 1
    for stale_value in (
        "old-location",
        "old-prefix",
        "https://old.example.com/",
        "old-rg",
    ):
        assert stale_value not in env_text
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config == {
        "version": 1,
        "defaultEnvironment": "dev",
        "customProperty": {"keep": True},
    }


def test_write_template_force_replaces_existing_azd_state(tmp_path):
    target = tmp_path / "provision"
    env_dir = target / ".azure" / "dev"
    env_dir.mkdir(parents=True)
    (env_dir / ".env").write_text('CUSTOM_VALUE="remove-me"\n', encoding="utf-8")
    config_path = target / ".azure" / "config.json"
    config_path.write_text(
        json.dumps({"version": 1, "customProperty": True}),
        encoding="utf-8",
    )

    _write_template(target, _choices("recommended"), force=True)

    assert "CUSTOM_VALUE" not in (env_dir / ".env").read_text(encoding="utf-8")
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "version": 1,
        "defaultEnvironment": "dev",
    }


def test_write_template_rejects_malformed_azd_config_before_writing(tmp_path):
    target = tmp_path / "provision"
    (target / "infra").mkdir(parents=True)
    (target / "azure.yaml").write_text("name: original\n", encoding="utf-8")
    models_path = target / "infra" / "models.json"
    models_path.write_text('{"original": true}\n', encoding="utf-8")
    (target / "infra" / "main.bicep").write_text(
        "targetScope = 'subscription'\n", encoding="utf-8"
    )
    env_dir = target / ".azure" / "dev"
    env_dir.mkdir(parents=True)
    env_path = env_dir / ".env"
    env_path.write_text('CUSTOM_VALUE="keep-me"\n', encoding="utf-8")
    config_path = target / ".azure" / "config.json"
    config_path.write_text("{ invalid", encoding="utf-8")
    before = {
        path: path.read_bytes()
        for path in (target / "azure.yaml", models_path, env_path, config_path)
    }

    with pytest.raises(CuCliError, match="could not read existing azd config"):
        _write_template(target, _choices("recommended"), force=False)

    assert {path: path.read_bytes() for path in before} == before


def test_write_template_rerun_preserves_azd_outputs_and_model_setup_state(tmp_path):
    target = tmp_path / "provision"
    choices = _choices("recommended")
    _write_template(target, choices, force=False)
    env_path = target / ".azure" / "dev" / ".env"
    env_path.write_text(
        env_path.read_text(encoding="utf-8")
        .replace('CU_MODEL_SETUP_COMPLETE="false"', 'CU_MODEL_SETUP_COMPLETE="true"')
        + 'FOUNDRY_ENDPOINT="https://created.services.ai.azure.com/"\n'
        + 'AZURE_RESOURCE_GROUP="rg-created"\n',
        encoding="utf-8",
    )

    choices.location = "eastus"
    _write_template(target, choices, force=False)

    env = env_path.read_text(encoding="utf-8")
    assert 'AZURE_LOCATION="eastus"' in env
    assert 'CU_MODEL_SETUP_COMPLETE="true"' in env
    assert 'FOUNDRY_ENDPOINT="https://created.services.ai.azure.com/"' in env
    assert 'AZURE_RESOURCE_GROUP="rg-created"' in env
    assert json.loads((target / "infra" / "models.json").read_text(encoding="utf-8")) == []


def test_write_template_rejects_non_template_non_empty_dir(tmp_path):
    target = tmp_path / "provision"
    target.mkdir(parents=True)
    (target / "random.txt").write_text("x\n", encoding="utf-8")
    choices = _choices("recommended")

    with pytest.raises(CuCliError) as exc:
        _write_template(target, choices, force=False)
    assert "already exists and is non-empty" in exc.value.message


def test_write_template_rejects_unsafe_env_before_writing(tmp_path):
    target = tmp_path / "provision"
    choices = _choices("recommended")
    choices.env = "../outside"

    with pytest.raises(CuCliError, match="invalid azd environment name"):
        _write_template(target, choices, force=False)

    assert not target.exists()
    assert not (tmp_path / "outside").exists()


def test_safe_env_directory_rejects_azure_symlink(tmp_path):
    target = tmp_path / "provision"
    outside = tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    (target / ".azure").symlink_to(outside, target_is_directory=True)

    with pytest.raises(CuCliError, match="outside provision/.azure"):
        _safe_env_directory(target, "dev")


def test_write_template_starts_bare_and_defers_live_model_setup(tmp_path):
    target = tmp_path / "provision"
    _write_template(target, _choices("prompt"), force=False)

    assert json.loads((target / "infra" / "models.json").read_text(encoding="utf-8")) == []
    env = (target / ".azure" / "dev" / ".env").read_text(encoding="utf-8")
    assert 'CU_MODEL_SELECTION="prompt"' in env
    assert 'CU_MODEL_SETUP_COMPLETE="false"' in env
    posix_hook = (target / "hooks" / "postprovision.sh").read_text(encoding="utf-8")
    windows_hook = (target / "hooks" / "postprovision.ps1").read_text(encoding="utf-8")
    assert "prebuilt-document" not in posix_hook
    assert "_infra-models" in posix_hook
    assert "_infra-models" in windows_hook
    assert '--subscription "$subscription_id"' in posix_hook
    assert "--subscription $subscriptionId" in windows_hook
    assert "az account set" not in posix_hook
    assert "az account set" not in windows_hook
    azure_yaml = (target / "azure.yaml").read_text(encoding="utf-8")
    assert "continueOnError: false" in azure_yaml
    assert "continueOnError: true" not in azure_yaml


def test_print_next_steps_defers_model_free_guidance_to_postprovision_hook(tmp_path):
    choices = _choices("none")
    choices.foundry_endpoint = None
    choices.foundry_resource_group = None
    with console.capture() as capture:
        _print_next_steps(tmp_path / "my-project", choices)

    output = " ".join(capture.get().split())
    assert "azd up" in output
    assert "provisions a Microsoft Foundry resource without model deployments" in output
    assert "post-provision hook prints verified Content Understanding setup" in output
    assert "prebuilt-" not in output


def test_print_next_steps_only_instructs_user_through_azd_up(tmp_path):
    choices = _choices("prompt")
    choices.foundry_endpoint = None
    choices.foundry_resource_group = None
    with console.capture() as capture:
        _print_next_steps(tmp_path / "provision", choices)

    output = " ".join(capture.get().split())
    assert "cd " in output
    assert "azd auth login" in output
    assert "azd up" in output
    assert (
        "provisions a Microsoft Foundry resource, optionally deploys selected "
        "supported LLMs and embeddings models, and configures Content Understanding "
        "defaults"
    ) in output
    assert "sample_invoice.pdf" not in output
    assert "cu analyze" not in output


def test_print_next_steps_quotes_output_path_with_spaces(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    choices = _choices("none")

    with console.capture() as capture:
        _print_next_steps(tmp_path / "provision output", choices)

    expected = (
        'cd "provision output"'
        if sys.platform == "win32"
        else "cd 'provision output'"
    )
    assert expected in capture.get()


def test_print_next_steps_explains_when_explicit_models_are_validated(tmp_path):
    choices = _choices("gpt-5.2,text-embedding-3-large")

    with console.capture() as capture:
        _print_next_steps(tmp_path / "provision", choices)

    output = " ".join(capture.get().split())
    assert "validated against the live CU-supported model catalog during azd up" in output
    assert "after the Microsoft Foundry resource is available" in output


# --- pure helpers ----------------------------------------------------------


def test_validate_foundry_account_prefix_normalizes_and_allows_blank():
    assert _validate_foundry_account_prefix("") is None
    assert _validate_foundry_account_prefix("   ") is None
    assert _validate_foundry_account_prefix("MyPrefix") == "myprefix"
    assert _validate_foundry_account_prefix("abc-123") == "abc-123"


def test_validate_foundry_account_prefix_rejects_invalid():
    with pytest.raises(CuCliError):
        _validate_foundry_account_prefix("a" * 21)
    with pytest.raises(CuCliError):
        _validate_foundry_account_prefix("-abc")
    with pytest.raises(CuCliError):
        _validate_foundry_account_prefix("abc-")
    with pytest.raises(CuCliError):
        _validate_foundry_account_prefix("abc_def")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("dev", "dev"),
        (" Feature_01 ", "feature_01"),
        ("Release.(Canary)-2", "release.(canary)-2"),
        ("a" * 64, "a" * 64),
    ],
)
def test_validate_azd_environment_name_normalizes_valid_names(raw, expected):
    assert _validate_azd_environment_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " ",
        ".",
        "..",
        "../escape",
        r"..\escape",
        "nested/env",
        r"nested\env",
        "/absolute",
        r"C:\absolute",
        r"\\server\share",
        "control\nname",
        "a" * 65,
        "colon:name",
    ],
)
def test_validate_azd_environment_name_rejects_unsafe_names(raw):
    with pytest.raises(CuCliError, match="invalid azd environment name"):
        _validate_azd_environment_name(raw)


def test_resolve_model_selection_deferred_modes():
    assert _resolve_model_selection(None, interactive=True) == "prompt"
    assert _resolve_model_selection(None, interactive=False) == "recommended"
    assert _resolve_model_selection(["gpt-5.2", "text-embedding-3-large"],
                                    interactive=False) == (
        "gpt-5.2,text-embedding-3-large"
    )


def test_resolve_model_selection_accepts_none_alone():
    assert _resolve_model_selection(["NoNe"], interactive=True) == "none"


def test_resolve_model_selection_rejects_none_with_models():
    with pytest.raises(CuCliError, match="cannot be combined"):
        _resolve_model_selection(["none", "gpt-5.2"], interactive=False)


def test_render_azd_env_contains_resolved_choices():
    choices = _choices("prompt")
    choices.env = "dev"
    choices.location = "westus"
    text = _render_azd_env(choices)
    assert 'AZURE_ENV_NAME="dev"' in text
    assert 'AZURE_LOCATION="westus"' in text
    assert f'AZURE_SUBSCRIPTION_ID="{choices.subscription_id}"' in text
    assert f'AZURE_TENANT_ID="{choices.tenant_id}"' in text
    assert 'CU_API_VERSION="2025-11-01"' in text
    assert 'CU_MODEL_SELECTION="prompt"' in text
    assert 'CU_MODEL_SETUP_COMPLETE="false"' in text
    assert 'FOUNDRY_EXISTING_ENDPOINT="https://mmi-sample-foundry-west-us.services.ai.azure.com/"' in text
    assert 'CU_PROFILE_SETUP_FORCE="false"' in text
    assert 'AZD_ASSIGN_ROLES="false"' in text


def test_merge_azd_env_preserves_unknown_content_and_deduplicates_managed_keys():
    choices = _choices("recommended")
    choices.location = "eastus2"
    existing = (
        "# keep this comment\r\n"
        'export AZURE_LOCATION="old"\r\n'
        'CU_MODEL_SETUP_COMPLETE="true"\r\n'
        'CUSTOM_VALUE="left=right"\r\n'
        "\r\n"
        'AZURE_LOCATION="duplicate"\r\n'
    )

    merged = _merge_azd_env(existing, choices)

    assert "# keep this comment\r\n" in merged
    assert 'CUSTOM_VALUE="left=right"\r\n' in merged
    assert "\r\n\r\n" in merged
    assert merged.count("AZURE_LOCATION=") == 1
    assert 'AZURE_LOCATION="eastus2"\r\n' in merged
    assert 'CU_MODEL_SETUP_COMPLETE="true"\r\n' in merged
    for key in (
        "AZURE_ENV_NAME",
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_TENANT_ID",
        "CU_API_VERSION",
        "CU_MODEL_SELECTION",
        "CU_MODEL_SETUP_COMPLETE",
        "FOUNDRY_RESOURCE_PREFIX",
        "FOUNDRY_EXISTING_ENDPOINT",
        "FOUNDRY_EXISTING_RESOURCE_GROUP",
        "AZD_ASSIGN_ROLES",
        "CU_PROFILE_SETUP_FORCE",
    ):
        assert merged.count(f"{key}=") == 1
