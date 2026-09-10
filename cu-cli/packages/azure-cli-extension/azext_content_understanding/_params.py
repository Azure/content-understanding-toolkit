# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Generate Azure CLI arguments from the shared CU command surface."""

import logging
from typing import Any

from azure.cli.core.commands.parameters import get_enum_type

from cu_cli_core.command_spec import ArgumentValueType, SurfaceClassification
from cu_cli_core.service_options import get_service_option

from .commands import azure_command_specs


logger = logging.getLogger(__name__)

_EXCLUDED_CLASSIFICATIONS = {
    SurfaceClassification.STANDALONE_SHORTCUT,
    SurfaceClassification.STANDALONE_ONLY,
    SurfaceClassification.FRONTEND_PRESENTATION,
}


class _ExplicitArgumentContext:
    """Register arguments absent from variadic command wrapper signatures."""

    def __init__(self, context) -> None:
        self._context = context

    def argument(self, argument_dest: str, **kwargs: Any) -> None:
        self._context.extra(argument_dest, **kwargs)


def _argument_kwargs(argument: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "options_list": [argument.name, *argument.aliases],
        "help": argument.help,
    }
    if argument.required:
        kwargs["required"] = True
    if argument.default is not None:
        kwargs["default"] = argument.default
    if argument.choices:
        kwargs["arg_type"] = get_enum_type(argument.choices)
    elif argument.value_type is ArgumentValueType.INTEGER:
        kwargs["type"] = int
    if argument.value_type is ArgumentValueType.BOOLEAN:
        kwargs["action"] = "store_true"
    elif getattr(argument, "repeatable", False):
        kwargs["action"] = "append"
    if getattr(argument, "metavar", None) is not None:
        kwargs["metavar"] = argument.metavar
    return kwargs


def _register(context: _ExplicitArgumentContext, argument: Any) -> None:
    context.argument(argument.parser_name, **_argument_kwargs(argument))


def load_arguments(loader, command) -> None:
    """Register Azure-applicable arguments directly from shared metadata."""

    logger.debug("Loading Content Understanding arguments for requested command %r", command)
    for spec in azure_command_specs():
        command_name = "cu " + " ".join(spec.path)
        with loader.argument_context(command_name) as raw_context:
            context = _ExplicitArgumentContext(raw_context)
            registered: set[str] = set()
            for key in spec.service_options:
                option = get_service_option(key)
                if option.classification in _EXCLUDED_CLASSIFICATIONS:
                    continue
                _register(context, option)
                registered.add(option.parser_name)
            for argument in spec.arguments:
                if argument.positional or argument.classification in _EXCLUDED_CLASSIFICATIONS:
                    continue
                if argument.parser_name in registered:
                    continue
                _register(context, argument)
                registered.add(argument.parser_name)
