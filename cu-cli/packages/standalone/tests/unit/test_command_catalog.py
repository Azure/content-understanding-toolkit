# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import inspect
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import click
import pytest

from cu_cli.cli import main
from support.command_catalog import CommandCatalog, _ACTIVE, _REGIONS, command_inventory, invoke_cli, render_command
from support.command_catalog import invoke_azure, record_external, record_output, recording_evidence, verification_for


pytestmark = pytest.mark.unit


@pytest.fixture
def catalog_region(request):
    identifier = "catalog_probe"
    lines, start = inspect.getsourcelines(request.function)
    token = _REGIONS.set({
        identifier: (Path(__file__), start, start + len(lines), request.function.__name__),
    })
    try:
        yield identifier
    finally:
        _REGIONS.reset(token)


def test_verification_records_only_consumed_playback_and_preserves_output_provenance(tmp_path, catalog_region):
    from types import SimpleNamespace

    path = tmp_path / "recording.yaml"
    path.write_text("sanitized fixture", encoding="utf-8")
    cassette = SimpleNamespace(play_count=0)
    arguments = ["analyze", "invoice.pdf", "--json"]
    with recording_evidence(path, "playback", cassette):
        assert verification_for(arguments, 0)["mode"] == "mocked"
        cassette.play_count = 1
        proof = verification_for(arguments, 0)
    assert proof["mode"] == "playback"
    assert proof["recordings"][0]["path"] == "recording.yaml"
    assert len(proof["recordings"][0]["sha256"]) == 64
    assert verification_for(arguments, 0)["mode"] == "mocked"
    catalog = CommandCatalog(main)
    catalog.record_execution("test", proof)
    token = _ACTIVE.set((catalog, "test"))
    try:
        record_output("{}", language="json")
    finally:
        _ACTIVE.reset(token)
    exported = catalog.examples[catalog_region]
    assert exported["verification"]["mode"] == "playback"
    assert exported["verification"]["output_validation"] == "json"
    assert "output_validation" not in proof


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["profile", "set", "endpoint", "https://sample.invalid/"], "local"),
        (["analyzer", "schema", "create"], "local"),
        (["analyze", "invoice.pdf", "--dry-run"], "local"),
        (["analyze", "invoice.pdf", "--inline"], "mocked"),
        (["profile", "show", "--deployments"], "mocked"),
        (["cu", "analyzer", "list"], "mocked"),
    ],
)
def test_verification_does_not_present_unrecorded_service_calls_as_playback(arguments, expected):
    assert verification_for(arguments, 0)["mode"] == expected


def test_inventory_includes_frontend_only_commands_and_option_metadata():
    inventory = command_inventory(main)

    assert "upgrade" in inventory
    assert not any(name.startswith("_") for name in inventory)
    parameters = {parameter["name"]: parameter for parameter in inventory["analyze"]["parameters"]}
    assert set(parameters["concurrency"]["spellings"]) == {"--concurrency", "-j"}
    assert parameters["concurrency"]["minimum"] == 1
    assert parameters["concurrency"]["maximum"] == 32
    assert parameters["on_existing"]["choices"] == ["error", "skip", "reanalyze"]


def test_capture_distinguishes_help_aliases_positionals_and_option_values():
    catalog = CommandCatalog(main)
    catalog.record_call("test", ["analyze", "--source", "documents", "--pattern", "*.pdf"], 0)
    catalog.record_call("test", ["analyze", "document.pdf", "-a", "prebuilt-layout"], 0)
    catalog.record_call("test", ["analyze", "--source=documents", "--help"], 0)

    assert catalog.calls[0]["options"] == ["--pattern", "--source"]
    assert catalog.calls[0]["positional"] is False
    assert catalog.calls[1]["positional"] is True
    assert catalog.calls[1]["options"] == ["-a"]
    assert catalog.calls[2]["options"] == ["--source"]
    assert catalog.calls[2]["help_only"] is True


