# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI command loader for the Content Understanding extension."""

from importlib.metadata import version

from azure.cli.core import AzCommandsLoader

from ._help import helps as helps

__version__ = version("content-understanding")


class ContentUnderstandingCommandsLoader(AzCommandsLoader):
    """Load the native ``az cu`` command surface."""

    def __init__(self, cli_ctx=None):
        from azure.cli.core.commands import CliCommandType

        custom_type = CliCommandType(
            operations_tmpl="azext_content_understanding._commands#{}",
        )
        super().__init__(cli_ctx=cli_ctx, custom_command_type=custom_type)

    def load_command_table(self, args):
        from .commands import load_command_table

        load_command_table(self, args)
        return self.command_table

    def load_arguments(self, command):
        from ._params import load_arguments

        load_arguments(self, command)


COMMAND_LOADER_CLS = ContentUnderstandingCommandsLoader
