# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Generate Azure CLI command registration from the shared CU command surface."""

from cu_cli_core.command_spec import COMMAND_SPECS, SurfaceClassification


_OPERATIONS = {
    ("analyze",): "analyze",
    ("analyzer", "list"): "list_analyzers",
    ("analyzer", "show"): "show_analyzer",
    ("analyzer", "create"): "create_analyzer",
    ("analyzer", "delete"): "delete_analyzer",
    ("analyzer", "validate"): "validate_analyzer",
    ("analyzer", "schema", "create"): "create_analyzer_schema",
    ("analyzer", "test"): "test_analyzer",
    ("analyzer", "copy"): "copy_analyzer",
    ("defaults", "show"): "show_defaults",
    ("defaults", "set"): "set_defaults",
    ("profile", "show"): "show_profile",
    ("profile", "list"): "list_profiles",
    ("profile", "get"): "get_profile",
    ("profile", "set"): "set_profile",
    ("profile", "unset"): "unset_profile",
    ("profile", "create"): "create_profile",
    ("profile", "delete"): "delete_profile",
    ("profile", "copy"): "copy_profile",
    ("profile", "rename"): "rename_profile",
    ("profile", "set-active"): "set_active_profile",
    ("profile", "sync-defaults"): "sync_profile_defaults",
    ("doctor",): "doctor",
    ("env-var", "list"): "list_environment_variables",
    ("infra", "generate"): "generate_infrastructure",
    ("_infra-models",): "setup_infrastructure_models",
}

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


def load_command_table(loader, _):
    for spec in azure_command_specs():
        group_path = "cu" + (" " + " ".join(spec.path[:-1]) if len(spec.path) > 1 else "")
        kwargs = {}
        if spec.path in _TABLE_TRANSFORMERS:
            kwargs["table_transformer"] = _TABLE_TRANSFORMERS[spec.path]
        with loader.command_group(group_path, is_preview=True) as group:
            group.custom_command(spec.path[-1], _OPERATIONS[spec.path], **kwargs)
    return loader.command_table