def test_capture_recognizes_attached_short_option_values():
    catalog = CommandCatalog(main)

    catalog.record_call("attached", ["analyze", "-j8", "--json"], 0)

    assert catalog.calls[0]["options"] == ["--json", "-j"]
    assert catalog.calls[0]["positional"] is False


def test_parser_rejected_options_cannot_satisfy_coverage():
    catalog = CommandCatalog(main)
    catalog.outcomes["invalid"] = ["passed"] * 3

    catalog.record_call(
        "invalid", ["analyze", "--unknown", "--json", "-j", "8", "--concurrency", "8"], 2,
    )

    assert catalog.calls[0]["options"] == []
    assert "cu analyze: no non-help invocation in a passing test" in catalog.invocation_gaps()


@pytest.fixture
def parsing_cli():
    executed = []

    @click.group()
    def root():
        pass

    @root.command()
    @click.argument("inputs", nargs=-1)
    @click.option("--concurrency", "-j", type=click.IntRange(1, 32))
    @click.option("--recursive", "-r", is_flag=True)
    @click.option("--json", "json_output", is_flag=True)
    @click.option("--label")
    @click.option("--cache/--no-cache", default=True)
    def analyze(**values):
        executed.append(values)

    return root, executed


@pytest.mark.parametrize(
    ("arguments", "options", "positional", "help_only"),
    [
        (["-rj8", "--json", "input.pdf"], ["--json", "-j", "-r"], True, False),
        (["--label=caption", "--concurrency=8"], ["--concurrency", "--label"], False, False),
        (["--label", "--help"], ["--label"], False, False),
        (["--", "--help", "-j8"], [], True, False),
        (["--no-cache"], ["--no-cache"], False, False),
        (["-j4", "--concurrency", "8"], ["--concurrency", "-j"], False, False),
        (["--help"], [], False, True),
    ],
    ids=["short-cluster", "equals", "help-value", "separator", "negative-flag", "aliases", "help"],
)
def test_capture_matches_click_syntax(parsing_cli, arguments, options, positional, help_only):
    root, executed = parsing_cli
    arguments = ["analyze", *arguments]
    result = click.testing.CliRunner().invoke(root, arguments)
    assert result.exit_code == 0, result.output
    assert len(executed) == (0 if help_only else 1)
    catalog = CommandCatalog(root)

    catalog.record_call("syntax", arguments, result.exit_code)

    assert catalog.calls[0]["parsed"] is True
    assert catalog.calls[0]["options"] == options
    assert catalog.calls[0]["positional"] is positional
    assert catalog.calls[0]["help_only"] is help_only
    assert len(executed) == (0 if help_only else 1)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--unknown", "--json"],
        ["--json", "--concurrency"],
        ["--json", "--concurrency", "invalid"],
        ["--json", "-j33"],
    ],
    ids=["unknown", "missing-value", "invalid-type", "out-of-range"],
)
def test_capture_excludes_calls_rejected_by_click(parsing_cli, arguments):
    root, executed = parsing_cli
    arguments = ["analyze", *arguments]
    result = click.testing.CliRunner().invoke(root, arguments)
    assert result.exit_code == 2, result.output
    catalog = CommandCatalog(root)
    catalog.outcomes["rejected"] = ["passed"] * 3

    catalog.record_call("rejected", arguments, result.exit_code)

    assert executed == []
    assert catalog.calls[0]["parsed"] is False
    assert catalog.calls[0]["options"] == []
    assert catalog.invocation_gaps() == ["cu analyze: no non-help invocation in a passing test"]
    assert "Non-help calls: 0." in catalog.matrix()


