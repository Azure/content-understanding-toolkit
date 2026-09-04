# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""End-to-end CLI tests via Click's CliRunner (offline commands only)."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from types import SimpleNamespace

import click
from click.testing import CliRunner

from cu_cli.apiversion import API_VERSION_HELP
import cu_cli.commands.analyze as analyze_module
from cu_cli.cli import main
from cu_cli.core.analyze import AnalyzeResponse
from cu_cli.errors import CuCliError


import pytest

pytestmark = pytest.mark.unit

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_BOX_RE = re.compile(r"[│╭╮╰╯─]")


def _plain(output: str) -> str:
    """ANSI/box-stripped, whitespace-collapsed view of CLI output.

    rich-click word-wraps help and error-panel text to the console width and
    draws panel borders; collapsing whitespace and dropping box-drawing glyphs
    makes substring assertions robust to width differences (local TTY vs CI).
    """
    text = _ANSI_RE.sub("", output)
    text = _BOX_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _run(*args, **kwargs):
    return CliRunner().invoke(main, list(args), **kwargs)


def _create_profile(name: str) -> None:
    result = _run("profile", "create", name)
    assert result.exit_code == 0, result.output


def test_help_lists_all_commands():
    res = _run("--help")
    assert res.exit_code == 0
    for cmd in (
        "infra", "profile", "doctor", "env-var", "defaults", "analyze",
        "analyzer", "upgrade",
    ):
        assert cmd in res.output


def test_main_help_ends_with_supported_api_versions():
    result = _run("--help")
    output = _plain(result.output)
    assert output.endswith(API_VERSION_HELP)
    assert "Environment variables:" not in output
    assert "For environment-variable help, run cu env-var -h." in output
    assert "generates an azd/Bicep project used to provision" in output
    assert "`azd up` performs the Azure provisioning" in output
    assert "local CU CLI profile" in output
    assert "ready-to-use prebuilt analyzer or create a custom analyzer" in output
    assert "If CU CLI is not connected" not in output
    assert "cu profile set endpoint https://<resource-name>.services.ai.azure.com/" in output
    assert "cu analyze sample.pdf -a prebuilt-layout" in output
    assert "prebuilt-layout analyzer" in output
    assert output.index("cu doctor") < output.index("cu analyze sample.pdf")


@pytest.mark.parametrize(
    "args",
    [
        ("analyze", "--help"),
        ("analyzer", "list", "--help"),
        ("analyzer", "show", "--help"),
        ("analyzer", "create", "--help"),
        ("analyzer", "delete", "--help"),
        ("analyzer", "copy", "--help"),
        ("analyzer", "schema", "create", "--help"),
        ("analyzer", "validate", "--help"),
        ("analyzer", "test", "--help"),
        ("defaults", "show", "--help"),
        ("defaults", "set", "--help"),
        ("doctor", "--help"),
        ("infra", "generate", "--help"),
    ],
)
def test_api_version_help_is_consistent(args):
    result = _run(*args)

    assert result.exit_code == 0
    assert API_VERSION_HELP in _plain(result.output)


def test_bare_cu_prints_help():
    res = _run()
    assert res.exit_code == 0
    assert "Usage:" in res.output


def test_env_var_help_documents_all_supported_variables():
    output = _plain(_run("env-var", "--help").output)

    for name in (
        "CU_ENDPOINT",
        "CU_API_KEY",
        "CU_AUTH_MODE",
        "CU_API_VERSION",
        "CU_TELEMETRY",
        "CU_NO_UPDATE_CHECK",
        "CU_ON_EXISTS",
    ):
        assert name in output
    assert "sensitive; always redacted" in output
    assert "command flags" not in output
    assert "selected config" not in output
    assert "selected CU CLI profile" in output
    assert "If CU CLI is not connected" not in output
    assert "Supported CU API versions:" not in output
    assert output.count("cu env-var list") == 1


def test_env_var_list_shows_only_set_recognized_variables(monkeypatch):
    monkeypatch.delenv("CU_NO_UPDATE_CHECK")
    monkeypatch.setenv("CU_ENDPOINT", "https://example.services.ai.azure.com/")
    monkeypatch.setenv("CU_AUTH_MODE", "login")
    monkeypatch.setenv("UNRELATED_VARIABLE", "not shown")

    result = _run("env-var", "list")
    output = _plain(result.output)

    assert result.exit_code == 0, result.output
    assert "CU_ENDPOINT" in output
    assert "https://example.services.ai.azure.com/" in output
    assert "CU_AUTH_MODE" in output
    assert "login" in output
    assert "CU_API_VERSION" not in output
    assert "UNRELATED_VARIABLE" not in output


def test_env_var_list_redacts_sensitive_values_in_all_formats(monkeypatch):
    secret = "do-not-print-this-api-key"
    monkeypatch.delenv("CU_NO_UPDATE_CHECK")
    monkeypatch.setenv("CU_API_KEY", secret)

    table_result = _run("env-var", "list")
    json_result = _run("env-var", "list", "--json")

    assert table_result.exit_code == 0, table_result.output
    assert secret not in table_result.output
    assert "********" in table_result.output
    assert json_result.exit_code == 0, json_result.output
    assert secret not in json_result.output
    assert json.loads(json_result.stdout) == [
        {
            "name": "CU_API_KEY",
            "value": "********",
            "scope": "authentication",
            "sensitive": True,
        }
    ]


@pytest.mark.parametrize(
    ("args", "commands"),
    [
        (
            ("--help",),
            (
                "cu infra generate",
                "cu profile set endpoint https://<resource-name>.services.ai.azure.com/",
                "cu doctor",
                "cu analyze sample.pdf -a prebuilt-layout",
            ),
        ),
        (
            ("analyze", "--help"),
            (
                "cu analyze FILE",
                "cu analyze FILE -a prebuilt-invoice --json",
                "cu analyze --source DIRECTORY --output-dir TARGET_DIR",
            ),
        ),
        (
            ("analyzer", "--help"),
            (
                "cu analyzer list",
                "cu analyzer schema create --from-sample SAMPLE_FILE",
                "cu analyzer create NAME --schema SCHEMA.json",
            ),
        ),
        (
            ("defaults", "--help"),
            ("cu defaults show", "cu defaults set --from-profile"),
        ),
        (
            ("env-var", "--help"),
            ("cu env-var list --json",),
        ),
        (
            ("env-var", "list", "--help"),
            ("cu env-var list", "cu env-var list --json"),
        ),
        (
            ("infra", "generate", "--help"),
            (
                "cu infra generate",
                "cu infra generate --foundry-endpoint URL",
            ),
        ),
        (
            ("profile", "--help"),
            (
                "cu profile show",
                "cu profile create dev",
                "cu profile set endpoint URL",
                "cu profile set-active dev",
            ),
        ),
        (("profile", "create", "--help"), ("cu profile create dev",)),
        (
            ("profile", "show", "--help"),
            (
                "cu profile show",
                "cu profile show --name dev",
                "cu profile show --deployments",
            ),
        ),
        (
            ("profile", "get", "--help"),
            ("cu profile get endpoint",),
        ),
        (
            ("profile", "set", "--help"),
            (
                "cu profile set endpoint URL",
                "cu profile set auth_mode login --name dev",
            ),
        ),
        (
            ("profile", "unset", "--help"),
            ("cu profile unset api_key",),
        ),
        (("profile", "list", "--help"), ("cu profile list",)),
        (("profile", "set-active", "--help"), ("cu profile set-active dev",)),
        (
            ("profile", "copy", "--help"),
            (
                "cu profile copy dev test",
                "cu profile copy --source dev --destination test",
                "cu profile copy --destination test",
            ),
        ),
        (
            ("profile", "rename", "--help"),
            ("cu profile rename dev prod",),
        ),
        (("profile", "delete", "--help"), ("cu profile delete dev",)),
        (
            ("profile", "sync-defaults", "--help"),
            ("cu profile sync-defaults --name dev",),
        ),
        (
            ("doctor", "--help"),
            ("cu doctor", "cu doctor --profile NAME", "cu doctor --fix-defaults"),
        ),
        (
            ("analyzer", "list", "--help"),
            (
                "cu analyzer list",
                "cu analyzer list --kind custom",
                "cu analyzer list --json",
            ),
        ),
        (
            ("analyzer", "show", "--help"),
            ("cu analyzer show ANALYZER_NAME",),
        ),
        (
            ("analyzer", "create", "--help"),
            (
                "cu analyzer create ANALYZER_NAME --schema SCHEMA.json",
                "cu analyzer create --name ANALYZER_NAME --schema SCHEMA.json",
            ),
        ),
        (
            ("analyzer", "delete", "--help"),
            (
                "cu analyzer delete ANALYZER_NAME",
                "cu analyzer delete -n ANALYZER_NAME --yes",
            ),
        ),
        (
            ("analyzer", "copy", "--help"),
            (
                "cu analyzer copy SOURCE DESTINATION",
                (
                    "cu analyzer copy --source SOURCE --destination DESTINATION "
                    "--source-profile dev --destination-profile prod"
                ),
                (
                    "cu analyzer copy SOURCE DESTINATION "
                    "--source-resource RESOURCE --destination-resource RESOURCE"
                ),
            ),
        ),
        (
            ("analyzer", "schema", "--help"),
            (
                "cu analyzer schema create --output-file SCHEMA.json",
                "cu analyzer schema create --from-sample SAMPLE_FILE --output-file SCHEMA.json",
            ),
        ),
        (
            ("analyzer", "schema", "create", "--help"),
            (
                "cu analyzer schema create --output-file SCHEMA.json",
                "cu analyzer schema create --type classification --output-file SCHEMA.json",
                "cu analyzer schema create --from-sample SAMPLE_FILE --output-file SCHEMA.json",
            ),
        ),
        (
            ("analyzer", "validate", "--help"),
            (
                "cu analyzer validate SCHEMA.json",
                "cu analyzer validate SCHEMA.json --strict --spec",
            ),
        ),
        (
            ("analyzer", "test", "--help"),
            (
                "cu analyzer test ANALYZER_NAME SAMPLE_DIR",
                (
                    "cu analyzer test --name ANALYZER_NAME --source SAMPLE_DIR "
                    "--json --output-file REPORT.json"
                ),
            ),
        ),
        (
            ("defaults", "show", "--help"),
            ("cu defaults show", "cu defaults show --table"),
        ),
        (
            ("defaults", "set", "--help"),
            (
                "cu defaults set --from-profile",
                "cu defaults set --model MODEL=DEPLOYMENT",
            ),
        ),
        (
            ("upgrade", "--help"),
            ("cu upgrade --check", "cu upgrade"),
        ),
    ],
)
def test_command_help_shows_common_commands(args, commands):
    result = _run(*args)

    assert result.exit_code == 0, result.output
    output = _plain(result.output)
    assert "Common commands:" in output
    assert output.index("Common commands:") > output.index("Options")
    for command in commands:
        assert command in output
        parsed = _run(*shlex.split(command)[1:], "--help")
        assert parsed.exit_code == 0, f"{command}: {parsed.output}"


def test_every_command_help_has_common_commands():
    missing: list[str] = []

    def walk(command: click.Command, path: tuple[str, ...]) -> None:
        if not command.epilog or "Common commands:" not in command.epilog:
            missing.append(" ".join(path))
        if isinstance(command, click.Group):
            for name, child in command.commands.items():
                walk(child, (*path, name))

    walk(main, ("cu",))
    assert not missing


def test_profile_help_exposes_and_describes_rename_command():
    result = _run("profile", "--help")

    assert result.exit_code == 0, result.output
    output = _plain(result.output)
    assert "rename" in output
    assert "Rename a CU CLI profile while preserving its values and active state." in output


@pytest.mark.parametrize("command", ["create", "copy", "rename"])
def test_profile_destination_help_uses_named_profile_language(command):
    result = _run("profile", command, "--help")

    assert result.exit_code == 0, result.output
    output = _plain(result.output)
    assert "profile" in output.lower()
    assert "hyphens (-) or underscores (_)" in output
    assert "'default' and 'model_deployments' are reserved" in output


