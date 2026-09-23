# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import re
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from cu_cli.apiversion import API_VERSION_HELP
from support.command_catalog import invoke_azure, invoke_cli, record_external
from support.recording import copy_sample_invoice, use_cassette


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


DOC_SCENARIOS = {
    "cli_installation": ("cli_install", "cli_version", "cli_help"),
    "configure_login": ("profile_endpoint", "profile_login", "azure_login", "doctor"),
    "analyze_layout_options": ("analyze_layout", "analyze_layout_short"),
    "custom_analyzer_workflow": (
        "schema_from_sample", "analyzer_create", "analyzer_test_single", "analyze_custom",
    ),
    "setup_help": ("profile_help", "copy_help", "infra_help"),
    "multiple_profiles": (
        "profile_create_dev", "profile_dev_endpoint", "profile_create_prod", "profile_prod_endpoint",
        "profile_activate_dev", "analyzer_list_active", "analyzer_list_prod", "doctor_named",
    ),
    "profile_setup": (
        "profile_create_dev", "profile_dev_endpoint", "profile_create_prod", "profile_prod_endpoint",
        "profile_activate_dev",
    ),
    "profile_workflow": (
        "profile_show", "profile_get_endpoint", "profile_list", "profile_show_prod",
    ),
    "login_authentication": ("azure_login", "profile_login"),
    "environment_inspection": ("env_list", "env_json"),
    "configure_model_mappings": (
        "profile_completion_model", "profile_embedding_model",
    ),
    "analyze_with_profile_default": ("profile_default_analyzer", "analyze_default"),
    "analyzer_management": ("analyzer_list", "analyzer_show"),
    "schema_templates": ("schema_template", "schema_image", "schema_classification"),
    "schema_validation": ("schema_validate", "schema_validate_spec"),
    "analyzer_evaluation": ("analyzer_create", "analyzer_test_single"),
    "diagnose_configuration": ("doctor", "doctor_named"),
    "cli_help_overview": ("cli_help", "profile_help", "copy_help"),
    "schema_modalities": ("schema_document", "schema_audio", "schema_video"),
}


def test_readme_cli_help_snippet_executes():
    # region Snippet:cu_cli_help
    result = invoke_cli(
        ["--help"], executable="cu-cli",
    )
    # endregion
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


