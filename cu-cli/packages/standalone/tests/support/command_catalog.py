# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import copy
from dataclasses import dataclass, field
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys

import click
from click.testing import CliRunner, Result


_IDENTIFIER = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")
_ACTIVE: ContextVar[tuple["CommandCatalog", str] | None] = ContextVar(
    "command_catalog", default=None,
)
_RECORDING: ContextVar[tuple[Path, str, object] | None] = ContextVar("recording_evidence", default=None)
_REGIONS: ContextVar[dict[str, tuple[Path, int, int, str]]] = ContextVar("snippet_regions", default={})


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


def file_evidence(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    test_root = Path(__file__).resolve().parents[1]
    name = path.relative_to(test_root).as_posix() if path.is_relative_to(test_root) else path.name
    return {"path": name, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def record_sample(path: Path) -> None:
    active = _ACTIVE.get()
    if active is not None:
        catalog, test = active
        evidence = file_evidence(path)
        fixtures = catalog.fixtures.setdefault(test, [])
        if evidence not in fixtures:
            fixtures.append(evidence)


@contextmanager
def recording_evidence(path: Path, mode: str, cassette):
    token = _RECORDING.set((path, mode, cassette))
    try:
        yield
    finally:
        _RECORDING.reset(token)


def verification_for(arguments: list[str], before: int) -> dict:
    recording = _RECORDING.get()
    if recording is not None:
        path, mode, cassette = recording
        if mode == "playback" and cassette.play_count > before:
            return {"mode": "playback", "recordings": [file_evidence(path)]}
        if mode != "playback":
            return {"mode": mode, "reason": "Explicit live or record execution, not offline playback."}
    command = arguments[1:] if arguments[:1] == ["cu"] else arguments
    local = (
        any(option in command for option in ("--help", "-h", "--version", "-V"))
        or command[:1] == ["env-var"]
        or (command[:1] == ["profile"] and command[1:2] != ["sync-defaults"] and "--deployments" not in command)
        or command[:2] == ["analyzer", "validate"]
        or (command[:3] == ["analyzer", "schema", "create"] and "--from-sample" not in command)
        or ("--dry-run" in command and (command[:1] == ["analyze"] or command[:2] == ["analyzer", "test"]))
        or (recording is not None and "skip" in command and "--on-existing" in command)
    )
    return {
        "mode": "local" if local else "mocked",
        "reason": "Local command contract." if local else "Service behavior uses test doubles; no matching HTTP recording consumed.",
    }


def command_inventory(root: click.Command) -> dict[str, dict]:
    inventory: dict[str, dict] = {}

    def visit(command: click.Command, path: tuple[str, ...]) -> None:
        if command.hidden:
            return
        if isinstance(command, click.Group):
            for name, child in command.commands.items():
                visit(child, (*path, name))
            return
        parameters = []
        for parameter in command.params:
            if getattr(parameter, "hidden", False):
                continue
            default = parameter.default
            if callable(default):
                default = "dynamic"
            elif not isinstance(default, (str, int, float, bool, type(None))):
                default = None if str(default) == "Sentinel.UNSET" else str(default)
            names = list(parameter.opts)
            if isinstance(parameter, click.Option):
                names.extend(parameter.secondary_opts)
            parameters.append({
                "name": parameter.name,
                "spellings": names,
                "positional": isinstance(parameter, click.Argument),
                "required": parameter.required,
                "default": default,
                "multiple": parameter.multiple or parameter.nargs == -1,
                "flag": isinstance(parameter, click.Option) and parameter.is_flag,
                "type": parameter.type.name,
                "choices": list(getattr(parameter.type, "choices", ())),
                "minimum": getattr(parameter.type, "min", None),
                "maximum": getattr(parameter.type, "max", None),
            })
        inventory[" ".join(path)] = {"parameters": parameters}

    visit(root, ())
    return dict(sorted(inventory.items()))


@dataclass
class CommandCatalog:
    root: click.Command = field(repr=False)
    inventory: dict[str, dict] = field(init=False)
    calls: list[dict] = field(default_factory=list)
    examples: dict[str, dict] = field(default_factory=dict)
    outcomes: dict[str, list[str]] = field(default_factory=dict)
    fixtures: dict[str, list[dict]] = field(default_factory=dict)
    executions: dict[str, list[dict]] = field(default_factory=dict)
    region_parts: dict[str, list[dict]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.inventory = command_inventory(self.root)

    def record_call(self, test: str, arguments: list[str], exit_code: int) -> None:
        path = next((
            name for name in sorted(self.inventory, key=len, reverse=True)
            if arguments[:len(name.split())] == name.split()
        ), None)
        if path is None:
            return
        command = self.root
        for name in path.split():
            command = command.commands[name]
        context = click.Context(
            command, help_option_names=self.root.context_settings.get("help_option_names"),
        )
        parameters: list[click.Parameter] = []
        required_options: list[click.Option] = []
        for parameter in command.get_params(context):
            spellings = parameter.opts + parameter.secondary_opts if isinstance(parameter, click.Option) else [parameter.name]
            if isinstance(parameter, click.Option) and parameter.required:
                required_options.append(parameter)
            for spelling in spellings:
                parsed_parameter = copy(parameter)
                parsed_parameter.callback = None
                parsed_parameter.envvar = None
                parsed_parameter.default = None
                if isinstance(parsed_parameter, click.Option):
                    parsed_parameter.opts = [spelling]
                    parsed_parameter.secondary_opts = []
                    parsed_parameter.name = spelling
                    parsed_parameter.required = False
                    parsed_parameter.prompt = None
                    if spelling in parameter.secondary_opts:
                        parsed_parameter.flag_value = False
                parameters.append(parsed_parameter)
        parser = click.Command(command.name, params=parameters, add_help_option=False)
        options: set[str] = set()
        positional = False
        help_only = False
        parsed = False
        try:
            with parser.make_context(command.name or "", arguments[len(path.split()):]) as parsed_context:
                supplied = {
                    parameter.name for parameter in parameters
                    if parsed_context.get_parameter_source(parameter.name) is click.core.ParameterSource.COMMANDLINE
                }
                help_only = bool(supplied & set(context.help_option_names))
                if not help_only and any(
                    not supplied.intersection(parameter.opts + parameter.secondary_opts)
                    for parameter in required_options
                ):
                    raise click.UsageError("Missing required option")
                known_options = {
                    spelling for parameter in self.inventory[path]["parameters"]
                    if not parameter["positional"] for spelling in parameter["spellings"]
                }
                options = supplied & known_options
                positional = any(
                    isinstance(parameter, click.Argument) and parameter.name in supplied
                    and parsed_context.params[parameter.name] not in (None, ())
                    for parameter in parameters
                )
                parsed = True
        except click.ClickException:
            pass
        self.calls.append({
            "test": test,
            "command": path,
            "options": sorted(options),
            "positional": positional,
            "exit_code": exit_code,
            "help_only": help_only,
            "parsed": parsed,
        })

    def record_example(
        self, identifier: str, test: str, text: str, language: str, *, reason: str | None = None,
        verification: dict | None = None,
    ) -> None:
        if not _IDENTIFIER.fullmatch(identifier):
            raise AssertionError(f"invalid documentation example ID: {identifier!r}")
        if identifier in self.examples:
            raise AssertionError(f"duplicate documentation example ID: {identifier!r}")
        self.examples[identifier] = {
            "test": test, "content": text.rstrip("\n"), "language": language,
            "reason": reason,
            "verification": verification or {"mode": "unclassified"},
            "step": len(self.executions.get(test, [])) - 1,
            "fixtures": list(self.fixtures.get(test, [])),
        }

    def record_execution(self, test: str, verification: dict) -> None:
        self.executions.setdefault(test, []).append(verification)

    def record_region(
        self, identifier: str, line: int, test: str, content: str, language: str,
        verification: dict, *, reason: str | None = None,
    ) -> None:
        parts = self.region_parts.setdefault(identifier, [])
        if parts and (
            self.examples[identifier]["test"] != test
            or self.examples[identifier]["language"] != language
            or any(part["line"] == line for part in parts)
        ):
            raise AssertionError(f"Snippet region {identifier!r} repeats a call, test, or mixes languages")
        step = len(self.executions.get(test, [])) - 1
        parts.append({"line": line, "content": content, "step": step, "verification": verification})
        if len(parts) == 1:
            self.record_example(identifier, test, content, language, verification=verification, reason=reason)
        else:
            entry = self.examples[identifier]
            entry["content"] = "\n\n".join(part["content"].rstrip("\n") for part in parts)
            modes = {part["verification"].get("mode", "unclassified") for part in parts}
            steps = [part["step"] for part in parts]
            entry["verification"] = {
                "mode": next(iter(modes)) if len(modes) == 1 else "mixed",
                "commands": [part["verification"] for part in parts],
                "consecutive": steps[0] >= 0 and steps == list(range(steps[0], steps[0] + len(steps))),
            }
            entry["fixtures"] = list(self.fixtures.get(test, []))
        self.examples[identifier]["last_step"] = step

    def passed(self, test: str) -> bool:
        outcomes = self.outcomes.get(test, [])
        return outcomes == ["passed", "passed", "passed"]

    def invocation_gaps(self) -> list[str]:
        calls = [
            call for call in self.calls
            if self.passed(call["test"]) and call["parsed"] and not call["help_only"]
        ]
        missing: list[str] = []
        for command, entry in self.inventory.items():
            command_calls = [call for call in calls if call["command"] == command]
            if not command_calls:
                missing.append(f"cu {command}: no non-help invocation in a passing test")
                continue
            observed = {option for call in command_calls for option in call["options"]}
            for parameter in entry["parameters"]:
                if parameter["positional"]:
                    continue
                for spelling in parameter["spellings"]:
                    if spelling not in observed:
                        missing.append(f"cu {command}: {spelling}")
        return missing

    def export(self, target: Path) -> None:
        payload = {
            "inventory": self.inventory,
            "calls": [call for call in self.calls if self.passed(call["test"])],
            "examples": {
                identifier: example
                for identifier, example in sorted(self.examples.items())
                if self.passed(example["test"])
            },
            "not_passed": sorted(test for test in self.outcomes if not self.passed(test)),
            "invocation_gaps": self.invocation_gaps(),
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def matrix(self) -> str:
        calls = [
            call for call in self.calls
            if self.passed(call["test"]) and call["parsed"] and not call["help_only"]
        ]
        lines = [
            "# CLI command test matrix", "",
            "Generated from the actual Click command tree and passing pytest invocations.",
            "The existing README and usage guide do not define this inventory.", "",
            "This is invocation evidence, not a claim of exhaustive value or state coverage.",
            "Help-only calls and failed, skipped, or teardown-failed tests do not count.",
            "Calls rejected by Click's argument parser do not count as invocation coverage.",
            "Argument values are deliberately omitted to avoid publishing credentials.",
            "A parameter appearing in a passing negative test does not prove its happy path.", "",
            f"Public leaf commands: {len(self.inventory)}. Non-help calls: {len(calls)}.", "",
            "| Command | Calls | Parameters without an explicit invocation |",
            "| --- | ---: | --- |",
        ]

        def relevant(parameter, command_calls):
            if parameter["positional"]:
                return [call for call in command_calls if call["positional"]]
            return [
                call for call in command_calls
                if set(parameter["spellings"]) & set(call["options"])
            ]

        for command, entry in self.inventory.items():
            command_calls = [call for call in calls if call["command"] == command]
            missing = [
                parameter["name"] for parameter in entry["parameters"]
                if not relevant(parameter, command_calls)
            ]
            lines.append(
                f"| `cu {command}` | {len(command_calls)} | {', '.join(missing) or 'None'} |"
            )

        for command, entry in self.inventory.items():
            command_calls = [call for call in calls if call["command"] == command]
            lines.extend([
                "", f"## cu {command}", "",
                "| Parameter | Domain | Observed spellings | Example test |",
                "| --- | --- | --- | --- |",
            ])
            for parameter in entry["parameters"]:
                evidence = relevant(parameter, command_calls)
                observed = sorted({
                    spelling for call in evidence for spelling in call["options"]
                    if spelling in parameter["spellings"]
                })
                domain = parameter["type"]
                if parameter["choices"]:
                    domain += ": " + ", ".join(str(value) for value in parameter["choices"])
                if parameter["minimum"] is not None or parameter["maximum"] is not None:
                    domain += f" [{parameter['minimum']}, {parameter['maximum']}]"
                if parameter["multiple"]:
                    domain += "; repeatable"
                if parameter["required"]:
                    domain += "; required"
                if parameter["default"] is not None:
                    domain += f"; default={parameter['default']}"
                evidence.sort(key=lambda call: (call["exit_code"] != 0, call["test"]))
                example = f"`{evidence[0]['test']}`" if evidence else "MISSING"
                names = ", ".join(parameter["spellings"])
                spelling_text = ", ".join(observed) or ("positional" if evidence else "MISSING")
                lines.append(f"| `{names}` | {domain} | {spelling_text} | {example} |")
            combinations: dict[tuple, str] = {}
            for call in command_calls:
                key = (call["positional"], tuple(call["options"]), call["exit_code"])
                combinations.setdefault(key, call["test"])
            lines.extend([
                "", "### Observed combinations", "",
                "| Explicit arguments | Exit | Example test |", "| --- | ---: | --- |",
            ])
            for (positional, options, exit_code), test in sorted(combinations.items()):
                shape = " ".join((["POSITIONAL"] if positional else []) + list(options))
                lines.append(f"| `{shape or '(defaults)'}` | {exit_code} | `{test}` |")
        not_passed = sorted(test for test in self.outcomes if not self.passed(test))
        if not_passed:
            lines.extend(["", "## Tests excluded from evidence", ""])
            lines.extend(f"- `{test}`" for test in not_passed)
        return "\n".join(lines) + "\n"


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
    arguments, *, example_executable: str = "cu",
    example_language: str = "bash", expected_exit_code: int = 0,
    example_description: str | None = None, placeholder_values: dict[str, str] | None = None,
    **kwargs,
) -> Result:
    from cu_cli.cli import main

    regions = _matching_regions()
    arguments = [str(argument) for argument in arguments]
    document_arguments = arguments
    document_environment = kwargs.get("env") or {}
    if placeholder_values is not None or regions:
        placeholder = re.compile(r"<([a-z][a-z0-9_-]*)>")
        templates = arguments + [
            value for value in document_environment.values() if isinstance(value, str)
        ]
        names = {name for template in templates for name in placeholder.findall(template)}
        values = placeholder_values or {}
        if names != values.keys():
            raise ValueError(
                f"placeholder bindings mismatch: missing {sorted(names - values.keys())}, "
                f"unused {sorted(values.keys() - names)}"
            )
        if any(not isinstance(value, str) for value in values.values()):
            raise ValueError("placeholder values must be strings")

        def bind(template: str) -> str:
            return placeholder.sub(lambda match: values[match.group(1)], template)

        arguments = [bind(argument) for argument in arguments]
        if document_environment:
            kwargs["env"] = {
                name: bind(value) if isinstance(value, str) else value
                for name, value in document_environment.items()
            }
    recording = _RECORDING.get()
    before = getattr(recording[2], "play_count", 0) if recording else 0
    result = CliRunner().invoke(main, arguments, **kwargs)
    verification = verification_for(arguments, before)
    active = _ACTIVE.get()
    if active is not None:
        active[0].record_execution(active[1], verification)
    if regions:
        assert result.exit_code == expected_exit_code, result.output
        assert example_executable in {"cu", "cu-cli"}
        active = _ACTIVE.get()
        if active is not None:
            catalog, test = active
            content = render_command(
                document_arguments, executable=example_executable, language=example_language,
                environment=document_environment,
            )
            comments = [f"# {line}" for line in (example_description or "").splitlines()]
            if expected_exit_code:
                comments.append(f"# Expected exit code: {expected_exit_code}")
            content = "\n".join([*comments, content])
            for identifier, line in regions:
                catalog.record_region(identifier, line, test, content, example_language, verification)
    return result


def record_output(content: str, *, language: str = "text") -> None:
    regions = _matching_regions()
    assert isinstance(content, str)
    if language not in {"text", "json", "yaml"}:
        raise AssertionError(f"not an output language: {language}")
    if language == "json":
        json.loads(content)
    elif language == "yaml":
        import yaml

        yaml.safe_load(content)
    active = _ACTIVE.get()
    if active is not None:
        catalog, test = active
        executions = catalog.executions.get(test, [])
        verification = dict(executions[-1]) if executions else {"mode": "local"}
        verification["output_validation"] = language
        for name, line in regions:
            catalog.record_region(name, line, test, content, language, verification)


def record_external(arguments: list[str], *, reason: str) -> None:
    regions = _matching_regions()
    assert reason.strip()
    assert arguments == ["az", "login"] or arguments[:4] == ["python", "-m", "pip", "install"], (
        "Only installation and login prerequisites can use external classification"
    )
    active = _ACTIVE.get()
    if active is not None:
        catalog, test = active
        verification = {"mode": "external", "reason": reason}
        content = shlex.join(arguments)
        for identifier, line in regions:
            catalog.record_region(identifier, line, test, content, "bash", verification, reason=reason)


def invoke_azure(arguments: list[str]):
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
    active = _ACTIVE.get()
    if active is not None:
        catalog, test = active
        verification = verification_for(arguments, 0)
        catalog.record_execution(test, verification)
        content = shlex.join(["az", *arguments])
        for identifier, line in regions:
            catalog.record_region(identifier, line, test, content, "bash", verification)
    return cli.result.result