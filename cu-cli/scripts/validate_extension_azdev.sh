#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

set -euo pipefail

if [[ "$#" -ne 3 ]]; then
    echo "Usage: $0 <extension-wheel> <core-wheel> <extension-source>" >&2
    exit 2
fi

extension_wheel="$(realpath "$1")"
core_wheel="$(realpath "$2")"
extension_source="$(realpath "$3")"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
temp_root="$(mktemp -d)"
trap 'rm -rf "${temp_root}"' EXIT

if command -v python >/dev/null 2>&1; then
    bootstrap_python="python"
else
    bootstrap_python="python3"
fi

"${bootstrap_python}" -m venv "${temp_root}/venv"
export VIRTUAL_ENV="${temp_root}/venv"
export PATH="${VIRTUAL_ENV}/bin:${PATH}"
export AZURE_CONFIG_DIR="${temp_root}/azure"
export AZURE_EXTENSION_DIR="${AZURE_CONFIG_DIR}/cliextensions"
export PIP_FIND_LINKS="$(dirname "${core_wheel}")"

git clone --depth 1 --branch dev \
    https://github.com/Azure/azure-cli.git "${temp_root}/azure-cli"
git clone --depth 1 \
    https://github.com/Azure/azure-cli-extensions.git "${temp_root}/azure-cli-extensions"
cat "${script_dir}/extension_linter_exclusions.yml" \
    >> "${temp_root}/azure-cli-extensions/linter_exclusions.yml"

python -m pip install --disable-pip-version-check --quiet \
    --upgrade pip \
    "azdev==0.2.13" \
    "build==1.3.0" \
    wheel
azdev setup \
    -c "${temp_root}/azure-cli" \
    -r "${temp_root}/azure-cli-extensions"

az extension add \
    --source "${extension_wheel}" \
    --yes \
    --only-show-errors
python -m pip install --disable-pip-version-check --quiet \
    --no-deps \
    --upgrade \
    --force-reinstall \
    --target "${AZURE_EXTENSION_DIR}/content-understanding" \
    "${core_wheel}"
python - <<'PY'
import os
import sys

from pathlib import Path

extension_dir = Path(os.environ["AZURE_EXTENSION_DIR"]) / "content-understanding"
sys.path.insert(0, str(extension_dir))

from cu_cli_core import serialization

assert Path(serialization.__file__).is_relative_to(extension_dir)
assert hasattr(serialization, "render_llm_input")
PY
(
    cd "${temp_root}/azure-cli-extensions"
    azdev linter \
        --include-whl-extensions content-understanding \
        --min-severity medium
)

rm -rf "${AZURE_EXTENSION_DIR}/content-understanding"
extension_checkout="${temp_root}/azure-cli-extensions/src/content-understanding"
mkdir -p "${extension_checkout}"
cp -R "${extension_source}/." "${extension_checkout}/"
rm -rf \
    "${extension_checkout}/build" \
    "${extension_checkout}/dist" \
    "${extension_checkout}/.pytest_cache" \
    "${extension_checkout}"/*.egg-info
find "${extension_checkout}" -type d -name __pycache__ -prune -exec rm -rf {} +
# azdev 0.2.13 discovers source extensions by setup.py even though its build
# pipeline supports pyproject.toml. Add a temporary shim only in the checkout.
cat > "${extension_checkout}/setup.py" <<'PY'
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from setuptools import setup

setup()
PY
(
    cd "${temp_root}/azure-cli-extensions"
    azdev extension add content-understanding
)
python -m pip install --disable-pip-version-check --quiet \
    --no-deps \
    --upgrade \
    --force-reinstall \
    "${core_wheel}"
python -m pip install --disable-pip-version-check --quiet \
    --no-deps \
    --upgrade \
    --force-reinstall \
    --target "${AZURE_EXTENSION_DIR}/content-understanding" \
    "${core_wheel}"
(
    cd "${temp_root}/azure-cli-extensions"
    azdev style content-understanding
)

echo "Validated $(basename "${extension_wheel}") with Azure CLI extension lint and style checks."
