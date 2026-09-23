# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import inspect
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import click
import pytest

from support.snippets import (
    _PARTS, _REGIONS, invoke_azure, invoke_cli, record_external, record_output, render_command,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def region(request):
    """Treat the whole requesting test as one active Snippet region and return its published parts."""
    lines, start = inspect.getsourcelines(request.function)
    parts: dict[str, list[dict]] = {}
    regions = _REGIONS.set({"probe": (Path(__file__), start, start + len(lines), request.function.__name__)})
    published = _PARTS.set(parts)
    try:
        yield parts
    finally:
        _PARTS.reset(published)
        _REGIONS.reset(regions)


def _content(parts):
    return "\n".join(part["content"] for part in parts["probe"])


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
        ("--api-key=<key>", True),
        ("*.pdf", False),
        ("gpt-5.2, text-embedding-3-large", False),
    ],
    ids=[
        "endpoint", "sas", "query", "spaces", "shell-expansion", "key",
        "resource", "option-value", "wildcard", "model-list",
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
    powershell = render_command(arguments, executable="cu", language="powershell", environment=environment)
    assert shlex.split(bash)[0] == "CU_ENDPOINT=" + environment["CU_ENDPOINT"]
    assert "$previous_CU_ENDPOINT = $env:CU_ENDPOINT" in powershell
    assert "finally {\n  $env:CU_ENDPOINT = $previous_CU_ENDPOINT" in powershell
    assert f'$env:CU_ENDPOINT = "{environment["CU_ENDPOINT"]}"' in powershell


@pytest.mark.parametrize("total_length", [78, 79], ids=["fits", "wraps"])
def test_bash_environment_wrapping_counts_the_full_line(total_length):
    command = "cu profile list"
    value = "x" * (total_length - len("MODE= " + command))

    rendered = render_command(["profile", "list"], executable="cu", language="bash", environment={"MODE": value})

    separator = " " if total_length == 78 else " \\\n  "
    assert rendered == f"MODE={value}{separator}{command}"


def test_bash_long_environment_command_groups_options_and_values():
    endpoint = "https://<temporary-resource>.services.ai.azure.com/"
    explicit_endpoint = "https://<one-time-resource>.services.ai.azure.com/"
    arguments = ["analyzer", "list", "--profile", "prod", "--endpoint", explicit_endpoint, "--info"]

    rendered = render_command(arguments, executable="cu", language="bash", environment={"CU_ENDPOINT": endpoint})

    assert rendered == (
        f"CU_ENDPOINT={endpoint} \\\n"
        "  cu analyzer list \\\n"
        "    --profile prod \\\n"
        f"    --endpoint {explicit_endpoint} \\\n"
        "    --info"
    )


@pytest.mark.parametrize("language", ["bash", "powershell"])
def test_placeholders_execute_bound_values_and_publish_templates(language, region):
    from cu_cli.profile import ProfileStore

    endpoint = "https://<resource-name>.services.ai.azure.com/"
    arguments = ["profile", "set", "endpoint", endpoint]

    invoke_cli(arguments, language=language, placeholder_values={"resource-name": "cu-docs-resource"})

    assert ProfileStore.load().get("endpoint") == "https://cu-docs-resource.services.ai.azure.com/"
    assert "cu-docs-resource" not in _content(region)
    assert arguments == ["profile", "set", "endpoint", endpoint]
    if language == "bash":
        assert _content(region) == f"cu profile set endpoint {endpoint}"
    else:
        assert f'"{endpoint}"' in _content(region)


def test_key_placeholder_is_never_published(region):
    from cu_cli.profile import ProfileStore

    invoke_cli(["profile", "set", "api_key", "<key>"], placeholder_values={"key": "offline-test-key"})

    assert ProfileStore.load().get("api_key") == "offline-test-key"
    assert _content(region) == "cu profile set api_key <key>"


def test_environment_placeholder_binds_only_for_the_command(region, monkeypatch):
    template = "https://<temporary-resource>.services.ai.azure.com/"
    monkeypatch.setenv("CU_ENDPOINT", "https://saved.services.ai.azure.com/")

    result = invoke_cli(
        ["env-var", "list", "--json"], env={"CU_ENDPOINT": template},
        placeholder_values={"temporary-resource": "cu-docs-temporary"},
    )

    actual = {item["name"]: item["value"] for item in json.loads(result.stdout)}
    assert actual["CU_ENDPOINT"] == "https://cu-docs-temporary.services.ai.azure.com/"
    assert os.environ["CU_ENDPOINT"] == "https://saved.services.ai.azure.com/"
    assert _content(region).startswith(f"CU_ENDPOINT={template} ")


@pytest.mark.parametrize(
    "values", [{}, {"resource-name": "cu-docs-resource", "unused": "value"}],
    ids=["missing-binding", "unused-binding"],
)
@pytest.mark.parametrize("location", ["argument", "environment"])
def test_invalid_placeholder_bindings_fail_before_cli_execution(monkeypatch, values, location):
    monkeypatch.setattr(
        click.testing.CliRunner, "invoke",
        lambda *_args, **_kwargs: pytest.fail("invalid bindings must fail before invocation"),
    )
    template = "https://<resource-name>.services.ai.azure.com/"
    arguments = ["profile", "set", "endpoint", template] if location == "argument" else ["env-var", "list"]
    environment = {} if location == "argument" else {"CU_ENDPOINT": template}

    with pytest.raises(ValueError, match="placeholder"):
        invoke_cli(arguments, env=environment, placeholder_values=values)


def test_failing_documented_command_is_not_published(region, monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("invalid command must not call the service"),
    )

    with pytest.raises(AssertionError, match="--source"):
        invoke_cli(["analyze", "./documents", "--pattern", "*.pdf"])

    assert region == {}


def test_commands_outside_regions_are_not_published():
    parts: dict[str, list[dict]] = {}
    token = _PARTS.set(parts)
    try:
        result = invoke_cli(["--version"])
    finally:
        _PARTS.reset(token)

    assert result.exit_code == 0 and parts == {}


@pytest.mark.parametrize("language", ["bash", "powershell"])
def test_region_commands_are_compact_and_keep_comments(region, language):
    invoke_cli(["--version"], language=language)
    invoke_cli(["--help"], language=language, comment="Inspect available commands.")

    assert _content(region) == "cu --version\n# Inspect available commands.\ncu --help"


def test_region_cannot_mix_command_and_output_languages(region):
    invoke_cli(["--version"])

    with pytest.raises(AssertionError, match="mixes 'bash' and 'text'"):
        record_output("output")


def test_output_blocks_validate_their_language(region):
    record_output('{"ok": true}\n', language="json")

    assert region["probe"] == [{"line": region["probe"][0]["line"], "content": '{"ok": true}', "language": "json"}]
    with pytest.raises(json.JSONDecodeError):
        record_output("not json", language="json")


@pytest.mark.parametrize(
    "comment,expected",
    [
        (None, "az login"),
        ("", "az login"),
        ("Sign in.\nUse the intended account.", "# Sign in.\n# Use the intended account.\naz login"),
    ],
    ids=["plain", "empty", "multiline-comment"],
)
def test_external_prerequisites_are_published_without_running(region, monkeypatch, comment, expected):
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: pytest.fail("external commands must not execute"))

    record_external(["az", "login"], reason="Interactive sign-in prerequisite.", comment=comment)

    assert _content(region) == expected