def test_analyze_help_separates_warning_from_common_commands():
    result = _run("analyze", "--help")

    assert result.exit_code == 0, result.output
    lines = [_ANSI_RE.sub("", line).strip() for line in result.output.splitlines()]
    warning_end = next(
        index for index, line in enumerate(lines)
        if "CU_ON_EXISTS=error|skip|reanalyze" in line
    )
    common_commands = lines.index("Common commands:")
    assert any(not line for line in lines[warning_end + 1:common_commands])


@pytest.mark.parametrize(
    ("args", "descriptions"),
    [
        (
            ("analyze", "--help"),
            (
                (
                    "Analyze one file with the configured default analyzer."
                ),
                "Extract invoice fields as JSON.",
                (
                    "Analyze immediate files in DIRECTORY and write all result files "
                    "to TARGET_DIR instead of beside each input."
                ),
            ),
        ),
        (
            ("analyzer", "--help"),
            (
                "List available analyzers.",
                "Create a custom schema from one document sample.",
                "Create a custom analyzer from a schema.",
            ),
        ),
        (
            ("defaults", "--help"),
            (
                "Show Content Understanding model-to-deployment mappings.",
                "Apply model mappings from the current profile as defaults.",
            ),
        ),
        (
            ("infra", "generate", "--help"),
            (
                "Generate a project for a new resource and optional model deployments. Run azd up to provision it.",
                "Generate a project for optional model deployments and defaults on an existing resource. Run azd up to apply it.",
            ),
        ),
        (
            ("profile", "--help"),
            (
                "Show the active CU CLI profile.",
                "Configure the default CU CLI profile.",
                "Create a CU CLI profile for another resource.",
                "Select a saved CU CLI profile.",
            ),
        ),
        (
            ("upgrade", "--help"),
            (
                "Check for a newer release without installing it.",
                "Check for a newer release and offer to install it.",
            ),
        ),
    ],
)
def test_common_command_examples_explain_their_purpose(args, descriptions):
    result = _run(*args)

    assert result.exit_code == 0, result.output
    output = _plain(result.output)
    for description in descriptions:
        assert description in output


def test_version():
    res = _run("--version")
    assert res.exit_code == 0
    assert "0.1.0" in res.output


def test_schema_template_stamps_default_version():
    res = _run("analyzer", "schema", "create", "--output-file", "s.json")
    assert res.exit_code == 0
    body = json.loads(Path("s.json").read_text())
    assert body["apiVersion"] == "2025-11-01"
    assert "example_string_field" in body["fieldSchema"]["fields"]


def test_schema_template_respects_api_flag():
    res = _run("analyzer", "schema", "create", "--output-file", "p.json",
               "--api-version", "2025-11-01")
    assert res.exit_code == 0
    assert json.loads(Path("p.json").read_text())["apiVersion"] == "2025-11-01"


def test_schema_template_uses_completion_model_from_active_profile():
    assert _run(
        "profile", "set", "model_deployments.gpt-5.2", "dep-gpt"
    ).exit_code == 0
    res = _run("analyzer", "schema", "create", "--output-file", "s.json")
    assert res.exit_code == 0, res.output
    body = json.loads(Path("s.json").read_text())
    assert body["models"]["completion"] == "gpt-5.2"


def test_schema_template_uses_completion_model_from_named_profile():
    _create_profile("westus_preview")
    assert _run(
        "profile", "set", "model_deployments.gpt-5.2", "dep-gpt",
        "--name", "westus_preview"
    ).exit_code == 0
    res = _run(
        "analyzer", "schema", "create", "--output-file", "n.json",
        "--profile", "westus_preview"
    )
    assert res.exit_code == 0, res.output
    body = json.loads(Path("n.json").read_text())
    assert body["models"]["completion"] == "gpt-5.2"


def test_schema_template_defaults_to_extraction_type():
    res = _run("analyzer", "schema", "create", "--output-file", "extract.json")
    assert res.exit_code == 0, res.output
    body = json.loads(Path("extract.json").read_text())
    fields = body["fieldSchema"]["fields"]
    assert "example_string_field" in fields
    assert fields["example_string_field"]["method"] == "extract"
    assert "example_number_field" in fields
    assert fields["example_number_field"]["type"] == "number"
    assert "example_summary" in fields
    assert fields["example_summary"]["method"] == "generate"
    assert "one-line summary" in fields["example_summary"]["description"]
    assert "example_classify_field" in fields
    assert fields["example_classify_field"]["method"] == "classify"
    assert "enumDescriptions" in fields["example_classify_field"]
    assert "option_a" in fields["example_classify_field"]["enumDescriptions"]
    assert "example_table_field" in fields
    assert fields["example_table_field"]["type"] == "array"
    assert fields["example_table_field"]["items"]["type"] == "object"
    table_props = fields["example_table_field"]["items"]["properties"]
    assert "column_description" in table_props
    assert "column_amount" in table_props
    assert "column_category" in table_props
    column_category = table_props["column_category"]
    assert "enumDescriptions" in column_category
    assert "product" in column_category["enumDescriptions"]


def test_schema_template_classification_type_has_creatable_categories():
    res = _run(
        "analyzer", "schema", "create", "--output-file", "classify.json",
        "--type", "classification"
    )
    assert res.exit_code == 0, res.output
    body = json.loads(Path("classify.json").read_text())
    assert "fieldSchema" not in body
    cfg = body["config"]
    assert cfg["enableSegment"] is True
    assert "contentCategories" in cfg
    categories = cfg["contentCategories"]
    assert "invoice" in categories
    # Default categories are description-only so the template is directly creatable;
    # routing (analyzerId) is opt-in and requires the target analyzer to already exist.
    for name, definition in categories.items():
        assert definition.get("description"), f"category {name} needs a description"
        assert "analyzerId" not in definition, (
            f"default category {name} must not hardcode routing to a non-existent analyzer"
        )
    # Routing guidance is surfaced in the template description.
    assert "analyzerId" in body["description"]


class _FakeSuggestResult:
    def __init__(self, fields):
        self.contents = [SimpleNamespace(fields={"schema": {"valueJson": fields}})]


class _FakeSuggestPoller:
    def __init__(self, fields):
        self._result = _FakeSuggestResult(fields)

    def result(self):
        return self._result


class _FakeSuggestClient:
    def __init__(self, fields):
        self.fields = fields

    def begin_analyze(self, analyzer_id, *, inputs):
        assert analyzer_id == "prebuilt-documentFieldSchema"
        assert len(inputs) == 1
        return _FakeSuggestPoller(self.fields)


def test_schema_create_defaults_to_template_mode():
    res = _run("analyzer", "schema", "create", "--output-file", "default.json")
    assert res.exit_code == 0, res.output
    assert Path("default.json").exists()


def test_schema_create_refuses_to_overwrite_existing_file():
    output = Path("existing.json")
    output.write_text('{"marker": "preserve-me"}\n', encoding="utf-8")

    res = _run("analyzer", "schema", "create", "--output-file", str(output))

    assert res.exit_code != 0
    assert "schema output already exists" in _plain(res.output)
    assert "--force" in _plain(res.output)
    assert output.read_text(encoding="utf-8") == '{"marker": "preserve-me"}\n'


@pytest.mark.parametrize("force", [False, True])
def test_schema_create_reports_output_parent_that_is_a_file(force):
    parent = Path("parent-file")
    parent.write_text("not a directory", encoding="utf-8")
    args = [
        "analyzer",
        "schema",
        "create",
        "--output-file",
        str(parent / "schema.json"),
    ]
    if force:
        args.append("--force")

    res = _run(*args)
    output = _plain(res.output)

    assert res.exit_code != 0
    assert "schema output parent path is not a directory: parent-file" in output
    assert "schema output already exists" not in output
    assert parent.read_text(encoding="utf-8") == "not a directory"


def test_schema_create_force_overwrites_existing_file():
    output = Path("existing.json")
    output.write_text('{"marker": "replace-me"}\n', encoding="utf-8")

    res = _run(
        "analyzer",
        "schema",
        "create",
        "--output-file",
        str(output),
        "--force",
    )

    assert res.exit_code == 0, res.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["analyzerId"] == "my_analyzer_v1"
    assert "marker" not in payload


def test_schema_create_checks_existing_output_before_sample_service_call(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.suggest_schema_payload_from_sample",
        lambda **_kwargs: pytest.fail("schema suggestion service must not be called"),
    )
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    output = Path("existing.json")
    output.write_text('{"marker": "preserve-me"}\n', encoding="utf-8")

    res = _run(
        "analyzer",
        "schema",
        "create",
        "--from-sample",
        str(sample),
        "--output-file",
        str(output),
    )

    assert res.exit_code != 0
    assert "schema output already exists" in _plain(res.output)
    assert output.read_text(encoding="utf-8") == '{"marker": "preserve-me"}\n'


def test_schema_template_rejects_service_reserved_hyphenated_id():
    res = _run(
        "analyzer", "schema", "create",
        "--name", "customer-invoice",
        "--output-file", "invalid.json",
    )
    output = _plain(res.output)
    assert res.exit_code != 0
    assert "Hyphens are reserved for service-provided prebuilt analyzer IDs" in output
    assert "prebuilt-invoice" in output
    assert not Path("invalid.json").exists()


def test_schema_suggest_rejects_hyphenated_id_before_service_call(monkeypatch):
    def _unexpected_service_call(**_kwargs):
        raise AssertionError("schema suggestion service must not be called")

    monkeypatch.setattr(
        "cu_cli.commands.analyzer.suggest_schema_payload_from_sample",
        _unexpected_service_call,
    )
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")

    res = _run(
        "analyzer", "schema", "create",
        "--from-sample", str(sample),
        "--name", "customer-invoice",
        "--output-file", "invalid.json",
    )
    assert res.exit_code != 0
    assert "Hyphens are reserved for service-provided prebuilt analyzer IDs" in _plain(res.output)
    assert not Path("invalid.json").exists()


def test_analyzer_create_rejects_hyphenated_id_before_service_call(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("create service must not be called"),
    )
    Path("schema.json").write_text(
        json.dumps({"analyzerId": "customer-invoice"}),
        encoding="utf-8",
    )

    res = _run("analyzer", "create", "customer-invoice", "--schema", "schema.json")
    assert res.exit_code != 0
    assert "Hyphens are reserved for service-provided prebuilt analyzer IDs" in _plain(res.output)


@pytest.mark.parametrize("payload", [[], None, "schema", 42, True])
@pytest.mark.parametrize("named_selector", [False, True])
def test_analyzer_create_rejects_non_object_root_before_service_call(
    monkeypatch, payload, named_selector
):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("create service must not be called"),
    )
    Path("schema.json").write_text(json.dumps(payload), encoding="utf-8")
    args = ["analyzer", "create", "--schema", "schema.json"]
    if named_selector:
        args.extend(["--name", "valid_analyzer_id"])
    else:
        args.insert(2, "valid_analyzer_id")

    res = _run(*args)

    assert res.exit_code != 0
    assert "schema root must be a JSON object" in _plain(res.output)


def test_analyzer_create_reports_malformed_json_location_before_service_call(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("create service must not be called"),
    )
    Path("schema.json").write_text('{"analyzerId": "example",\n}', encoding="utf-8")

    res = _run(
        "analyzer",
        "create",
        "--schema",
        "schema.json",
        "--name",
        "valid_analyzer_id",
    )

    output = _plain(res.output)
    assert res.exit_code != 0
    assert "schema file is not valid JSON" in output
    assert "line " in output
    assert " col " in output


def test_analyzer_create_rejects_ref_before_service_call(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("create service must not be called"),
    )
    body = {
        "analyzerId": "ref_repro",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-5.2"},
        "fieldSchema": {
            "fields": {
                "party": {
                    "$ref": "#/fieldSchema/definitions/party",
                    "description": "Structured party information from the document.",
                }
            },
            "definitions": {
                "party": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the identified party.",
                        }
                    },
                }
            },
        },
    }
    Path("ref.json").write_text(json.dumps(body), encoding="utf-8")

    res = _run("analyzer", "create", "ref_repro", "--schema", "ref.json")

    assert res.exit_code != 0
    output = _plain(res.output)
    assert "fieldSchema.fields.party.$ref" in output
    assert "inline the field definition" in output


