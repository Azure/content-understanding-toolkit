"""Shared pytest fixtures.

Profiles use Azure CLI configuration; these fixtures redirect HOME,
AZURE_CONFIG_DIR, and the cwd so tests never touch developer settings.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original_home = Path.home()
    rec_mode = (os.getenv("CU_TEST_REC_MODE") or "playback").strip().lower()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    isolated_config = home / ".azure" / "config"
    monkeypatch.setattr(
        "cu_cli_core.profiles.azure_config_path",
        lambda: isolated_config,
    )
    # In live/record mode, keep Azure CLI pointed at the real login cache so
    # AzureCliCredential can obtain tokens after `az login`. ProfileStore remains
    # patched to the isolated path above and never mutates the real config.
    if rec_mode in {"live", "record"}:
        monkeypatch.setenv("AZURE_CONFIG_DIR", str(original_home / ".azure"))
    else:
        monkeypatch.setenv("AZURE_CONFIG_DIR", str(home / ".azure"))
    # Strip any CU_* env so tests control precedence explicitly, but preserve
    # the CU_TEST_REC_* recording-harness vars (record/live modes rely on them).
    for key in list(os.environ):
        if key.startswith("CU_TEST_REC_"):
            continue
        if key.startswith("CU_") or key.startswith("CONTENTUNDERSTANDING_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CU_NO_UPDATE_CHECK", "1")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    yield work


@pytest.fixture(autouse=True)
def _fixed_cli_width(monkeypatch: pytest.MonkeyPatch):
    """Pin rich-click rendering so CLI-output assertions are deterministic.

    Rich derives the console width from the real std streams — a TTY locally
    (capped at ``MAX_WIDTH``) but none in CI, where it falls back to 80. That
    changes wrapping, while GitHub Actions forces terminal styling that inserts
    ANSI sequences into captured output. Disable terminal styling and force a
    fixed width so local and CI render identically.
    """
    import rich_click

    monkeypatch.setattr(rich_click.rich_click, "FORCE_TERMINAL", False, raising=False)
    monkeypatch.setattr(rich_click.rich_click, "WIDTH", 100, raising=False)
    monkeypatch.setattr(rich_click.rich_click, "MAX_WIDTH", 100, raising=False)
