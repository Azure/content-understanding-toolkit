#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

set -euo pipefail

product_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
core_dir="${product_dir}/packages/core"
cli_dir="${product_dir}/packages/standalone"
extension_dir="${product_dir}/packages/azure-cli-extension"

section() {
    local title="$1"
    if [[ -n "${TF_BUILD:-}" ]]; then
        printf '##[group]%s\n' "${title}"
    elif [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        printf '::group::%s\n' "${title}"
    else
        printf '\n===== %s =====\n' "${title}"
    fi
}

end_section() {
    if [[ -n "${TF_BUILD:-}" ]]; then
        printf '##[endgroup]\n'
    elif [[ -n "${GITHUB_ACTIONS:-}" ]]; then
        printf '::endgroup::\n'
    fi
}

section "Install dependencies"
python -m pip install --upgrade pip
python -m pip install "build==1.3.0"
cd "${core_dir}"
python -m pip install -e ".[dev]"
cd "${cli_dir}"
python -m pip install -e ".[dev]"
cd "${extension_dir}"
python -m pip install -e ".[dev]"
end_section

section "Build shared core wheel"
cd "${core_dir}"
rm -rf build dist
python -m build --wheel
end_section

section "Build frontend wheels"
cd "${cli_dir}"
rm -rf build dist
python -m build --wheel
cd "${extension_dir}"
rm -rf build dist
python -m build --wheel
end_section

section "Copyright headers"
cd "${product_dir}"
python scripts/check_headers.py
end_section

section "Lint shared core (ruff)"
cd "${core_dir}"
python -m ruff check .
end_section

section "Type check shared core (mypy)"
python -m mypy src
end_section

section "Unit tests - shared core"
python -m pytest -q -m unit tests/
end_section

section "Validate installed wheels and frontend parity"
installed_core="$(mktemp -d)"
installed_frontends="$(mktemp -d)"
generated_projects="$(mktemp -d)"
trap 'rm -rf "${installed_core}" "${installed_frontends}" "${generated_projects}"' EXIT
python -m pip install --no-deps --target "${installed_core}" dist/cu_cli_core-*.whl
python -m pip install --no-deps --target "${installed_frontends}" \
    "${cli_dir}"/dist/cu_cli-*.whl \
    "${extension_dir}"/dist/content_understanding-*.whl
cd "${product_dir}"
PYTHONPATH="${installed_frontends}:${installed_core}" GENERATED_PROJECTS="${generated_projects}" python - <<'PY'
import os
from pathlib import Path

from cu_cli_core.infra import AzureAccount, InfraChoices, materialize_project
from cu_cli.commands import _infra_wizard
from cu_cli.commands._infra_wizard import InfraChoices as StandaloneChoices
from cu_cli.commands._infra_wizard import _write_template
from azext_content_understanding import _infra

root = Path(os.environ["GENERATED_PROJECTS"])
installed_frontends = Path(os.environ["PYTHONPATH"].split(os.pathsep)[0]).resolve()
assert Path(_infra_wizard.__file__).resolve().is_relative_to(installed_frontends)
assert Path(_infra.__file__).resolve().is_relative_to(installed_frontends)
target = root / "core"
files, reused = materialize_project(
    target,
    InfraChoices(
        environment="release",
        location="eastus2",
        api_version="2025-11-01",
        account=AzureAccount("subscription", "Release", "tenant"),
        foundry_prefix=None,
        foundry_endpoint=None,
        foundry_resource_group=None,
        model_selection="recommended",
    ),
    force=False,
)
expected = {
    "README.md",
    "azure.yaml",
    "hooks/postprovision.ps1",
    "hooks/postprovision.sh",
    "infra/main.bicep",
    "infra/main.parameters.json",
    "infra/models.json",
    "infra/modules/foundry.bicep",
}
assert expected <= set(files)
assert not reused
assert all((target / relative).is_file() for relative in expected)

standalone = root / "standalone"
_write_template(
    standalone,
    StandaloneChoices(
        env="release",
        location="eastus2",
        api_version="2025-11-01",
        subscription_id="subscription",
        subscription_name="Release",
        tenant_id="tenant",
        foundry_account_prefix=None,
        foundry_endpoint=None,
        foundry_resource_group=None,
        model_selection="recommended",
        assign_roles=False,
        force_profile_setup=False,
    ),
    force=False,
)
azure = root / "azure"
_infra._write_project(
    azure,
    InfraChoices(
        environment="release",
        location="eastus2",
        api_version="2025-11-01",
        account=AzureAccount("subscription", "Release", "tenant"),
        foundry_prefix=None,
        foundry_endpoint=None,
        foundry_resource_group=None,
        model_selection="recommended",
    ),
    force=False,
)


def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes().replace(b"\r\n", b"\n")
        for path in directory.rglob("*")
        if path.is_file()
    }


assert snapshot(standalone) == snapshot(azure) == snapshot(target)
PY
end_section

section "Lint standalone CLI (ruff)"
cd "${cli_dir}"
python -m ruff check .
end_section

section "Type check standalone CLI (mypy)"
python -m mypy src
end_section

export CU_NO_UPDATE_CHECK=1
section "Unit tests - standalone core modules"
python -m pytest -q -m unit tests/unit/core/
end_section

section "Unit tests - remaining standalone modules"
python -m pytest -q -m unit --ignore=tests/unit/core/ tests/unit/
end_section

export CU_TEST_REC_MODE=playback
section "Integration tests - offline playback"
python -m pytest -q -m integration tests/integration/
end_section

section "Lint Azure CLI extension (ruff)"
cd "${extension_dir}"
python -m ruff check .
end_section

section "Type check Azure CLI extension (mypy)"
python -m mypy azext_content_understanding
end_section

section "Unit tests - Azure CLI extension"
python -m pytest -q -m unit tests/unit/
end_section

section "Build Azure CLI extension wheel"
rm -rf build dist
python -m build --wheel
end_section