def test_only_installation_and_sign_in_can_skip_execution(region):
    with pytest.raises(AssertionError, match="Only installation and login"):
        record_external(["cu", "analyze", "sample_invoice.pdf"], reason="Not allowed.")


@pytest.mark.parametrize(
    "comment,expected",
    [
        (None, "az cu profile list --output json"),
        (
            "Read the shared profile.\nKeep the same Azure CLI configuration.",
            "# Read the shared profile.\n# Keep the same Azure CLI configuration.\n"
            "az cu profile list --output json",
        ),
    ],
    ids=["plain", "multiline-comment"],
)
def test_azure_cli_commands_run_the_local_extension(region, monkeypatch, comment, expected):
    monkeypatch.setattr("azure.cli.core.util.handle_version_update", lambda: None)

    profiles = invoke_azure(["cu", "profile", "list", "--output", "json"], comment=comment)

    assert any(profile["name"] == "default" for profile in profiles)
    assert _content(region) == expected


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
        arguments = ["profile", "set", "endpoint", "https://<dev-resource>.services.ai.azure.com/", "--name", "dev"]
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
    rendered = render_command(arguments, executable="cu", language=language, environment={"CU_ENDPOINT": endpoint})
    if scenario == "profile-endpoint":
        rendered = rendered.replace("<dev-resource>", "dev")
        arguments = [argument.replace("<dev-resource>", "dev") for argument in arguments]
    if language == "bash":
        script = (
            "cu() { printf '%s\\0' \"$CU_ENDPOINT\" \"$@\"; }\n"
            "export CU_ENDPOINT=before\n" + rendered + "\nprintf '%s\\0' \"$CU_ENDPOINT\"\n"
        )
        result = subprocess.run([executable, "--noprofile", "--norc", "-c", script], capture_output=True, check=False)
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
            [executable, "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout.decode("utf-8-sig")) == {
            "endpoint": endpoint, "arguments": arguments, "restored": "before",
        }
