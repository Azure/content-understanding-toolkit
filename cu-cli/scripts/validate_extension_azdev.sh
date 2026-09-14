#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

set -euo pipefail

if [[ "$#" -ne 2 ]]; then
    echo "Usage: $0 <extension-wheel> <core-wheel>" >&2
    exit 2
fi

extension_wheel="$(realpath "$1")"
core_wheel="$(realpath "$2")"
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
    --target "${AZURE_CONFIG_DIR}/cliextensions/content-understanding" \
    "${core_wheel}"
(
    cd "${temp_root}/azure-cli-extensions"
    azdev linter \
        --include-whl-extensions content-understanding \
        --min-severity medium
)

echo "Validated $(basename "${extension_wheel}") with the Azure CLI extension linter."