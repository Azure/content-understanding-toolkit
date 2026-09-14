# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI command loader for the Content Understanding extension."""

from importlib.metadata import version
from pathlib import Path

import azure.ai
from azure.cli.core import AzCommandsLoader

from ._help import helps as helps  # pylint: disable=unused-import,useless-import-alias

__version__ = version("content-understanding")

# Azure CLI adds an extension's ``azure`` directory to the namespace package,
# but currently does not do the same for an already imported ``azure.ai``.
# azdev loads that namespace before loading extensions, so expose SDKs bundled
# with this extension explicitly.
_azure_ai_path = str(Path(__file__).resolve().parent.parent / "azure" / "ai")
if Path(_azure_ai_path).is_dir() and _azure_ai_path not in azure.ai.__path__:
    azure.ai.__path__.append(_azure_ai_path)


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
