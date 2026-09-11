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

section "Validate installed shared core wheel"
installed_core="$(mktemp -d)"
generated_project="$(mktemp -d)"
trap 'rm -rf "${installed_core}" "${generated_project}"' EXIT
python -m pip install --no-deps --target "${installed_core}" dist/cu_cli_core-*.whl
cd "${product_dir}"
PYTHONPATH="${installed_core}" GENERATED_PROJECT="${generated_project}" python - <<'PY'
import os
from pathlib import Path

from cu_cli_core.infra import AzureAccount, InfraChoices, materialize_project

target = Path(os.environ["GENERATED_PROJECT"])
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
