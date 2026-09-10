# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Generate Azure CLI command registration from the shared CU command surface."""

from cu_cli_core.command_spec import COMMAND_SPECS, SurfaceClassification

_TABLE_TRANSFORMERS = {
    ("analyzer", "list"): "azext_content_understanding._format#analyzer_list_table",
    ("defaults", "show"): "azext_content_understanding._format#defaults_table",
    ("defaults", "set"): "azext_content_understanding._format#defaults_table",
    ("profile", "list"): "azext_content_understanding._format#profile_list_table",
    ("env-var", "list"): "azext_content_understanding._format#environment_table",
}


def azure_command_specs():
    """Return shared commands applicable to the Azure CLI frontend."""

    return tuple(
        spec
        for spec in COMMAND_SPECS
        if spec.classification is not SurfaceClassification.STANDALONE_ONLY
    )


def command_adapter_name(path: tuple[str, ...]) -> str:
    """Derive ``_commands.py`` entry points using ``__`` between normalized segments."""

    return "__".join(segment.replace("-", "_") for segment in path)


def load_command_table(loader, _):
    for spec in azure_command_specs():
        group_path = "cu" + (" " + " ".join(spec.path[:-1]) if len(spec.path) > 1 else "")
        kwargs = {}
        if spec.path in _TABLE_TRANSFORMERS:
            kwargs["table_transformer"] = _TABLE_TRANSFORMERS[spec.path]
        with loader.command_group(group_path, is_preview=True) as group:
            group.custom_command(spec.path[-1], command_adapter_name(spec.path), **kwargs)
    return loader.command_table
