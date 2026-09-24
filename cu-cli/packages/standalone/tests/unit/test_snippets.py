# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import textwrap

import click
import pytest

from support.snippets import _PARTS, _REGIONS, _documented_command, record_external, record_output, run_command


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


def _shell(language):
    executable = shutil.which("bash" if language == "bash" else "pwsh")
    if language == "bash" and os.name == "nt":
        git = shutil.which("git")
        if git:
            candidate = Path(git).parents[1] / "bin" / "bash.exe"
            if candidate.is_file():
                executable = str(candidate)
    if not executable:
        pytest.skip(f"{language} shell is unavailable for generated-script execution")
    return executable


def test_key_placeholder_is_never_published(region):
    from cu_cli.profile import ProfileStore

    run_command("cu profile set api_key <key>", placeholder_values={"key": "offline-test-key"})

    assert ProfileStore.load().get("api_key") == "offline-test-key"
    assert _content(region) == "cu profile set api_key <key>"


@pytest.mark.parametrize(
    "values", [{}, {"resource-name": "cu-docs-resource", "unused": "value"}],
    ids=["missing-binding", "unused-binding"],
)
@pytest.mark.parametrize(
    "command",
    [
        "cu profile set endpoint https://<resource-name>.services.ai.azure.com/",
        "CU_ENDPOINT=https://<resource-name>.services.ai.azure.com/ cu env-var list",
    ],
    ids=["argument", "environment"],
)
def test_invalid_placeholder_bindings_fail_before_cli_execution(monkeypatch, values, command):
    monkeypatch.setattr(
        click.testing.CliRunner, "invoke",
        lambda *_args, **_kwargs: pytest.fail("invalid bindings must fail before invocation"),
    )

    with pytest.raises(ValueError, match="placeholder"):
        run_command(command, placeholder_values=values)


def test_failing_documented_command_is_not_published(region, monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("invalid command must not call the service"),
    )

    with pytest.raises(AssertionError, match="--source"):
        run_command('cu analyze ./documents --pattern "*.pdf"')

    assert region == {}


def test_commands_outside_regions_are_not_published():
    parts: dict[str, list[dict]] = {}
    token = _PARTS.set(parts)
    try:
        result = run_command("cu --version")
    finally:
        _PARTS.reset(token)

    assert result.exit_code == 0 and parts == {}


def test_region_commands_are_compact_and_keep_comments(region):
    run_command("cu --version")
    run_command("""
        # Inspect available commands.
        cu --help
    """)

    assert _content(region) == "cu --version\n# Inspect available commands.\ncu --help"


def test_region_cannot_mix_command_and_output_languages(region):
    run_command("cu --version")

    with pytest.raises(AssertionError, match="mixes 'bash' and 'text'"):
        record_output("output")


def test_output_blocks_validate_their_language(region):
    record_output('{"ok": true}\n', language="json")

    assert region["probe"] == [{"line": region["probe"][0]["line"], "content": '{"ok": true}', "language": "json"}]
    with pytest.raises(json.JSONDecodeError):
        record_output("not json", language="json")


def test_command_text_runs_bound_words_and_is_published_as_written(region):
    from cu_cli.profile import ProfileStore

    result = run_command(r"""
        # Save the endpoint on the active profile.
        cu profile set endpoint \
          https://<resource-name>.services.ai.azure.com/
    """, placeholder_values={"resource-name": "cu-docs-resource"})

    assert result.exit_code == 0
    assert ProfileStore.load().get("endpoint") == "https://cu-docs-resource.services.ai.azure.com/"
    assert _content(region) == (
        "# Save the endpoint on the active profile.\n"
        "cu profile set endpoint \\\n"
        "  https://<resource-name>.services.ai.azure.com/"
    )


def test_line_continuation_lost_by_a_plain_string_is_rejected():
    with pytest.raises(AssertionError, match="raw string"):
        run_command("""
            cu profile set endpoint \
              https://example.services.ai.azure.com/
        """)


@pytest.mark.parametrize(
    "script", ["cu --version\ncu --help", "# Only a comment."], ids=["two-commands", "comment-only"],
)
def test_each_call_runs_exactly_one_command(script):
    with pytest.raises(AssertionError, match="exactly one command"):
        run_command(script)


@pytest.mark.parametrize(
    "command",
    [
        "cu analyze --source documents --pattern *.pdf",
        "cu profile set endpoint $CU_ENDPOINT",
        'cu analyze "$(pwd)/sample_invoice.pdf"',
        "cu --version; cu --help",
        "cu --version # trailing comment",
        "cu analyze ~/sample_invoice.pdf",
        "cu analyze --url https://example.test/a.pdf?sp=r&sig=value",
        "cu analyze sample\\ invoice.pdf",
        'cu analyze "unterminated.pdf',
    ],
    ids=[
        "glob", "variable", "substitution", "separator", "trailing-comment",
        "home", "background", "escape", "unterminated-quote",
    ],
)
def test_shell_syntax_bash_would_interpret_is_rejected(command, monkeypatch):
    monkeypatch.setattr(
        click.testing.CliRunner, "invoke",
        lambda *_args, **_kwargs: pytest.fail("rejected command text must not run"),
    )

    with pytest.raises(AssertionError, match="shell syntax"):
        run_command(command)


@pytest.mark.parametrize("command", ["python --version", "az login"], ids=["other-program", "other-az-command"])
def test_only_cu_and_az_cu_commands_run(command, monkeypatch):
    monkeypatch.setattr(
        click.testing.CliRunner, "invoke",
        lambda *_args, **_kwargs: pytest.fail("rejected command text must not run"),
    )

    with pytest.raises(AssertionError, match="cu, cu-cli, or az cu"):
        run_command(command)


