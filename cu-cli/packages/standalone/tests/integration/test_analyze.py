# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Integration tests for the ``analyze`` command.

Covers single-file markdown output, directory batch with --output-dir, and prebuilt
analyzer JSON output (README scenarios §1 and §6).

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from click.testing import CliRunner
import pytest

from cu_cli.cli import main

from support.recording import use_cassette
from tests.support.doc_snippets import load_doc_snippets, parse_cu_commands

pytestmark = pytest.mark.integration

_PRODUCT_ROOT = Path(__file__).resolve().parents[4]
_DOC_SNIPPETS = load_doc_snippets(
    _PRODUCT_ROOT / "README.md",
    _PRODUCT_ROOT / "docs" / "usage-guide.md",
)


def _run(*args):
    return CliRunner().invoke(main, list(args))


def _copy_sample(name: str = "sample_invoice.pdf") -> Path:
    dest = Path.cwd() / name
    source = Path(__file__).parent / "fixtures" / "sample_invoice.pdf"
    dest.write_bytes(source.read_bytes())
    return dest


@pytest.mark.parametrize(
    "snippet_id",
    [
        "cu_cli_analyze_layout",
        "cu_cli_analyze_local_file",
        "cu_cli_analyze_with_default_analyzer",
    ],
)
def test_scenario_1_analyze_single_file_markdown(cloud_project, snippet_id):
    _copy_sample("document.pdf")
    commands = parse_cu_commands(_DOC_SNIPPETS[snippet_id])
    for args in commands[:-1]:
        res = _run(*args)
        assert res.exit_code == 0, res.output
    with use_cassette("analyze_single"):
        res = _run(*commands[-1])
    assert res.exit_code == 0, res.output
    assert res.output.startswith("---")
    assert "mimeType:" in res.output
    assert "pages:" in res.output
    assert "<!-- InputPageNumber:" in res.output


def test_scenario_1_analyze_directory_writes_result_files(cloud_project):
    """`cu analyze <dir> --output-dir <dir> --json` writes result files."""
    docs = Path("docs")
    docs.mkdir()
    src = _copy_sample()
    shutil.move(str(src), str(docs / "sample_invoice.pdf"))
    with use_cassette("analyze_batch"):
        res = _run(
            "analyze",
            "docs",
            "--analyzer",
            "prebuilt-layout",
            "--output-dir",
            "out",
            "--json",
        )
    assert res.exit_code == 0, res.output
    # Paths under --output-dir are relative to the selected source directory.
    assert (Path("out") / "sample_invoice.pdf.result.json").exists()


def test_scenario_3_analyze_prebuilt_invoice_json(cloud_project):
    """`cu analyze --analyzer prebuilt-invoice --json`."""
    import json
    _copy_sample("invoice.pdf")
    [args] = parse_cu_commands(_DOC_SNIPPETS["cu_cli_analyze_prebuilt_invoice"])
    with use_cassette("analyze_prebuilt_invoice_json"):
        res = _run(*args)
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output[res.output.find("{"):])
    assert payload["status"] == "Succeeded"
    assert payload["result"]["analyzerId"] == "prebuilt-invoice"
    assert payload["result"]["contents"]
    assert "usage" in payload