@pytest.mark.parametrize("api_flag", [None, "2026-06-01-preview"])
def test_analyzer_create_uses_schema_pinned_api_version(monkeypatch, api_flag):
    captured_api_versions: list[str] = []
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.Profile.load",
        lambda **_kwargs: SimpleNamespace(api_version="2025-11-01"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda _endpoint, _key, api_version, *_args: (
            captured_api_versions.append(api_version) or object()
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.resolve_identifier",
        lambda _identifier: (
            lambda *_args, **_kwargs: SimpleNamespace(analyzer_id="versioned_analyzer")
        ),
    )
    Path("schema.json").write_text(
        json.dumps(
            {
                "analyzerId": "versioned_analyzer",
                "apiVersion": "2026-06-01-preview",
            }
        ),
        encoding="utf-8",
    )
    args = ["analyzer", "create", "versioned_analyzer", "--schema", "schema.json"]
    if api_flag is not None:
        args.extend(["--api-version", api_flag])

    res = _run(*args)

    assert res.exit_code == 0, res.output
    assert captured_api_versions == ["2026-06-01-preview"]


def test_analyzer_create_rejects_conflicting_schema_api_before_client(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.Profile.load",
        lambda **_kwargs: SimpleNamespace(api_version="2025-11-01"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("client must not be created"),
    )
    Path("schema.json").write_text(
        json.dumps(
            {
                "analyzerId": "versioned_analyzer",
                "apiVersion": "2026-06-01-preview",
            }
        ),
        encoding="utf-8",
    )

    res = _run(
        "analyzer",
        "create",
        "versioned_analyzer",
        "--schema",
        "schema.json",
        "--api-version",
        "2025-11-01",
    )

    output = _plain(res.output)
    assert res.exit_code == 2
    assert "Schema pins apiVersion '2026-06-01-preview'" in output
    assert "--api-version '2025-11-01' was passed" in output


def test_schema_suggest_writes_suggested_fields(monkeypatch):
    def _fake_payload(**_kwargs):
        return {
            "apiVersion": "2025-11-01",
            "analyzerId": "my_analyzer_v1",
            "baseAnalyzerId": "prebuilt-document",
            "fieldSchema": {
                "name": "my_analyzer_v1_schema",
                "description": "suggested",
                "fields": {
                    "InvoiceNumber": {
                        "type": "string",
                        "method": "extract",
                        "description": "Invoice id",
                    },
                    "TotalAmount": {
                        "type": "number",
                        "method": "extract",
                        "description": "Invoice total",
                    },
                },
            },
            "models": {
                "completion": "gpt-4.1",
                "embedding": "text-embedding-3-large",
            },
        }

    monkeypatch.setattr("cu_cli.commands.analyzer.suggest_schema_payload_from_sample", _fake_payload)
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")

    res = _run(
        "analyzer", "schema", "create",
        "--from-sample", str(sample),
        "--output-file", "suggested.json",
    )
    assert res.exit_code == 0, res.output
    body = json.loads(Path("suggested.json").read_text(encoding="utf-8"))
    assert "InvoiceNumber" in body["fieldSchema"]["fields"]
    assert "TotalAmount" in body["fieldSchema"]["fields"]


def test_suggest_schema_payload_from_sample_uses_prebuilt_fields(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_a, **_k: _FakeSuggestClient(
            {
                "InvoiceNumber": {
                    "type": "string",
                    "method": "extract",
                    "description": "Invoice identifier printed on the document.",
                },
                "TotalAmount": {
                    "type": "number",
                    "method": "extract",
                    "description": "Total amount due on the invoice.",
                },
                "LineItems": {
                    "type": "array",
                    "method": "generate",
                    "description": "Line items extracted from the invoice table.",
                    "items": {
                        "type": "object",
                        "method": "generate",
                        "properties": {
                            "Description": {
                                "type": "string",
                                "method": "extract",
                                "description": "Line item description from the invoice.",
                            },
                        },
                    },
                },
            }
        ),
    )
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")

    from cu_cli.commands.analyzer import suggest_schema_payload_from_sample

    body = suggest_schema_payload_from_sample(
        sample_path=sample,
        analyzer_id="my_analyzer_v1",
        api_version="2025-11-01",
    )
    assert "InvoiceNumber" in body["fieldSchema"]["fields"]
    assert "TotalAmount" in body["fieldSchema"]["fields"]
    assert body["fieldSchema"]["fields"]["LineItems"]["items"]["description"] == (
        "TODO: describe one item in this array."
    )

    Path("suggested.json").write_text(json.dumps(body), encoding="utf-8")
    result = _run("analyzer", "validate", "suggested.json", "--strict", "--spec")
    assert result.exit_code == 0, result.output


def test_schema_suggest_rejects_non_document_sample(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeSuggestClient({}))
    sample = Path("sample.mp3")
    sample.write_bytes(b"ID3")
    res = _run(
        "analyzer", "schema", "create",
        "--from-sample", str(sample),
        "--output-file", "bad.json",
    )
    assert res.exit_code != 0
    assert "expects a document file" in res.output


def test_template_then_validate_roundtrip_exit_0():
    _run("analyzer", "schema", "create", "--output-file", "s.json")
    res = _run("analyzer", "validate", "s.json")
    assert res.exit_code == 0


def test_validate_bad_type_exit_2():
    body = {
        "analyzerId": "a1", "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {"fields": {"dob": {
            "type": "datetime", "method": "extract",
            "description": "date of birth printed on the form"}}},
    }
    Path("bad.json").write_text(json.dumps(body), encoding="utf-8")
    res = _run("analyzer", "validate", "bad.json")
    assert res.exit_code == 2
    assert "got 'datetime'" in res.output


@pytest.mark.parametrize("api_version", ["2025-11-01", "2026-06-01-preview"])
@pytest.mark.parametrize("use_spec", [False, True])
def test_validate_ref_exits_2_with_and_without_spec(api_version, use_spec):
    body = {
        "analyzerId": "ref_repro",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-5.2"},
        "fieldSchema": {
            "fields": {
                "rows": {
                    "type": "array",
                    "description": "Rows extracted from the document.",
                    "items": {"$ref": "#/fieldSchema/definitions/row"},
                }
            },
            "definitions": {
                "row": {
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "string",
                            "description": "Value extracted from the row.",
                        }
                    },
                }
            },
        },
    }
    Path("ref.json").write_text(json.dumps(body), encoding="utf-8")
    args = [
        "analyzer",
        "validate",
        "ref.json",
        "--api-version",
        api_version,
    ]
    if use_spec:
        args.append("--spec")

    res = _run(*args)

    assert res.exit_code == 2
    output = _plain(res.output)
    assert "fieldSchema.fields.rows.items.$ref" in output
    assert "inline the field definition" in output


def test_validate_conflict_exit_2():
    _run("analyzer", "schema", "create", "--output-file", "s.json")
    res = _run("analyzer", "validate", "s.json", "--api-version", "2099-12-31")
    assert res.exit_code == 2


def test_validate_classification_template_roundtrip_exit_0():
    _run(
        "analyzer", "schema", "create",
        "--type", "classification",
        "--output-file", "c.json",
    )
    res = _run("analyzer", "validate", "c.json")
    assert res.exit_code == 0


def test_validate_strict_fails_on_warnings():
    body = {
        "analyzerId": "a1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {
            "fields": {
                "vendor": {
                    "type": "string",
                    "method": "extract",
                    "description": "short desc",
                }
            }
        },
    }
    Path("warn.json").write_text(json.dumps(body), encoding="utf-8")
    res = _run("analyzer", "validate", "warn.json", "--strict")
    assert res.exit_code == 2
    assert "warning" in res.output.lower()


def test_validate_strict_json_reports_failure_for_warnings():
    body = {
        "analyzerId": "a1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {
            "fields": {
                "vendor": {
                    "type": "string",
                    "method": "extract",
                    "description": "short",
                }
            }
        },
    }
    Path("warn-strict.json").write_text(json.dumps(body), encoding="utf-8")

    res = _run("analyzer", "validate", "warn-strict.json", "--strict", "--json")

    assert res.exit_code == 2
    payload = json.loads(res.output)
    assert payload["ok"] is False
    assert payload["strict"] is True
    assert payload["errors"] == []
    assert payload["warnings"]


def test_validate_json_output_contains_errors_and_warnings():
    body = {
        "analyzerId": "a1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {
            "fields": {
                "kind": {
                    "type": "string",
                    "method": "classify",
                    "description": "short desc",
                    "enum": ["invoice"],
                }
            }
        },
    }
    Path("warn_err.json").write_text(json.dumps(body), encoding="utf-8")
    res = _run("analyzer", "validate", "warn_err.json", "--json")
    assert res.exit_code == 2
    payload = json.loads(res.output)
    assert payload["ok"] is False
    assert isinstance(payload["errors"], list)
    assert isinstance(payload["warnings"], list)
    assert any(e["path"] == "fieldSchema.fields.kind.enum" for e in payload["errors"])


def test_service_command_rejects_malformed_environment_endpoint(monkeypatch):
    monkeypatch.setenv("CU_ENDPOINT", "not-a-url")
    monkeypatch.setenv("CU_AUTH_MODE", "key")
    monkeypatch.setenv("CU_API_KEY", "test-key")

    res = _run("analyzer", "list")

    assert res.exit_code == 1
    assert "invalid foundry endpoint" in res.output
    assert "unexpected error" not in res.output
    assert "Invalid URL" not in res.output


def test_upgrade_check_up_to_date(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.upgrade.fetch_latest_version_detailed",
                        lambda **_: ("0.1.0", "ok"))
    res = _run("upgrade", "--check")
    assert res.exit_code == 0
    assert "up to date" in res.output


def test_upgrade_check_newer_available(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.upgrade.fetch_latest_version_detailed",
                        lambda **_: ("9.9.9", "ok"))
    res = _run("upgrade", "--check")
    assert res.exit_code == 0
    assert "9.9.9" in res.output


def test_upgrade_uses_provider_environment(monkeypatch):
    class FakeProvider:
        name = "private feed"
        release_notes_url = "https://example.test/releases"
        source_install_hint = "install privately"

        @staticmethod
        def pip_environment():
            return {"PIP_INDEX_URL": "https://credential@example.test/simple/"}

    captured = {}

    def _subprocess_run(args, *, env):
        captured["args"] = args
        captured["env"] = env
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(
        "cu_cli.commands.upgrade.get_update_provider", lambda: FakeProvider()
    )
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.fetch_latest_version_detailed",
        lambda **_: ("9.9.9", "ok"),
    )
    monkeypatch.setattr("cu_cli.commands.upgrade.subprocess.run", _subprocess_run)
    monkeypatch.setattr("cu_cli.commands.upgrade.is_windows", lambda: False)
    res = _run("upgrade", "--yes")
    assert res.exit_code == 0, res.output
    assert captured["args"][-1] == "cu-cli==9.9.9"
    assert captured["env"]["PIP_INDEX_URL"].startswith("https://credential@")
    assert "private feed" in res.output


def test_upgrade_on_windows_uses_detached_helper_not_inprocess_pip(monkeypatch, tmp_path):
    """Regression: Windows must never run pip synchronously from inside cu.exe.

    `pip install --upgrade` is non-atomic, and Windows exclusively locks the
    running `cu.exe` file image, so an in-process upgrade attempt can
    uninstall the current package and then fail to install the new one,
    leaving no importable `cu_cli` at all. On Windows, `cu upgrade` must
    hand off to a detached helper instead of calling `subprocess.run` itself.
    """

    class FakeProvider:
        name = "private feed"
        release_notes_url = "https://example.test/releases"
        source_install_hint = "install privately"

        @staticmethod
        def pip_environment():
            return {"PIP_INDEX_URL": "https://credential@example.test/simple/"}

    monkeypatch.setattr(
        "cu_cli.commands.upgrade.get_update_provider", lambda: FakeProvider()
    )
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.fetch_latest_version_detailed",
        lambda **_: ("9.9.9", "ok"),
    )
    monkeypatch.setattr("cu_cli.commands.upgrade.is_windows", lambda: True)

    def _subprocess_run_should_not_be_called(*_args, **_kwargs):
        raise AssertionError("subprocess.run must not be called in-process on Windows")

    monkeypatch.setattr(
        "cu_cli.commands.upgrade.subprocess.run", _subprocess_run_should_not_be_called
    )

    captured = {}

    def _fake_run_windows_upgrade(**kwargs):
        captured.update(kwargs)
        return 0, tmp_path / "upgrade.log"

    monkeypatch.setattr(
        "cu_cli.commands.upgrade.run_windows_upgrade", _fake_run_windows_upgrade
    )

    res = _run("upgrade", "--yes")

    assert res.exit_code == 0, res.output
    assert captured["pip_args"][-1] == "cu-cli==9.9.9"
    assert captured["pip_env"]["PIP_INDEX_URL"].startswith("https://credential@")
    assert "started" in res.output
    assert "upgrade.log" in res.output.replace("\n", "")


