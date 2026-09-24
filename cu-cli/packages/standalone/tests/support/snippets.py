# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Helpers whose calls inside ``# region Snippet:<id>`` blocks become documentation code blocks."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from contextvars import ContextVar
from io import StringIO
import json
import os
from pathlib import Path
import re
import shlex
import sys
import textwrap

from click.testing import CliRunner


_PLACEHOLDER = re.compile(r"<([a-z][a-z0-9_-]*)>")
# Quoted words that bash keeps literal; any other shell syntax in a documented command is rejected.
_QUOTED = re.compile(r"'[^']*'|\"[^\"$`\\!]*\"")
_SHELL_SYNTAX = re.compile(r"[\"'$`\\;&|<>()*?\[\]{}!]|(?:^|\s)[~#]")
_ASSIGNMENT = re.compile(r"([A-Za-z_]\w*)=(.*)")
# The only PowerShell form: save, set, and restore one environment variable around one command.
_POWERSHELL_ENVIRONMENT = re.compile(
    r'\$previous_(?P<name>\w+) = \$env:(?P=name)\n'
    r'\$env:(?P=name) = "(?P<value>[^"`$]*)"\n'
    r"try \{\n  (?P<command>[^\n]+)\n\} finally \{\n"
    r"  \$env:(?P=name) = \$previous_(?P=name)\n\}"
)
_REGIONS: ContextVar[dict[str, tuple[Path, int, int, str]]] = ContextVar("snippet_regions", default={})
_PARTS: ContextVar[dict[str, list[dict]] | None] = ContextVar("snippet_parts", default=None)


def _matching_regions() -> list[tuple[str, int]]:
    regions = _REGIONS.get()
    if not regions:
        return []
    frame = sys._getframe(1)
    try:
        while frame is not None:
            matching = [
                (identifier, frame.f_lineno)
                for identifier, (path, start, end, function) in regions.items()
                if function == frame.f_code.co_name and start < frame.f_lineno < end
                and path.resolve() == Path(frame.f_code.co_filename).resolve()
            ]
            if matching:
                return matching
            frame = frame.f_back
    finally:
        del frame
    return []


def _publish(regions: list[tuple[str, int]], content: str, language: str) -> None:
    parts = _PARTS.get()
    if parts is None:
        return
    for identifier, line in regions:
        existing = parts.setdefault(identifier, [])
        if existing and existing[0]["language"] != language:
            raise AssertionError(
                f"Snippet region {identifier!r} mixes {existing[0]['language']!r} and {language!r} blocks"
            )
        if any(part["line"] == line for part in existing):
            raise AssertionError(f"Snippet region {identifier!r} runs line {line} more than once")
        existing.append({"line": line, "content": content.rstrip("\n"), "language": language})


def _placeholder_binder(templates: list[str], values: dict[str, str]):
    names = {name for template in templates for name in _PLACEHOLDER.findall(template)}
    if names != values.keys():
        raise ValueError(
            f"placeholder bindings mismatch: missing {sorted(names - values.keys())}, "
            f"unused {sorted(values.keys() - names)}"
        )
    if any(not isinstance(value, str) for value in values.values()):
        raise ValueError("placeholder values must be strings")
    return lambda template: _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