def test_external_install_and_login_commands_have_safe_local_validation():
    install = ["python", "-m", "pip", "install", "cu-cli"]
    result = subprocess.run(
        [sys.executable, *install[1:-1], "--help"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "install" in result.stdout and "--no-index" in result.stdout
    # region Snippet:cli_install
    record_external(
        install,
        reason="External prerequisite: pip parser checked locally; wheel installation is covered by release CI.",
    )
    # endregion
    login = ["az", "login"]
    # region Snippet:azure_login
    record_external(
        login,
        reason="External interactive prerequisite: Azure CLI sign-in is classified explicitly and never executed by CU tests.",
    )
    # endregion


def test_frontend_interchange_uses_real_azure_cli_parser_and_shared_profile(monkeypatch):
    from azext_content_understanding import _analyzers
    from cu_cli.profile import ProfileStore

    monkeypatch.setattr("azure.cli.core.util.handle_version_update", lambda: None)
    monkeypatch.setenv("CU_TEST_REC_MODE", "playback")
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    copy_sample_invoice()
    setup = invoke_cli(["profile", "set", "api_key", "playback-dummy-key"])
    assert setup.exit_code == 0, setup.output
    analyzer = SimpleNamespace(
        analyzer_id="prebuilt-layout", created_at=None, last_modified_at=None,
        as_dict=lambda: {"analyzerId": "prebuilt-layout"},
    )
    monkeypatch.setattr(
        _analyzers, "create_content_understanding_client",
        lambda *_args, **_kwargs: SimpleNamespace(list_analyzers=lambda: [analyzer]),
    )
    # region Snippet:shared_frontend_profile
    invoke_cli(
        ["profile", "set", "endpoint", "https://<resource-name>.services.ai.azure.com/"],
        placeholder_values={"resource-name": "example"},
        comment="Save the endpoint with the standalone frontend.",
    )
    result = invoke_azure(
        ["cu", "analyzer", "list", "--output", "table"],
        comment="Use the same default profile with the Azure CLI extension.",
    )
    assert result == [{"analyzerId": "prebuilt-layout"}]
    invoke_azure(
        ["cu", "profile", "set", "--key", "default_analyzer", "--value", "prebuilt-layout"],
        comment="Change the default analyzer with the Azure CLI extension.",
    )
    assert ProfileStore.load().get("default_analyzer") == "prebuilt-layout"
    with use_cassette("analyze_single"):
        result = invoke_cli(
            ["analyze", "sample_invoice.pdf", "--json"],
            comment="Use that setting with the standalone frontend.",
        )
    # endregion
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["result"]["analyzerId"] == "prebuilt-layout"
    assert payload["result"]["contents"][0]["markdown"]
    result = invoke_cli(["profile", "get", "default_analyzer"])
    assert result.stdout.strip() == "prebuilt-layout"


def test_readme_frontend_interchange_preserves_step_comments():
    readme = _README.read_text(encoding="utf-8")
    snippet = readme.split("<!-- Snippet:shared_frontend_profile -->", 1)[1].split("```", 2)[1]

    assert [line for line in snippet.splitlines() if line.startswith("# ")] == [
        "# Save the endpoint with the standalone frontend.",
        "# Use the same default profile with the Azure CLI extension.",
        "# Change the default analyzer with the Azure CLI extension.",
        "# Use that setting with the standalone frontend.",
    ]


def test_recording_invoice_fixture_matches_public_sample():
    public_sample = _PRODUCT_ROOT / "sample_files" / "sample_invoice.pdf"
    sample = copy_sample_invoice("documents/sample_invoice.pdf")
    content = sample.read_bytes()

    assert content == public_sample.read_bytes()
    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert not sample.samefile(public_sample)


def test_local_profile_output_ignores_host_terminal_coloring(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("TERM", "xterm-256color")
    result = invoke_cli(["profile", "set", "api_version", "2025-11-01"])
    assert result.exit_code == 0, result.output
    assert "profile 'default'" in result.output
    assert "\x1b[" not in result.output
    result = invoke_cli(["profile", "show"])
    assert result.exit_code == 0, result.output
    assert "2025-11-01" in result.output
    assert "\x1b[" not in result.output


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
    prebuilt = readme.split("## Use prebuilt analyzers\n", 1)[1].split("\n## ", 1)[0]

    assert (
        "cu analyze sample_invoice.pdf --analyzer prebuilt-layout\n"
        "# `-a` is the short form of `--analyzer`.\n"
        "cu analyze sample_invoice.pdf -a prebuilt-layout\n"
    ) in prebuilt
    remaining_content = readme.split("cu analyze sample_invoice.pdf -a prebuilt-layout\n", 1)[1]
    assert "--analyzer" not in remaining_content


def test_readme_video_url_uses_default_markdown_output():
    readme = _README.read_text(encoding="utf-8")
    snippet = readme.split("<!-- Snippet:analyze_url -->", 1)[1].split("```", 2)[1]

    assert "-a prebuilt-videoSearch" in snippet
    assert "--json" not in snippet


def test_directory_workflow_uses_explicit_input_directory():
    for path, identifiers in (
        (_README, ("analyze_pattern",)),
        (_USAGE_GUIDE, ("analyze_pattern", "analyze_recursive", "analyze_recursive_report")),
    ):
        content = path.read_text(encoding="utf-8")
        for identifier in identifiers:
            snippet = content.split(f"<!-- Snippet:{identifier} -->", 1)[1].split("```", 2)[1]
            assert "--source my_document_dir" in snippet

    readme = _README.read_text(encoding="utf-8")
    guide = _USAGE_GUIDE.read_text(encoding="utf-8")
    assert "`./my_document_dir/invoice-01.pdf`" in readme
    assert "Place the input PDFs in `my_document_dir`" in guide
    assert "my_document_dir/nested/sample_invoice.pdf\n" in guide


def test_api_version_description_matches_cli_help():
    for path in (_README, _USAGE_GUIDE):
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        assert API_VERSION_HELP in normalized


def test_usage_guide_separates_read_only_examples_from_mutations():
    expected = {
        "profile_workflow": ("profile_show", "profile_get_endpoint", "profile_list", "profile_show_prod"),
        "analyzer_management": ("analyzer_list", "analyzer_show"),
        "diagnose_configuration": ("doctor", "doctor_named"),
        "configure_model_mappings": ("profile_completion_model", "profile_embedding_model"),
    }
    for scenario, members in expected.items():
        assert DOC_SCENARIOS[scenario] == members

    guide = _USAGE_GUIDE.read_text(encoding="utf-8")
    readiness = guide.split("### Check readiness\n", 1)[1].split("\n### ", 1)[0]
    inspection = guide.split("### Inspect and manage\n", 1)[1].split("\n### ", 1)[0]
    assert "--fix-defaults" not in readiness
    assert "analyzer delete" not in inspection
    assert "analyzer copy" not in inspection
    assert "cu analyzer delete invoice_v1 --yes" not in guide
    assert "<!-- Snippet:doctor_fix_defaults -->" in guide
    assert "<!-- Snippet:analyzer_delete -->" in guide


def test_usage_guide_reuses_profile_setup_and_keeps_batch_outputs_distinct():
    guide = _USAGE_GUIDE.read_text(encoding="utf-8")
    assert guide.count("cu profile create dev") == 1
    assert guide.count("cu profile create prod") == 1
    assert guide.index("<!-- Snippet:profile_setup -->") < guide.index("<!-- Snippet:profile_workflow -->")
    assert "src-config" not in guide and "tgt-config" not in guide
    assert guide.count("<!-- Snippet:analyze_recursive -->") == 1
    assert guide.count("<!-- Snippet:analyze_recursive_report -->") == 1
    assert "--output-dir recursive-results" in guide
    assert "--output-dir batch-results" in guide


def test_usage_guide_places_examples_and_outputs_in_their_owning_sections():
    guide = _USAGE_GUIDE.read_text(encoding="utf-8")
    sections = {
        "CU CLI profiles": ("profile_deployments", "profile_sync_auth"),
        "Provisioning": ("infra_generate", "infra_custom"),
        "Analyze": ("analyze_directory", "analyze_skip", "analyze_reanalyze", "analysis_timing"),
        "Analyzers": ("schema_modalities", "schema_base", "analyzer_test_preview", "analyzer_test_batch"),
        "Content Understanding defaults": ("defaults_show", "defaults_json_output", "defaults_replace"),
        "Diagnostics and environment": ("diagnose_configuration", "doctor_fix_defaults"),
        "Upgrade": ("upgrade_check", "upgrade_apply"),
    }
    for heading, identifiers in sections.items():
        section = guide.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
        assert all(f"<!-- Snippet:{identifier} -->" in section for identifier in identifiers)

    precedence = guide.split("### Resolution precedence\n", 1)[1].split("\n### ", 1)[0]
    assert (
        precedence.index("Snippet:analyzer_list_active")
        < precedence.index("Snippet:runtime_info")
        < precedence.index("Snippet:analyzer_list_prod")
    )

    defaults_read = guide.split("### Show remote mappings\n", 1)[1].split("\n### ", 1)[0]
    assert defaults_read.index("Snippet:defaults_show") < defaults_read.index("Snippet:defaults_json_output")
    assert defaults_read.index("Snippet:defaults_json_output") < defaults_read.index("Snippet:defaults_table")
    assert "## Additional workflows" not in guide
    assert "generated from passing command tests" not in guide
    assert "sanitized service recording" not in guide


def test_new_command_examples_have_distinct_sources_and_owning_sections():
    readme = _README.read_text(encoding="utf-8")
    prebuilt = readme.split("## Use prebuilt analyzers\n", 1)[1].split("\n## ", 1)[0]
    assert "<!-- Snippet:analyzer_list_prebuilt -->" in prebuilt
    assert "<!-- Snippet:analyzer_list -->" not in prebuilt
    assert "analyzer_list" in DOC_SCENARIOS["analyzer_management"]

    guide = _USAGE_GUIDE.read_text(encoding="utf-8")
    sections = {
        "Select multiple local inputs": ("analyze_files_preview", "analyze_sources_preview"),
        "Inspect service usage": ("analyze_usage",),
        "Create a schema": ("schema_validate_strict",),
        "Copy within a resource": ("analyzer_copy_same_resource",),
    }
    for heading, identifiers in sections.items():
        section = guide.split(f"### {heading}\n", 1)[1].split("\n### ", 1)[0]
        assert all(f"<!-- Snippet:{identifier} -->" in section for identifier in identifiers)
    assert "../README.md#supported-content-understanding-api-versions" in guide