def test_upgrade_on_windows_reports_helper_failure_exit_code(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.fetch_latest_version_detailed",
        lambda **_: ("9.9.9", "ok"),
    )
    monkeypatch.setattr("cu_cli.commands.upgrade.is_windows", lambda: True)
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.run_windows_upgrade",
        lambda **_: (1, tmp_path / "upgrade.log"),
    )
    res = _run("upgrade", "--yes")
    assert res.exit_code == 1


def test_analyze_rejects_missing_literal_path():
    res = _run("analyze", "https://example.com/a.pdf")
    assert res.exit_code != 0
    assert "does not exist" in _plain(res.output)


def test_analyze_requires_analyzer_when_default_is_unset(monkeypatch):
    Path("doc.pdf").write_bytes(b"%PDF-1.4 sample")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_a, **_k: pytest.fail("client must not be built without an analyzer"),
    )

    res = _run("analyze", "doc.pdf", "--json")
    assert res.exit_code == 2, res.output
    out = _plain(res.output)
    assert "no default_analyzer is configured" in out
    assert "--analyzer" in out
    assert "cu profile set default_analyzer" in out


def test_readme_sample_analyze_single_file_output_json(monkeypatch):
    sample = Path("sample_invoice.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")

    def _fake_run_one(_client, job):
        return job, {"analyzerId": job.analyzer_id, "status": "ok"}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "sample_invoice.pdf", "--analyzer", "prebuilt-layout", "--json"
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["status"] == "ok"


def test_readme_sample_analyze_single_file_output_markdown_with_prebuilt_invoice(monkeypatch):
    sample = Path("sample_invoice.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")

    def _fake_run_one(_client, job):
        return job, {"analyzerId": job.analyzer_id}

    def _fake_dump_markdown(result, out=None):
        assert out is None
        assert result["analyzerId"] == "prebuilt-invoice"
        print("# INVOICE")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)
    monkeypatch.setattr("cu_cli.commands.analyze.dump_markdown", _fake_dump_markdown)

    res = _run(
        "analyze",
        "sample_invoice.pdf",
        "--analyzer",
        "prebuilt-invoice",
    )
    assert res.exit_code == 0, res.output
    assert "# INVOICE" in res.output


def test_analyze_accepts_short_analyzer_option(monkeypatch):
    sample = Path("sample_invoice.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    captured: dict[str, str] = {}

    def _fake_run_one(_client, job):
        captured["analyzer"] = job.analyzer_id
        return job, {"analyzerId": job.analyzer_id, "status": "ok"}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze",
        "sample_invoice.pdf",
        "-a",
        "my_custom_analyzer_v1",
        "--json",
    )
    assert res.exit_code == 0, res.output
    assert captured["analyzer"] == "my_custom_analyzer_v1"


def test_analyze_rejects_id_alias():
    res = _run("analyze", "sample_invoice.pdf", "--id", "my_custom_analyzer_v1")
    assert res.exit_code == 2
    assert "No such option '--id'" in _plain(res.output)


def test_analyze_help_lists_only_supported_analyzer_options():
    res = _run("analyze", "--help")
    assert res.exit_code == 0, res.output
    out = _plain(res.output)
    assert "--id" not in out
    assert "-a" in out
    assert "--analyzer" in out


def test_readme_sample_analyze_glob_writes_json_output_files(monkeypatch):
    base = Path("sample_files")
    base.mkdir(parents=True, exist_ok=True)
    (base / "a.pdf").write_bytes(b"%PDF-1.4 a")
    nested = base / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "b.pdf").write_bytes(b"%PDF-1.4 b")

    def _fake_run_one(_client, job):
        return job, {"input": job.input_ref, "analyzerId": job.analyzer_id}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "--source", "sample_files", "--pattern", "*.pdf", "--recursive",
        "--analyzer", "prebuilt-layout", "--output-dir", "out", "--json",
    )
    assert res.exit_code == 0, res.output
    out_files = sorted(p.relative_to("out").as_posix() for p in Path("out").rglob("*.result.json"))
    # Structure is preserved relative to the non-pattern glob prefix.
    assert out_files == [
        "a.pdf.result.json",
        "nested/b.pdf.result.json",
    ]


def test_readme_sample_analyze_directory_writes_markdown_sidecar_files(monkeypatch):
    base = Path("sample_files")
    base.mkdir(parents=True, exist_ok=True)
    (base / "a.pdf").write_bytes(b"%PDF-1.4 a")
    nested = base / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "b.pdf").write_bytes(b"%PDF-1.4 b")

    def _fake_run_one(_client, job):
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)
    monkeypatch.setattr("cu_cli.commands.analyze.render_markdown", lambda _result: "# doc\n")

    res = _run(
        "analyze", "sample_files", "--recursive", "--analyzer", "prebuilt-layout"
    )
    assert res.exit_code == 0, res.output
    assert (base / "a.pdf.result.md").exists()
    assert (nested / "b.pdf.result.md").exists()


def test_analyze_output_dir_writes_correct_sidecar_extension_for_each_view(monkeypatch):
    # Same input, both output formats: markdown -> .result.md, json -> .result.json.
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")

    def _fake_run_one(_client, job):
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)
    monkeypatch.setattr("cu_cli.commands.analyze.render_markdown", lambda _r: "# doc\n")

    assert _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "md_out",
    ).exit_code == 0
    assert (Path("md_out") / "doc.pdf.result.md").exists()
    assert not (Path("md_out") / "doc.pdf.result.json").exists()

    assert _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "json_out", "--json",
    ).exit_code == 0
    assert (Path("json_out") / "doc.pdf.result.json").exists()
    assert not (Path("json_out") / "doc.pdf.result.md").exists()


def test_analyze_inline_uses_synchronous_runner(monkeypatch):
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    calls = []

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda *_a, **_k: pytest.fail("LRO runner should not be used with --inline"),
    )

    def _fake_inline(_client, job):
        calls.append(job.input_ref)
        return job, {"analyzerId": job.analyzer_id, "mode": "inline"}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one_inline", _fake_inline)

    res = _run(
        "analyze", "-i", str(sample), "--analyzer", "prebuilt-layout", "--json",
        "--api-version", "2026-06-01-preview",
    )

    assert res.exit_code == 0, res.output
    assert [Path(call).name for call in calls] == [sample.name]
    assert json.loads(res.output)["mode"] == "inline"


def test_analyze_inline_supports_prebuilt_digital_parse(monkeypatch):
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    calls = []

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())

    def _fake_inline(_client, job):
        calls.append(job.analyzer_id)
        return job, {"analyzerId": job.analyzer_id, "mode": "inline"}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one_inline", _fake_inline)

    res = _run(
        "analyze", "--inline", str(sample), "--analyzer", "prebuilt-digitalParse",
        "--json", "--api-version", "2026-06-01-preview",
    )

    assert res.exit_code == 0, res.output
    assert calls == ["prebuilt-digitalParse"]
    assert json.loads(res.output)["analyzerId"] == "prebuilt-digitalParse"


def test_analyze_inline_batch_uses_synchronous_runner_for_every_job(monkeypatch):
    paths = [Path("one.pdf"), Path("two.pdf")]
    for path in paths:
        path.write_bytes(b"%PDF-1.4 sample")
    calls = []

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze.render_markdown", lambda result: result["input"])
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one_inline",
        lambda _client, job: (calls.append(job.input_ref) or (job, {"input": job.input_ref})),
    )

    res = _run(
        "analyze", "--inline", "one.pdf", "two.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "results",
        "--api-version", "2026-06-01-preview",
    )

    assert res.exit_code == 0, res.output
    assert {Path(call).name for call in calls} == {path.name for path in paths}
    assert (Path("results") / "one.pdf.result.md").exists()
    assert (Path("results") / "two.pdf.result.md").exists()


def test_analyze_inline_requires_preview_api_version(monkeypatch):
    Path("sample.pdf").write_bytes(b"%PDF-1.4 sample")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_a, **_k: pytest.fail("client must not be built for an unsupported version"),
    )

    res = _run("analyze", "--inline", "sample.pdf", "--analyzer", "prebuilt-layout")

    assert res.exit_code != 0
    assert "requires API version 2026-06-01-preview" in _plain(res.output)


def test_analyze_inline_defers_analyzer_support_to_service(monkeypatch):
    Path("sample.pdf").write_bytes(b"%PDF-1.4 sample")
    calls = []
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())

    def _fake_inline(_client, job):
        calls.append(job.analyzer_id)
        return job, {"analyzerId": job.analyzer_id, "mode": "inline"}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one_inline", _fake_inline)

    res = _run(
        "analyze", "--inline", "sample.pdf", "--analyzer", "future-analyzer",
        "--json",
        "--api-version", "2026-06-01-preview",
    )

    assert res.exit_code == 0, res.output
    assert calls == ["future-analyzer"]
    assert json.loads(res.output)["analyzerId"] == "future-analyzer"


def test_analyze_usage_prints_inline_usage_to_stderr_without_changing_json(monkeypatch):
    Path("sample.pdf").write_bytes(b"%PDF-1.4 sample")
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one_inline_with_usage",
        lambda _client, job: (
            job,
            AnalyzeResponse(
                result={"analyzerId": job.analyzer_id, "mode": "inline"},
                usage={"documentPagesMinimalInline": 1},
            ),
        ),
    )

    res = _run(
        "analyze", "sample.pdf", "--inline", "--usage", "--analyzer", "prebuilt-layout",
        "--json",
        "--api-version", "2026-06-01-preview", "--time",
    )

    assert res.exit_code == 0, res.output
    assert json.loads(res.stdout)["mode"] == "inline"
    assert "Usage:" in _plain(res.stderr)
    assert "sample.pdf" in _plain(res.stderr)
    assert res.stderr.startswith("\n\n")
    assert "·" not in res.stderr
    assert '"documentPagesMinimalInline": 1' in res.stderr
    plain_stderr = _plain(res.stderr)
    assert plain_stderr.index("Usage:") < plain_stderr.index(
        "CU service calling time:"
    )
    assert re.search(r"CU service calling time: \d+\.\d{3}s", plain_stderr)
    assert re.search(r"Total command time: \d+\.\d{3}s$", plain_stderr)


def test_analyze_usage_title_is_colored(monkeypatch):
    printed = []
    monkeypatch.setattr(analyze_module.console, "print", printed.append)
    monkeypatch.setattr(analyze_module.console, "print_json", lambda **_kwargs: None)

    analyze_module._print_usage({}, input_ref="sample.pdf")

    assert printed == ["\n", "[bold cyan]Usage:[/bold cyan] sample.pdf"]


def test_analyze_usage_prints_lro_usage_for_each_batch_input(monkeypatch):
    for name in ("one.pdf", "two.pdf"):
        Path(name).write_bytes(b"%PDF-1.4 sample")
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one_with_usage",
        lambda _client, job: (
            job,
            AnalyzeResponse(
                result={"analyzerId": job.analyzer_id},
                usage={"documentPagesStandard": 1},
            ),
        ),
    )

    res = _run(
        "analyze", "one.pdf", "two.pdf", "--usage", "--analyzer", "prebuilt-layout",
        "--json", "--output-dir", "results", "--api-version", "2026-06-01-preview",
    )

    assert res.exit_code == 0, res.output
    assert "one.pdf" in _plain(res.stderr)
    assert "two.pdf" in _plain(res.stderr)
    assert "·" not in res.stderr
    assert res.stderr.count('"documentPagesStandard": 1') == 2
    plain_stderr = _plain(res.stderr)
    assert plain_stderr.index("2 ok, 0 failed") < plain_stderr.index("Usage:")