def test_capture_does_not_repeat_callbacks_or_mutate_original_parameters():
    callbacks = []
    invoked = []

    def normalize(_context, _parameter, value):
        callbacks.append(value)
        return value.upper()

    @click.group()
    def root():
        pass

    @root.command()
    @click.option("--name", "-n", required=True, callback=normalize)
    def save(name):
        invoked.append(name)

    arguments = ["save", "-n", "dev"]
    result = click.testing.CliRunner().invoke(root, arguments)
    assert result.exit_code == 0, result.output
    catalog = CommandCatalog(root)

    catalog.record_call("callback", arguments, result.exit_code)

    assert callbacks == ["dev"]
    assert invoked == ["DEV"]
    assert catalog.calls[0]["options"] == ["-n"]
    assert save.params[0].name == "name"
    assert save.params[0].opts == ["--name", "-n"]
    assert save.params[0].callback is normalize
    catalog.record_call("missing", ["save"], 2)
    assert catalog.calls[-1]["parsed"] is False


def test_only_passing_tests_export_commands_and_examples(tmp_path):
    catalog = CommandCatalog(main)
    for test in ("passed", "failed", "skipped", "teardown_failed"):
        catalog.record_call(test, ["analyze", "input.pdf"], 0)
        catalog.record_example(test, test, "cu analyze input.pdf", "bash")
    catalog.outcomes = {
        "passed": ["passed", "passed", "passed"],
        "failed": ["passed", "failed", "passed"],
        "skipped": ["passed", "skipped", "passed"],
        "teardown_failed": ["passed", "passed", "failed"],
    }
    target = tmp_path / "catalog.json"

    catalog.export(target)

    payload = json.loads(target.read_text())
    assert set(payload["examples"]) == {"passed"}
    assert [call["test"] for call in payload["calls"]] == ["passed"]
    assert payload["not_passed"] == ["failed", "skipped", "teardown_failed"]
    with pytest.raises(AssertionError, match="duplicate"):
        catalog.record_example("passed", "another", "cu --help", "bash")


def test_matrix_lists_missing_options_and_does_not_count_help():
    catalog = CommandCatalog(main)
    catalog.outcomes["behavior"] = ["passed"] * 3
    catalog.outcomes["help"] = ["passed"] * 3
    catalog.record_call("behavior", ["analyze", "--file", "input.pdf", "--json"], 0)
    catalog.record_call("help", ["analyze", "--concurrency", "2", "--help"], 0)

    matrix = catalog.matrix()

    assert "not a claim of exhaustive" in matrix
    assert "| `--file` |" in matrix
    assert "| `--file --json` | 0 | `behavior` |" in matrix
    assert "| -j |" not in matrix
    assert "| --concurrency |" not in matrix
    assert "MISSING" in matrix


def test_inventory_uses_actual_click_options_not_the_shared_registry():
    @click.command()
    @click.option("--enabled/--disabled")
    def standalone(enabled):
        pass

    inventory = command_inventory(standalone)

    assert inventory[""]["parameters"][0]["spellings"] == ["--enabled", "--disabled"]


def test_bash_rendering_roundtrips_multiline_spaces_quotes_and_sas():
    arguments = [
        "analyze", "--url", "https://example.test/bob's/video.mp4?sp=r&sig=a%2Bb",
        "--analyzer", "prebuilt-videoSearch", "--output-dir", "results with spaces", "--json",
    ]
    rendered = render_command(arguments, executable="cu", language="bash", environment={})
    assert "\\\n" in rendered
    assert shlex.split(rendered.replace("\\\n", "")) == ["cu", *arguments]


