from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from cu_cli_core.command_spec import (
    ANALYZER_LIST,
    ANALYZER_SHOW,
    COMMAND_SPECS,
    DEFAULTS_SET,
    PROFILE_COPY,
    PROFILE_SET,
    CommandBindingError,
    SurfaceClassification,
    bind_command_arguments,
    build_request,
    get_command_spec,
    resolve_identifier,
)
from cu_cli_core.contracts import AnalyzerShowRequest

pytestmark = pytest.mark.unit


def test_registry_paths_are_unique_and_resolvable():
    assert get_command_spec("analyzer", "show") is ANALYZER_SHOW
    assert len({spec.path for spec in COMMAND_SPECS}) == len(COMMAND_SPECS)
    for spec in COMMAND_SPECS:
        assert callable(resolve_identifier(spec.operation)), spec.path
        assert isinstance(resolve_identifier(spec.request_type), type), spec.path


def test_registry_metadata_is_unambiguous_for_frontend_adapters():
    supported_service_options = {"endpoint", "api-version", "auth-mode", "api-key"}

    for spec in COMMAND_SPECS:
        assert spec.path and all(part and " " not in part for part in spec.path)
        assert len(spec.service_options) == len(set(spec.service_options))
        assert set(spec.service_options) <= supported_service_options

        parser_names = [argument.parser_name for argument in spec.arguments]
        assert len(parser_names) == len(set(parser_names)), spec.path

        surface_tokens = [
            token
            for argument in spec.arguments
            for token in (argument.name, *argument.aliases)
        ]
        assert len(surface_tokens) == len(set(surface_tokens)), spec.path


def test_analyzer_show_canonical_and_positional_forms_bind_identically():
    positional = bind_command_arguments(
        ANALYZER_SHOW,
        {"positional_analyzer_name": "invoice-v1", "analyzer_name": None},
    )
    canonical = bind_command_arguments(
        ANALYZER_SHOW,
        {"positional_analyzer_name": None, "analyzer_name": "invoice-v1"},
    )

    assert positional == canonical == {"name": "invoice-v1"}
    assert ANALYZER_SHOW.arguments[1].classification is SurfaceClassification.STANDALONE_SHORTCUT


@pytest.mark.parametrize(
    ("path", "canonical", "shortcut", "expected"),
    [
        (
            ("analyzer", "show"),
            {"analyzer_name": "invoice-v1"},
            {"positional_analyzer_name": "invoice-v1"},
            {"name": "invoice-v1"},
        ),
        (
            ("analyzer", "create"),
            {"analyzer_name": "invoice-v1", "schema_path": Path("schema.json")},
            {
                "positional_analyzer_name": "invoice-v1",
                "schema_path": Path("schema.json"),
            },
            {"name": "invoice-v1", "schema": Path("schema.json")},
        ),
        (
            ("analyzer", "delete"),
            {"analyzer_name": "invoice-v1"},
            {"positional_analyzer_name": "invoice-v1"},
            {"name": "invoice-v1"},
        ),
        (
            ("analyzer", "test"),
            {"analyzer_name": "invoice-v1"},
            {"positional_analyzer_name": "invoice-v1"},
            {"name": "invoice-v1", "concurrency": 4},
        ),
        (
            ("analyzer", "copy"),
            {"named_source": "dev", "named_destination": "prod"},
            {"positional_source": "dev", "positional_destination": "prod"},
            {"source": "dev", "destination": "prod"},
        ),
        (
            ("analyzer", "validate"),
            {"named_schema_path": Path("schema.json")},
            {"positional_schema_path": Path("schema.json")},
            {"schema": Path("schema.json")},
        ),
    ],
)
def test_canonical_and_standalone_shortcut_forms_bind_identically(
    path,
    canonical,
    shortcut,
    expected,
):
    spec = get_command_spec(*path)

    assert bind_command_arguments(spec, canonical) == expected
    assert bind_command_arguments(spec, shortcut) == expected


def test_analyzer_show_builds_normalized_typed_request():
    request = build_request(
        ANALYZER_SHOW,
        {"positional_analyzer_name": None, "analyzer_name": " invoice-v1 "},
    )

    assert request == AnalyzerShowRequest(name="invoice-v1")


def test_profile_set_canonical_and_positional_forms_bind_identically():
    canonical = bind_command_arguments(
        PROFILE_SET,
        {
            "profile_key": "endpoint",
            "profile_value": "https://example/",
            "profile_name": "dev",
        },
    )
    shortcut = bind_command_arguments(
        PROFILE_SET,
        {
            "positional_profile_key": "endpoint",
            "positional_profile_value": "https://example/",
            "profile_name": "dev",
        },
    )

    assert canonical == shortcut == {
        "key": "endpoint",
        "value": "https://example/",
        "name": "dev",
    }


def test_profile_copy_destination_is_required_but_source_defaults_to_active():
    assert bind_command_arguments(
        PROFILE_COPY,
        {"destination_profile": "prod"},
    ) == {"destination": "prod"}


def test_defaults_set_does_not_implicitly_select_profile_mappings():
    request = build_request(DEFAULTS_SET, {})

    assert request.from_profile is False
    assert request.models == ()


def test_frontend_presentation_arguments_are_not_bound_to_core_request():
    request = build_request(
        ANALYZER_LIST,
        {"kind": "custom", "sort_by": "createdAt", "json_output": True},
    )

    assert request.kind == "custom"
    assert request.sort_by == "createdAt"


@pytest.mark.parametrize(
    "parsed, message",
    [
        (
            {
                "positional_analyzer_name": "invoice-v1",
                "analyzer_name": "invoice-v2",
            },
            "provide name only once",
        ),
        (
            {"positional_analyzer_name": None, "analyzer_name": None},
            "missing required argument: --name",
        ),
    ],
)
def test_analyzer_show_rejects_invalid_bindings(parsed, message):
    with pytest.raises(CommandBindingError, match=message):
        bind_command_arguments(ANALYZER_SHOW, parsed)


def test_registry_import_is_frontend_sdk_and_side_effect_safe():
    source_root = Path(__file__).parents[1] / "src"
    script = """
import json
import sys
import cu_cli_core.command_spec
import cu_cli_core.contracts
import cu_cli_core.errors
import cu_cli_core.service_options
blocked = [
    name for name in sys.modules
    if name == "click"
    or name.startswith(("rich", "knack", "azure"))
    or name.startswith(("cu_cli.", "azext_"))
]
print(json.dumps(blocked))
"""
    env = dict(os.environ, PYTHONPATH=str(source_root))
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        cwd=source_root,
    )

    assert json.loads(result.stdout) == []
