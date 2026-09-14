# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_validator() -> ModuleType:
    script_path = Path(__file__).resolve().parents[4] / "scripts" / "validate_frontend_sdk_boundary.py"
    spec = importlib.util.spec_from_file_location("validate_frontend_sdk_boundary", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _write_frontends(root: Path) -> None:
    for package, source in (
        ("standalone", "src/cu_cli"),
        ("azure-cli-extension", "azext_content_understanding"),
    ):
        source_root = root / "packages" / package / source
        source_root.mkdir(parents=True)
        (source_root / "module.py").write_text("from cu_cli_core import client\n", encoding="utf-8")
        tests = root / "packages" / package / "tests"
        tests.mkdir(parents=True)
        (tests / "test_module.py").write_text("def test_placeholder(): pass\n", encoding="utf-8")
        (root / "packages" / package / "pyproject.toml").write_text(
            '[project]\nname = "frontend"\nversion = "1.0.0"\ndependencies = ["cu-cli-core"]\n',
            encoding="utf-8",
        )


def test_repository_frontends_use_core_sdk_boundary() -> None:
    assert validator.find_violations() == []


@pytest.mark.parametrize(
    ("relative_path", "content", "message"),
    [
        (
            "packages/standalone/src/cu_cli/module.py",
            "from " + "azure.ai." + "contentunderstanding import to_llm_input\n",
            "direct CU SDK reference",
        ),
        (
            "packages/azure-cli-extension/tests/test_module.py",
            'TARGET = "' + "azure.ai." + 'contentunderstanding.ContentUnderstandingClient"\n',
            "direct CU SDK reference",
        ),
        (
            "packages/standalone/pyproject.toml",
            '[project]\nname = "frontend"\nversion = "1.0.0"\n'
            'dependencies = ["azure_ai_' + 'contentunderstanding>=1"]\n',
            "direct CU SDK dependency",
        ),
    ],
)
def test_validator_rejects_direct_sdk_coupling(
    tmp_path: Path,
    relative_path: str,
    content: str,
    message: str,
) -> None:
    _write_frontends(tmp_path)
    (tmp_path / relative_path).write_text(content, encoding="utf-8")

    assert any(message in violation for violation in validator.find_violations(tmp_path))