def _documented_command(script: str, language: str = "bash") -> tuple[str, dict[str, str], list[str]]:
    """Return ``script`` as published, its environment overrides, and the words of its one command."""
    text = textwrap.dedent(script).strip("\n")
    for line in text.splitlines():
        if not line.lstrip().startswith("#") and re.search(r"\S {2,}\S", line):
            raise AssertionError(
                f"repeated spaces in {line.strip()!r}; collapse them, or use a raw string "
                "so backslash line continuations are kept"
            )
    if language == "powershell":
        match = _POWERSHELL_ENVIRONMENT.fullmatch("\n".join(
            line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
        ))
        if match is None:
            raise AssertionError(
                "PowerShell examples must save, set, and restore one environment variable around one command"
            )
        if not re.fullmatch(r"[\w ./:=-]+", _PLACEHOLDER.sub("_", match["command"])):
            raise AssertionError(f"quote shell syntax that PowerShell would interpret: {match['command']!r}")
        return text, {match["name"]: match["value"]}, match["command"].split()
    if language != "bash":
        raise AssertionError(f"unsupported command language: {language}")
    commands = [
        line for line in text.replace("\\\n", "").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(commands) != 1:
        raise AssertionError(f"write exactly one command per call:\n{text}")
    if _SHELL_SYNTAX.search(_PLACEHOLDER.sub("_", _QUOTED.sub("_", commands[0]))):
        raise AssertionError(f"quote shell syntax that bash would interpret: {commands[0].strip()!r}")
    words = shlex.split(commands[0])
    environment = {}
    while words and (assignment := _ASSIGNMENT.fullmatch(words[0])):
        environment[assignment[1]] = assignment[2]
        del words[0]
    return text, environment, words


def _run_azure(arguments: list[str]):
    from azure.cli.core import AzCli, MainCommandsLoader
    from azure.cli.core.commands import AzCliCommandInvoker
    from azure.cli.core.parser import AzCliCommandParser
    from azure.cli.core.azlogging import AzCliLogging
    from azure.cli.core._help import AzCliHelp
    from azure.cli.core._output import AzOutputProducer
    from azext_content_understanding import ContentUnderstandingCommandsLoader

    class LocalCommandsLoader(MainCommandsLoader):
        def load_command_table(self, args):
            extension = ContentUnderstandingCommandsLoader(self.cli_ctx)
            self.command_table = extension.load_command_table(args)
            self.command_group_table.update(extension.command_group_table)
            self.cmd_to_loader_map = {name: [extension] for name in self.command_table}
            return self.command_table

    output = StringIO()
    with redirect_stdout(output), redirect_stderr(output):
        cli = AzCli(
            cli_name="az", config_dir=os.environ["AZURE_CONFIG_DIR"],
            commands_loader_cls=LocalCommandsLoader,
            invocation_cls=AzCliCommandInvoker,
            parser_cls=AzCliCommandParser, logging_cls=AzCliLogging,
            output_cls=AzOutputProducer, help_cls=AzCliHelp,
            config_env_var_prefix="AZURE",
        )
        status = cli.invoke(arguments)
    assert status == 0, output.getvalue()
    return cli.result.result


def run_command(
    script: str, *, language: str = "bash", placeholder_values: dict[str, str] | None = None,
    **kwargs,
):
    """Run one ``cu`` or ``az cu`` command written as shell text; inside a region, publish it as written."""
    regions = _matching_regions()
    content, environment, words = _documented_command(script, language)
    if placeholder_values is not None or regions:
        bind = _placeholder_binder([*words, *environment.values()], placeholder_values or {})
        words = [bind(word) for word in words]
        environment = {name: bind(value) for name, value in environment.items()}
    if words[:1] not in (["cu"], ["cu-cli"]) and words[:2] != ["az", "cu"]:
        raise AssertionError(f"documented commands start with cu, cu-cli, or az cu:\n{content}")
    if words[0] == "az":
        assert not kwargs and not environment, "az cu commands take no environment or CliRunner options"
        result = _run_azure(words[1:])
    else:
        from cu_cli.cli import main

        result = CliRunner().invoke(main, words[1:], env=environment, **kwargs)
        if regions:
            assert result.exit_code == 0, result.output
    if regions:
        _publish(regions, content, language)
    return result


def record_output(content: str, *, language: str = "text") -> None:
    """Publish text produced by the preceding commands as an output block."""
    regions = _matching_regions()
    assert isinstance(content, str)
    if language not in {"text", "json", "yaml"}:
        raise AssertionError(f"not an output language: {language}")
    if language == "json":
        json.loads(content)
    elif language == "yaml":
        import yaml

        yaml.safe_load(content)
    _publish(regions, content, language)


def record_external(command: str, *, reason: str) -> None:
    """Publish an installation or sign-in prerequisite that tests never execute."""
    regions = _matching_regions()
    assert reason.strip()
    content, environment, arguments = _documented_command(command)
    assert not environment and (
        arguments == ["az", "login"] or arguments[:4] == ["python", "-m", "pip", "install"]
    ), "Only installation and login prerequisites can be documented without running them"
    _publish(regions, content, "bash")
