from __future__ import annotations

import os
from pathlib import Path

import pytest

from cu_cli_core.errors import ConflictError, NotFoundError, ValidationError
from cu_cli_core.profiles import (
    DEFAULT_PROFILE_NAME,
    Profile,
    ProfileStore,
    azure_config_path,
    normalize_profile_name,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / ".azure" / "config"


def test_azure_config_path_honors_azure_config_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(tmp_path / "az"))

    assert azure_config_path() == tmp_path / "az" / "config"


def test_default_profile_exists_without_a_file(config_path: Path):
    store = ProfileStore.load(config_path)

    assert store.list_names() == [DEFAULT_PROFILE_NAME]
    assert store.get_active_name() == DEFAULT_PROFILE_NAME
    assert store.get_profile() == {}


def test_profile_round_trip_preserves_unrelated_azure_config(config_path: Path):
    original = (
        "# keep this comment\n"
        "[core]\n"
        "output = json\n\n"
        "[cloud]\n"
        "name = AzureCloud\n"
    )
    config_path.parent.mkdir()
    config_path.write_text(original, encoding="utf-8")
    store = ProfileStore.load(config_path)
    store.set("endpoint", "https://default.example/")
    store.create_name("dev")
    store.set("endpoint", "https://dev.example/", name="dev")
    store.set("model_deployments.gpt-5.2", "gpt-prod", name="dev")
    store.set_active_name("dev")

    store.save()

    written = config_path.read_text(encoding="utf-8")
    assert written.startswith(original)
    assert "[cu]\n" in written
    assert "active_profile = dev\n" in written
    assert "default.endpoint = https://default.example/\n" in written
    assert "dev.model_deployments.gpt-5.2 = gpt-prod\n" in written
    if os.name != "nt":
        assert config_path.stat().st_mode & 0o777 == 0o600


def test_profile_update_replaces_only_existing_cu_section(config_path: Path):
    config_path.parent.mkdir()
    config_path.write_text(
        "[core]\n# preserved\noutput = table\n\n"
        "[cu]\n# replaced CU comment\nold = ignored\n\n"
        "[extension]\nfoo = bar\n",
        encoding="utf-8",
    )
    store = ProfileStore.load(config_path)
    store.set("api_version", "2026-06-01-preview")

    store.save()

    written = config_path.read_text(encoding="utf-8")
    assert "[core]\n# preserved\noutput = table\n\n" in written
    assert "[extension]\nfoo = bar\n" in written
    assert "old = ignored" in written
    assert "default.api_version = 2026-06-01-preview" in written


def test_named_profile_inherits_base_settings_but_not_default_profile(config_path: Path):
    config_path.parent.mkdir()
    config_path.write_text(
        "[cu]\n"
        "api_version = 2026-06-01-preview\n"
        "auth_mode = login\n"
        "default.endpoint = https://default.example/\n"
        "dev._created = true\n"
        "dev.endpoint = https://dev.example/\n",
        encoding="utf-8",
    )

    store = ProfileStore.load(config_path)

    assert store.get_profile("dev") == {
        "api_version": "2026-06-01-preview",
        "auth_mode": "login",
        "endpoint": "https://dev.example/",
    }