@pytest.mark.parametrize(
    ("value", "unquoted"),
    [
        ("https://<dev-resource>.services.ai.azure.com/", True),
        ("https://<account>.blob.core.windows.net/<container>/<blob>?<sas-token>", False),
        ("https://storage.example.net/video.mp4?sv=<version>&sp=r&sig=<signature>", False),
        ("https://<resource>/folder with spaces", False),
        ("https://<resource>/$(command)", False),
        ("<key>", True),
        ("<source-resource>", True),
        ("<destination-resource>", True),
        ("--api-key=<key>", True),
        ("<path>/file with spaces", False),
        ("*.pdf", False),
        ("gpt-5.2, text-embedding-3-large", False),
    ],
    ids=[
        "endpoint", "sas", "query", "spaces", "shell-expansion", "key",
        "source-resource", "destination-resource", "option-value", "path-spaces",
        "wildcard", "model-list",
    ],
)
def test_bash_placeholders_only_omit_unnecessary_quotes(value, unquoted):
    rendered = render_command([value], executable="cu", language="bash", environment={})
    if unquoted:
        assert rendered == "cu " + value
    else:
        assert rendered.startswith('cu "') and rendered.endswith('"')


def test_environment_rendering_preserves_values_and_powershell_restoration():
    arguments = ["profile", "get", "endpoint"]
    environment = {"CU_ENDPOINT": "https://example.services.ai.azure.com/"}
    bash = render_command(arguments, executable="cu", language="bash", environment=environment)
    powershell = render_command(
        arguments, executable="cu", language="powershell", environment=environment,
    )
    assert shlex.split(bash)[0] == "CU_ENDPOINT=" + environment["CU_ENDPOINT"]
    assert "$previous_CU_ENDPOINT = $env:CU_ENDPOINT" in powershell
    assert "finally {\n  $env:CU_ENDPOINT = $previous_CU_ENDPOINT" in powershell
    assert 'cu profile get endpoint' in powershell
    assert f'$env:CU_ENDPOINT = "{environment["CU_ENDPOINT"]}"' in powershell


@pytest.mark.parametrize("total_length", [78, 79], ids=["fits", "wraps"])
def test_bash_environment_wrapping_counts_the_full_line(total_length):
    command = "cu profile list"
    value = "x" * (total_length - len("MODE= " + command))

    rendered = render_command(
        ["profile", "list"], executable="cu", language="bash", environment={"MODE": value},
    )

    separator = " " if total_length == 78 else " \\\n  "
    assert rendered == f"MODE={value}{separator}{command}"
    assert shlex.split(rendered.replace("\\\n", "")) == [f"MODE={value}", "cu", "profile", "list"]


@pytest.mark.parametrize("multiple_variables", [False, True], ids=["endpoint", "multiple-environment"])
def test_bash_long_environment_command_groups_options_and_values(multiple_variables):
    endpoint = "https://<temporary-resource>.services.ai.azure.com/"
    explicit_endpoint = "https://<one-time-resource>.services.ai.azure.com/"
    environment = {"CU_ENDPOINT": endpoint}
    if multiple_variables:
        environment["CU_API_VERSION"] = "2025-11-01"
    arguments = ["analyzer", "list", "--profile", "prod", "--endpoint", explicit_endpoint, "--info"]

    rendered = render_command(arguments, executable="cu", language="bash", environment=environment)

    prefix = "CU_API_VERSION=2025-11-01 \\\n  " if multiple_variables else ""
    assert rendered == (
        prefix + f"CU_ENDPOINT={endpoint} \\\n"
        "  cu analyzer list \\\n"
        "    --profile prod \\\n"
        f"    --endpoint {explicit_endpoint} \\\n"
        "    --info"
    )
    assert all(len(line) <= 80 and line == line.rstrip() for line in rendered.splitlines())
    assert shlex.split(rendered.replace("\\\n", "")) == [
        *(f"{key}={value}" for key, value in sorted(environment.items())), "cu", *arguments,
    ]


