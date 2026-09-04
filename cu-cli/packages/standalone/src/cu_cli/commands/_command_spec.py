"""Translate framework-neutral command arguments into Click decorators."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import rich_click as click

from cu_cli_core.command_spec import ArgumentSpec, ArgumentValueType, CommandSpec


_SIMPLE_CLICK_TYPES: dict[ArgumentValueType, Any] = {
    ArgumentValueType.STRING: str,
    ArgumentValueType.BOOLEAN: bool,
}


def _click_type(argument: ArgumentSpec) -> Any:
    if argument.value_type is ArgumentValueType.INTEGER:
        return click.IntRange(argument.minimum, argument.maximum)
    if argument.value_type is ArgumentValueType.PATH:
        return click.Path(
            exists=argument.path_exists,
            file_okay=argument.file_okay,
            dir_okay=argument.dir_okay,
            path_type=Path,
        )
    return _SIMPLE_CLICK_TYPES[argument.value_type]


def _click_argument(argument: ArgumentSpec) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    metavar = argument.name if argument.required else f"[{argument.name}]"
    return click.argument(
        argument.parser_name,
        required=argument.required,
        type=_click_type(argument),
        metavar=argument.metavar or metavar,
        nargs=-1 if argument.repeatable else 1,
    )


def _click_option(
    argument: ArgumentSpec,
    *,
    has_alternate_binding: bool,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    declarations = (*argument.aliases, argument.name, argument.parser_name)
    kwargs: dict[str, Any] = {
        "required": argument.required and not has_alternate_binding,
        "help": argument.help,
    }
    if argument.default is not None:
        kwargs["default"] = argument.default
    if argument.value_type is ArgumentValueType.BOOLEAN:
        kwargs["is_flag"] = True
    else:
        kwargs["type"] = (
            click.Choice(argument.choices)
            if argument.choices
            else _click_type(argument)
        )
        kwargs["multiple"] = argument.repeatable
    if argument.metavar is not None:
        kwargs["metavar"] = argument.metavar
    return click.option(*declarations, **kwargs)


def with_command_arguments(spec: CommandSpec):
    """Attach the command-specific arguments declared by ``spec``."""

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        fields_with_alternates = {
            argument.field
            for argument in spec.arguments
            if sum(item.field == argument.field for item in spec.arguments) > 1
        }
        for argument in reversed(spec.arguments):
            option = (
                _click_argument(argument)
                if argument.positional
                else _click_option(
                    argument,
                    has_alternate_binding=argument.field in fields_with_alternates,
                )
            )
            fn = option(fn)
        return fn

    return decorate
