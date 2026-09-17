# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Integration-test fixtures (cloud-gated: playback / record / live).

The universal fixtures (_isolate_env, _fixed_cli_width) are inherited from the
top-level conftest.py and apply automatically here too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from support.recording import mode, write_cloud_profile


@pytest.fixture
def cloud_project(monkeypatch: pytest.MonkeyPatch):
    """cwd with a cloud-ready profile and instant playback-only LRO polling.

    Used by the record/playback cloud-gated tests. In playback mode the profile
    uses a dummy key + placeholder endpoint (no network, no Entra token fetch).
    """
    if mode() == "playback":
        monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)
    write_cloud_profile(Path.cwd())
    return Path.cwd()
