# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tests for the thin Azure CLI dispatch boundary."""

import inspect
from pathlib import Path
import re
from types import SimpleNamespace

import pytest
from azure.cli.core.azclierror import InvalidArgumentValueError

from azext_content_understanding import _commands
from cu_cli_core.errors import ValidationError


@pytest.mark.unit
def test_dispatch_returns_plain_values(monkeypatch: pytest.MonkeyPatch) -> None:
    value = SimpleNamespace(as_dict=lambda: {"analyzerId": "prebuilt-layout"})
    monkeypatch.setattr(_commands._analyzers, "show_analyzer", lambda cmd, **values: value)

    result = _commands.show_analyzer(SimpleNamespace(), analyzer_name="prebuilt-layout")

    assert result == {"analyzerId": "prebuilt-layout"}


@pytest.mark.unit
def test_dispatch_translates_core_errors_with_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(cmd, **values):
        raise ValidationError("invalid value", hint="choose another value")

    monkeypatch.setattr(_commands._profiles, "set_profile", fail)

    with pytest.raises(InvalidArgumentValueError, match="choose another value"):
        _commands.set_profile(SimpleNamespace(), profile_key="endpoint", profile_value="bad")


@pytest.mark.unit
def test_entry_points_use_azure_cli_kwargs_convention() -> None:
    entry_points = {
        name: value
        for name, value in vars(_commands).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == _commands.__name__
    }
    for name, entry_point in entry_points.items():
        parameters = inspect.signature(entry_point).parameters
        variadic = next(
            parameter
            for parameter in parameters.values()
            if parameter.kind is inspect.Parameter.VAR_KEYWORD
        )
        assert variadic.name == "kwargs", name


@pytest.mark.unit
def test_active_extension_does_not_import_standalone_frontend() -> None:
    package = Path(_commands.__file__).parent
    source = "\n".join(path.read_text(encoding="utf-8") for path in package.glob("*.py"))

    assert re.search(r"\bfrom cu_cli(?:\.|\s+import)", source) is None
    assert re.search(r"\bimport cu_cli(?:\s|$)", source) is None