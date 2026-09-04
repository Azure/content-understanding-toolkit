"""Integration tests for the ``doctor`` command and ``defaults show``.

Covers service connectivity checks and reading the CU service defaults
(README scenarios §4 and §5).

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import json

from click.testing import CliRunner
import pytest

from cu_cli.cli import main

from support.recording import use_cassette

pytestmark = pytest.mark.integration


def _run(*args):
    return CliRunner().invoke(main, list(args))


def test_scenario_4_doctor_connectivity(cloud_project):
    with use_cassette("doctor"):
        res = _run("doctor")
    # doctor exits 0 when the service is reachable and checks pass.
    assert res.exit_code == 0, res.output


def test_scenario_4_defaults_show_json(cloud_project):
    """`cu defaults show` reads the CU service defaults."""
    with use_cassette("defaults_get"):
        res = _run("defaults", "show")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output[res.output.find("{"):])
    assert "modelDeployments" in payload
