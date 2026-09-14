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
temp_root="$(mktemp -d)"
trap 'rm -rf "${temp_root}"' EXIT

if command -v python >/dev/null 2>&1; then
    bootstrap_python="python"
else
    bootstrap_python="python3"
fi

"${bootstrap_python}" -m venv "${temp_root}/venv"
python_bin="${temp_root}/venv/bin/python"
az_bin="${temp_root}/venv/bin/az"
export AZURE_CONFIG_DIR="${temp_root}/azure"
export PIP_FIND_LINKS="$(dirname "${core_wheel}")"

"${python_bin}" -m pip install --disable-pip-version-check --quiet \
    "azure-cli>=2.75.0"
"${az_bin}" extension add \
    --source "${extension_wheel}" \
    --yes \
    --only-show-errors
"${python_bin}" -m pip install --disable-pip-version-check --quiet \
    --no-deps \
    --upgrade \
    --force-reinstall \
    --target "${AZURE_CONFIG_DIR}/cliextensions/content-understanding" \
    "${core_wheel}"

"${python_bin}" - <<'PY'
import azure.ai  # Simulate Azure CLI command modules that load this namespace first.
from azure.cli.core import get_default_cli

raise SystemExit(get_default_cli().invoke(["cu", "--help"]))
PY

echo "Validated clean Azure CLI installation of $(basename "${extension_wheel}")."
