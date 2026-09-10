# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Offline tests for the native Azure CLI command registration."""

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
import yaml

from azext_content_understanding import _help  # noqa: F401
from azext_content_understanding import _commands
from azext_content_understanding.commands import (
    azure_command_specs,
    command_adapter_name,
    load_command_table,
)


class FakeGroup:
    def __init__(self, path: str, registered: dict[str, dict[str, Any]]) -> None:
        self.path = path
        self.registered = registered

    def custom_command(self, name: str, operation: str, **kwargs: Any) -> None:
        self.registered[f"{self.path} {name}"] = {"operation": operation, **kwargs}


class FakeLoader:
    def __init__(self) -> None:
        self.command_table: dict[str, dict[str, Any]] = {}

    @contextmanager
    def command_group(self, path: str, **kwargs: Any) -> Iterator[FakeGroup]:
        assert kwargs["is_preview"] is True
        yield FakeGroup(path, self.command_table)


@pytest.mark.unit
def test_preview_commands_are_generated_from_shared_specs() -> None:
    loader = FakeLoader()

    command_table = load_command_table(loader, [])

    assert set(command_table) == {
        "cu " + " ".join(spec.path) for spec in azure_command_specs()
    }
    assert len(command_table) == len(azure_command_specs())
    assert command_table["cu analyzer list"]["table_transformer"].endswith(
        "#analyzer_list_table"
    )
    assert command_table["cu defaults show"]["table_transformer"].endswith("#defaults_table")


@pytest.mark.unit
def test_every_shared_command_derives_a_unique_callable_adapter() -> None:
    names = [command_adapter_name(spec.path) for spec in azure_command_specs()]

    assert len(names) == len(set(names))
    for name in names:
        assert callable(getattr(_commands, name)), name


@pytest.mark.unit
def test_infrastructure_generation_is_registered_but_obsolete_commands_are_not() -> None:
    loader = FakeLoader()

    command_table = load_command_table(loader, [])

    assert "cu infra generate" in command_table
    assert "cu _infra-models" in command_table
    assert "cu provision" not in command_table
    assert "cu _has-values" not in command_table
    assert "cu upgrade" not in command_table


@pytest.mark.unit
def test_all_help_entries_are_valid_yaml() -> None:
    from knack.help_files import helps

    for command_name in ("cu", *("cu " + " ".join(spec.path) for spec in azure_command_specs() if not spec.path[0].startswith("_"))):
        parsed = yaml.safe_load(helps[command_name])
        assert isinstance(parsed, dict), command_name
        assert parsed["type"] in {"group", "command"}, command_name


@pytest.mark.unit
def test_command_help_keys_and_summaries_come_from_shared_specs() -> None:
    from knack.help_files import helps

    for spec in azure_command_specs():
        parsed = yaml.safe_load(helps[_help.command_help_key(spec.path)])
        assert parsed["short-summary"] == spec.help
