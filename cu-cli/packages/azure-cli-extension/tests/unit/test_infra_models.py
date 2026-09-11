# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path
from types import SimpleNamespace

import pytest

from azext_content_understanding import _infra_models
from azext_content_understanding._infra_models import DeployableModel
from cu_cli_core.errors import ValidationError

pytestmark = pytest.mark.unit


def _model(name: str, version: str, kind: str, *, default: bool = False) -> DeployableModel:
    return DeployableModel(name, version, "OpenAI", kind, "GlobalStandard", 1, default)


def test_supported_models_accepts_sdk_and_wire_shapes() -> None:
    wire = {"supportedModels": {"completion": ["GPT-5"], "embedding": ["Embedding"]}}

    result = _infra_models._supported_models(wire)

    assert result == {"completion": {"gpt-5"}, "embedding": {"embedding"}}


def test_recommended_prefers_known_default_versions() -> None:
    candidates = [
        _model("gpt-5", "1", "completion", default=True),
        _model("gpt-5", "2", "completion"),
        _model("text-embedding-3-large", "1", "embedding", default=True),
    ]

    selected = _infra_models._recommended(candidates)

    assert [item.selector for item in selected] == ["gpt-5@1", "text-embedding-3-large@1"]


def test_select_requires_version_for_ambiguous_family() -> None:
    candidates = [_model("gpt-5", "1", "completion"), _model("gpt-5", "2", "completion")]

    with pytest.raises(ValidationError, match="multiple deployable versions"):
        _infra_models._select(candidates, ["gpt-5"])


def test_none_writes_empty_model_file_without_clients(tmp_path: Path) -> None:
    output = tmp_path / "infra/models.json"

    result = _infra_models.setup_models(object(), selection="none", out_path=str(output))

    assert output.read_text(encoding="utf-8") == "[]\n"
    assert result == {"models": [], "outputFile": str(output), "deployed": False}


def test_model_setup_deploys_and_configures_service_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    deployed = []
    configured = []

    class Poller:
        def result(self):
            return None

    management = SimpleNamespace(
        accounts=SimpleNamespace(
            list_models=lambda _rg, _account: [
                {
                    "name": "gpt-5",
                    "version": "1",
                    "format": "OpenAI",
                    "isDefaultVersion": True,
                    "skus": [{"name": "GlobalStandard", "capacity": {"default": 1}}],
                }
            ]
        ),
        deployments=SimpleNamespace(
            list=lambda _rg, _account: [],
            begin_create_or_update=lambda *_args: (deployed.append(_args) or Poller()),
        ),
    )
    cu_client = SimpleNamespace(
        get_analyzer=lambda _name: {
            "supportedModels": {"completion": ["gpt-5"], "embedding": []}
        }
    )
    monkeypatch.setattr(_infra_models, "get_subscription_id", lambda _ctx: "sub-id")
    monkeypatch.setattr(_infra_models, "_management_client", lambda _cmd, _sub: management)
    monkeypatch.setattr(
        _infra_models, "create_content_understanding_client", lambda *_args, **_kwargs: cu_client
    )
    monkeypatch.setattr(
        _infra_models,
        "apply_defaults",
        lambda client, mappings, replace: configured.append((client, mappings, replace)),
    )

    result = _infra_models.setup_models(
        SimpleNamespace(cli_ctx=object()),
        selection="recommended",
        out_path=str(tmp_path / "models.json"),
        resource_group="rg",
        account_name="account",
        endpoint="https://example.services.ai.azure.com/",
        deploy=True,
    )

    assert deployed
    assert configured == [(cu_client, {"gpt-5": "gpt-5"}, False)]
    assert result["defaultsConfigured"] is True


def test_deploy_reuses_matching_name_and_version() -> None:
    created = []
    current = SimpleNamespace(
        name="GPT-5",
        properties=SimpleNamespace(
            model=SimpleNamespace(name="gpt-5", version="1")
        ),
    )
    management = SimpleNamespace(
        deployments=SimpleNamespace(
            list=lambda _rg, _account: [current],
            begin_create_or_update=lambda *_args: created.append(_args),
        )
    )

    _infra_models._deploy(management, "rg", "account", [_model("gpt-5", "1", "completion")])

    assert created == []