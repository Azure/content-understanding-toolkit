from __future__ import annotations

from pathlib import Path

import pytest
from cu_cli_core.defaults import with_prebuilt_default_mappings

from cu_cli.profile import Profile, ProfileStore, azure_config_path

pytestmark = pytest.mark.unit


def test_standalone_uses_shared_profile_types():
    assert Profile.__module__ == "cu_cli_core.profiles"
    assert ProfileStore.__module__ == "cu_cli_core.profiles"


def test_isolated_azure_config_is_used():
    path = azure_config_path()

    assert path == Path.home() / ".azure" / "config"
    assert not path.exists()


def test_profile_environment_precedence(monkeypatch: pytest.MonkeyPatch):
    store = ProfileStore.load()
    store.set("endpoint", "https://saved.services.ai.azure.com/")
    store.save()
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.services.ai.azure.com/")

    profile = Profile.load()

    assert profile.endpoint == "https://environment.services.ai.azure.com/"


def test_prebuilt_model_aliases_remain_shared_core_behavior():
    mapped = with_prebuilt_default_mappings(
        {
            "gpt-5.2": "dep-completion",
            "text-embedding-3-large": "dep-embedding",
        }
    )

    assert mapped["prebuilt-analyzer-completion"] == "dep-completion"
    assert mapped["prebuilt-analyzer-embedding"] == "dep-embedding"
