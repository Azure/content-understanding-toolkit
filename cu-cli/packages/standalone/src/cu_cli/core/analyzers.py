# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Compatibility imports for analyzer operations now provided by cu-cli-core."""

from cu_cli_core.operations.analyzer_copy import (
    collect_custom_dependencies,
    copy_analyzer,
    get_copy_source_analyzer,
    preflight_dependencies_on_target,
)
from cu_cli_core.operations.analyzers import (
    analyzer_kind,
    create_analyzer,
    delete_analyzer,
    get_analyzer,
    list_analyzers,
)

__all__ = [
    "analyzer_kind",
    "collect_custom_dependencies",
    "copy_analyzer",
    "create_analyzer",
    "delete_analyzer",
    "get_analyzer",
    "get_copy_source_analyzer",
    "list_analyzers",
    "preflight_dependencies_on_target",
]
