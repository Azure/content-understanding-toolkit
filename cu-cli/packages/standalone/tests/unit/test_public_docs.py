# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from pathlib import Path

import pytest

from cu_cli.apiversion import API_VERSION_HELP
from tests.support.doc_snippets import SNIPPET_EXECUTION_MODES, load_doc_snippets


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
_SNIPPET_INFO_RE = re.compile(
    r"^\S+\s+Snippet:(?P<identifier>[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)$"
)
_SNIPPET_REFERENCES = {
    _README: {
        "cu_cli_analyze_directory_pattern",
        "cu_cli_analyze_inline_preview",
        "cu_cli_analyze_layout",
        "cu_cli_analyze_prebuilt_invoice",
        "cu_cli_analyze_remote_url",
        "cu_cli_command_help",
        "cu_cli_configure_key_profile",
        "cu_cli_configure_login_profile",
        "cu_cli_create_and_test_custom_analyzer",
        "cu_cli_install",
        "cu_cli_list_analyzers",
        "cu_cli_mac_os_help",
        "cu_cli_show_defaults",
        "cu_cli_use_multiple_profiles",
    },
    _USAGE_GUIDE: {
        "cu_cli_analyze_batch_with_report",
        "cu_cli_analyze_concurrency_and_timing",
        "cu_cli_analyze_directory",
        "cu_cli_analyze_directory_recursive",
        "cu_cli_analyze_local_file",
        "cu_cli_analyze_multiple_urls_dry_run",
        "cu_cli_analyze_output_formats",
        "cu_cli_analyze_public_url",
        "cu_cli_analyze_sas_url",
        "cu_cli_analyze_with_default_analyzer",
        "cu_cli_azure_login",
        "cu_cli_configure_and_apply_defaults",
        "cu_cli_copy_analyzer_with_profiles",
        "cu_cli_copy_analyzer_with_resources",
        "cu_cli_create_and_test_analyzer",
        "cu_cli_create_local_schemas",
        "cu_cli_create_schema_from_sample",
        "cu_cli_directory_output_mapping",
        "cu_cli_help_and_exit_behavior",
        "cu_cli_list_environment_overrides",
        "cu_cli_manage_analyzers",
        "cu_cli_manage_defaults",
        "cu_cli_preview_batch",
        "cu_cli_profile_commands",
        "cu_cli_profile_info_output",
        "cu_cli_profile_resolution_precedence",
        "cu_cli_run_diagnostics",
        "cu_cli_set_key_authentication",
        "cu_cli_sync_profile_defaults",
        "cu_cli_temporarily_override_endpoint",
        "cu_cli_timing_output",
        "cu_cli_unset_key_authentication",
        "cu_cli_validate_schema",
    },
}


def _snippet_reference_problems(
    documents: dict[Path, str], references: dict[Path, set[str]]
) -> list[str]:
    documented_locations: dict[str, list[str]] = {}
    problems = []

    for path, referenced_ids in references.items():
        text = documents[path]
        documented_ids = set()
        in_fence = False

        for line, content in enumerate(text.splitlines(), start=1):
            if not content.startswith("```"):
                continue
            if in_fence:
                in_fence = False
                continue
            in_fence = True
            info_match = _SNIPPET_INFO_RE.fullmatch(content[3:].strip())
            if info_match is None:
                problems.append(f"{path}:{line}: fence is missing a valid Snippet ID")
                continue
            identifier = info_match.group("identifier")
            documented_ids.add(identifier)
            documented_locations.setdefault(identifier, []).append(f"{path}:{line}")

        for identifier in sorted(documented_ids - referenced_ids):
            problems.append(
                f"{path}: Snippet:{identifier} has no test reference; "
                "add it to _SNIPPET_REFERENCES"
            )
        for identifier in sorted(referenced_ids - documented_ids):
            problems.append(
                f"{path}: test reference Snippet:{identifier} is orphaned; "
                "restore the document block or remove the reference"
            )

    for identifier, locations in documented_locations.items():
        if len(locations) > 1:
            problems.append(
                f"Snippet:{identifier} is duplicated at "
                + ", ".join(locations)
            )

    return problems


def test_public_doc_snippet_ids_match_test_references():
    documents = {
        path: path.read_text(encoding="utf-8") for path in _SNIPPET_REFERENCES
    }

    problems = _snippet_reference_problems(documents, _SNIPPET_REFERENCES)

    assert not problems, "\n" + "\n".join(problems)


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

    assert set(SNIPPET_EXECUTION_MODES) == bash_ids


@pytest.mark.parametrize(
    ("document", "references", "expected_problem"),
    [
        pytest.param("```bash\ncu --help\n```", set(), "missing", id="missing-id"),
        pytest.param(
            "```bash Snippet:PascalCase\ncu --help\n```",
            {"PascalCase"},
            "valid Snippet ID",
            id="non-python-style-id",
        ),
        pytest.param(
            "```bash Snippet:same\ncu --help\n```\n"
            "```text Snippet:same\noutput\n```",
            {"same"},
            "duplicated",
            id="duplicate-id",
        ),
        pytest.param("", {"Gone"}, "orphaned", id="orphaned-reference"),
    ],
)
def test_snippet_reference_failures_are_actionable(
    tmp_path: Path,
    document: str,
    references: set[str],
    expected_problem: str,
):
    path = tmp_path / "doc.md"

    problems = _snippet_reference_problems({path: document}, {path: references})

    assert any(expected_problem in problem for problem in problems)


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


def test_usage_guide_directory_patterns_use_source_option():
    usage_guide = _USAGE_GUIDE.read_text(encoding="utf-8")
    bash_blocks = re.findall(
        r"```bash(?:\s+Snippet:\S+)?\n(.*?)```",
        usage_guide,
        flags=re.DOTALL,
    )
    commands = "\n".join(bash_blocks).replace("\\\n", " ")
    pattern_commands = [
        line for line in commands.splitlines()
        if line.startswith("cu analyze ") and "--pattern" in line
    ]

    assert pattern_commands
    assert all("--source " in command for command in pattern_commands)


def test_api_version_description_matches_cli_help():
    for path in (_README, _USAGE_GUIDE):
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert API_VERSION_HELP in normalized