@pytest.mark.parametrize("language", ["bash", "powershell"])
def test_resource_placeholder_executes_bound_value_and_exports_template(
    language, catalog_region,
):
    from cu_cli.profile import ProfileStore

    endpoint = "https://<resource-name>.services.ai.azure.com/"
    arguments = ["profile", "set", "endpoint", endpoint]
    values = {"resource-name": "cu-docs-resource"}
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        result = invoke_cli(
            arguments, language=language,
            placeholder_values=values,
        )
    finally:
        _ACTIVE.reset(token)

    assert result.exit_code == 0, result.output
    assert ProfileStore.load().get("endpoint") == "https://cu-docs-resource.services.ai.azure.com/"
    content = catalog.examples[catalog_region]["content"]
    assert "cu-docs-resource" not in content
    assert arguments == ["profile", "set", "endpoint", endpoint]
    assert values == {"resource-name": "cu-docs-resource"}
    if language == "bash":
        assert content == f"cu profile set endpoint {endpoint}"
        substituted = content.replace("<resource-name>", values["resource-name"])
        assert shlex.split(substituted) == [
            "cu", "profile", "set", "endpoint", "https://cu-docs-resource.services.ai.azure.com/",
        ]
    else:
        assert f'"{endpoint}"' in content


def test_key_placeholder_executes_bound_value_without_exporting_it(catalog_region):
    from cu_cli.profile import ProfileStore

    arguments = ["profile", "set", "api_key", "<key>"]
    values = {"key": "offline-test-key"}
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        result = invoke_cli(
            arguments, placeholder_values=values,
        )
    finally:
        _ACTIVE.reset(token)

    assert result.exit_code == 0, result.output
    assert ProfileStore.load().get("api_key") == values["key"]
    assert ProfileStore.load().get("auth_mode") == "key"
    content = catalog.examples[catalog_region]["content"]
    assert content == "cu profile set api_key <key>"
    assert values["key"] not in content
    assert arguments == ["profile", "set", "api_key", "<key>"]
    assert values == {"key": "offline-test-key"}


@pytest.mark.parametrize("language", ["bash", "powershell"])
def test_environment_placeholder_binds_at_execution_and_preserves_template(
    language, catalog_region, monkeypatch,
):
    template = "https://<temporary-resource>.services.ai.azure.com/"
    environment = {"CU_ENDPOINT": template}
    values = {"temporary-resource": "cu-docs-temporary"}
    original_endpoint = "https://saved.services.ai.azure.com/"
    monkeypatch.setenv("CU_ENDPOINT", original_endpoint)
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        result = invoke_cli(
            ["env-var", "list", "--json"], env=environment,
            language=language,
            placeholder_values=values,
        )
    finally:
        _ACTIVE.reset(token)

    actual = {item["name"]: item["value"] for item in json.loads(result.stdout)}
    assert actual["CU_ENDPOINT"] == "https://cu-docs-temporary.services.ai.azure.com/"
    assert os.environ["CU_ENDPOINT"] == original_endpoint
    content = catalog.examples[catalog_region]["content"]
    if language == "bash":
        assert content.startswith(f"CU_ENDPOINT={template} ")
    else:
        assert f'"{template}"' in content
    assert "cu-docs-temporary" not in content
    assert environment == {"CU_ENDPOINT": template}
    assert values == {"temporary-resource": "cu-docs-temporary"}


@pytest.mark.parametrize(
    "values", [{}, {"resource-name": "cu-docs-resource", "unused": "value"}],
    ids=["missing-binding", "unused-binding"],
)
@pytest.mark.parametrize("location", ["argument", "environment"])
def test_invalid_placeholder_bindings_fail_before_cli_execution(
    monkeypatch, values, catalog_region, location,
):
    monkeypatch.setattr(
        click.testing.CliRunner, "invoke",
        lambda *_args, **_kwargs: pytest.fail("invalid bindings must fail before invocation"),
    )
    template = "https://<resource-name>.services.ai.azure.com/"
    arguments = ["profile", "set", "endpoint", template] if location == "argument" else ["env-var", "list"]
    environment = {} if location == "argument" else {"CU_ENDPOINT": template}
    with pytest.raises(ValueError, match="placeholder"):
        invoke_cli(
            arguments, env=environment, placeholder_values=values,
        )


