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

from click.testing import CliRunner, Result


_PLACEHOLDER = re.compile(r"<([a-z][a-z0-9_-]*)>")
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


def _with_comment(content: str, comment: str | None) -> str:
    return "\n".join([*(f"# {line}" for line in (comment or "").splitlines()), content])


def render_command(arguments: list[str], *, executable: str, language: str, environment: dict) -> str:
    if language == "bash":
        def quote(value):
            substituted = re.sub(r"<[a-z][a-z0-9_-]*>", "placeholder", value)
            if shlex.quote(substituted) == substituted:
                return value
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
            return '"' + escaped + '"'
        continuation = " \\\n  "
    elif language == "powershell":
        def quote(value):
            escaped = value.replace("`", "``").replace('"', '`"').replace("$", "`$")
            return '"' + escaped + '"'
        continuation = " `\n  "
    else:
        raise AssertionError(f"unsupported command language: {language}")
    rendered_arguments = [
        argument if language == "powershell" and re.fullmatch(r"(?:--?)?[A-Za-z_][A-Za-z0-9_-]*", argument)
        else quote(argument)
        for argument in arguments
    ]
    if language == "bash" and environment:
        assignments = [f"{key}={quote(value)}" for key, value in sorted(environment.items())]
        command = " ".join([executable, *rendered_arguments])
        single_line = " ".join([*assignments, command])
        if len(single_line) <= 78:
            return single_line
        if len(command) + 2 > 78:
            groups = [executable]
            for argument, rendered_argument in zip(arguments, rendered_arguments):
                if argument.startswith("--"):
                    groups.append(rendered_argument)
                else:
                    groups[-1] += " " + rendered_argument
            command = " \\\n    ".join(groups)
        return " \\\n  ".join([*assignments, command])
    chunks = [executable]
    for argument, rendered_argument in zip(arguments, rendered_arguments):
        if argument.startswith("--") and len(" ".join(chunks)) > 78:
            chunks.append(continuation + rendered_argument)
        else:
            chunks.append(rendered_argument)
    command = " ".join(chunks).replace(" " + continuation, continuation)
    if not environment:
        return command
    setup = [
        line for key, value in sorted(environment.items())
        for line in (f"$previous_{key} = $env:{key}", f"$env:{key} = {quote(value)}")
    ]
    cleanup = [f"  $env:{key} = $previous_{key}" for key in sorted(environment)]
    return "\n".join([*setup, "try {", "  " + command, "} finally {", *cleanup, "}"])


def invoke_cli(
    arguments, *, executable: str = "cu", language: str = "bash",
    comment: str | None = None, placeholder_values: dict[str, str] | None = None,
    **kwargs,
) -> Result:
    """Run ``cu`` in process; inside a region, publish the command with its template values."""
    from cu_cli.cli import main

    regions = _matching_regions()
    arguments = [str(argument) for argument in arguments]
    document_arguments = arguments
    document_environment = kwargs.get("env") or {}
    if placeholder_values is not None or regions:
        templates = arguments + [
            value for value in document_environment.values() if isinstance(value, str)
        ]
        names = {name for template in templates for name in _PLACEHOLDER.findall(template)}
        values = placeholder_values or {}
        if names != values.keys():
            raise ValueError(
                f"placeholder bindings mismatch: missing {sorted(names - values.keys())}, "
                f"unused {sorted(values.keys() - names)}"
            )
        if any(not isinstance(value, str) for value in values.values()):
            raise ValueError("placeholder values must be strings")

        def bind(template: str) -> str:
            return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)

        arguments = [bind(argument) for argument in arguments]
        if document_environment:
            kwargs["env"] = {
                name: bind(value) if isinstance(value, str) else value
                for name, value in document_environment.items()
            }
    result = CliRunner().invoke(main, arguments, **kwargs)
    if regions:
        assert result.exit_code == 0, result.output
        assert executable in {"cu", "cu-cli"}
        content = render_command(
            document_arguments, executable=executable, language=language,
            environment=document_environment,
        )
        _publish(regions, _with_comment(content, comment), language)
    return result


def invoke_azure(arguments: list[str], *, comment: str | None = None):
    """Run ``az`` with only the local CU extension loaded and return the command result."""
    regions = _matching_regions()
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
    if regions:
        _publish(regions, _with_comment(shlex.join(["az", *arguments]), comment), "bash")
    return cli.result.result


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


def record_external(arguments: list[str], *, reason: str, comment: str | None = None) -> None:
    """Publish an installation or sign-in prerequisite that tests never execute."""
    regions = _matching_regions()
    assert reason.strip()
    assert arguments == ["az", "login"] or arguments[:4] == ["python", "-m", "pip", "install"], (
        "Only installation and login prerequisites can be documented without running them"
    )
    _publish(regions, _with_comment(shlex.join(arguments), comment), "bash")
