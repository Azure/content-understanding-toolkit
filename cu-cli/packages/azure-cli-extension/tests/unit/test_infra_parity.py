# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path
from types import SimpleNamespace

import pytest

from azext_content_understanding import _infra
from cu_cli_core.infra import materialize_project

from .test_infra import _choices

pytestmark = pytest.mark.unit


def test_azure_frontend_materialization_matches_core(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    direct = tmp_path / "direct"

    _infra._write_project(frontend, _choices(), force=False)
    materialize_project(direct, _choices(), force=False)

    frontend_files = {
        path.relative_to(frontend): path.read_bytes()
        for path in frontend.rglob("*")
        if path.is_file()
    }
    direct_files = {
        path.relative_to(direct): path.read_bytes()
        for path in direct.rglob("*")
        if path.is_file()
    }
    assert frontend_files == direct_files


@pytest.mark.parametrize("use_existing", [False, True], ids=["new", "existing"])
@pytest.mark.parametrize(
    ("assign_roles", "expected_assign_roles"),
    [(None, False), (False, False), (True, True)],
    ids=["omitted", "false", "true"],
)
def test_frontends_generate_matching_role_choices(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    use_existing: bool,
    assign_roles: bool | None,
    expected_assign_roles: bool,
) -> None:
    from click.testing import CliRunner
    from cu_cli.cli import main
    from cu_cli.commands import infra as standalone_infra

    account = _infra.AzureAccount("sub-id", "Development", "tenant-id")
    endpoint = "https://existing.services.ai.azure.com/"
    monkeypatch.setenv("CU_NO_UPDATE_CHECK", "1")
    monkeypatch.setattr(_infra.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(_infra, "ensure_supported_cloud", lambda _ctx: None)
    monkeypatch.setattr(_infra, "_choose_account", lambda _ctx, interactive: account)
    monkeypatch.setattr(
        _infra,
        "resolve_resource",
        lambda *_args, **_kwargs: SimpleNamespace(
            endpoint=endpoint, resource_group="rg-existing", region="eastus2"
        ),
    )
    monkeypatch.setattr(
        standalone_infra, "_check_az_subscription", lambda subscription=None: account
    )
    monkeypatch.setattr(
        standalone_infra,
        "_resolve_existing_foundry_account",
        lambda *_args: ("existing", "rg-existing", "eastus2"),
    )
    arguments = ["--environment", "dev", "--location", "eastus2", "--models", "none"]
    values = {"environment": "dev", "location": "eastus2", "models": "none"}
    if use_existing:
        arguments.extend(["--foundry-endpoint", endpoint])
        values["foundry_endpoint"] = endpoint
    if assign_roles is not None:
        arguments.extend(["--assign-roles", str(assign_roles).lower()])

    standalone_target = tmp_path / "standalone"
    azure_target = tmp_path / "azure"
    standalone_result = CliRunner().invoke(
        main,
        ["infra", "generate", "--output-dir", str(standalone_target), *arguments],
        color=False,
    )
    assert standalone_result.exit_code == 0, standalone_result.output
    azure_result = _infra.generate_infrastructure(
        SimpleNamespace(cli_ctx=object()),
        output_dir=str(azure_target),
        assign_roles=assign_roles,
        **values,
    )
    assert azure_result["assign_roles"] is expected_assign_roles
    for target in (standalone_target, azure_target):
        environment = (target / ".azure/dev/.env").read_text(encoding="utf-8")
        assert f'AZD_ASSIGN_ROLES="{str(expected_assign_roles).lower()}"' in environment

    assert {
        path.relative_to(standalone_target): path.read_bytes()
        for path in standalone_target.rglob("*")
        if path.is_file()
    } == {
        path.relative_to(azure_target): path.read_bytes()
        for path in azure_target.rglob("*")
        if path.is_file()
    }