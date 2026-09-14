# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI adapters for analyzer operations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from azure.cli.core.util import user_confirmation

from cu_cli_core.analysis import CONFIRM_THRESHOLD
from cu_cli_core.command_spec import (
    ANALYZER_COPY,
    ANALYZER_CREATE,
    ANALYZER_DELETE,
    ANALYZER_LIST,
    ANALYZER_SCHEMA_CREATE,
    ANALYZER_SHOW,
    ANALYZER_TEST,
    ANALYZER_VALIDATE,
    build_request,
    resolve_identifier,
)
from cu_cli_core.errors import ServiceError, UsageError, ValidationError
from cu_cli_core.input_planning import plan_inputs
from cu_cli_core.profiles import Profile
from cu_cli_core.schema import template_completion_model
from cu_cli_core.schema_validation import (
    custom_analyzer_id_error,
    parse_and_validate,
    schema_pinned_version,
)

from ._client_factory import create_content_understanding_client, resolve_service_settings
from ._io import require_available, write_json
from ._resources import ResolvedResource, resolve_resource, resources_equal


def _client(cmd: Any, values: dict[str, Any], *, profile_name: str | None = None) -> Any:
    return create_content_understanding_client(
        cmd,
        endpoint=values.get("endpoint"),
        api_version=values.get("api_version"),
        profile_name=profile_name if profile_name is not None else values.get("profile_name"),
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
    )


def list_analyzers(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZER_LIST, values)
    return resolve_identifier(ANALYZER_LIST.operation)(
        _client(cmd, values), kind=request.kind, sort_by=request.sort_by
    )


def show_analyzer(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZER_SHOW, values)
    return resolve_identifier(ANALYZER_SHOW.operation)(_client(cmd, values), request.name)


def create_analyzer(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZER_CREATE, values)
    name_error = custom_analyzer_id_error(request.name)
    if name_error:
        raise ValidationError(f"invalid analyzer name '{request.name}'.", hint=name_error)
    text = request.schema.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    pinned = schema_pinned_version(parsed) if isinstance(parsed, dict) else None
    profile = Profile.load(profile_name=values.get("profile_name"))
    version = values.get("api_version") or profile.api_version
    if pinned and pinned != version:
        source = "--api-version" if values.get("api_version") else "the selected profile"
        raise ValidationError(
            f"schema pins apiVersion '{pinned}' but {source} resolves to '{version}'.",
            hint="Align the schema apiVersion with the selected API version before creating the analyzer.",
        )
    validation, body = parse_and_validate(text, api_version=version)
    if body is None or validation.errors:
        finding = validation.errors[0]
        raise ValidationError(
            f"invalid schema at {finding.path}: {finding.msg}",
            hint="Run 'az cu analyzer validate --schema PATH' for all findings.",
        )
    client = create_content_understanding_client(
        cmd,
        endpoint=values.get("endpoint"),
        api_version=version,
        profile_name=values.get("profile_name"),
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
    )
    return resolve_identifier(ANALYZER_CREATE.operation)(client, request.name, body)


def delete_analyzer(cmd: Any, **values: Any) -> dict[str, Any]:
    request = build_request(ANALYZER_DELETE, values)
    user_confirmation(f"Delete analyzer '{request.name}'?", yes=request.yes)
    resolve_identifier(ANALYZER_DELETE.operation)(_client(cmd, values), request.name)
    return {"deleted": True, "analyzerId": request.name}


def validate_analyzer(_cmd: Any, **values: Any) -> dict[str, Any]:
    request = build_request(ANALYZER_VALIDATE, values)
    profile = Profile.load(profile_name=values.get("profile_name"))
    version = values.get("api_version") or profile.api_version
    result = resolve_identifier(ANALYZER_VALIDATE.operation)(request, api_version=version)
    findings = list(result.errors)
    if request.strict:
        findings.extend(result.warnings)
    if findings:
        details = "\n".join(f"{finding.path}: {finding.msg}" for finding in findings)
        raise ValidationError(f"schema validation failed:\n{details}")
    payload = result.as_dict()
    payload.update({"ok": True, "strict": request.strict, "apiVersion": version})
    return payload


def create_analyzer_schema(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZER_SCHEMA_CREATE, values)
    require_available(request.output_file, force=request.force, description="schema output")
    name_error = custom_analyzer_id_error(request.name)
    if name_error:
        raise ValidationError(name_error)
    profile = Profile.load(profile_name=values.get("profile_name"))
    version = values.get("api_version") or profile.api_version
    client = _client(cmd, values) if request.from_sample is not None else None
    payload, _ = resolve_identifier(ANALYZER_SCHEMA_CREATE.operation)(
        request,
        api_version=version,
        completion_model=template_completion_model(profile),
        client=client,
    )
    if request.output_file is not None:
        write_json(request.output_file, payload, overwrite=request.force)
    return payload


