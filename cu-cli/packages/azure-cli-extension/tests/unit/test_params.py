# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for Azure CLI parameter generation from shared metadata."""

from contextlib import contextmanager
from time import perf_counter
from typing import Any, Iterator

import pytest

from azext_content_understanding._params import load_arguments
from azext_content_understanding.commands import azure_command_specs, load_command_table


class FakeContext:
    def __init__(self, arguments: dict[str, dict[str, Any]]) -> None:
        self.arguments = arguments

    def argument(self, name: str, **kwargs: Any) -> None:
        raise AssertionError(f"{name} must be registered with extra(), not argument()")

    def extra(self, name: str, **kwargs: Any) -> None:
        self.arguments[name] = kwargs


class FakeGroup:
    def __init__(self, loader: "FakeLoader", path: str) -> None:
        self.loader = loader
        self.path = path

    def custom_command(self, name: str, operation: str, **kwargs: Any) -> None:
        self.loader.command_table[f"{self.path} {name}"] = {"operation": operation, **kwargs}


class FakeLoader:
    def __init__(self) -> None:
        self.arguments: dict[str, dict[str, dict[str, Any]]] = {}
        self.seen_commands: list[str] = []
        self.command_table: dict[str, dict[str, Any]] = {}

    @contextmanager
    def argument_context(self, command: str) -> Iterator[FakeContext]:
        self.seen_commands.append(command)
        yield FakeContext(self.arguments.setdefault(command, {}))

    @contextmanager
    def command_group(self, path: str, **kwargs: Any) -> Iterator[FakeGroup]:
        yield FakeGroup(self, path)


@pytest.mark.unit
@pytest.mark.parametrize("spec", azure_command_specs())
def test_every_shared_command_loads_named_parameters(spec) -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    for argument in loader.arguments["cu " + " ".join(spec.path)].values():
        assert all(option.startswith("-") for option in argument.get("options_list", []))


@pytest.mark.unit
def test_analyze_uses_named_non_conflicting_options() -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    analyze = loader.arguments["cu analyze"]
    assert analyze["files"]["options_list"] == ["--file"]
    assert analyze["sources"]["options_list"] == ["--source"]
    assert analyze["urls"]["options_list"] == ["--url"]
    assert analyze["analyzer_id"]["options_list"] == ["--analyzer", "-a"]


@pytest.mark.unit
def test_generic_adapter_converts_portable_argument_types() -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    analyze = loader.arguments["cu analyze"]
    assert analyze["files"]["action"] == "append"
    assert analyze["dry_run"]["action"] == "store_true"
    assert analyze["concurrency"]["type"] is int
    assert analyze["on_existing"]["arg_type"] is not None


@pytest.mark.unit
def test_loader_initialization_registers_the_complete_approved_surface() -> None:
    loader = FakeLoader()

    load_arguments(loader, None)

    assert set(loader.seen_commands) == {
        "cu " + " ".join(spec.path) for spec in azure_command_specs()
    }


@pytest.mark.unit
def test_complete_shared_registry_conversion_finishes_within_budget() -> None:
    loader = FakeLoader()

    started = perf_counter()
    load_command_table(loader, None)
    load_arguments(loader, None)
    elapsed = perf_counter() - started

    assert elapsed <= 0.300