def test_profile_resolution_applies_environment_last(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path.parent.mkdir()
    config_path.write_text(
        "[cu]\n"
        "api_version = 2026-06-01-preview\n"
        "dev.endpoint = https://saved.example/\n"
        "dev.auth_mode = login\n"
        "dev.model_deployments.gpt-5.2 = saved-gpt\n"
        "active_profile = dev\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.example/")
    monkeypatch.setenv("CU_API_KEY", "secret")
    monkeypatch.setenv("GPT_5_2_DEPLOYMENT", "environment-gpt")

    profile = Profile.load(path=config_path)

    assert profile.profile_name == "dev"
    assert profile.endpoint == "https://environment.example/"
    assert profile.auth_mode == "key"
    assert profile.api_key == "secret"
    assert profile.api_version == "2026-06-01-preview"
    assert profile.model_deployments["gpt-5.2"] == "environment-gpt"
    assert profile.to_public_dict()["api_key"] == "***redacted***"


def test_setting_api_key_selects_key_auth_and_unsetting_restores_login(config_path: Path):
    store = ProfileStore.load(config_path)
    store.set("api_key", "secret")

    assert store.get("api_key") == "secret"
    assert store.get("auth_mode") == "key"

    assert store.unset("api_key")
    assert store.get("api_key") is None
    assert store.get("auth_mode") == "login"


def test_empty_named_profile_can_be_created_saved_and_reloaded(config_path: Path):
    store = ProfileStore.load(config_path)
    store.create_name("dev")
    store.save()

    reloaded = ProfileStore.load(config_path)

    assert reloaded.has_name("dev")
    assert reloaded.get_profile("dev") == {}


def test_copy_uses_explicit_values_and_rename_updates_active(config_path: Path):
    store = ProfileStore.load(config_path)
    store.create_name("dev")
    store.set("endpoint", "https://dev.example/", name="dev")
    store.copy_name("dev", "test")
    store.set_active_name("test")
    store.rename_name("test", "prod")

    assert store.get_active_name() == "prod"
    assert store.get_profile("prod")["endpoint"] == "https://dev.example/"


def test_active_profile_cannot_be_deleted(config_path: Path):
    store = ProfileStore.load(config_path)
    store.create_name("dev")
    store.set_active_name("dev")

    with pytest.raises(ConflictError, match="cannot delete active"):
        store.delete_name("dev")


def test_missing_profile_is_reported(config_path: Path):
    store = ProfileStore.load(config_path)

    with pytest.raises(NotFoundError, match="was not found"):
        store.get_profile("missing")


@pytest.mark.parametrize(
    "name",
    [
        "default",
        "Default",
        "model_deployments",
        "MODEL_DEPLOYMENTS",
        "-dev",
        "dev-",
        "dev.profile",
        "contains space",
        "x" * 65,
    ],
)
def test_mutable_profile_name_validation(name: str):
    with pytest.raises(ValidationError, match="invalid profile name"):
        normalize_profile_name(name)


@pytest.mark.parametrize(
    "key",
    [
        "model_deployments.",
        "model_deployments. gpt-5.2",
        "model_deployments.gpt=5.2",
        "model_deployments.gpt:5.2",
        "model_deployments.gpt/5.2",
    ],
)
def test_invalid_model_deployment_key_is_rejected(config_path: Path, key: str):
    store = ProfileStore.load(config_path)

    with pytest.raises(ValidationError, match="invalid model deployment key"):
        store.set(key, "deployment")


def test_model_deployment_key_round_trips(config_path: Path):
    store = ProfileStore.load(config_path)
    store.set("model_deployments.gpt-5.2_mini", "deployment")
    store.save()

    reloaded = ProfileStore.load(config_path)

    assert reloaded.get("model_deployments.gpt-5.2_mini") == "deployment"


def test_save_detects_concurrent_modification(config_path: Path):
    first = ProfileStore.load(config_path)
    second = ProfileStore.load(config_path)
    first.set("endpoint", "https://first.example/")
    first.save()
    second.set("endpoint", "https://second.example/")

    with pytest.raises(ConflictError, match="changed after it was loaded"):
        second.save()


def test_invalid_azure_config_is_not_overwritten(config_path: Path):
    config_path.parent.mkdir()
    config_path.write_text("[broken\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="not valid INI"):
        ProfileStore.load(config_path)

    assert config_path.read_text(encoding="utf-8") == "[broken\n"


def test_import_does_not_create_azure_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    azure_dir = tmp_path / ".azure"
    monkeypatch.setenv("AZURE_CONFIG_DIR", str(azure_dir))

    __import__("cu_cli_core.profiles")

    assert not azure_dir.exists()
    assert not os.path.exists(azure_dir / "config")