def test_invalid_synchronized_command_cannot_export_as_a_successful_example(monkeypatch, catalog_region):
    catalog = CommandCatalog(main)
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("invalid command must not call the service"),
    )
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        with pytest.raises(AssertionError, match="--source"):
            invoke_cli(
                ["analyze", "./documents", "--pattern", "*.pdf"],
            )
    finally:
        _ACTIVE.reset(token)
    assert catalog.examples == {}


def test_expected_failure_and_comments_are_explicit_in_exported_example(catalog_region):
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        result = invoke_cli(
            ["analyze", "documents", "--pattern", "*.pdf"],
            expected_exit_code=2,
            comment="Incorrect selection mode.",
        )
    finally:
        _ACTIVE.reset(token)
    assert result.exit_code == 2
    assert catalog.examples[catalog_region]["content"].startswith(
        "# Incorrect selection mode.\n# Expected exit code: 2\ncu analyze"
    )


@pytest.mark.parametrize(
    "description,expected",
    [
        (None, "az cu profile list --output json"),
        (
            "Read the shared profile.\nKeep the same Azure CLI configuration.",
            "# Read the shared profile.\n# Keep the same Azure CLI configuration.\n"
            "az cu profile list --output json",
        ),
    ],
    ids=["plain", "multiline-description"],
)
def test_azure_invocation_preserves_optional_description(
    catalog_region, monkeypatch, description, expected,
):
    monkeypatch.setattr("azure.cli.core.util.handle_version_update", lambda: None)
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        invoke_azure(["cu", "profile", "list", "--output", "json"], comment=description)
    finally:
        _ACTIVE.reset(token)

    assert catalog.examples[catalog_region]["content"] == expected


@pytest.mark.parametrize("language", ["bash", "powershell"])
def test_region_commands_are_compact_and_keep_descriptions(catalog_region, language):
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    try:
        version = invoke_cli(["--version"], language=language)
        help_result = invoke_cli(
            ["--help"], language=language,
            comment="Inspect available commands.",
        )
    finally:
        _ACTIVE.reset(token)

    assert version.exit_code == 0, version.output
    assert help_result.exit_code == 0, help_result.output
    assert catalog.examples[catalog_region]["content"] == (
        "cu --version\n# Inspect available commands.\ncu --help"
    )
    assert catalog.examples[catalog_region]["verification"]["consecutive"] is True


@pytest.mark.parametrize("language,continuation", [("bash", "\\"), ("powershell", "`")])
def test_region_preserves_source_formatting(language, continuation):
    catalog = CommandCatalog(main)
    content = f"cu profile {continuation}\n  --help\n\n# Inspect the version.\ncu --version"

    catalog.record_region("workflow", 1, "test_workflow", content, language, {"mode": "local"})
    catalog.record_region("workflow", 2, "test_workflow", "cu --help\n", language, {"mode": "local"})

    assert catalog.examples["workflow"]["content"] == f"{content}\ncu --help"


@pytest.mark.parametrize(
    "comment,expected",
    [
        (None, "az login"),
        ("", "az login"),
        ("Sign in.\nUse the intended account.", "# Sign in.\n# Use the intended account.\naz login"),
    ],
    ids=["plain", "empty", "multiline-comment"],
)
def test_external_command_preserves_optional_comment(catalog_region, monkeypatch, comment, expected):
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: pytest.fail("external commands must not execute"),
    )
    catalog = CommandCatalog(main)
    token = _ACTIVE.set((catalog, catalog_region))
    reason = "Interactive sign-in prerequisite."
    try:
        record_external(["az", "login"], reason=reason, comment=comment)
    finally:
        _ACTIVE.reset(token)

    entry = catalog.examples[catalog_region]
    assert entry["content"] == expected
    assert entry["reason"] == reason
    assert entry["verification"] == {"mode": "external", "reason": reason}