def test_analyzer(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZER_TEST, values)
    if request.dry_run and request.yes:
        raise UsageError("--dry-run and --yes cannot be combined.")
    require_available(request.output_file, force=request.force, description="test report")
    inputs = plan_inputs(
        files=request.files,
        sources=request.sources,
        pattern=request.pattern,
        recursive=request.recursive,
    )
    if request.dry_run:
        return {
            "dryRun": True,
            "analyzerId": request.name,
            "inputs": [item.reference for item in inputs.inputs],
        }
    if len(inputs.inputs) > CONFIRM_THRESHOLD:
        user_confirmation(
            f"Analyze {len(inputs.inputs)} samples with '{request.name}'? This may incur cost.",
            yes=request.yes,
        )
    report = resolve_identifier(ANALYZER_TEST.operation)(
        _client(cmd, values), request, input_plan=inputs
    )
    if request.output_file is not None:
        write_json(request.output_file, report, overwrite=request.force)
    if report["summary"]["samplesFailed"]:
        raise ServiceError(
            f"{report['summary']['samplesFailed']} analyzer test sample(s) failed.",
            context={"report": report},
        )
    return report


@dataclass(frozen=True)
class _CopySide:
    client: Any
    resource: ResolvedResource
    profile_name: str | None


def _copy_side(
    cmd: Any,
    values: dict[str, Any],
    *,
    selector: str | None,
    subscription: str | None,
    resource_group: str | None,
    profile_name: str | None,
    use_top_level_endpoint: bool,
) -> _CopySide:
    if selector:
        resource = resolve_resource(
            cmd, selector, subscription_id=subscription, resource_group=resource_group
        )
        client = create_content_understanding_client(
            cmd,
            endpoint=resource.endpoint,
            api_version=values.get("api_version"),
            profile_name=None,
            auth_mode=values.get("auth_mode"),
            api_key=values.get("api_key"),
            subscription_id=resource.subscription_id,
        )
        return _CopySide(client, resource, None)
    selected_profile = profile_name or values.get("profile_name")
    endpoint = values.get("endpoint") if use_top_level_endpoint else None
    resolved_endpoint, _ = resolve_service_settings(
        endpoint=endpoint,
        api_version=values.get("api_version"),
        profile_name=selected_profile,
    )
    resource = resolve_resource(cmd, resolved_endpoint, subscription_id=subscription)
    client = create_content_understanding_client(
        cmd,
        endpoint=resolved_endpoint,
        api_version=values.get("api_version"),
        profile_name=selected_profile,
        auth_mode=values.get("auth_mode"),
        api_key=values.get("api_key"),
        subscription_id=resource.subscription_id,
    )
    return _CopySide(client, resource, selected_profile)


def copy_analyzer(cmd: Any, **values: Any) -> Any:
    request = build_request(ANALYZER_COPY, values)
    if request.source_resource_group and not request.source_resource:
        raise UsageError("--source-resource-group requires --source-resource.")
    if request.destination_resource_group and not request.destination_resource:
        raise UsageError("--destination-resource-group requires --destination-resource.")
    source = _copy_side(
        cmd,
        values,
        selector=request.source_resource,
        subscription=request.source_subscription,
        resource_group=request.source_resource_group,
        profile_name=request.source_profile,
        use_top_level_endpoint=True,
    )
    destination = (
        _copy_side(
            cmd,
            values,
            selector=request.destination_resource,
            subscription=request.destination_subscription,
            resource_group=request.destination_resource_group,
            profile_name=request.destination_profile,
            use_top_level_endpoint=False,
        )
        if request.destination_resource or request.destination_profile
        else source
    )
    cross_resource = not resources_equal(source.resource, destination.resource)
    if not cross_resource and request.source == request.destination:
        raise ValidationError("source and destination analyzers are identical.")

    operations = __import__(
        "cu_cli_core.operations.analyzer_copy", fromlist=["collect_custom_dependencies"]
    )
    source_analyzer = None
    if cross_resource:
        source_analyzer = operations.get_copy_source_analyzer(source.client, request.source)
        dependencies = operations.collect_custom_dependencies(source_analyzer)
        missing = operations.preflight_dependencies_on_target(destination.client, dependencies)
        if missing:
            raise ValidationError(
                "destination is missing custom analyzer dependencies: " + ", ".join(missing),
                hint="Copy each dependency to the destination before copying this analyzer.",
            )
    target_options = (
        f"--profile {destination.profile_name}"
        if destination.profile_name
        else f"--endpoint {destination.resource.endpoint}"
    )
    return resolve_identifier(ANALYZER_COPY.operation)(
        source.client,
        request.source,
        request.destination,
        target_client=destination.client if cross_resource else None,
        source_azure_resource_id=source.resource.arm_id if cross_resource else None,
        source_region=source.resource.region if cross_resource else None,
        target_azure_resource_id=destination.resource.arm_id if cross_resource else None,
        target_region=destination.resource.region if cross_resource else None,
        source_analyzer=source_analyzer,
        target_cli_options=target_options,
    )