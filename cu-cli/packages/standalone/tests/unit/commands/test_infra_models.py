# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from cu_cli.cli import main
from cu_cli.commands._infra_models import _parse_picker, _prompt_for_models
from cu_cli.core.infra_models import DeployableModel


pytestmark = pytest.mark.unit


def _candidate(name: str, version: str, kind: str) -> DeployableModel:
    return DeployableModel(
        name=name,
        version=version,
        format="OpenAI",
        kind=kind,
        sku_name="GlobalStandard",
        sku_capacity=10,
    )


def test_picker_zero_means_no_models_and_cannot_be_combined():
    candidates = [_candidate("gpt-5.5", "v1", "completion")]
    assert _parse_picker("0", candidates) == []
    with pytest.raises(ValueError, match="cannot be combined"):
        _parse_picker("0,1", candidates)


def test_picker_rejects_two_versions_of_one_family():
    candidates = [
        _candidate("gpt-5.5", "v1", "completion"),
        _candidate("gpt-5.5", "v2", "completion"),
    ]
    with pytest.raises(ValueError, match="one version"):
        _parse_picker("1,2", candidates)


def test_picker_defaults_to_live_recommended_models(monkeypatch):
    candidates = [
        _candidate("gpt-5.5", "v1", "completion"),
        _candidate("text-embedding-3-small", "v1", "embedding"),
    ]

    def fake_prompt(*_args, **kwargs):
        assert kwargs["default"] == "1,2"
        return kwargs["default"]

    monkeypatch.setattr("cu_cli.commands._infra_models.click.prompt", fake_prompt)

    assert _prompt_for_models(candidates) == candidates


def test_hidden_infra_models_none_skips_live_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands._infra_models._client",
        lambda *_args, **_kwargs: pytest.fail("no client expected"),
    )
    target = tmp_path / "models.json"

    result = CliRunner().invoke(main, [
        "_infra-models",
        "--resource-group", "rg-test",
        "--account", "account-test",
        "--subscription", "sub-test",
        "--selection", "none",
        "--out", str(target),
    ])

    assert result.exit_code == 0, result.output
    assert json.loads(target.read_text(encoding="utf-8")) == []
    assert "prebuilt-digitalParse" in result.output
    assert "prebuilt-read" in result.output
    assert "prebuilt-layout" in result.output


def test_hidden_infra_models_discovers_and_deploys_live_model(tmp_path, monkeypatch):
    observed = {}

    class FakeClient:
        def get_analyzer(self, analyzer_id):
            observed["analyzer_id"] = analyzer_id
            return SimpleNamespace(
                supported_models=SimpleNamespace(
                    completion=["gpt-5.5"],
                    embedding=["text-embedding-3-large"],
                )
            )

    monkeypatch.setattr(
        "cu_cli.commands._infra_models._client",
        lambda *_args, **_kwargs: FakeClient(),
    )
    monkeypatch.setattr(
        "cu_cli.commands._infra_models.fetch_account_models",
        lambda resource_group, account_name, subscription_id: [
            {
                "name": "gpt-5.5",
                "version": "2025-12-11",
                "format": "OpenAI",
                "skus": [{"name": "GlobalStandard", "capacity": {"default": 25}}],
            },
            {
                "name": "not-supported-by-cu",
                "version": "1",
                "format": "OpenAI",
                "skus": [{"name": "GlobalStandard"}],
            },
        ],
    )
    monkeypatch.setattr(
        "cu_cli.commands._infra_models.deploy_models",
        lambda resource_group, account_name, subscription_id, models: observed.update(
            resource_group=resource_group,
            account_name=account_name,
            subscription_id=subscription_id,
            models=list(models),
        ),
    )
    target = tmp_path / "models.json"

    result = CliRunner().invoke(main, [
        "_infra-models",
        "--resource-group", "rg-test",
        "--account", "account-test",
        "--subscription", "sub-test",
        "--selection", "gpt-5.5@2025-12-11",
        "--out", str(target),
        "--endpoint", "https://account-test.services.ai.azure.com/",
        "--api-version", "2025-11-01",
    ])

    assert result.exit_code == 0, result.output
    assert observed["analyzer_id"] == "prebuilt-document"
    assert observed["resource_group"] == "rg-test"
    assert observed["subscription_id"] == "sub-test"
    assert [model.name for model in observed["models"]] == ["gpt-5.5"]
    assert json.loads(target.read_text(encoding="utf-8"))[0]["version"] == "2025-12-11"