def test_invocation_gate_requires_each_alias_and_ignores_help_only_calls():
    @click.group()
    def root():
        pass

    @root.command()
    @click.option("--analyzer", "-a")
    def analyze(analyzer):
        pass

    catalog = CommandCatalog(root)
    catalog.outcomes["test"] = ["passed"] * 3
    catalog.record_call("test", ["analyze", "--analyzer", "prebuilt-layout"], 0)
    catalog.record_call("test", ["analyze", "-a", "prebuilt-layout", "--help"], 0)
    assert catalog.invocation_gaps() == ["cu analyze: -a"]
    catalog.record_call("test", ["analyze", "-a", "prebuilt-layout"], 0)
    assert catalog.invocation_gaps() == []


@pytest.mark.parametrize("language", ["bash", "powershell"])
@pytest.mark.parametrize("scenario", ["complex-values", "profile-endpoint", "metacharacters", "endpoint-precedence"])
def test_generated_shell_runs_exact_arguments_and_restores_environment(language, scenario):
    executable = shutil.which("bash" if language == "bash" else "pwsh")
    if language == "bash" and os.name == "nt":
        git = shutil.which("git")
        if git:
            candidate = Path(git).parents[1] / "bin" / "bash.exe"
            if candidate.is_file():
                executable = str(candidate)
    if not executable:
        pytest.skip(f"{language} shell is unavailable for generated-script execution")
    arguments = [
        "analyze", "--url", "https://example.test/bob's/video.mp4?sp=r&sig=a%2Bb",
        "--analyzer", "prebuilt-videoSearch", "--output-dir", "results with spaces", "--json",
    ]
    if scenario == "profile-endpoint":
        arguments = [
            "profile", "set", "endpoint", "https://<dev-resource>.services.ai.azure.com/", "--name", "dev",
        ]
    endpoint = "https://temporary.services.ai.azure.com/"
    if scenario == "endpoint-precedence":
        endpoint = "https://temporary-resource.services.ai.azure.com/"
        arguments = [
            "analyzer", "list", "--profile", "prod", "--endpoint",
            "https://one-time-resource.services.ai.azure.com/", "--info",
        ]
    if scenario == "metacharacters":
        Path("match.pdf").touch()
        arguments = [
            "analyze", "--pattern", "*.pdf", "--models", "gpt-5.2, text-embedding-3-large",
            "--value", "$should_stay_literal", "$(echo expanded)", "`echo expanded`",
            'embedded"quote', "", "C:\\folder\\file.pdf", "trailing\\", "-9e2",
        ]
        endpoint = 'https://temporary.services.ai.azure.com/?value=$should_stay_literal&literal=`text`&quoted="text"'
    rendered = render_command(
        arguments, executable="cu", language=language, environment={"CU_ENDPOINT": endpoint},
    )
    if scenario == "profile-endpoint":
        rendered = rendered.replace("<dev-resource>", "dev")
        arguments = [argument.replace("<dev-resource>", "dev") for argument in arguments]
    if language == "bash":
        script = (
            "cu() { printf '%s\\0' \"$CU_ENDPOINT\" \"$@\"; }\n"
            "export CU_ENDPOINT=before\n" + rendered + "\nprintf '%s\\0' \"$CU_ENDPOINT\"\n"
        )
        result = subprocess.run(
            [executable, "--noprofile", "--norc", "-c", script], capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.decode().split("\0") == [endpoint, *arguments, "before", ""]
    else:
        script = (
            "function cu { @{ endpoint=$env:CU_ENDPOINT; arguments=@($args) } }\n"
            "$env:CU_ENDPOINT = 'before'\n$observed = & {\n" + rendered + "\n}\n"
            "$observed['restored'] = $env:CU_ENDPOINT\n"
            "$observed | ConvertTo-Json -Depth 4 -Compress\n"
        )
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout.decode("utf-8-sig")) == {
            "endpoint": endpoint, "arguments": arguments, "restored": "before",
        }