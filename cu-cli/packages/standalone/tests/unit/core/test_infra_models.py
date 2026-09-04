import json
from types import SimpleNamespace

import pytest

from cu_cli.core.infra_models import (
    DeployableModel,
    deploy_models,
    deployable_models,
    fetch_account_models,
    recommended_models,
    select_requested_models,
    supported_model_names,
    write_models_file,
)
from cu_cli.errors import CuCliError


pytestmark = pytest.mark.unit


def _candidate(
    name: str,
    version: str,
    kind: str,
    sku_name: str = "GlobalStandard",
    sku_capacity: int = 10,
    is_default_version: bool = False,
) -> DeployableModel:
    return DeployableModel(
        name=name,
        version=version,
        format="OpenAI",
        kind=kind,
        sku_name=sku_name,
        sku_capacity=sku_capacity,
        is_default_version=is_default_version,
    )


def test_supported_model_names_accepts_sdk_object_and_dict():
    sdk_analyzer = SimpleNamespace(
        supported_models=SimpleNamespace(
            completion=["GPT-5.5"],
            embedding=["text-embedding-3-large"],
        )
    )
    assert supported_model_names(sdk_analyzer) == {
        "completion": {"gpt-5.5"},
        "embedding": {"text-embedding-3-large"},
    }
    assert supported_model_names({
        "supportedModels": {
            "completion": ["gpt-5.4"],
            "embedding": [],
        }
    }) == {
        "completion": {"gpt-5.4"},
        "embedding": set(),
    }


def test_supported_model_names_rejects_missing_metadata():
    with pytest.raises(CuCliError, match="did not return supportedModels"):
        supported_model_names({})


def test_fetch_account_models_scopes_azure_cli_to_subscription(monkeypatch):
    calls = []

    def fake_run(args, **_kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr("cu_cli.core.infra_models.subprocess.run", fake_run)

    assert fetch_account_models("rg-test", "account-test", "sub-test") == []
    assert calls[0][calls[0].index("--subscription") + 1] == "sub-test"


def test_deployable_models_intersects_live_cu_and_arm_catalogs():
    supported = {
        "completion": {"gpt-5.5"},
        "embedding": {"text-embedding-3-large"},
    }
    arm = [
        {
            "name": "gpt-5.5",
            "version": "2025-12-11",
            "format": "OpenAI",
            "skus": [
                {"name": "Standard", "capacity": {"default": 5}},
                {"name": "GlobalStandard", "capacity": {"default": 20}},
            ],
        },
        {
            "name": "gpt-not-supported-by-cu",
            "version": "1",
            "format": "OpenAI",
            "skus": [{"name": "GlobalStandard"}],
        },
        {
            "name": "text-embedding-3-large",
            "version": "1",
            "format": "OpenAI",
            "skus": [{"name": "DataZoneStandard", "capacity": {"default": 30}}],
        },
    ]

    models = deployable_models(arm, supported)

    assert [model.name for model in models] == ["gpt-5.5", "text-embedding-3-large"]
    assert models[0].sku_name == "GlobalStandard"
    assert models[0].sku_capacity == 20
    assert models[1].kind == "embedding"


def test_requested_model_requires_version_when_multiple_are_available():
    candidates = [
        _candidate("gpt-5.5", "v1", "completion"),
        _candidate("gpt-5.5", "v2", "completion"),
    ]
    with pytest.raises(CuCliError, match="multiple deployable versions"):
        select_requested_models(candidates, ["gpt-5.5"])
    assert select_requested_models(candidates, ["gpt-5.5@v2"]) == [candidates[1]]


def test_recommended_models_uses_live_candidates():
    candidates = [
        _candidate("gpt-5.2", "2025-12-11", "completion"),
        _candidate("gpt-5.5", "2025-12-11", "completion"),
        _candidate("text-embedding-3-large", "1", "embedding"),
    ]
    selected = recommended_models(candidates)
    assert [model.name for model in selected] == [
        "gpt-5.2",
        "text-embedding-3-large",
    ]


def test_recommended_models_uses_arm_default_version():
    candidates = [
        _candidate("gpt-5.2", "old", "completion"),
        _candidate("gpt-5.2", "current", "completion", is_default_version=True),
    ]
    assert recommended_models(candidates) == [candidates[1]]


def test_recommended_models_rejects_ambiguous_versions():
    candidates = [
        _candidate("gpt-5.2", "v1", "completion"),
        _candidate("gpt-5.2", "v2", "completion"),
    ]
    with pytest.raises(CuCliError, match="multiple deployable versions"):
        recommended_models(candidates)


def test_write_models_file_is_bicep_shape(tmp_path):
    target = tmp_path / "infra" / "models.json"
    model = _candidate("gpt-5.5", "2025-12-11", "completion", sku_capacity=25)

    write_models_file(target, [model])

    assert json.loads(target.read_text(encoding="utf-8")) == [{
        "name": "gpt-5.5",
        "model": "gpt-5.5",
        "version": "2025-12-11",
        "format": "OpenAI",
        "skuName": "GlobalStandard",
        "skuCapacity": 25,
    }]


def test_deploy_models_uses_live_version_and_sku(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        stdout = "[]" if "list" in args else ""
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("cu_cli.core.infra_models.subprocess.run", fake_run)
    deploy_models("rg-test", "account-test", "sub-test", [
        _candidate("gpt-5.5", "2025-12-11", "completion", sku_capacity=25)
    ])

    args = calls[1][0]
    assert args[:5] == ["az", "cognitiveservices", "account", "deployment", "create"]
    assert args[args.index("--model-version") + 1] == "2025-12-11"
    assert args[args.index("--sku-capacity") + 1] == "25"
    assert args[args.index("--subscription") + 1] == "sub-test"


def test_deploy_models_surfaces_azure_failure(monkeypatch):
    calls = 0

    def fake_run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return SimpleNamespace(returncode=0, stdout="[]", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="quota exceeded")

    monkeypatch.setattr("cu_cli.core.infra_models.subprocess.run", fake_run)
    with pytest.raises(CuCliError, match="quota exceeded"):
        deploy_models("rg-test", "account-test", "sub-test", [
            _candidate("gpt-5.5", "2025-12-11", "completion")
        ])


def test_deploy_models_never_replaces_existing_deployment(monkeypatch):
    existing = [{
        "name": "gpt-5.5",
        "properties": {"model": {"name": "gpt-5.5", "version": "old"}},
    }]
    monkeypatch.setattr(
        "cu_cli.core.infra_models.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout=json.dumps(existing), stderr=""
        ),
    )
    with pytest.raises(CuCliError, match="already exists"):
        deploy_models("rg-test", "account-test", "sub-test", [
            _candidate("gpt-5.5", "new", "completion")
        ])
