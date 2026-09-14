# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import importlib.util
from pathlib import Path
import sys

import pytest


pytestmark = pytest.mark.unit

_PRODUCT_ROOT = Path(__file__).resolve().parents[4]
_MODULE_PATH = _PRODUCT_ROOT / "scripts" / "check_doc_snippets.py"
_SPEC = importlib.util.spec_from_file_location("check_doc_snippets", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

extract_test_snippets = _MODULE.extract_test_snippets
synchronize_document = _MODULE.synchronize_document


def test_update_is_deterministic_and_check_detects_drift(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text(
        "# [START example]\n"
        'COMMAND = "cu --help\\n"\n'
        "# [END example]\n",
        encoding="utf-8",
    )
    document = tmp_path / "README.md"
    document.write_text(
        "<!-- Snippet:example -->\n```bash\nold command\n```\n",
        encoding="utf-8",
    )
    snippets = extract_test_snippets(tests)

    errors = synchronize_document(document, snippets, update=False)
    assert errors == [
        f"{document}:1: snippet 'example' differs from {tests / 'test_example.py'}:1; "
        "run 'python scripts/check_doc_snippets.py update'"
    ]

    assert synchronize_document(document, snippets, update=True) == []
    updated = document.read_text(encoding="utf-8")
    assert updated == "<!-- Snippet:example -->\n```bash\ncu --help\n```\n"
    assert synchronize_document(document, snippets, update=True) == []
    assert document.read_text(encoding="utf-8") == updated
    assert synchronize_document(document, snippets, update=False) == []