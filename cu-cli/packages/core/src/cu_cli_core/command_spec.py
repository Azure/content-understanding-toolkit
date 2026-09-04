"""Framework-neutral metadata for the shared CU command surface."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import importlib
from typing import Any, Mapping


class SurfaceClassification(str, Enum):
    """Identify which frontend owns a command-surface element."""

    COMMON = "common"
    SHARED_ALIAS = "shared-alias"
    STANDALONE_SHORTCUT = "standalone-shortcut"
    AZURE_HOST_GLOBAL = "azure-host-global"
    FRONTEND_PRESENTATION = "frontend-presentation"


class ArgumentValueType(str, Enum):
    """Portable value types understood by frontend adapters."""

    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    PATH = "path"


@dataclass(frozen=True)
class ArgumentSpec:
    """Describe one canonical argument or frontend-specific overlay."""

    name: str
    field: str
    parser_name: str
    help: str
    value_type: ArgumentValueType = ArgumentValueType.STRING
    aliases: tuple[str, ...] = ()
    required: bool = False
    default: Any = None
    choices: tuple[str, ...] = ()
    repeatable: bool = False
    minimum: int | None = None
    maximum: int | None = None
    path_exists: bool = False
    file_okay: bool = True
    dir_okay: bool = True
    metavar: str | None = None
    classification: SurfaceClassification = SurfaceClassification.COMMON

    @property
    def positional(self) -> bool:
        return not self.name.startswith("-")


@dataclass(frozen=True)
class CommandSpec:
    """Describe one command without importing either CLI framework or operation."""

    path: tuple[str, ...]
    help: str
    operation: str
    request_type: str
    arguments: tuple[ArgumentSpec, ...] = ()
    service_options: tuple[str, ...] = ()
    classification: SurfaceClassification = SurfaceClassification.COMMON
    preview: bool = False
    deprecated: bool = False


class CommandBindingError(ValueError):
    """Raised when parsed frontend values cannot form a canonical request."""


@lru_cache(maxsize=None)
def resolve_identifier(identifier: str) -> Any:
    """Resolve a lazy ``module#attribute`` identifier on first use."""

    module_name, separator, attribute_name = identifier.partition("#")
    if not separator or not module_name or not attribute_name:
        raise ValueError(f"invalid lazy identifier: {identifier!r}")
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)


