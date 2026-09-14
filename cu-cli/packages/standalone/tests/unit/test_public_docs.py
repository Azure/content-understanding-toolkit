# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
import shlex
from pathlib import Path

from click.testing import CliRunner
import pytest

from cu_cli.apiversion import API_VERSION_HELP
from cu_cli.cli import main


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


# [START cu_cli_help]
CU_CLI_HELP_COMMAND = """\
cu-cli --help
"""
# [END cu_cli_help]


def test_readme_cli_help_snippet_executes():
    executable, *args = shlex.split(CU_CLI_HELP_COMMAND)

    assert executable == "cu-cli"
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


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
    bash_blocks = re.findall(r"```bash\n(.*?)```", usage_guide, flags=re.DOTALL)
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
