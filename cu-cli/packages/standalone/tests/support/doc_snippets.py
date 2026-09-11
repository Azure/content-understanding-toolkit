# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import shlex


_FENCE_RE = re.compile(
    r"^```(?P<language>\S+)\s+Snippet:(?P<identifier>[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)\s*$"
)


@dataclass(frozen=True)
class DocSnippet:
    identifier: str
    language: str
    body: str
    path: Path
    line: int


class ExecutionMode(str, Enum):
    OFFLINE = "offline"
    FAKE = "fake"
    PLAYBACK = "playback"
    EXTERNAL = "external"


SNIPPET_EXECUTION_MODES = {
    "cu_cli_analyze_batch_with_report": ExecutionMode.FAKE,
    "cu_cli_analyze_concurrency_and_timing": ExecutionMode.FAKE,
    "cu_cli_analyze_directory": ExecutionMode.FAKE,
    "cu_cli_analyze_directory_pattern": ExecutionMode.FAKE,
    "cu_cli_analyze_directory_recursive": ExecutionMode.FAKE,
    "cu_cli_analyze_inline_preview": ExecutionMode.FAKE,
    "cu_cli_analyze_layout": ExecutionMode.PLAYBACK,
    "cu_cli_analyze_local_file": ExecutionMode.PLAYBACK,
    "cu_cli_analyze_multiple_urls_dry_run": ExecutionMode.OFFLINE,
    "cu_cli_analyze_output_formats": ExecutionMode.FAKE,
    "cu_cli_analyze_prebuilt_invoice": ExecutionMode.PLAYBACK,
    "cu_cli_analyze_public_url": ExecutionMode.FAKE,
    "cu_cli_analyze_remote_url": ExecutionMode.FAKE,
    "cu_cli_analyze_sas_url": ExecutionMode.FAKE,
    "cu_cli_analyze_with_default_analyzer": ExecutionMode.PLAYBACK,
    "cu_cli_azure_login": ExecutionMode.EXTERNAL,
    "cu_cli_command_help": ExecutionMode.OFFLINE,
    "cu_cli_configure_and_apply_defaults": ExecutionMode.FAKE,
    "cu_cli_configure_key_profile": ExecutionMode.PLAYBACK,
    "cu_cli_configure_login_profile": ExecutionMode.FAKE,
    "cu_cli_copy_analyzer_with_profiles": ExecutionMode.FAKE,
    "cu_cli_copy_analyzer_with_resources": ExecutionMode.FAKE,
    "cu_cli_create_and_test_analyzer": ExecutionMode.FAKE,
    "cu_cli_create_and_test_custom_analyzer": ExecutionMode.FAKE,
    "cu_cli_create_local_schemas": ExecutionMode.OFFLINE,
    "cu_cli_create_schema_from_sample": ExecutionMode.FAKE,
    "cu_cli_help_and_exit_behavior": ExecutionMode.OFFLINE,
    "cu_cli_install": ExecutionMode.EXTERNAL,
    "cu_cli_list_analyzers": ExecutionMode.PLAYBACK,
    "cu_cli_list_environment_overrides": ExecutionMode.OFFLINE,
    "cu_cli_mac_os_help": ExecutionMode.OFFLINE,
    "cu_cli_manage_analyzers": ExecutionMode.FAKE,
    "cu_cli_manage_defaults": ExecutionMode.FAKE,
    "cu_cli_preview_batch": ExecutionMode.OFFLINE,
    "cu_cli_profile_commands": ExecutionMode.OFFLINE,
    "cu_cli_profile_resolution_precedence": ExecutionMode.FAKE,
    "cu_cli_run_diagnostics": ExecutionMode.FAKE,
    "cu_cli_set_key_authentication": ExecutionMode.OFFLINE,
    "cu_cli_show_defaults": ExecutionMode.PLAYBACK,
    "cu_cli_sync_profile_defaults": ExecutionMode.FAKE,
    "cu_cli_temporarily_override_endpoint": ExecutionMode.FAKE,
    "cu_cli_unset_key_authentication": ExecutionMode.OFFLINE,
    "cu_cli_use_multiple_profiles": ExecutionMode.FAKE,
    "cu_cli_validate_schema": ExecutionMode.OFFLINE,
}


def load_doc_snippets(*paths: Path) -> dict[str, DocSnippet]:
    snippets: dict[str, DocSnippet] = {}

    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        line_index = 0
        while line_index < len(lines):
            match = _FENCE_RE.fullmatch(lines[line_index])
            if match is None:
                line_index += 1
                continue

            closing_index = line_index + 1
            while closing_index < len(lines) and lines[closing_index] != "```":
                closing_index += 1
            if closing_index == len(lines):
                raise ValueError(f"{path}:{line_index + 1}: unclosed Snippet fence")

            identifier = match.group("identifier")
            snippet = DocSnippet(
                identifier=identifier,
                language=match.group("language"),
                body="\n".join(lines[line_index + 1 : closing_index]),
                path=path,
                line=line_index + 1,
            )
            if previous := snippets.get(identifier):
                raise ValueError(
                    f"Snippet:{identifier} is duplicated at "
                    f"{previous.path}:{previous.line}, {path}:{snippet.line}"
                )
            snippets[identifier] = snippet
            line_index = closing_index + 1

    return snippets


def parse_shell_commands(snippet: DocSnippet) -> list[list[str]]:
    logical_lines: list[str] = []
    pending = ""
    for raw_line in snippet.body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        pending = f"{pending} {line}".strip()
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        logical_lines.append(pending)
        pending = ""
    if pending:
        raise ValueError(
            f"{snippet.path}:{snippet.line}: Snippet:{snippet.identifier} "
            "ends with an unfinished line continuation"
        )

    commands = []
    for command in logical_lines:
        argv = shlex.split(command, posix=True)
        if any(token in {"|", ">", ">>", "<", "&&", ";"} for token in argv):
            raise ValueError(
                f"{snippet.path}:{snippet.line}: Snippet:{snippet.identifier} "
                f"requires a shell adapter: {command}"
            )
        commands.append(argv)
    return commands


def parse_cu_commands(snippet: DocSnippet) -> list[list[str]]:
    commands = []
    for argv in parse_shell_commands(snippet):
        if not argv or argv[0] not in {"cu", "cu-cli"}:
            raise ValueError(
                f"{snippet.path}:{snippet.line}: Snippet:{snippet.identifier} "
                f"contains a non-CU command: {' '.join(argv)}"
            )
        commands.append(argv[1:])
    return commands