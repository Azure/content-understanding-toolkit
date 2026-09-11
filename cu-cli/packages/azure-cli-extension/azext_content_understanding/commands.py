# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Bind shared CU commands to Azure CLI paths and runtime handlers.

Public ``CommandSpec.path`` values register below ``az cu`` without a manual
inventory. Each path maps to a function in ``_commands.py`` by replacing
hyphens with underscores and joining nested segments with ``__``; for example,
``analyzer schema create`` maps to ``_commands.analyzer__schema__create``.
Internal commands are excluded from that generated surface. The azd hook's
required helper is deliberately remapped below the existing ``infra`` group so
it remains invocable without appearing in the top-level ``az cu`` command list.
"""

from cu_cli_core.command_spec import COMMAND_SPECS, SurfaceClassification

_TABLE_TRANSFORMERS = {
    ("analyzer", "list"): "azext_content_understanding._format#analyzer_list_table",
    ("defaults", "show"): "azext_content_understanding._format#defaults_table",
    ("defaults", "set"): "azext_content_understanding._format#defaults_table",
    ("profile", "list"): "azext_content_understanding._format#profile_list_table",
    ("env-var", "list"): "azext_content_understanding._format#environment_table",
}

_INTERNAL_COMMAND_PATHS = {
    ("_infra-models",): ("infra", "_models"),
    ("_infra-postprovision-v1",): ("infra", "_postprovision-v1"),
}


def azure_command_specs():
    """Return shared commands applicable to the Azure CLI frontend."""

    return tuple(
        spec
        for spec in COMMAND_SPECS
        if spec.classification
        not in {SurfaceClassification.STANDALONE_ONLY, SurfaceClassification.INTERNAL}
    )


def azure_command_bindings():
    """Return ``(spec, Azure path)`` pairs, including explicitly placed internals."""

    public = tuple((spec, spec.path) for spec in azure_command_specs())
    internal = tuple(
        (spec, _INTERNAL_COMMAND_PATHS[spec.path])
        for spec in COMMAND_SPECS
        if spec.path in _INTERNAL_COMMAND_PATHS
    )
    return public + internal


def command_adapter_name(path: tuple[str, ...]) -> str:
    """Derive ``_commands.py`` entry points using ``__`` between normalized segments."""

    return "__".join(segment.replace("-", "_") for segment in path)


def load_command_table(loader, _):
    for spec, azure_path in azure_command_bindings():
        group_path = "cu" + (
            " " + " ".join(azure_path[:-1]) if len(azure_path) > 1 else ""
        )
        kwargs = {}
        if spec.path in _TABLE_TRANSFORMERS:
            kwargs["table_transformer"] = _TABLE_TRANSFORMERS[spec.path]
        with loader.command_group(group_path, is_preview=True) as group:
            group.custom_command(azure_path[-1], command_adapter_name(spec.path), **kwargs)
    return loader.command_table
