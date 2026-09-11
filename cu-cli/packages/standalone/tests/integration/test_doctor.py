# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Integration tests for the ``doctor`` command and ``defaults show``.

Covers service connectivity checks and reading the CU service defaults
(README scenarios §4 and §5).

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from cu_cli.cli import main

from support.recording import use_cassette
from tests.support.doc_snippets import load_doc_snippets, parse_cu_commands

pytestmark = pytest.mark.integration

_PRODUCT_ROOT = Path(__file__).resolve().parents[4]
_DOC_SNIPPETS = load_doc_snippets(
    _PRODUCT_ROOT / "README.md",
    _PRODUCT_ROOT / "docs" / "usage-guide.md",
)


def _run(*args):
    return CliRunner().invoke(main, list(args))


def test_scenario_4_doctor_connectivity(cloud_project):
    commands = parse_cu_commands(_DOC_SNIPPETS["cu_cli_configure_key_profile"])
    for args in commands[:-1]:
        args = [
            "https://example.services.ai.azure.com/"
            if arg == "https://<resource-name>.services.ai.azure.com/"
            else "playback-dummy-key" if arg == "<key>" else arg
            for arg in args
        ]
        res = _run(*args)
        assert res.exit_code == 0, res.output
    with use_cassette("doctor"):
        res = _run(*commands[-1])
    # doctor exits 0 when the service is reachable and checks pass.
    assert res.exit_code == 0, res.output


def test_scenario_4_defaults_show_json(cloud_project):
    """`cu defaults show` reads the CU service defaults."""
    [args] = parse_cu_commands(_DOC_SNIPPETS["cu_cli_show_defaults"])
    with use_cassette("defaults_get"):
        res = _run(*args)
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output[res.output.find("{"):])
    assert "modelDeployments" in payload