def test_azure_command_text_runs_the_local_extension(region, monkeypatch):
    monkeypatch.setattr("azure.cli.core.util.handle_version_update", lambda: None)

    profiles = run_command("""
        # Read the shared profile.
        az cu profile list --output json
    """)

    assert any(profile["name"] == "default" for profile in profiles)
    assert _content(region) == "# Read the shared profile.\naz cu profile list --output json"


def test_external_command_text_is_published_without_running(region, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: pytest.fail("external commands must not execute"))

    record_external("""
        # Sign in.
        az login
    """, reason="Interactive sign-in prerequisite.")

    assert _content(region) == "# Sign in.\naz login"
    with pytest.raises(AssertionError, match="Only installation and login"):
        record_external("cu --version", reason="Not allowed.")


@pytest.mark.parametrize(
    "command",
    [
        'cu analyze --url "https://example.test/bob\'s/video.mp4?sp=r&sig=a%2Bb" --output-dir "results with spaces"',
        "cu analyze --pattern '*.pdf' --models \"gpt-5.2, text-embedding-3-large\" --value '$literal' \"\" -9e2",
        "# Continue a long command.\ncu analyze sample_invoice.pdf \\\n  --analyzer prebuilt-layout",
        "CU_ENDPOINT=https://temporary.example.test/ \\\n  cu analyzer list --info",
    ],
    ids=["quoted-url", "literal-words", "continuation", "environment-prefix"],
)
def test_accepted_command_text_matches_bash_words(command):
    content, environment, words = _documented_command(command)
    script = (
        "cu() { printf '%s\\0' \"$CU_ENDPOINT\" \"$@\"; }\nexport CU_ENDPOINT=before\n"
        + content + "\nprintf '%s\\0' \"$CU_ENDPOINT\"\n"
    )

    result = subprocess.run([_shell("bash"), "--noprofile", "--norc", "-c", script], capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().split("\0") == [
        environment.get("CU_ENDPOINT", "before"), *words[1:], "before", "",
    ]


def test_environment_prefix_sets_the_variable_only_for_the_command(region, monkeypatch):
    monkeypatch.setenv("CU_ENDPOINT", "https://saved.services.ai.azure.com/")

    result = run_command(r"""
        CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
          cu env-var list --json
    """, placeholder_values={"temporary-resource": "cu-docs-temporary"})

    actual = {item["name"]: item["value"] for item in json.loads(result.stdout)}
    assert actual["CU_ENDPOINT"] == "https://cu-docs-temporary.services.ai.azure.com/"
    assert os.environ["CU_ENDPOINT"] == "https://saved.services.ai.azure.com/"
    assert _content(region) == (
        "CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \\\n  cu env-var list --json"
    )


_POWERSHELL_OVERRIDE = """
    # Override the endpoint for one command.
    $previous_CU_ENDPOINT = $env:CU_ENDPOINT
    $env:CU_ENDPOINT = "https://<temporary-resource>.services.ai.azure.com/"
    try {
      cu env-var list --json
    } finally {
      $env:CU_ENDPOINT = $previous_CU_ENDPOINT
    }
"""


def test_powershell_environment_pattern_sets_the_variable_only_for_the_command(region, monkeypatch):
    monkeypatch.setenv("CU_ENDPOINT", "https://saved.services.ai.azure.com/")

    result = run_command(
        _POWERSHELL_OVERRIDE, language="powershell",
        placeholder_values={"temporary-resource": "cu-docs-temporary"},
    )

    actual = {item["name"]: item["value"] for item in json.loads(result.stdout)}
    assert actual["CU_ENDPOINT"] == "https://cu-docs-temporary.services.ai.azure.com/"
    assert os.environ["CU_ENDPOINT"] == "https://saved.services.ai.azure.com/"
    assert region["probe"][0]["language"] == "powershell"
    assert _content(region) == textwrap.dedent(_POWERSHELL_OVERRIDE).strip("\n")


@pytest.mark.parametrize(
    "script",
    [
        "cu --version",
        _POWERSHELL_OVERRIDE.replace("= $previous_CU_ENDPOINT", "= $null"),
        _POWERSHELL_OVERRIDE.replace("cu env-var list --json", 'cu analyze "sample invoice.pdf"'),
    ],
    ids=["no-environment", "no-restore", "quoted-argument"],
)
def test_powershell_text_outside_the_supported_pattern_is_rejected(script, monkeypatch):
    monkeypatch.setattr(
        click.testing.CliRunner, "invoke",
        lambda *_args, **_kwargs: pytest.fail("rejected command text must not run"),
    )

    with pytest.raises(AssertionError, match="PowerShell"):
        run_command(script, language="powershell")


def test_accepted_powershell_text_matches_powershell():
    content, environment, words = _documented_command(_POWERSHELL_OVERRIDE, "powershell")
    script = (
        "function cu { @{ endpoint=$env:CU_ENDPOINT; arguments=@($args) } }\n"
        "$env:CU_ENDPOINT = 'before'\n$observed = & {\n" + content + "\n}\n"
        "$observed['restored'] = $env:CU_ENDPOINT\n"
        "$observed | ConvertTo-Json -Depth 4 -Compress\n"
    )

    result = subprocess.run(
        [_shell("powershell"), "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.decode("utf-8-sig")) == {
        "endpoint": environment["CU_ENDPOINT"], "arguments": words[1:], "restored": "before",
    }
