# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import hashlib
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


def test_canonical_template_matches_golden_hashes() -> None:
    assert {
        relative: hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()
        for relative, content in iter_template_files(template_root())
    } == {
        "README.md": "d75fd48b73f92dbec27795f9dcc981f4b7a4237b5e38175bf2002591d2f8bc0d",
        "azure.yaml": "7bdbc6f8cf42fc1485ba52c04d7ed0c3ab78cd517d4892b1275a7b806ac31667",
        "hooks/postprovision.ps1": "37cc8f390b0201c7396046889d5e7c3fb7a61c27ca1f2486cf9ddc5344ccdd62",
        "hooks/postprovision.sh": "43ca49582fbde6c571b5fd67fdd16e0a0c3c5c5c1fc1c2da13c6c81f919d3157",
        "infra/main.bicep": "1103b1b3fdb28dba7fa6c2f3423257694eb07aefbea529d68213fb94c9f0998b",
        "infra/main.parameters.json": "c6a46f4caa1468b7c04a14f4ad15fabeda362dc16043be9f94a4b4e7b91bcf79",
        "infra/models.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
        "infra/modules/foundry.bicep": "18fd2b5d1ca12e75946ae317a08857f61fc5cdb05b329337036345521630c212",
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