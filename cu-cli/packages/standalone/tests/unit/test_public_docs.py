# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from pathlib import Path

import pytest

from cu_cli.apiversion import API_VERSION_HELP
from tests.support.doc_snippets import (
    ExecutionMode,
    SNIPPET_EXECUTIONS,
    DocSnippet,
    SnippetExecution,
    load_doc_snippets,
    parse_shell_commands,
)


pytestmark = pytest.mark.unit

_PRODUCT_ROOT = Path(__file__).resolve().parents[4]
_README = _PRODUCT_ROOT / "README.md"
_PACKAGE_README = Path(__file__).resolve().parents[2] / "README.md"
_PROVISIONING_GUIDE = _PRODUCT_ROOT / "docs" / "provisioning.md"
_USAGE_GUIDE = _PRODUCT_ROOT / "docs" / "usage-guide.md"
_REGION_SUPPORT_URL = (
    "https://learn.microsoft.com/azure/ai-services/content-understanding/"
    "language-region-support"
)
def test_public_doc_snippets_are_loaded_from_markdown():
    snippets = load_doc_snippets(_README, _USAGE_GUIDE)

    assert snippets["cu_cli_command_help"].language == "bash"
    assert snippets["cu_cli_command_help"].body.splitlines() == [
        "cu profile --help",
        "cu analyzer copy --help",
        "cu infra generate --help",
    ]


def test_every_bash_snippet_has_an_execution_mode():
    snippets = load_doc_snippets(_README, _USAGE_GUIDE)
    bash_ids = {
        identifier
        for identifier, snippet in snippets.items()
        if snippet.language == "bash"
    }

    assert set(SNIPPET_EXECUTIONS) == bash_ids


@pytest.mark.parametrize(
    ("language", "body", "expected"),
    [
        pytest.param(
            "bash",
            '# comment\nCU_ENDPOINT="https://example.test" \\\n  cu analyzer list --profile "dev profile"',
            [[
                "CU_ENDPOINT=https://example.test",
                "cu",
                "analyzer",
                "list",
                "--profile",
                "dev profile",
            ]],
            id="bash",
        ),
        pytest.param(
            "powershell",
            '# comment\n$env:CU_ENDPOINT = "https://example.test"\ncu analyzer list `\n'
            '  --profile "dev` profile"',
            [
                ["$env:CU_ENDPOINT", "=", "https://example.test"],
                ["cu", "analyzer", "list", "--profile", "dev profile"],
            ],
            id="powershell",
        ),
    ],
)
def test_shell_snippets_support_comments_quoting_environment_and_continuations(
    tmp_path: Path, language: str, body: str, expected: list[list[str]]
):
    snippet = DocSnippet("example", language, body, tmp_path / "doc.md", 1)

    assert parse_shell_commands(snippet) == expected


def test_snippet_execution_metadata_has_safe_defaults():
    metadata = SNIPPET_EXECUTIONS["cu_cli_command_help"]

    assert metadata.mode is ExecutionMode.OFFLINE
    assert metadata.expected_exit_codes == (0,)
    assert metadata.setup_fixture is None
    assert metadata.cleanup_fixture is None


def test_snippet_execution_metadata_supports_per_command_exit_codes(tmp_path: Path):
    snippet = DocSnippet(
        "mixed_exit_codes", "bash", "cu --help\ncu invalid", tmp_path / "doc.md", 12
    )
    metadata = SnippetExecution(ExecutionMode.OFFLINE, expected_exit_codes=(0, 2))

    assert metadata.exit_codes_for(snippet, 2) == (0, 2)


def test_snippet_execution_metadata_rejects_exit_code_count_mismatch(tmp_path: Path):
    snippet = DocSnippet(
        "mixed_exit_codes", "bash", "cu --help\ncu invalid", tmp_path / "doc.md", 12
    )
    metadata = SnippetExecution(ExecutionMode.OFFLINE, expected_exit_codes=(0, 1, 2))

    with pytest.raises(ValueError, match=r"Snippet:mixed_exit_codes.*2 commands.*3 expected"):
        metadata.exit_codes_for(snippet, 2)


def test_documented_custom_analyzer_ids_use_valid_format():
    for path in (_README, _USAGE_GUIDE):
        text = path.read_text(encoding="utf-8")
        assert "invoice-v1" not in text
        assert "invoice_v1" in text


def test_readme_links_are_absolute_for_pypi():
    readme = _README.read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)

    assert targets
    assert all(target.startswith(("https://", "http://")) for target in targets)


def test_pypi_readme_links_to_product_readme():
    assert _PACKAGE_README.is_symlink()
    assert _PACKAGE_README.read_bytes() == _README.read_bytes()


def test_documented_provision_region_and_support_link_are_current():
    provisioning_guide = _PROVISIONING_GUIDE.read_text(encoding="utf-8")

    assert "--location <supported-region>" in provisioning_guide
    assert "--location westus2" not in provisioning_guide
    assert _REGION_SUPPORT_URL in provisioning_guide


def test_readme_documents_analyzer_short_option():
    readme = _README.read_text(encoding="utf-8")

    assert "`-a` is the short form of `--analyzer`" in readme
    assert "cu analyze ./document.pdf -a prebuilt-layout" in readme


def _analyze_pattern_problems(snippets: dict[str, DocSnippet]) -> list[str]:
    problems = []
    for snippet in snippets.values():
        if snippet.language != "bash":
            continue
        for argv in parse_shell_commands(snippet):
            if argv[:2] == ["cu", "analyze"] and "--pattern" in argv and "--source" not in argv:
                problems.append(
                    f"{snippet.path}:{snippet.line}: Snippet:{snippet.identifier} "
                    "uses --pattern without --source"
                )
    return problems


def test_public_doc_directory_patterns_use_source_option():
    snippets = load_doc_snippets(_README, _USAGE_GUIDE)

    assert not _analyze_pattern_problems(snippets)


def test_positional_directory_pattern_cannot_enter_public_docs(tmp_path: Path):
    snippet = DocSnippet(
        "invalid_directory_pattern",
        "bash",
        'cu analyze ./documents --pattern "*.pdf"',
        tmp_path / "README.md",
        42,
    )

    assert _analyze_pattern_problems({snippet.identifier: snippet}) == [
        f"{snippet.path}:42: Snippet:invalid_directory_pattern uses --pattern without --source"
    ]


def test_api_version_description_matches_cli_help():
    for path in (_README, _USAGE_GUIDE):
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert API_VERSION_HELP in normalized
