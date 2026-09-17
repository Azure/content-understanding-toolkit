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

import pytest

from support.command_catalog import invoke_cli, record_output
from support.recording import use_cassette

pytestmark = pytest.mark.integration


def _run(*args):
    return invoke_cli(args)


def test_scenario_4_doctor_connectivity(cloud_project):
    with use_cassette("doctor"):
        res = _run("doctor")
    # doctor exits 0 when the service is reachable and checks pass.
    assert res.exit_code == 0, res.output


@pytest.mark.parametrize("table_output", [False, True], ids=["json", "table"])
def test_scenario_4_defaults_show_json(cloud_project, table_output):
    """`cu defaults show` reads the CU service defaults."""
    with use_cassette("defaults_get"):
        if table_output:
            # region Snippet:defaults_table
            res = _run("defaults", "show", "--table")
            # endregion
        else:
            # region Snippet:defaults_show
            res = _run("defaults", "show")
            # endregion
    assert res.exit_code == 0, res.output
    if table_output:
        assert "Model" in res.stdout and "Deployment" in res.stdout
    else:
        payload = json.loads(res.stdout)
        assert payload["modelDeployments"]
        # region Snippet:defaults_json_output
        record_output(res.stdout, language="json")
        # endregion
