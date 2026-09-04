"""Telemetry opt-out is honored.

Covers the PR #4 review: when the user opts out, the ``User-Agent`` prefix must
carry no ``cu-cli`` marker (we send an empty prefix, so azure-core emits only its
standard ``azsdk-python-...`` User-Agent).
"""

from __future__ import annotations

import pytest

from cu_cli import __version__
from cu_cli.telemetry import telemetry_enabled, user_agent



pytestmark = pytest.mark.unit

def test_default_carries_cu_cli_marker():
    # The isolate fixture strips CU_* env, so telemetry defaults to on.
    assert telemetry_enabled() is True
    assert user_agent() == f"cu-cli/{__version__}"


@pytest.mark.parametrize("value", ["off", "0", "false", "no", "OFF", "No", " off "])
def test_opt_out_sends_empty_prefix_without_cu_cli_marker(monkeypatch, value):
    monkeypatch.setenv("CU_TELEMETRY", value)
    assert telemetry_enabled() is False
    assert user_agent() == ""
    assert "cu-cli" not in user_agent()


@pytest.mark.parametrize("value", ["on", "1", "yes", "", "anything"])
def test_non_opt_out_values_keep_marker(monkeypatch, value):
    monkeypatch.setenv("CU_TELEMETRY", value)
    assert telemetry_enabled() is True
    assert user_agent() == f"cu-cli/{__version__}"