def test_analyze_usage_supports_ga_api_version(monkeypatch):
    Path("sample.pdf").write_bytes(b"%PDF-1.4 sample")
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one_with_usage",
        lambda _client, job: (
            job,
            AnalyzeResponse(
                result={"analyzerId": job.analyzer_id, "apiVersion": "2025-11-01"},
                usage={"documentPagesStandard": 1},
            ),
        ),
    )

    res = _run(
        "analyze", "sample.pdf", "--usage", "--analyzer", "prebuilt-layout",
        "--json",
    )

    assert res.exit_code == 0, res.output
    assert json.loads(res.stdout)["apiVersion"] == "2025-11-01"
    assert '"documentPagesStandard": 1' in res.stderr


# --- Scenario 2.1: cloud-only fail-fast (no endpoint configured) -----------

def test_analyze_no_endpoint_fails_fast():
    Path("report.pdf").write_bytes(b"%PDF-1.4 dummy")
    res = _run("analyze", "report.pdf", "--analyzer", "prebuilt-layout")
    assert res.exit_code != 0
    out = _plain(res.output)
    assert "No CU endpoint configured" in out
    assert "cu profile set endpoint <URL>" in out
    assert "cu profile set-active <name>" in out
    assert "cu profile show" in out


# --- Scenario 3.1: the bundled api-version validates fully offline ---------

def _minimal_schema(api_version: str) -> dict:
    return {
        "apiVersion": api_version,
        "analyzerId": "offline_v1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {"fields": {"vendor": {
            "type": "string", "method": "extract",
            "description": "Vendor legal name printed on the document."}}},
    }


def test_ga_schema_validates_offline():
    Path("ga.json").write_text(json.dumps(_minimal_schema("2025-11-01")), encoding="utf-8")
    assert _run("analyzer", "validate", "ga.json").exit_code == 0


# --- Scenario 3.3: unsupported api-version gives an actionable message ------

def test_unsupported_api_version_message():
    res = _run("profile", "set", "api_version", "2099-01-01")
    assert res.exit_code != 0
    assert "is not supported by this CLI build" in res.output
    assert "2025-11-01 (GA)" in res.output


def test_analyze_dry_run_rejects_unsupported_api_version():
    Path("sample.pdf").write_bytes(b"%PDF-1.4 sample")

    res = _run(
        "analyze",
        "sample.pdf",
        "--analyzer",
        "prebuilt-layout",
        "--api-version",
        "1900-01-01",
        "--dry-run",
    )

    assert res.exit_code == 1
    assert "API version 1900-01-01 is not supported" in res.output


def test_analyze_dry_run_accepts_future_preview_api_version():
    Path("sample.pdf").write_bytes(b"%PDF-1.4 sample")

    res = _run(
        "analyze",
        "sample.pdf",
        "--analyzer",
        "prebuilt-layout",
        "--api-version",
        "2099-12-31-preview",
        "--dry-run",
    )

    assert res.exit_code == 0, res.output
    assert "dry run" in res.output.lower()


# --- Scenario 2.2: deterministic output (same input -> identical output) ----

def test_validate_output_is_deterministic():
    Path("d.json").write_text(json.dumps(_minimal_schema("2025-11-01")), encoding="utf-8")
    first = _run("analyzer", "validate", "d.json", "--json")
    second = _run("analyzer", "validate", "d.json", "--json")
    assert first.exit_code == 0 and second.exit_code == 0
    assert first.output == second.output


def test_analyzer_test_summary_expands_object_and_array_subfields():
    from types import SimpleNamespace

    from cu_cli.commands.analyzer import _extract_fields_from_result, _test_summary

    sample_a = SimpleNamespace(contents=[SimpleNamespace(fields={
        "AmountDue": {
            "valueObject": {
                "Amount": {"valueNumber": 610, "confidence": 0.91},
                "CurrencyCode": {"valueString": "USD"},
            },
        },
        "LineItems": {
            "valueArray": [
                {"valueObject": {
                    "Description": {"valueString": "Consulting"},
                    "Amount": {"valueNumber": 60},
                }},
                {"valueObject": {
                    "Description": {"valueString": "Printing"},
                    "Amount": {"confidence": 0.2},
                }},
            ],
        },
    })])
    sample_b = SimpleNamespace(contents=[SimpleNamespace(fields={
        "AmountDue": {
            "valueObject": {
                "Amount": {"confidence": 0.4},
                "CurrencyCode": {"valueString": "USD"},
            },
        },
        "LineItems": {
            "valueArray": [
                {"valueObject": {
                    "Description": {"confidence": 0.3},
                    "Amount": {"confidence": 0.1},
                }},
            ],
        },
    })])

    report = _test_summary([
        {"input": "a.pdf", "status": "ok", "fields": _extract_fields_from_result(sample_a)},
        {"input": "b.pdf", "status": "ok", "fields": _extract_fields_from_result(sample_b)},
    ])

    assert report["disclaimer"].startswith("This is not a real accuracy benchmark")
    assert report["fields"]["AmountDue"]["populated"] == 2
    assert report["fields"]["AmountDue.Amount"]["populated"] == 1
    assert report["fields"]["AmountDue.Amount"]["meanConfidence"] == 0.91
    assert report["fields"]["AmountDue.CurrencyCode"]["populated"] == 2
    assert report["fields"]["LineItems"]["populated"] == 1
    assert report["fields"]["LineItems[].Description"]["populated"] == 1
    assert report["fields"]["LineItems[].Amount"]["populated"] == 1
    assert report["fields"]["LineItems[].Amount"]["meanConfidence"] == 0.15


def test_analyzer_test_markdown_shows_disclaimer_and_subfield_rows(monkeypatch):
    from types import SimpleNamespace

    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")

    def _fake_run_one(_client, job):
        result = SimpleNamespace(contents=[SimpleNamespace(fields={
            "AmountDue": {
                "valueObject": {
                    "Amount": {"valueNumber": 610},
                    "CurrencyCode": {"valueString": "USD"},
                },
                "confidence": 0.91,
            },
            "LineItems": {
                "valueArray": [
                    {"valueObject": {
                        "Description": {"valueString": "Consulting"},
                        "Amount": {"valueNumber": 60},
                    }}
                ],
                "confidence": 0.88,
            },
        })])
        return job, result

    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyzer", "test", "prebuilt-invoice", str(sample)
    )
    assert res.exit_code == 0, res.output
    assert "not a real accuracy benchmark" in res.output
    assert "AmountDue.Amount" in res.output
    assert "LineItems[].Description" in res.output
    assert "CustomerTaxId.confidence" not in res.output
    assert "CustomerTaxId.type" not in res.output


def test_analyzer_test_refuses_existing_report_before_service_call(monkeypatch):
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    report = Path("report.json")
    report.write_text('{"marker": "preserve-me"}\n', encoding="utf-8")
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("analyzer test service must not be called"),
    )

    res = _run(
        "analyzer",
        "test",
        "prebuilt-invoice",
        str(sample),
        "--output-file",
        str(report),
    )

    assert res.exit_code != 0
    assert "analyzer test report already exists" in _plain(res.output)
    assert "--force" in _plain(res.output)
    assert report.read_text(encoding="utf-8") == '{"marker": "preserve-me"}\n'


def test_analyzer_test_force_overwrites_existing_report(monkeypatch):
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    report = Path("report.json")
    report.write_text('{"marker": "replace-me"}\n', encoding="utf-8")
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (
            job,
            SimpleNamespace(contents=[SimpleNamespace(fields={})]),
        ),
    )

    res = _run(
        "analyzer",
        "test",
        "prebuilt-invoice",
        str(sample),
        "--json",
        "--output-file",
        str(report),
        "--force",
    )

    assert res.exit_code == 0, res.output
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["summary"]["samplesTotal"] == 1
    assert "marker" not in payload


def test_analyzer_test_dry_run_preserves_existing_report():
    sample = Path("sample.pdf")
    sample.write_bytes(b"%PDF-1.4 sample")
    report = Path("report.json")
    report.write_text('{"marker": "preserve-me"}\n', encoding="utf-8")

    res = _run(
        "analyzer",
        "test",
        "prebuilt-invoice",
        str(sample),
        "--dry-run",
        "--output-file",
        str(report),
    )

    assert res.exit_code == 0, res.output
    assert "No service calls or files were written" in _plain(res.output)
    assert report.read_text(encoding="utf-8") == '{"marker": "preserve-me"}\n'


class _FakeDefaults:
    def __init__(self, model_deployments):
        self.model_deployments = dict(model_deployments)

    def as_dict(self):
        return {"modelDeployments": dict(self.model_deployments)}


class _FakeDefaultsClient:
    def __init__(self, existing):
        self._existing = dict(existing)
        self.updated = None

    def get_defaults(self):
        return _FakeDefaults(self._existing)

    def update_defaults(self, *, model_deployments):
        self.updated = dict(model_deployments)
        self._existing = dict(model_deployments)
        return _FakeDefaults(self._existing)


class _FakeAnalyzer:
    def as_dict(self):
        return {"analyzerId": "prebuilt-documentSearch", "status": "ready"}


class _FakeAnalyzerClient:
    def get_analyzer(self, _analyzer_id):
        return _FakeAnalyzer()


class _FakeListAnalyzer:
    def __init__(self, analyzer_id: str, created_at: str, last_modified_at: str):
        self.analyzer_id = analyzer_id
        self.base_analyzer_id = "prebuilt-document"
        self.status = "ready"
        self.created_at = created_at
        self.last_modified_at = last_modified_at
        self.description = f"desc for {analyzer_id}"

    def as_dict(self):
        return {
            "analyzerId": self.analyzer_id,
            "baseAnalyzerId": self.base_analyzer_id,
            "status": self.status,
            "createdAt": self.created_at,
            "lastModifiedAt": self.last_modified_at,
            "description": self.description,
        }


class _FakeListAnalyzerClient:
    def list_analyzers(self):
        return [
            _FakeListAnalyzer("my_custom_v1", "2026-01-03T00:00:00Z", "2026-01-01T00:00:00Z"),
            _FakeListAnalyzer("prebuilt-invoice", "2026-01-01T00:00:00Z", "2026-01-03T00:00:00Z"),
            _FakeListAnalyzer("prebuilt-document", "2026-01-02T00:00:00Z", "2026-01-02T00:00:00Z"),
        ]


class _FakeConfigListClient:
    def get_defaults(self):
        return _FakeDefaults({"gpt-4.1": "live-gpt", "text-embedding-3-large": "live-emb"})


class _FakeConfigSyncClient:
    def __init__(self, model_deployments):
        self._defaults = _FakeDefaults(model_deployments)

    def get_defaults(self):
        return self._defaults


def test_defaults_show_json(monkeypatch):
    fake = _FakeDefaultsClient({"gpt-4.1": "dep-gpt", "text-embedding-3-large": "dep-emb"})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_a, **_k: fake)
    res = _run(
        "defaults",
        "show",
        "--endpoint",
        "https://x.services.ai.azure.com/",
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["modelDeployments"]["gpt-4.1"] == "dep-gpt"
    assert payload["modelDeployments"]["text-embedding-3-large"] == "dep-emb"


def test_defaults_show_uses_json_by_default(monkeypatch):
    fake = _FakeDefaultsClient({"gpt-4.1": "dep-gpt"})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_a, **_k: fake)
    res = _run("defaults", "show", "--endpoint", "https://x.services.ai.azure.com/")
    assert res.exit_code == 0, res.output
    assert json.loads(res.output)["modelDeployments"]["gpt-4.1"] == "dep-gpt"


