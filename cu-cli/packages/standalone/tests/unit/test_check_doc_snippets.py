# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _load_checker() -> ModuleType:
    script_path = Path(__file__).resolve().parents[4] / "scripts" / "check_doc_snippets.py"
    spec = importlib.util.spec_from_file_location("check_doc_snippets", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_doc_snippets = _load_checker()


def _write_documents(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "README.md").write_text(
        "```bash Snippet:readme_command\ncu analyzer list\n```\n", encoding="utf-8"
    )
    (root / "docs/usage-guide.md").write_text(
        "```text Snippet:usage_output\nAnalyzer ID\n```\n", encoding="utf-8"
    )


def test_update_is_deterministic_and_check_is_read_only(tmp_path: Path) -> None:
    _write_documents(tmp_path)

    assert not check_doc_snippets.check_inventory(tmp_path)
    check_doc_snippets.update_inventory(tmp_path)
    inventory_path = tmp_path / "docs/snippet-inventory.json"
    first = inventory_path.read_text(encoding="utf-8")

    assert check_doc_snippets.check_inventory(tmp_path)
    assert inventory_path.read_text(encoding="utf-8") == first
    check_doc_snippets.update_inventory(tmp_path)
    assert inventory_path.read_text(encoding="utf-8") == first

    inventory = json.loads(first)
    assert inventory == {
        "generatedFrom": ["README.md", "docs/usage-guide.md"],
        "snippets": [
            {"id": "readme_command", "language": "bash", "document": "README.md"},
            {
                "id": "usage_output",
                "language": "text",
                "document": "docs/usage-guide.md",
            },
        ],
    }
    assert "cu analyzer list" not in first


def test_check_detects_inventory_drift(tmp_path: Path) -> None:
    _write_documents(tmp_path)
    check_doc_snippets.update_inventory(tmp_path)
    (tmp_path / "README.md").write_text(
        "```bash Snippet:renamed_command\ncu analyzer list\n```\n", encoding="utf-8"
    )

    assert not check_doc_snippets.check_inventory(tmp_path)


def test_duplicate_identifier_reports_both_locations(tmp_path: Path) -> None:
    _write_documents(tmp_path)
    (tmp_path / "docs/usage-guide.md").write_text(
        "```bash Snippet:readme_command\ncu analyze sample.pdf\n```\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match=r"README\.md:1 and docs/usage-guide\.md:1"):
        check_doc_snippets.build_inventory(tmp_path)


def test_missing_identifier_reports_document_location(tmp_path: Path) -> None:
    _write_documents(tmp_path)
    (tmp_path / "README.md").write_text("```bash\ncu --help\n```\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"README\.md:1: fence is missing a valid Snippet ID"):
        check_doc_snippets.build_inventory(tmp_path)