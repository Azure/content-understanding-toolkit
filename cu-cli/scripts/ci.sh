#!/usr/bin/env bash
set -euo pipefail

product_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
core_dir="${product_dir}/packages/core"
cli_dir="${product_dir}/packages/standalone"

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
cd "${core_dir}"
python -m pip install -e ".[dev]"
cd "${cli_dir}"
python -m pip install -e ".[dev]"
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