def test_defaults_show_time_reports_service_call_without_polluting_json(monkeypatch):
    fake = _FakeDefaultsClient({"gpt-4.1": "dep-gpt"})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_a, **_k: fake)
    timing_lines = []
    monkeypatch.setattr(
        "cu_cli.commands._options.console.print",
        lambda message, **_kwargs: timing_lines.append(message),
    )

    res = _run(
        "defaults", "show", "--endpoint", "https://x.services.ai.azure.com/", "--time"
    )

    assert res.exit_code == 0, res.output
    assert json.loads(res.stdout)["modelDeployments"]["gpt-4.1"] == "dep-gpt"
    assert any(
        line.startswith("[bold cyan]CU service calling time:[/bold cyan]")
        and re.search(r"\d+\.\d{3}s$", _plain(line))
        for line in timing_lines
    )
    assert any(
        line.startswith("[bold cyan]Total command time:[/bold cyan]")
        and re.search(r"\d+\.\d{3}s$", _plain(line))
        for line in timing_lines
    )


def test_defaults_set_merges_explicit_profile_and_model_mappings(monkeypatch):
    fake = _FakeDefaultsClient({"gpt-4.1": "old-gpt", "text-embedding-3-large": "old-emb"})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_a, **_k: fake)

    class _Profile:
        endpoint = "https://cfg.services.ai.azure.com/"
        auth_mode = "entra"
        api_key = None
        api_version = "2025-11-01"
        model_deployments = {"gpt-4.1": "cfg-gpt"}
        @staticmethod
        def active_config_path():
            return "/tmp/fake-azure-config"

    monkeypatch.setattr("cu_cli.commands.defaults.Profile.load", lambda **_k: _Profile())
    res = _run(
        "defaults",
        "set",
        "--from-profile",
        "--model",
        "text-embedding-3-large=new-emb",
    )
    assert res.exit_code == 0, res.output
    assert fake.updated == {
        "gpt-4.1": "cfg-gpt",
        "text-embedding-3-large": "new-emb",
        "prebuilt-analyzer-completion": "cfg-gpt",
        "prebuilt-analyzer-completion-mini": "cfg-gpt",
        "prebuilt-analyzer-embedding": "new-emb",
    }


def test_defaults_set_model_does_not_implicitly_include_profile_mappings(monkeypatch):
    fake = _FakeDefaultsClient({})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_a, **_k: fake)

    class _Profile:
        endpoint = "https://cfg.services.ai.azure.com/"
        auth_mode = "entra"
        api_key = None
        api_version = "2025-11-01"
        model_deployments = {"gpt-4.1": "cfg-gpt"}

    monkeypatch.setattr("cu_cli.commands.defaults.Profile.load", lambda **_k: _Profile())

    result = _run(
        "defaults",
        "set",
        "--model",
        "text-embedding-3-large=new-emb",
    )

    assert result.exit_code == 0, result.output
    assert "gpt-4.1" not in fake.updated
    assert fake.updated["text-embedding-3-large"] == "new-emb"


def test_defaults_set_requires_explicit_source_before_client_creation(monkeypatch):
    class _Profile:
        model_deployments = {"gpt-4.1": "cfg-gpt"}

    monkeypatch.setattr("cu_cli.commands.defaults.Profile.load", lambda **_k: _Profile())
    monkeypatch.setattr(
        "cu_cli.commands.defaults.build_client",
        lambda *_a, **_k: pytest.fail("client must not be created"),
    )

    result = _run("defaults", "set")

    assert result.exit_code == 1
    assert "no model deployment mappings provided" in _plain(result.output)
    assert "--from-profile" in _plain(result.output)
    assert "--model MODEL=DEPLOYMENT" in _plain(result.output)


def test_defaults_set_help_exposes_only_explicit_profile_import():
    result = _run("defaults", "set", "--help")
    output = _plain(result.output)

    assert result.exit_code == 0, result.output
    assert "Configure Content Understanding defaults" in output
    assert "--from-profile" in output
    assert "--no-from-profile" not in output


def test_defaults_set_rejects_invalid_model_mapping():
    res = _run(
        "defaults",
        "set",
        "--model",
        "gpt-4.1",
        "--endpoint",
        "https://x.services.ai.azure.com/",
    )
    assert res.exit_code != 0
    assert "invalid --model mapping" in _plain(res.output)


def test_analyzer_show_json_not_polluted_without_runtime_context(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer.build_client", lambda *_a, **_k: _FakeAnalyzerClient())
    res = _run(
        "analyzer",
        "show",
        "prebuilt-documentSearch",
        "--endpoint",
        "https://x.services.ai.azure.com/",
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["analyzerId"] == "prebuilt-documentSearch"


@pytest.mark.parametrize("selector", [("--name",), ("-n",), ("-a",)])
def test_analyzer_show_named_selectors_match_positional(monkeypatch, selector):
    monkeypatch.setattr("cu_cli.commands.analyzer.build_client", lambda *_a, **_k: _FakeAnalyzerClient())

    positional = _run(
        "analyzer",
        "show",
        "prebuilt-documentSearch",
        "--endpoint",
        "https://x.services.ai.azure.com/",
    )
    named = _run(
        "analyzer",
        "show",
        *selector,
        "prebuilt-documentSearch",
        "--endpoint",
        "https://x.services.ai.azure.com/",
    )

    assert positional.exit_code == named.exit_code == 0
    assert json.loads(positional.output) == json.loads(named.output)


def test_analyzer_show_rejects_positional_and_named_selectors_together():
    result = _run(
        "analyzer",
        "show",
        "prebuilt-documentSearch",
        "--name",
        "prebuilt-layout",
    )

    assert result.exit_code == 2
    assert "provide name only once" in result.output


def test_analyzer_list_kind_custom_json(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--json", "--kind", "custom")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert [a["analyzerId"] for a in payload] == ["my_custom_v1"]


def test_analyzer_list_kind_custom_markdown_count(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--kind", "custom")
    assert res.exit_code == 0, res.output
    assert "Analyzers" in res.output
    assert "1 analyzer(s)" in res.output


def test_analyzer_list_kind_prebuilt_json(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--json", "--kind", "prebuilt")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert [a["analyzerId"] for a in payload] == ["prebuilt-document", "prebuilt-invoice"]


def test_analyzer_list_kind_all_is_default(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--json")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert len(payload) == 3  # no filtering by default


def test_analyzer_list_sort_by_analyzer_id(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--json", "--sort-by", "analyzerId")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert [a["analyzerId"] for a in payload] == [
        "my_custom_v1",
        "prebuilt-document",
        "prebuilt-invoice",
    ]


def test_analyzer_list_sort_by_created_at(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--json", "--sort-by", "createdAt")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert [a["analyzerId"] for a in payload] == [
        "prebuilt-invoice",
        "prebuilt-document",
        "my_custom_v1",
    ]


def test_analyzer_list_sort_by_last_modified_at(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _FakeListAnalyzerClient())
    res = _run("analyzer", "list", "--json", "--sort-by", "lastModifiedAt")
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert [a["analyzerId"] for a in payload] == [
        "my_custom_v1",
        "prebuilt-document",
        "prebuilt-invoice",
    ]


def test_defaults_show_prints_context_when_opted_in(monkeypatch):
    fake = _FakeDefaultsClient({"gpt-4.1": "dep-gpt"})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_a, **_k: fake)
    res = _run(
        "defaults",
        "show",
        "--endpoint",
        "https://x.services.ai.azure.com/",
        "--info",
    )
    assert res.exit_code == 0, res.output
    assert "endpoint:" in res.output
    payload = json.loads(res.output[res.output.find("{"):])
    assert payload["modelDeployments"]["gpt-4.1"] == "dep-gpt"


def test_service_commands_offer_common_time_flag():
    for args in (
        ("analyze", "--help"),
        ("analyzer", "list", "--help"),
        ("analyzer", "schema", "create", "--help"),
        ("analyzer", "test", "--help"),
        ("defaults", "show", "--help"),
        ("doctor", "--help"),
        ("profile", "sync-defaults", "--help"),
    ):
        output = _plain(_run(*args).output)
        assert "--time" in output
        assert "elapsed CU service and total command time" in output

    assert "--time" not in _plain(_run("analyzer", "validate", "--help").output)


def test_check_az_subscription_resolves_override_without_mutating_default(monkeypatch):
    calls = []
    monkeypatch.setattr("cu_cli.commands.infra.shutil.which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr(
        "cu_cli.commands.infra.subprocess.run",
        lambda args, **_kwargs: (
            calls.append(args)
            or SimpleNamespace(
                returncode=0,
                stdout=json.dumps({
                    "id": "resolved-sub-id",
                    "name": "Requested Subscription",
                    "tenantId": "resolved-tenant-id",
                }),
                stderr="",
            )
        ),
    )

    from cu_cli.commands.infra import _check_az_subscription

    account = _check_az_subscription("Requested Subscription")

    assert account.subscription_id == "resolved-sub-id"
    assert account.subscription_name == "Requested Subscription"
    assert account.tenant_id == "resolved-tenant-id"
    assert calls == [[
        "/usr/bin/az",
        "account",
        "show",
        "--subscription",
        "Requested Subscription",
        "--output",
        "json",
    ]]
    assert "set" not in calls[0]


def test_check_az_subscription_rejects_incomplete_account_json(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.infra.shutil.which", lambda _name: "/usr/bin/az")
    monkeypatch.setattr(
        "cu_cli.commands.infra.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"id": "sub-id", "tenantId": "tenant-id"}),
            stderr="",
        ),
    )

    from cu_cli.commands.infra import _check_az_subscription

    with pytest.raises(CuCliError, match="subscription id, name, and tenant id"):
        _check_az_subscription()


def test_resolve_existing_foundry_account_matches_custom_subdomain(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.infra.shutil.which", lambda _name: "/usr/bin/az")
    calls = []
    payload = [
        {
            "name": "some-account-name",
            "resourceGroup": "rg-cu",
            "location": "westus",
            "properties": {
                "endpoint": "https://some-account-name.cognitiveservices.azure.com/",
                "customSubDomainName": "mmi-sample-foundry-west-us",
            },
        }
    ]
    def _run_az(args, **_kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("cu_cli.commands.infra.subprocess.run", _run_az)

    from cu_cli.commands.infra import _resolve_existing_foundry_account

    name, rg, location = _resolve_existing_foundry_account(
        "https://mmi-sample-foundry-west-us.services.ai.azure.com/",
        "sub-test",
    )
    assert name == "some-account-name"
    assert rg == "rg-cu"
    assert location == "westus"
    assert calls[0][calls[0].index("--subscription") + 1] == "sub-test"


def test_resolve_existing_foundry_account_matches_account_name_label(monkeypatch):
    monkeypatch.setattr("cu_cli.commands.infra.shutil.which", lambda _name: "/usr/bin/az")
    payload = [
        {
            "name": "mmi-sample-foundry-west-us",
            "resourceGroup": "rg-cu",
            "location": "westus",
            "properties": {
                "endpoint": "https://mmi-sample-foundry-west-us.cognitiveservices.azure.com/",
            },
        }
    ]
    monkeypatch.setattr(
        "cu_cli.commands.infra.subprocess.run",
        lambda *_a, **_k: SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr=""),
    )

    from cu_cli.commands.infra import _resolve_existing_foundry_account

    name, rg, location = _resolve_existing_foundry_account(
        "https://mmi-sample-foundry-west-us.services.ai.azure.com/",
        "sub-test",
    )
    assert name == "mmi-sample-foundry-west-us"
    assert rg == "rg-cu"
    assert location == "westus"


# ---------------------------------------------------------------------------
# Regression tests for previously reported issues.
# ---------------------------------------------------------------------------


def test_analyze_on_exists_gate_errors_when_results_exist(monkeypatch):
    # Default (no flag, no env): existing results are ambiguous, so refuse to
    # guess — abort (exit 2) without any billed analyze call.
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    Path("out").mkdir()
    (Path("out") / "doc.pdf.result.json").write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def _fake_run_one(_client, job):
        calls.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.delenv("CU_ON_EXISTS", raising=False)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json",
    )
    assert res.exit_code == 2, res.output
    assert calls == []  # nothing billed
    assert "already exist" in res.output
    # Regression: the resolution hint must actually reach the user. rich-click
    # renders errors via ClickException.format_message (not our show()), so the
    # hint has to survive that path or the gate is a dead end (exit 2, no way
    # forward).
    plain = _plain(res.output)
    assert "hint:" in plain
    assert "--on-existing skip" in plain
    assert "--on-existing reanalyze" in plain


def test_analyze_on_existing_skip_skips_existing_result(monkeypatch):
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    Path("out").mkdir()
    (Path("out") / "doc.pdf.result.json").write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def _fake_run_one(_client, job):
        calls.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.delenv("CU_ON_EXISTS", raising=False)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json", "--on-existing", "skip",
    )
    assert res.exit_code == 0, res.output
    assert calls == []
    assert "nothing to do" in res.output


def test_analyze_on_existing_reanalyzes_existing_result(monkeypatch):
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    Path("out").mkdir()
    (Path("out") / "doc.pdf.result.json").write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def _fake_run_one(_client, job):
        calls.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.delenv("CU_ON_EXISTS", raising=False)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json", "--on-existing", "reanalyze", "--yes",
    )
    assert res.exit_code == 0, res.output
    assert [Path(call).name for call in calls] == ["doc.pdf"]  # re-billed
    assert "may incur additional charges" in _plain(res.output)
    assert "Existing result files will be replaced" in _plain(res.output)


def test_analyze_on_exists_env_skip(monkeypatch):
    # CU_ON_EXISTS=skip has the same effect as -s when no flag is passed.
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    Path("out").mkdir()
    (Path("out") / "doc.pdf.result.json").write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def _fake_run_one(_client, job):
        calls.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.setenv("CU_ON_EXISTS", "skip")
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json",
    )
    assert res.exit_code == 0, res.output
    assert calls == []


def test_analyze_on_exists_flag_overrides_env(monkeypatch):
    # An explicit flag wins over the env var (flag > env > default).
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    Path("out").mkdir()
    (Path("out") / "doc.pdf.result.json").write_text("{}", encoding="utf-8")

    calls: list[str] = []

    def _fake_run_one(_client, job):
        calls.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.setenv("CU_ON_EXISTS", "skip")  # would skip...
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json", "--on-existing", "reanalyze",
    )
    assert res.exit_code == 0, res.output
    assert [Path(call).name for call in calls] == ["doc.pdf"]


def test_analyze_on_exists_invalid_env_fails_fast(monkeypatch):
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    Path("out").mkdir()
    (Path("out") / "doc.pdf.result.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("CU_ON_EXISTS", "bogus")
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json",
    )
    assert res.exit_code == 2, res.output
    assert "CU_ON_EXISTS" in res.output


def test_analyze_rejects_invalid_on_existing_policy(monkeypatch):
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")
    monkeypatch.delenv("CU_ON_EXISTS", raising=False)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json", "--on-existing", "overwrite",
    )
    assert res.exit_code == 2, res.output
    assert "Invalid value for '--on-existing'" in _plain(res.output)


