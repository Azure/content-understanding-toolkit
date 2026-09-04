# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_checker() -> ModuleType:
    script_path = Path(__file__).resolve().parents[4] / "scripts" / "check_headers.py"
    spec = importlib.util.spec_from_file_location("check_headers", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_headers = _load_checker()


def test_recognizes_header_after_shebang(tmp_path: Path) -> None:
    path = tmp_path / "script.py"
    lines = [
        "#!/usr/bin/env python3\n",
        "# Copyright (c) Microsoft Corporation.\n",
        "# Licensed under the MIT license.\n",
        "\n",
    ]

    assert check_headers.has_header(path, lines)


def test_adds_header_after_powershell_requires(tmp_path: Path) -> None:
    path = tmp_path / "script.ps1"
    lines = ["#Requires -Version 7.0\n", "Write-Host 'hello'\n"]

    check_headers.add_header(path, lines)

    assert path.read_text(encoding="utf-8").splitlines() == [
        "#Requires -Version 7.0",
        "# Copyright (c) Microsoft Corporation.",
        "# Licensed under the MIT license.",
        "",
        "Write-Host 'hello'",
    ]


def test_uses_bicep_comment_prefix(tmp_path: Path) -> None:
    path = tmp_path / "main.bicep"

    assert check_headers.expected_header(path) == [
        "// Copyright (c) Microsoft Corporation.\n",
        "// Licensed under the MIT license.\n",
    ]


def test_main_reports_missing_header_and_fix_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "module.py"
    path.write_text('"""Module docstring."""\n', encoding="utf-8")
    monkeypatch.setattr(check_headers, "ROOT", tmp_path)
    monkeypatch.setattr(check_headers, "SOURCE_ROOTS", (tmp_path,))

    monkeypatch.setattr(sys, "argv", ["check_headers.py"])
    assert check_headers.main() == 1
    assert "module.py" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["check_headers.py", "--fix"])
    assert check_headers.main() == 0
    fixed = path.read_text(encoding="utf-8")
    assert check_headers.main() == 0
    assert path.read_text(encoding="utf-8") == fixed
