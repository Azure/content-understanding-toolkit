# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import zipfile
from pathlib import Path

import pytest

from cu_cli_core.infra import (
    AzureAccount,
    InfraChoices,
    iter_template_files,
    materialize_project,
    normalize_model_selection,
    template_root,
)

pytestmark = pytest.mark.unit


def _choices() -> InfraChoices:
    return InfraChoices(
        environment="dev",
        location="eastus2",
        api_version="2025-11-01",
        account=AzureAccount("sub-id", "Development", "tenant-id"),
        foundry_prefix=None,
        foundry_endpoint=None,
        foundry_resource_group=None,
        model_selection="recommended",
    )


def test_model_selection_supports_standalone_prompt_default() -> None:
    assert normalize_model_selection(None, prompt_when_unspecified=True) == "prompt"
    assert normalize_model_selection(None) == "recommended"
    assert normalize_model_selection(["GPT-5.2", " text-embedding-3-large "]) == (
        "GPT-5.2,text-embedding-3-large"
    )


def test_materialization_is_deterministic_and_preserves_state(tmp_path: Path) -> None:
    target = tmp_path / "provision"
    files, reused = materialize_project(target, _choices(), force=False)
    assert not reused
    assert files == sorted(files)
    env_path = target / ".azure/dev/.env"
    env_path.write_text(
        env_path.read_text(encoding="utf-8")
        .replace('CU_MODEL_SETUP_COMPLETE="false"', 'CU_MODEL_SETUP_COMPLETE="true"')
        + 'CUSTOM="keep"\n',
        encoding="utf-8",
    )
    (target / ".azure/config.json").write_text(
        '{"version": 1, "custom": true}\n', encoding="utf-8"
    )

    _, reused = materialize_project(target, _choices(), force=False)

    assert reused
    assert 'CU_MODEL_SETUP_COMPLETE="true"' in env_path.read_text(encoding="utf-8")
    assert 'CUSTOM="keep"' in env_path.read_text(encoding="utf-8")
    assert json.loads((target / ".azure/config.json").read_text(encoding="utf-8"))["custom"]


def test_canonical_template_has_expected_assets() -> None:
    assert {relative for relative, _ in iter_template_files(template_root())} == {
        "README.md",
        "azure.yaml",
        "hooks/postprovision.ps1",
        "hooks/postprovision.sh",
        "infra/main.bicep",
        "infra/main.parameters.json",
        "infra/models.json",
        "infra/modules/foundry.bicep",
    }


def test_built_wheel_contains_canonical_assets() -> None:
    wheels = sorted((Path(__file__).parents[1] / "dist").glob("cu_cli_core-*.whl"))
    assert wheels, "CI must build the core wheel before running core tests"
    with zipfile.ZipFile(wheels[-1]) as wheel:
        names = {
            name.removeprefix("cu_cli_core/resources/azd_template/")
            for name in wheel.namelist()
            if name.startswith("cu_cli_core/resources/azd_template/")
            and not name.endswith("/")
        }
    assert names == {
        "README.md",
        "azure.yaml",
        "hooks/postprovision.ps1",
        "hooks/postprovision.sh",
        "infra/main.bicep",
        "infra/main.parameters.json",
        "infra/models.json",
        "infra/modules/foundry.bicep",
    }