def test_analyze_fresh_out_dir_needs_no_mode(monkeypatch):
    # No pre-existing results → the gate never fires; a plain run succeeds.
    Path("doc.pdf").write_bytes(b"%PDF-1.4 x")

    calls: list[str] = []

    def _fake_run_one(_client, job):
        calls.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.delenv("CU_ON_EXISTS", raising=False)
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "doc.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json",
    )
    assert res.exit_code == 0, res.output
    assert [Path(call).name for call in calls] == ["doc.pdf"]


def test_analyze_batch_disambiguates_same_name_inputs(monkeypatch):
    # Direct files are relative to their respective parent directories, so two
    # shared basenames are deterministically disambiguated under --out.
    Path("a").mkdir()
    Path("b").mkdir()
    (Path("a") / "foo.pdf").write_bytes(b"%PDF-1.4 a")
    (Path("b") / "foo.pdf").write_bytes(b"%PDF-1.4 b")

    def _fake_run_one(_client, job):
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "a/foo.pdf", "b/foo.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json",
    )
    assert res.exit_code == 0, res.output
    produced = sorted(Path("out").rglob("*.result.json"))
    assert len(produced) == 2  # no silent overwrite
    assert all(path.parent == Path("out") for path in produced)
    assert all(path.name.startswith("foo.pdf.") for path in produced)


def test_analyze_absolute_directory_out_is_relative_to_source_root(monkeypatch, tmp_path):
    source = tmp_path / "invoices"
    sample = source / "2026" / "q1.pdf"
    sample.parent.mkdir(parents=True)
    sample.write_bytes(b"%PDF-1.4 x")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"input": job.input_ref}),
    )

    res = _run(
        "analyze",
        str(source),
        "--analyzer",
        "prebuilt-layout",
        "--output-dir",
        "out",
        "--json",
        "--recursive",
    )

    assert res.exit_code == 0, res.output
    assert (Path("out") / "2026" / "q1.pdf.result.json").exists()
    assert not (Path("out") / "private").exists()


def test_analyze_skips_duplicate_same_physical_file(monkeypatch):
    # Same file passed twice via different spellings is analyzed once (no double
    # billing), the CLI warns, and the report retains the skipped alias.
    Path("d").mkdir()
    (Path("d") / "report.pdf").write_bytes(b"%PDF-1.4 x")

    analyzed: list[str] = []

    def _fake_run_one(_client, job):
        analyzed.append(job.input_ref)
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "d/report.pdf", "d/../d/report.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--json", "--report-file", "report.json",
    )
    assert res.exit_code == 0, res.output
    assert len(analyzed) == 1  # the same physical file is analyzed only once
    assert len(sorted(Path("out").rglob("*.result.json"))) == 1
    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    assert report["counts"] == {
        "succeeded": 1,
        "failed": 0,
        "skipped": 0,
        "total": 1,
    }


def test_analyzer_delete_nonexistent_exits_nonzero(monkeypatch):
    # Regression: deleting a missing analyzer must not report "ok" with exit 0.
    from azure.core.exceptions import ResourceNotFoundError

    class _Client:
        def get_analyzer(self, analyzer_id):
            raise ResourceNotFoundError("analyzer not found")

        def delete_analyzer(self, analyzer_id):
            raise AssertionError("delete must not run for a missing analyzer")

    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: _Client())
    res = _run("analyzer", "delete", "does-not-exist", "--yes")
    assert res.exit_code != 0
    assert "not found" in res.output.lower()


def test_analyzer_test_exits_nonzero_on_sample_failure(monkeypatch):
    # Regression: a failed sample makes `analyzer test` exit non-zero.
    Path("s.pdf").write_bytes(b"%PDF-1.4 x")

    def _boom(_client, _job):
        raise RuntimeError("analyze failed")

    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _boom)
    res = _run("analyzer", "test", "prebuilt-invoice", "s.pdf", "--json")
    assert res.exit_code != 0


def test_analyzer_test_missing_samples_exits_nonzero(monkeypatch):
    # Regression: a nonexistent input path is reported, not silently counted.
    monkeypatch.setattr("cu_cli.commands.analyzer._client", lambda *_a, **_k: object())
    res = _run("analyzer", "test", "prebuilt-invoice", "nope/")
    assert res.exit_code != 0
    assert "does not exist" in res.output.lower()


def test_validate_strict_reports_failure_message():
    # Regression: under --strict, warnings-only must say "failed", not "passed".
    body = {
        "analyzerId": "a1",
        "baseAnalyzerId": "prebuilt-document",
        "models": {"completion": "gpt-4.1"},
        "fieldSchema": {"fields": {"vendor": {
            "type": "string", "method": "extract", "description": "short"}}},
    }
    Path("w.json").write_text(json.dumps(body), encoding="utf-8")
    res = _run("analyzer", "validate", "w.json", "--strict")
    assert res.exit_code == 2
    assert "failed under --strict" in res.output
    assert "validation passed" not in res.output


def test_schema_create_help_has_one_api_option():
    # Regression: the API option must be registered only once.
    res = _run("analyzer", "schema", "create", "--help")
    assert res.exit_code == 0, res.output
    assert "more than once" not in res.output
    assert res.output.count("--api-version ") == 1


def test_upgrade_check_not_published_points_to_source(monkeypatch):
    # Regression: a PyPI 404 must not tell users to `pip install cu-cli`.
    monkeypatch.setattr("cu_cli.commands.upgrade.fetch_latest_version_detailed",
                        lambda **_: (None, "not_published"))
    res = _run("upgrade", "--check")
    assert res.exit_code == 0, res.output
    assert "not published" in res.output.lower()
    assert "git clone" in res.output


def test_analyze_help_documents_on_exists_env():
    # Regression: the on-exists knob must be discoverable from `cu analyze --help`,
    # not just the README.
    res = _run("analyze", "--help")
    assert res.exit_code == 0
    plain = _plain(res.output)
    assert "CU_ON_EXISTS" in plain
    assert "--on-existing" in plain
    assert "reanalyze" in plain


def test_validate_binary_pdf_exits_2_not_unexpected_error():
    # Regression: a PDF/binary passed to validate is a validation failure (exit 2),
    # not an "unexpected error" from a raw UnicodeDecodeError (exit 1).
    Path("not_a_schema.pdf").write_bytes(b"%PDF-1.4 \x80\x81\x82 binary body")
    res = _run("analyzer", "validate", "not_a_schema.pdf")
    assert res.exit_code == 2, res.output
    out = _plain(res.output)
    assert "unexpected error" not in out
    assert "not a UTF-8 JSON schema file" in out


def test_validate_binary_pdf_json_output_exits_2():
    Path("bin.pdf").write_bytes(b"%PDF-1.4 \xff\xfe more binary")
    res = _run("analyzer", "validate", "bin.pdf", "--json")
    assert res.exit_code == 2, res.output
    payload = json.loads(res.output)
    assert payload["ok"] is False
    assert payload["errors"]


def test_analyze_directory_sends_unknown_extensions_to_service(monkeypatch):
    base = Path("corpus")
    base.mkdir()
    (base / "good.pdf").write_bytes(b"%PDF-1.4 a")
    (base / "notes.py").write_bytes(b"print('hello')\n")
    (base / "archive.zip").write_bytes(b"PK\x03\x04")

    analyzed = []

    def _fake_run_one(_client, job):
        analyzed.append(Path(job.input_ref).name)
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)
    monkeypatch.setattr("cu_cli.commands.analyze.render_markdown", lambda _r: "# doc\n")

    res = _run(
        "analyze", "corpus", "--analyzer", "prebuilt-layout", "--output-dir", "out", "-y"
    )
    assert res.exit_code == 0, res.output
    assert sorted(analyzed) == ["archive.zip", "good.pdf", "notes.py"]


def test_analyze_explicit_unknown_file_reaches_service(monkeypatch):
    Path("archive.zip").write_bytes(b"PK\x03\x04")
    captured: dict[str, str] = {}

    def _fake_run_one(_client, job):
        captured["input"] = job.input_ref
        return job, {"analyzerId": job.analyzer_id, "status": "ok"}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "archive.zip", "--analyzer", "custom-analyzer", "--json"
    )
    assert res.exit_code == 0, res.output
    assert Path(captured["input"]).name == "archive.zip"


def test_analyze_unexpanded_glob_fails_before_service_call(monkeypatch):
    Path("archive.zip").write_bytes(b"PK\x03\x04")

    def _boom(*_a, **_k):
        raise AssertionError("build_client should not be called for unsupported input")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", _boom)

    res = _run("analyze", "*.zip")
    assert res.exit_code == 2, res.output
    out = _plain(res.output)
    assert "wildcard patterns aren't accepted" in out
    assert "--source" in out
    assert "--pattern" in out


def test_analyze_batch_reports_every_failure_in_full(monkeypatch):
    # Regression: every failed input is listed (not truncated after 10) with
    # its complete, untruncated service message (not cut at 160 chars).
    assert _run(
        "profile", "set", "endpoint", "https://x.services.ai.azure.com/"
    ).exit_code == 0
    for i in range(12):
        Path(f"f{i:02d}.pdf").write_bytes(b"%PDF-1.4 x")

    long_err = (
        "service responded 400 (InvalidRequest): No fields were extracted.\n"
        "  InnerError: " + ("x" * 200) + "\n"
        "  TAIL_MARKER_LINE end of message"
    )

    def _fake_run_one(_client, job):
        raise RuntimeError(long_err)

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", *[f"f{i:02d}.pdf" for i in range(12)],
        "--analyzer", "prebuilt-layout", "--output-dir", "out", "-y",
    )
    assert res.exit_code == 1, res.output
    out = _plain(res.output)
    # Every one of the 12 failures is named (no "... and N more" truncation).
    for i in range(12):
        assert f"f{i:02d}.pdf" in out
    assert "and 2 more" not in out
    # The full message survives: the trailing line sits beyond the old 160-char
    # cut, so its presence proves the per-file error is no longer truncated.
    assert "TAIL_MARKER_LINE end of message" in out