def bind_command_arguments(
    spec: CommandSpec,
    parsed: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind canonical and overlay parser values to shared request fields."""

    bound: dict[str, Any] = {}
    sources: dict[str, str] = {}
    required: dict[str, str] = {}

    for argument in spec.arguments:
        if argument.classification in {
            SurfaceClassification.AZURE_HOST_GLOBAL,
            SurfaceClassification.FRONTEND_PRESENTATION,
        }:
            continue
        if argument.required:
            required[argument.field] = argument.name
        value = parsed.get(argument.parser_name, argument.default)
        if value is None or (argument.repeatable and not value):
            continue
        if argument.field in bound:
            raise CommandBindingError(
                f"provide {argument.field.replace('_', ' ')} only once; "
                f"{sources[argument.field]} cannot be combined with {argument.name}."
            )
        bound[argument.field] = value
        sources[argument.field] = argument.name

    for field, argument_name in required.items():
        if field not in bound:
            raise CommandBindingError(f"missing required argument: {argument_name}.")

    return bound


def build_request(spec: CommandSpec, parsed: Mapping[str, Any]) -> Any:
    """Bind frontend values and instantiate the spec's lazy request type."""

    request_type = resolve_identifier(spec.request_type)
    try:
        return request_type(**bind_command_arguments(spec, parsed))
    except (TypeError, ValueError) as exc:
        if isinstance(exc, CommandBindingError):
            raise
        raise CommandBindingError(str(exc)) from exc


_SERVICE_OPTIONS = ("endpoint", "api-version", "auth-mode", "api-key")


def _profile_name_arguments(option_help: str) -> tuple[ArgumentSpec, ...]:
    return (
        ArgumentSpec(
            "--name",
            aliases=("-n",),
            field="name",
            parser_name="profile_name",
            help=option_help,
            required=True,
        ),
        ArgumentSpec(
            "PROFILE_NAME",
            field="name",
            parser_name="positional_profile_name",
            help="Standalone positional shortcut for --name.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
    )


_ANALYZER_NAME_ARGUMENTS = (
    ArgumentSpec(
        "--name",
        aliases=("-n", "-a"),
        field="name",
        parser_name="analyzer_name",
        help="Analyzer name.",
        required=True,
    ),
    ArgumentSpec(
        "ANALYZER_NAME",
        field="name",
        parser_name="positional_analyzer_name",
        help="Standalone positional shortcut for --name.",
        classification=SurfaceClassification.STANDALONE_SHORTCUT,
    ),
)

_INPUT_ARGUMENTS = (
    ArgumentSpec(
        "INPUTS",
        field="positional_inputs",
        parser_name="inputs",
        help="Standalone positional file and directory shortcuts.",
        value_type=ArgumentValueType.PATH,
        repeatable=True,
        classification=SurfaceClassification.STANDALONE_SHORTCUT,
    ),
    ArgumentSpec(
        "--file",
        field="files",
        parser_name="files",
        help="Literal local file. Repeat for multiple files.",
        value_type=ArgumentValueType.PATH,
        repeatable=True,
        file_okay=True,
        dir_okay=False,
    ),
    ArgumentSpec(
        "--source",
        field="sources",
        parser_name="sources",
        help="Local source directory. Repeat for multiple directories.",
        value_type=ArgumentValueType.PATH,
        repeatable=True,
        file_okay=False,
        dir_okay=True,
    ),
    ArgumentSpec(
        "--pattern",
        field="pattern",
        parser_name="pattern",
        help="Python fnmatch pattern applied to every --source.",
    ),
    ArgumentSpec(
        "--recursive",
        aliases=("-r",),
        field="recursive",
        parser_name="recursive",
        help="Recurse into selected directories.",
        value_type=ArgumentValueType.BOOLEAN,
    ),
)


ANALYZE = CommandSpec(
    path=("analyze",),
    help="Process local files with an analyzer and return analyzer results.",
    operation="cu_cli_core.operations.analysis#execute_analyze",
    request_type="cu_cli_core.contracts#AnalyzeRequest",
    arguments=(
        *_INPUT_ARGUMENTS,
        ArgumentSpec(
            "--analyzer",
            aliases=("-a",),
            field="analyzer",
            parser_name="analyzer_id",
            help="Analyzer name; defaults to the configured default analyzer.",
        ),
        ArgumentSpec(
            "--inline",
            aliases=("-i",),
            field="inline",
            parser_name="inline",
            help="Use preview synchronous analysis.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--usage",
            field="usage",
            parser_name="show_usage",
            help="Include service usage details.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--llm-input",
            field="llm_input",
            parser_name="llm_input",
            help="Return the analyzer result formatted as generative AI model input.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--json",
            field="json",
            parser_name="json_output",
            help="Emit the complete analyzer result as JSON.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
        ArgumentSpec(
            "--output-file",
            field="output_file",
            parser_name="output_file",
            help="Write the primary payload for one selected file.",
            value_type=ArgumentValueType.PATH,
            file_okay=True,
            dir_okay=False,
        ),
        ArgumentSpec(
            "--output-dir",
            aliases=("-d",),
            field="output_dir",
            parser_name="out_dir",
            help="Write results under this directory, preserving source-relative paths.",
            value_type=ArgumentValueType.PATH,
            file_okay=False,
            dir_okay=True,
        ),
        ArgumentSpec(
            "--on-existing",
            field="on_existing",
            parser_name="on_existing",
            help="How to handle existing result files.",
            choices=("error", "skip", "reanalyze"),
        ),
        ArgumentSpec(
            "--dry-run",
            field="dry_run",
            parser_name="dry_run",
            help="Display the local execution plan without service calls or writes.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--yes",
            aliases=("-y",),
            field="yes",
            parser_name="assume_yes",
            help="Skip discovery confirmation.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--report-file",
            field="report_file",
            parser_name="report_path",
            help="Write a standalone JSON status report.",
            value_type=ArgumentValueType.PATH,
            file_okay=True,
            dir_okay=False,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
        ArgumentSpec(
            "--concurrency",
            aliases=("-j",),
            field="concurrency",
            parser_name="concurrency",
            help="Concurrent analysis jobs.",
            value_type=ArgumentValueType.INTEGER,
            default=4,
            minimum=1,
            maximum=32,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
    preview=True,
)


ANALYZER_SHOW = CommandSpec(
    path=("analyzer", "show"),
    help="Show a single analyzer definition (JSON).",
    operation="cu_cli_core.operations.analyzers#get_analyzer",
    request_type="cu_cli_core.contracts#AnalyzerShowRequest",
    arguments=(
        ArgumentSpec(
            "--name",
            aliases=("-n", "-a"),
            field="name",
            parser_name="analyzer_name",
            help="Analyzer name.",
            required=True,
        ),
        ArgumentSpec(
            "ANALYZER_NAME",
            field="name",
            parser_name="positional_analyzer_name",
            help="Standalone positional shortcut for --name.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

ANALYZER_LIST = CommandSpec(
    path=("analyzer", "list"),
    help="List analyzers in the Microsoft Foundry resource.",
    operation="cu_cli_core.operations.analyzers#list_analyzers",
    request_type="cu_cli_core.contracts#AnalyzerListRequest",
    arguments=(
        ArgumentSpec(
            "--kind",
            field="kind",
            parser_name="kind",
            help="Filter analyzers by kind.",
            default="all",
            choices=("all", "prebuilt", "custom"),
        ),
        ArgumentSpec(
            "--sort-by",
            field="sort_by",
            parser_name="sort_by",
            help="Sort analyzers by name, creation time, or modification time.",
            default="analyzerId",
            choices=("analyzerId", "createdAt", "lastModifiedAt"),
        ),
        ArgumentSpec(
            "--json",
            field="json",
            parser_name="json_output",
            help="Write the complete result as JSON.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

ANALYZER_CREATE = CommandSpec(
    path=("analyzer", "create"),
    help="Create an analyzer from a JSON schema file.",
    operation="cu_cli_core.operations.analyzers#create_analyzer",
    request_type="cu_cli_core.contracts#AnalyzerCreateRequest",
    arguments=(
        ArgumentSpec(
            "--name",
            aliases=("-n", "-a"),
            field="name",
            parser_name="analyzer_name",
            help="Custom analyzer ID: 1-64 ASCII letters, numbers, or underscores.",
            required=True,
        ),
        ArgumentSpec(
            "ANALYZER_NAME",
            field="name",
            parser_name="positional_analyzer_name",
            help="Standalone positional shortcut for --name.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--schema",
            aliases=("-s",),
            field="schema",
            parser_name="schema_path",
            help="Path to a JSON analyzer schema.",
            value_type=ArgumentValueType.PATH,
            required=True,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

ANALYZER_DELETE = CommandSpec(
    path=("analyzer", "delete"),
    help="Delete an analyzer.",
    operation="cu_cli_core.operations.analyzers#delete_analyzer",
    request_type="cu_cli_core.contracts#AnalyzerDeleteRequest",
    arguments=(
        ArgumentSpec(
            "--name",
            aliases=("-n", "-a"),
            field="name",
            parser_name="analyzer_name",
            help="Analyzer name.",
            required=True,
        ),
        ArgumentSpec(
            "ANALYZER_NAME",
            field="name",
            parser_name="positional_analyzer_name",
            help="Standalone positional shortcut for --name.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--yes",
            aliases=("-y",),
            field="yes",
            parser_name="yes",
            help="Skip confirmation.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

ANALYZER_TEST = CommandSpec(
    path=("analyzer", "test"),
    help="Run an analyzer over local samples.",
    operation="cu_cli_core.operations.analysis#execute_analyzer_test",
    request_type="cu_cli_core.contracts#AnalyzerTestRequest",
    arguments=(
        *_ANALYZER_NAME_ARGUMENTS,
        *_INPUT_ARGUMENTS,
        ArgumentSpec(
            "--dry-run",
            field="dry_run",
            parser_name="dry_run",
            help="Display the local test plan without service calls.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--json",
            field="json",
            parser_name="json_output",
            help="Emit the complete structured test report.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
        ArgumentSpec(
            "--output-file",
            field="output_file",
            parser_name="out_path",
            help="Write the structured test report to a file.",
            value_type=ArgumentValueType.PATH,
            file_okay=True,
            dir_okay=False,
        ),
        ArgumentSpec(
            "--force",
            field="force",
            parser_name="force",
            help="Overwrite an existing test report.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--yes",
            aliases=("-y",),
            field="yes",
            parser_name="assume_yes",
            help="Skip discovery confirmation.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--concurrency",
            aliases=("-j",),
            field="concurrency",
            parser_name="concurrency",
            help="Concurrent analysis jobs.",
            value_type=ArgumentValueType.INTEGER,
            default=4,
            minimum=1,
            maximum=16,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

ANALYZER_COPY = CommandSpec(
    path=("analyzer", "copy"),
    help="Copy an analyzer within or across Microsoft Foundry resources.",
    operation="cu_cli_core.operations.analyzer_copy#copy_analyzer",
    request_type="cu_cli_core.contracts#AnalyzerCopyRequest",
    arguments=(
        ArgumentSpec(
            "--source",
            field="source",
            parser_name="named_source",
            help="Analyzer to copy.",
            required=True,
        ),
        ArgumentSpec(
            "SOURCE",
            field="source",
            parser_name="positional_source",
            help="Standalone positional shortcut for --source.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--destination",
            field="destination",
            parser_name="named_destination",
            help="New analyzer name to create.",
            required=True,
        ),
        ArgumentSpec(
            "DESTINATION",
            field="destination",
            parser_name="positional_destination",
            help="Standalone positional shortcut for --destination.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--source-resource",
            field="source_resource",
            parser_name="source_resource",
            help="Resolve the source resource directly from Azure.",
        ),
        ArgumentSpec(
            "--source-subscription",
            field="source_subscription",
            parser_name="source_subscription",
            help=(
                "Subscription in which to resolve the source resource; "
                "defaults to the active Azure CLI subscription."
            ),
        ),
        ArgumentSpec(
            "--source-resource-group",
            field="source_resource_group",
            parser_name="source_resource_group",
            help="Resource group used for source discovery.",
        ),
        ArgumentSpec(
            "--source-profile",
            field="source_profile",
            parser_name="source_profile",
            help="Standalone named CU CLI profile for the source.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--destination-resource",
            field="destination_resource",
            parser_name="destination_resource",
            help="Resolve the destination resource directly from Azure.",
        ),
        ArgumentSpec(
            "--destination-subscription",
            field="destination_subscription",
            parser_name="destination_subscription",
            help=(
                "Subscription in which to resolve the destination resource; "
                "defaults to the active Azure CLI subscription."
            ),
        ),
        ArgumentSpec(
            "--destination-resource-group",
            field="destination_resource_group",
            parser_name="destination_resource_group",
            help="Resource group used for destination discovery.",
        ),
        ArgumentSpec(
            "--destination-profile",
            field="destination_profile",
            parser_name="destination_profile",
            help="Standalone named CU CLI profile for the destination.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

ANALYZER_VALIDATE = CommandSpec(
    path=("analyzer", "validate"),
    help="Validate a local analyzer schema.",
    operation="cu_cli_core.operations.validation#validate_schema",
    request_type="cu_cli_core.contracts#AnalyzerValidateRequest",
    arguments=(
        ArgumentSpec(
            "--schema",
            aliases=("-s",),
            field="schema",
            parser_name="named_schema_path",
            help="Path to a JSON analyzer schema.",
            value_type=ArgumentValueType.PATH,
            required=True,
            path_exists=True,
            file_okay=True,
            dir_okay=False,
        ),
        ArgumentSpec(
            "SCHEMA",
            field="schema",
            parser_name="positional_schema_path",
            help="Standalone positional shortcut for --schema.",
            value_type=ArgumentValueType.PATH,
            path_exists=True,
            file_okay=True,
            dir_okay=False,
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--json",
            field="json",
            parser_name="json_output",
            help="Emit structured validation results.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
        ArgumentSpec(
            "--strict",
            field="strict",
            parser_name="strict",
            help="Treat warnings as errors.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--spec",
            field="spec",
            parser_name="use_spec",
            help="Also validate against the bundled service contract.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
    ),
    service_options=("api-version",),
)

ANALYZER_SCHEMA_CREATE = CommandSpec(
    path=("analyzer", "schema", "create"),
    help="Create a starter schema or derive one from a local document sample.",
    operation="cu_cli_core.operations.schema#create_schema",
    request_type="cu_cli_core.contracts#AnalyzerSchemaCreateRequest",
    arguments=(
        ArgumentSpec(
            "--from-template",
            field="from_template",
            parser_name="from_template",
            help="Create an offline starter schema (the default).",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--from-sample",
            field="from_sample",
            parser_name="sample_path",
            help="Create an extraction schema from one local document sample.",
            value_type=ArgumentValueType.PATH,
            path_exists=True,
            file_okay=True,
            dir_okay=False,
        ),
        ArgumentSpec(
            "--name",
            aliases=("-n", "-a"),
            field="name",
            parser_name="analyzer_id",
            help="Custom analyzer name.",
            default="my_analyzer_v1",
        ),
        ArgumentSpec(
            "--base",
            field="base",
            parser_name="base",
            help="Base analyzer name; defaults from --modality.",
        ),
        ArgumentSpec(
            "--modality",
            field="modality",
            parser_name="modality",
            help="Modality used to choose a base analyzer.",
            default="document",
            choices=("document", "image", "audio", "video"),
        ),
        ArgumentSpec(
            "--output-file",
            field="output_file",
            parser_name="out_path",
            help="Write the schema to a file.",
            value_type=ArgumentValueType.PATH,
            file_okay=True,
            dir_okay=False,
        ),
        ArgumentSpec(
            "--force",
            field="force",
            parser_name="force",
            help="Overwrite an existing schema output file.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--type",
            field="template_type",
            parser_name="template_type",
            help="Schema template style.",
            default="extraction",
            choices=("extraction", "classification"),
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

DEFAULTS_SHOW = CommandSpec(
    path=("defaults", "show"),
    help="Show Content Understanding defaults that map models to deployments.",
    operation="cu_cli_core.defaults#get_defaults",
    request_type="cu_cli_core.contracts#DefaultsShowRequest",
    arguments=(
        ArgumentSpec(
            "--table",
            field="table",
            parser_name="table_output",
            help="Print model mappings as a readable table.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

DEFAULTS_SET = CommandSpec(
    path=("defaults", "set"),
    help="Configure Content Understanding defaults that map models to deployments.",
    operation="cu_cli_core.defaults#apply_defaults",
    request_type="cu_cli_core.contracts#DefaultsSetRequest",
    arguments=(
        ArgumentSpec(
            "--model",
            field="models",
            parser_name="model_kv",
            help="Model deployment mapping in MODEL=DEPLOYMENT form.",
            repeatable=True,
        ),
        ArgumentSpec(
            "--from-profile",
            field="from_profile",
            parser_name="from_profile",
            help="Include mappings from the effective standalone CU CLI profile.",
            value_type=ArgumentValueType.BOOLEAN,
            default=False,
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--replace",
            field="replace",
            parser_name="replace",
            help="Replace defaults instead of merging.",
            value_type=ArgumentValueType.BOOLEAN,
        ),
        ArgumentSpec(
            "--json",
            field="json",
            parser_name="json_output",
            help="Emit the complete updated defaults object.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
    ),
    service_options=_SERVICE_OPTIONS,
)

PROFILE_SHOW = CommandSpec(
    path=("profile", "show"),
    help="Show the effective CU CLI profile with secrets redacted.",
    operation="cu_cli_core.operations.profiles#show_profile",
    request_type="cu_cli_core.contracts#ProfileShowRequest",
    arguments=(
        ArgumentSpec(
            "--name",
            aliases=("-n",),
            field="name",
            parser_name="profile_name",
            help="CU CLI profile to show; defaults to the active CU CLI profile.",
        ),
        ArgumentSpec(
            "--deployments",
            field="deployments",
            parser_name="deployments",
            help="Also list live Foundry model deployments.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
    ),
)

PROFILE_LIST = CommandSpec(
    path=("profile", "list"),
    help="List saved CU CLI profiles and identify the active CU CLI profile.",
    operation="cu_cli_core.operations.profiles#list_profiles",
    request_type="cu_cli_core.contracts#ProfileListRequest",
)

PROFILE_GET = CommandSpec(
    path=("profile", "get"),
    help="Print one saved CU CLI profile value.",
    operation="cu_cli_core.operations.profiles#get_profile_value",
    request_type="cu_cli_core.contracts#ProfileGetRequest",
    arguments=(
        ArgumentSpec(
            "--key",
            field="key",
            parser_name="profile_key",
            help="CU CLI profile setting key.",
            required=True,
        ),
        ArgumentSpec(
            "KEY",
            field="key",
            parser_name="positional_profile_key",
            help="Standalone positional shortcut for --key.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--name",
            aliases=("-n",),
            field="name",
            parser_name="profile_name",
            help="CU CLI profile to inspect; defaults to the active CU CLI profile.",
        ),
    ),
)

PROFILE_SET = CommandSpec(
    path=("profile", "set"),
    help="Set one saved CU CLI profile value.",
    operation="cu_cli_core.operations.profiles#set_profile_value",
    request_type="cu_cli_core.contracts#ProfileSetRequest",
    arguments=(
        ArgumentSpec(
            "--key",
            field="key",
            parser_name="profile_key",
            help="CU CLI profile setting key.",
            required=True,
        ),
        ArgumentSpec(
            "KEY",
            field="key",
            parser_name="positional_profile_key",
            help="Standalone positional shortcut for --key.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--value",
            field="value",
            parser_name="profile_value",
            help="Value to save.",
            required=True,
        ),
        ArgumentSpec(
            "VALUE",
            field="value",
            parser_name="positional_profile_value",
            help="Standalone positional shortcut for --value.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "--name",
            aliases=("-n",),
            field="name",
            parser_name="profile_name",
            help="CU CLI profile to update; defaults to the active CU CLI profile.",
        ),
    ),
)

PROFILE_UNSET = CommandSpec(
    path=("profile", "unset"),
    help="Remove one explicitly saved CU CLI profile value.",
    operation="cu_cli_core.operations.profiles#unset_profile_value",
    request_type="cu_cli_core.contracts#ProfileUnsetRequest",
    arguments=PROFILE_GET.arguments,
)

PROFILE_CREATE = CommandSpec(
    path=("profile", "create"),
    help="Create an empty named CU CLI profile without activating it.",
    operation="cu_cli_core.operations.profiles#create_profile",
    request_type="cu_cli_core.contracts#ProfileCreateRequest",
    arguments=_profile_name_arguments(
        "New profile name. Use 1-64 ASCII letters or numbers, with "
        "hyphens (-) or underscores (_); 'default' and "
        "'model_deployments' are reserved."
    ),
)

PROFILE_DELETE = CommandSpec(
    path=("profile", "delete"),
    help="Delete an inactive named CU CLI profile.",
    operation="cu_cli_core.operations.profiles#delete_profile",
    request_type="cu_cli_core.contracts#ProfileDeleteRequest",
    arguments=_profile_name_arguments("Existing inactive profile to delete."),
)

PROFILE_COPY = CommandSpec(
    path=("profile", "copy"),
    help="Copy a CU CLI profile to a new name.",
    operation="cu_cli_core.operations.profiles#copy_profile",
    request_type="cu_cli_core.contracts#ProfileCopyRequest",
    arguments=(
        ArgumentSpec(
            "--source",
            field="source",
            parser_name="source_profile",
            help="Source CU CLI profile; defaults to the active CU CLI profile.",
        ),
        ArgumentSpec(
            "--destination",
            field="destination",
            parser_name="destination_profile",
            help=(
                "New destination profile name. Use 1-64 ASCII letters or numbers, "
                "with hyphens (-) or underscores (_); 'default' and "
                "'model_deployments' are reserved."
            ),
            required=True,
        ),
        ArgumentSpec(
            "SOURCE",
            field="source",
            parser_name="positional_source_profile",
            help="Standalone source-profile shortcut.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "DESTINATION",
            field="destination",
            parser_name="positional_destination_profile",
            help="Standalone destination-profile shortcut.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
    ),
)

PROFILE_RENAME = CommandSpec(
    path=("profile", "rename"),
    help="Rename a CU CLI profile while preserving its values and active state.",
    operation="cu_cli_core.operations.profiles#rename_profile",
    request_type="cu_cli_core.contracts#ProfileRenameRequest",
    arguments=(
        ArgumentSpec(
            "--source",
            field="source",
            parser_name="source_profile",
            help="Existing profile name.",
            required=True,
        ),
        ArgumentSpec(
            "--destination",
            field="destination",
            parser_name="destination_profile",
            help=(
                "New profile name. Use 1-64 ASCII letters or numbers, with "
                "hyphens (-) or underscores (_); 'default' and "
                "'model_deployments' are reserved."
            ),
            required=True,
        ),
        ArgumentSpec(
            "SOURCE",
            field="source",
            parser_name="positional_source_profile",
            help="Standalone source-profile shortcut.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
        ArgumentSpec(
            "DESTINATION",
            field="destination",
            parser_name="positional_destination_profile",
            help="Standalone destination-profile shortcut.",
            classification=SurfaceClassification.STANDALONE_SHORTCUT,
        ),
    ),
)

PROFILE_SET_ACTIVE = CommandSpec(
    path=("profile", "set-active"),
    help="Select the active CU CLI profile.",
    operation="cu_cli_core.operations.profiles#set_active_profile",
    request_type="cu_cli_core.contracts#ProfileSetActiveRequest",
    arguments=_profile_name_arguments("Existing profile to activate."),
)

PROFILE_SYNC_DEFAULTS = CommandSpec(
    path=("profile", "sync-defaults"),
    help="Refresh a profile's model mappings from Content Understanding defaults.",
    operation="cu_cli_core.operations.profiles#sync_profile_models",
    request_type="cu_cli_core.contracts#ProfileSyncModelsRequest",
    arguments=(
        ArgumentSpec(
            "--name",
            aliases=("-n",),
            field="name",
            parser_name="profile_name",
            help="CU CLI profile to synchronize; defaults to the active CU CLI profile.",
        ),
    ),
    service_options=("auth-mode", "api-key"),
)

ENV_VAR_LIST = CommandSpec(
    path=("env-var", "list"),
    help="List recognized environment variables that are currently set.",
    operation="cu_cli_core.environment#list_set_environment_variables",
    request_type="cu_cli_core.contracts#EnvironmentVariableListRequest",
    arguments=(
        ArgumentSpec(
            "--json",
            field="json",
            parser_name="json_output",
            help="Print set variables as redacted JSON.",
            value_type=ArgumentValueType.BOOLEAN,
            classification=SurfaceClassification.FRONTEND_PRESENTATION,
        ),
    ),
)


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    ANALYZE,
    ANALYZER_LIST,
    ANALYZER_SHOW,
    ANALYZER_CREATE,
    ANALYZER_COPY,
    ANALYZER_DELETE,
    ANALYZER_VALIDATE,
    ANALYZER_TEST,
    ANALYZER_SCHEMA_CREATE,
    DEFAULTS_SHOW,
    DEFAULTS_SET,
    PROFILE_SHOW,
    PROFILE_LIST,
    PROFILE_GET,
    PROFILE_SET,
    PROFILE_UNSET,
    PROFILE_CREATE,
    PROFILE_DELETE,
    PROFILE_COPY,
    PROFILE_RENAME,
    PROFILE_SET_ACTIVE,
    PROFILE_SYNC_DEFAULTS,
    ENV_VAR_LIST,
)
_COMMAND_SPECS_BY_PATH = {spec.path: spec for spec in COMMAND_SPECS}

if len(_COMMAND_SPECS_BY_PATH) != len(COMMAND_SPECS):
    raise RuntimeError("duplicate command path in COMMAND_SPECS")


def get_command_spec(*path: str) -> CommandSpec:
    """Return the static specification for ``path``."""

    return _COMMAND_SPECS_BY_PATH[tuple(path)]
