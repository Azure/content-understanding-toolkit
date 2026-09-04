"""Tests for the framework-neutral command registry and Click adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from click.testing import CliRunner

from cu_cli.cli import main
from cu_cli_core.command_spec import (
    ANALYZER_SHOW,
    COMMAND_SPECS,
    CommandBindingError,
    SurfaceClassification,
    bind_command_arguments,
    build_request,
    get_command_spec,
    resolve_identifier,
)
from cu_cli_core.contracts import AnalyzerShowRequest

pytestmark = pytest.mark.unit


def test_registry_uses_lazy_identifiers_and_unique_paths():
    assert get_command_spec("analyzer", "show") is ANALYZER_SHOW
    assert len({spec.path for spec in COMMAND_SPECS}) == len(COMMAND_SPECS)
    assert ANALYZER_SHOW.operation == "cu_cli_core.operations.analyzers#get_analyzer"
    assert ANALYZER_SHOW.request_type == "cu_cli_core.contracts#AnalyzerShowRequest"


def test_registry_lazy_identifiers_resolve():
    for spec in COMMAND_SPECS:
        assert callable(resolve_identifier(spec.operation))
        assert isinstance(resolve_identifier(spec.request_type), type)


def test_analyzer_show_positional_and_named_forms_bind_identically():
    positional = bind_command_arguments(
        ANALYZER_SHOW,
        {"positional_analyzer_name": "invoice-v1", "analyzer_name": None},
    )
    named = bind_command_arguments(
        ANALYZER_SHOW,
        {"positional_analyzer_name": None, "analyzer_name": "invoice-v1"},
    )

    assert positional == named == {"name": "invoice-v1"}
    assert ANALYZER_SHOW.arguments[1].classification is SurfaceClassification.STANDALONE_SHORTCUT


def test_analyzer_show_builds_typed_normalized_request():
    request = build_request(
        ANALYZER_SHOW,
        {"positional_analyzer_name": None, "analyzer_name": " invoice-v1 "},
    )

    assert request == AnalyzerShowRequest(name="invoice-v1")


def test_analyzer_show_binding_rejects_duplicate_or_missing_name():
    with pytest.raises(CommandBindingError, match="provide name only once"):
        bind_command_arguments(
            ANALYZER_SHOW,
            {
                "positional_analyzer_name": "invoice-v1",
                "analyzer_name": "invoice-v2",
            },
        )

    with pytest.raises(CommandBindingError, match="missing required argument: --name"):
        bind_command_arguments(
            ANALYZER_SHOW,
            {"positional_analyzer_name": None, "analyzer_name": None},
        )


def test_command_spec_import_is_frontend_and_sdk_safe():
    source_root = Path(__file__).parents[2] / "src"
    core_source_root = Path(__file__).parents[3] / "core" / "src"
    script = """
import json
import sys
import cu_cli_core.command_spec
blocked = [
    name for name in sys.modules
    if name == "click"
    or name.startswith(("rich", "azure"))
    or name in {
        "cu_cli.client",
        "cu_cli.commands",
        "cu_cli_core.operations.analyzers",
        "cu_cli.output",
        "cu_cli.schema_validate",
    }
]
print(json.dumps(blocked))
"""
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join((str(core_source_root), str(source_root))),
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert json.loads(result.stdout) == []


def test_analyzer_show_help_exposes_canonical_and_positional_forms():
    result = CliRunner().invoke(main, ["analyzer", "show", "--help"])

    assert result.exit_code == 0, result.output
    assert "[ANALYZER_NAME]" in result.output
    assert "--name" in result.output
    assert "-n" in result.output
    assert "-a" in result.output