def test_analyze_report_writes_per_input_status(monkeypatch):
    # --report-file writes a machine-readable per-input status file even when
    # the run exits 1.
    base = Path("corpus")
    base.mkdir()
    (base / "good.pdf").write_bytes(b"%PDF-1.4 a")
    (base / "bad.pdf").write_bytes(b"%PDF-1.4 b")
    (base / "notes.py").write_bytes(b"x")

    def _fake_run_one(_client, job):
        if job.input_ref.endswith("bad.pdf"):
            raise RuntimeError("service responded 400: boom")
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)
    monkeypatch.setattr("cu_cli.commands.analyze.render_markdown", lambda _r: "# doc\n")

    res = _run(
        "analyze", "corpus", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--report-file", "report.json", "-y",
    )
    assert res.exit_code == 1, res.output  # a failure occurred, but the report is still written
    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    assert report["schema"] == "cu-cli/analyze-report/v1"
    assert report["counts"]["succeeded"] == 2
    assert report["counts"]["failed"] == 1
    assert report["counts"]["skipped"] == 0
    assert report["counts"]["total"] == 3
    by_status = {Path(r["input"]).name: r["status"] for r in report["results"]}
    assert by_status["good.pdf"] == "succeeded"
    assert by_status["bad.pdf"] == "failed"
    assert by_status["notes.py"] == "succeeded"
    failed = next(r for r in report["results"] if r["status"] == "failed")
    assert "boom" in failed["error"]


def test_analyze_pattern_with_no_matches_fails_without_report_or_client(monkeypatch):
    base = Path("corpus")
    base.mkdir()
    (base / "notes.py").write_bytes(b"x")
    (base / "archive.zip").write_bytes(b"PK\x03\x04")

    def _unexpected_client(*_args, **_kwargs):
        raise AssertionError("all-rejected discovery must not create a client")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", _unexpected_client)

    res = _run(
        "analyze",
        "--analyzer",
        "prebuilt-layout",
        "--source",
        "corpus",
        "--pattern",
        "*.pdf",
        "--output-dir",
        "out",
        "--report-file",
        "report.json",
    )

    assert res.exit_code != 0
    assert "did not find any files" in _plain(res.output)
    assert not Path("report.json").exists()


def test_analyze_single_input_writes_report_on_failure(monkeypatch):
    # Regression: a single-input analyze that fails (e.g. the endpoint is
    # unreachable) still writes the --report file with one "failed" entry before
    # the friendly error exits 1 — matching the batch path, so a scripted
    # single-file caller never gets a missing report.
    Path("only.pdf").write_bytes(b"%PDF-1.4 a")

    def _fake_run_one(_client, _job):
        raise RuntimeError("service unreachable: boom")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "only.pdf", "--analyzer", "prebuilt-layout",
        "--json", "--report-file", "report.json",
    )
    assert res.exit_code == 1, res.output
    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    assert report["schema"] == "cu-cli/analyze-report/v1"
    assert report["counts"]["failed"] == 1
    assert report["counts"]["total"] == 1
    assert len(report["results"]) == 1
    entry = report["results"][0]
    assert Path(entry["input"]).name == "only.pdf"
    assert entry["status"] == "failed"
    assert "boom" in entry["error"]


def test_analyze_empty_markdown_error_is_user_facing_in_output_and_report(monkeypatch):
    # Regression: identify an empty Markdown view without guessing that the
    # successfully analyzed input was corrupt or unsupported.
    Path("only.pdf").write_bytes(b"%PDF-1.4 a")

    def _fake_run_one(_client, _job):
        return _job, {"ok": True}

    def _boom_markdown(_result):
        from cu_cli.output import EmptyMarkdownOutputError

        raise EmptyMarkdownOutputError("to_llm_input() returned empty markdown output.")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)
    monkeypatch.setattr("cu_cli.commands.analyze.render_markdown", _boom_markdown)

    res = _run(
        "analyze", "only.pdf", "--analyzer", "prebuilt-layout",
        "--output-dir", "out", "--report-file", "report.json", "-y",
    )
    assert res.exit_code == 1, res.output
    out = _plain(res.output)
    assert "to_llm_input" not in out
    assert "Analysis succeeded, but the Markdown view was empty" in out
    assert "Retry with --json to inspect the complete result" in out
    assert "corrupt" not in out
    assert "unsupported" not in out

    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    failed = next(r for r in report["results"] if r["status"] == "failed")
    assert "to_llm_input" not in failed["error"]
    assert failed["error"] == (
        "Analysis succeeded, but the Markdown view was empty. "
        "Retry with --json to inspect the complete result."
    )


def test_analyze_single_stdout_empty_markdown_writes_actionable_failure_report(monkeypatch):
    from cu_cli.output import EmptyMarkdownOutputError

    Path("only.pdf").write_bytes(b"%PDF-1.4 a")

    def _empty_markdown(_result):
        raise EmptyMarkdownOutputError("to_llm_input() returned empty markdown output.")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"ok": True}),
    )
    monkeypatch.setattr("cu_cli.commands.analyze.dump_markdown", _empty_markdown)

    res = _run(
        "analyze",
        "only.pdf",
        "--analyzer",
        "prebuilt-layout",
        "--report-file",
        "report.json",
    )

    assert res.exit_code == 1, res.output
    out = _plain(res.output)
    assert "Analysis succeeded, but the Markdown view was empty" in out
    assert "Retry with --json" in out
    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    assert report["counts"] == {
        "succeeded": 0,
        "failed": 1,
        "skipped": 0,
        "total": 1,
    }
    assert report["results"][0]["error"].startswith(
        "Analysis succeeded, but the Markdown view was empty"
    )


def test_analyze_batch_preserves_nested_service_error_in_output_and_report(monkeypatch):
    from azure.core.exceptions import HttpResponseError, ODataV4Format

    Path("only.gif").write_bytes(b"GIF89a")
    service_error = HttpResponseError()
    service_error.status_code = 415
    service_error.error = ODataV4Format(
        {
            "code": "UnsupportedMediaType",
            "message": "The input media type is not supported.",
            "innererror": {
                "code": "UnsupportedFileType",
                "message": "GIF input is not supported.",
            },
        }
    )

    def _raise_service_error(_client, _job):
        raise service_error

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _raise_service_error)

    res = _run(
        "analyze",
        "only.gif",
        "--analyzer",
        "prebuilt-layout",
        "--output-dir",
        "out",
        "--report-file",
        "report.json",
        "-y",
    )

    assert res.exit_code == 1, res.output
    out = _plain(res.output)
    assert "service responded 415 (UnsupportedMediaType)" in out
    assert "UnsupportedFileType: GIF input is not supported." in out
    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    error = report["results"][0]["error"]
    assert "service responded 415 (UnsupportedMediaType)" in error
    assert "UnsupportedFileType: GIF input is not supported." in error


def test_analyze_help_documents_report_option():
    res = _run("analyze", "--help")
    assert res.exit_code == 0
    assert "--report-file" in _plain(res.output)


def test_analyze_report_existing_file_blocks_before_analysis(monkeypatch):
    # Report-file existence protection: an existing --report path must fail
    # fast (exit 2) before any input discovery, CU service call, or result
    # file write, and the existing report must be preserved byte-for-byte.
    Path("only.pdf").write_bytes(b"%PDF-1.4 a")
    existing_report_bytes = b'{"pre-existing": true}'
    Path("report.json").write_bytes(existing_report_bytes)

    call_count = {"n": 0}

    def _fake_run_one(_client, job):
        call_count["n"] += 1
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run("analyze", "only.pdf", "--report-file", "report.json")

    assert res.exit_code == 2, res.output
    assert call_count["n"] == 0, "no analysis/service call should happen when --report already exists"
    assert Path("report.json").read_bytes() == existing_report_bytes
    out = _plain(res.output)
    assert "report" in out.lower()
    assert "already exist" in out.lower()
    # No result file should have been written either — the guard fires before
    # any input is even discovered/planned.
    assert not Path("only.pdf.result.md").exists()


def test_analyze_report_absent_file_retains_current_behavior(monkeypatch):
    # Absence of a pre-existing --report path is unaffected by the new
    # existence guard: the report is written normally after a successful run.
    Path("only.pdf").write_bytes(b"%PDF-1.4 a")
    assert not Path("report.json").exists()

    def _fake_run_one(_client, job):
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "only.pdf", "--analyzer", "prebuilt-layout",
        "--json", "--report-file", "report.json",
    )

    assert res.exit_code == 0, res.output
    report = json.loads(Path("report.json").read_text(encoding="utf-8"))
    assert report["schema"] == "cu-cli/analyze-report/v1"
    assert report["counts"]["succeeded"] == 1


@pytest.mark.parametrize("report_alias", ["relative", "absolute"])
def test_analyze_report_result_path_collision_blocks_before_client(
    monkeypatch, report_alias
):
    # --report must not overwrite a finalized analysis result, including when
    # relative and absolute spellings identify the same path.
    Path("invoice.pdf").write_bytes(b"%PDF-1.4 a")
    planned_result = Path("results/invoice.pdf.result.json")
    report_path = (
        planned_result
        if report_alias == "relative"
        else planned_result.resolve(strict=False)
    )
    call_count = {"client": 0, "analysis": 0}

    def _fake_build_client(*_args, **_kwargs):
        call_count["client"] += 1
        return object()

    def _fake_run_one(_client, job):
        call_count["analysis"] += 1
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", _fake_build_client)
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "invoice.pdf", "--analyzer", "prebuilt-layout",
        "--json", "--output-dir", "results", "--report-file", str(report_path),
    )

    assert res.exit_code == 2, res.output
    assert call_count == {"client": 0, "analysis": 0}
    assert not planned_result.exists()
    assert "conflicts with an analysis result file" in _plain(res.output)


def test_analyze_report_near_result_path_succeeds(monkeypatch):
    Path("invoice.pdf").write_bytes(b"%PDF-1.4 a")
    planned_result = Path("results/invoice.pdf.result.json")
    report_path = Path("results/invoice.report.json")

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"analysis": "preserved"}),
    )

    res = _run(
        "analyze", "invoice.pdf", "--analyzer", "prebuilt-layout",
        "--json", "--output-dir", "results", "--report-file", str(report_path),
    )

    assert res.exit_code == 0, res.output
    assert json.loads(planned_result.read_text(encoding="utf-8")) == {
        "analysis": "preserved"
    }
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema"] == "cu-cli/analyze-report/v1"
    assert report["counts"]["succeeded"] == 1


def test_analyze_report_reanalyze_does_not_bypass_existing_report_protection(monkeypatch):
    Path("only.pdf").write_bytes(b"%PDF-1.4 a")
    existing_report_bytes = b'{"pre-existing": true}'
    Path("report.json").write_bytes(existing_report_bytes)

    call_count = {"n": 0}

    def _fake_run_one(_client, job):
        call_count["n"] += 1
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "only.pdf", "--on-existing", "reanalyze",
        "--report-file", "report.json",
    )

    assert res.exit_code == 2, res.output
    assert call_count["n"] == 0
    assert Path("report.json").read_bytes() == existing_report_bytes


def test_analyze_report_skip_does_not_bypass_existing_report_protection(monkeypatch):
    Path("only.pdf").write_bytes(b"%PDF-1.4 a")
    existing_report_bytes = b'{"pre-existing": true}'
    Path("report.json").write_bytes(existing_report_bytes)

    call_count = {"n": 0}

    def _fake_run_one(_client, job):
        call_count["n"] += 1
        return job, {"input": job.input_ref}

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_a, **_k: object())
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", _fake_run_one)

    res = _run(
        "analyze", "only.pdf", "--on-existing", "skip",
        "--report-file", "report.json",
    )

    assert res.exit_code == 2, res.output
    assert call_count["n"] == 0
    assert Path("report.json").read_bytes() == existing_report_bytes
