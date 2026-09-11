# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from click.testing import CliRunner
import pytest

from cu_cli.cli import main
from cu_cli_core.postprovision import PostprovisionResult

pytestmark = pytest.mark.unit


def test_versioned_postprovision_command_is_hidden_and_invocable(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands._postprovision._request_from_environment", lambda: object()
    )
    monkeypatch.setattr(
        "cu_cli.commands._postprovision.execute_postprovision",
        lambda request, capabilities: PostprovisionResult(
            succeeded=True, messages=("adapter reached",)
        ),
    )
    runner = CliRunner()

    help_result = runner.invoke(main, ["--help"])
    result = runner.invoke(main, ["_infra-postprovision-v1"])

    assert help_result.exit_code == 0
    assert "_infra-postprovision-v1" not in help_result.output
    assert result.exit_code == 0, result.output
    assert "adapter reached" in result.output
