# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from click.testing import CliRunner
import pytest
from types import SimpleNamespace

from cu_cli.cli import main
from cu_cli.commands import _postprovision
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


def test_get_account_key_rejects_missing_azure_cli(monkeypatch):
    monkeypatch.setattr(_postprovision.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="was not found"):
        _postprovision._StandaloneCapabilities().get_account_key(SimpleNamespace())


def test_get_account_key_rejects_failed_login(monkeypatch):
    monkeypatch.setattr(_postprovision.shutil, "which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr(
        _postprovision,
        "_run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="login"),
    )

    with pytest.raises(RuntimeError, match="not logged in"):
        _postprovision._StandaloneCapabilities().get_account_key(
            SimpleNamespace(subscription_id="sub-id")
        )


def test_get_account_key_rejects_failed_key_retrieval(monkeypatch):
    results = iter([
        SimpleNamespace(returncode=0, stdout="{}", stderr=""),
        SimpleNamespace(returncode=1, stdout="", stderr="forbidden"),
    ])
    monkeypatch.setattr(_postprovision.shutil, "which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr(_postprovision, "_run", lambda *_args, **_kwargs: next(results))

    with pytest.raises(RuntimeError, match="could not obtain"):
        _postprovision._StandaloneCapabilities().get_account_key(
            SimpleNamespace(
                subscription_id="sub-id",
                resource_group="rg",
                account_name="account",
            )
        )
