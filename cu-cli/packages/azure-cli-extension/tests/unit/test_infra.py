# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from azext_content_understanding import _infra
from azext_content_understanding._infra import AzureAccount, InfraChoices
from cu_cli_core.errors import LocalIOError, ValidationError

pytestmark = pytest.mark.unit


def _choices() -> InfraChoices:
    return InfraChoices(
        environment="dev",
        location="eastus2",
        api_version="2025-11-01",
        account=AzureAccount("sub-id", "Development", "tenant-id"),
        foundry_prefix="contoso-cu",
        foundry_endpoint=None,
        foundry_resource_group=None,
        model_selection="recommended",
        assign_roles=False,
        force_profile_setup=False,
    )


def test_write_project_materializes_canonical_template(tmp_path: Path) -> None:
    target = tmp_path / "provision"

    written, reused = _infra._write_project(target, _choices(), force=False)

    assert reused is False
    assert "azure.yaml" in written
    assert "infra/main.bicep" in written
    assert "hooks/postprovision.sh" in written
    if os.name != "nt":
        assert (target / "hooks/postprovision.sh").stat().st_mode & 0o100
    posix_hook = (target / "hooks/postprovision.sh").read_text(encoding="utf-8")
    powershell_hook = (target / "hooks/postprovision.ps1").read_text(encoding="utf-8")
    readme = (target / "README.md").read_text(encoding="utf-8")
    assert "az cu _infra-models" in posix_hook
    assert "'cu', '_infra-models'" in powershell_hook
    assert "profile set --key endpoint --value" in posix_hook
    assert "profile set --key endpoint --value" in powershell_hook
    assert "defaults set --from-profile" not in posix_hook
    assert "defaults set --from-profile" not in powershell_hook
    assert "cu-cli" not in posix_hook
    assert "cu-cli" not in powershell_hook
    assert "keep the `cu` CLI installed" not in readme
    assert "az cu profile set --key endpoint --value" in readme
    assert "`AZD_ASSIGN_ROLES`" in readme
    environment = (target / ".azure/dev/.env").read_text(encoding="utf-8")
    assert 'AZURE_SUBSCRIPTION_ID="sub-id"' in environment
    assert 'CU_MODEL_SELECTION="recommended"' in environment


def test_template_is_packaged_with_the_extension() -> None:
    template = _infra._template_root()

    assert template.parent == Path(_infra.__file__).parent
    assert {relative.as_posix() for _, relative in _infra._iter_template_files(template)} == {
        "README.md",
        "azure.yaml",
        "hooks/postprovision.ps1",
        "hooks/postprovision.sh",
        "infra/main.bicep",
        "infra/main.parameters.json",
        "infra/models.json",
        "infra/modules/foundry.bicep",
    }


def test_write_project_reuses_template_and_preserves_unknown_state(tmp_path: Path) -> None:
    target = tmp_path / "provision"
    _infra._write_project(target, _choices(), force=False)
    env_path = target / ".azure/dev/.env"
    env_path.write_text(env_path.read_text(encoding="utf-8") + 'CUSTOM="keep"\n', encoding="utf-8")

    written, reused = _infra._write_project(target, _choices(), force=False)

    assert reused is True
    assert "azure.yaml" not in written
    assert 'CUSTOM="keep"' in env_path.read_text(encoding="utf-8")


def test_write_project_rejects_non_template_directory(tmp_path: Path) -> None:
    target = tmp_path / "provision"
    target.mkdir()
    (target / "unrelated.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(LocalIOError, match="non-empty"):
        _infra._write_project(target, _choices(), force=False)


def test_validation_rejects_unsafe_environment_and_region() -> None:
    with pytest.raises(ValidationError, match="environment"):
        _infra._validate_environment("../outside")
    with pytest.raises(ValidationError, match="CU-supported"):
        _infra._validate_location("westus2")


def test_generate_noninteractive_uses_active_azure_cli_account(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    account = AzureAccount("sub-id", "Development", "tenant-id")
    monkeypatch.setattr(_infra.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(_infra, "ensure_supported_cloud", lambda _ctx: None)
    monkeypatch.setattr(_infra, "_choose_account", lambda _ctx, interactive: account)
    cmd = SimpleNamespace(cli_ctx=object())

    result = _infra.generate_infrastructure(
        cmd,
        output_dir=str(tmp_path / "provision"),
        location="eastus2",
        models="none",
    )

    assert result["subscriptionId"] == "sub-id"
    assert result["model_selection"] == "none"
    assert result["assign_roles"] is True
    assert result["nextSteps"][-1] == "azd up"
    assert Path(result["outputDirectory"], "azure.yaml").is_file()
    environment = Path(result["outputDirectory"], ".azure/dev/.env").read_text(encoding="utf-8")
    assert 'AZD_ASSIGN_ROLES="true"' in environment


def test_generate_can_explicitly_skip_role_assignment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    account = AzureAccount("sub-id", "Development", "tenant-id")
    monkeypatch.setattr(_infra.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(_infra, "ensure_supported_cloud", lambda _ctx: None)
    monkeypatch.setattr(_infra, "_choose_account", lambda _ctx, interactive: account)

    result = _infra.generate_infrastructure(
        SimpleNamespace(cli_ctx=object()),
        output_dir=str(tmp_path / "provision"),
        location="eastus2",
        models="none",
        no_assign_roles=True,
    )

    assert result["assign_roles"] is False


def test_models_special_values_cannot_be_combined() -> None:
    with pytest.raises(ValidationError, match="used alone"):
        _infra._parse_models("recommended,gpt-5")
