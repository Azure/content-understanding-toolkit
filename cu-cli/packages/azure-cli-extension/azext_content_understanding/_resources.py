# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Resolve Content Understanding resources through Azure CLI host context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from azure.cli.core.commands.client_factory import get_mgmt_service_client
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

from cu_cli_core.errors import AuthenticationError, NotFoundError, ValidationError

from ._client_factory import (
    ensure_supported_cloud,
    get_cli_credential_for_subscription,
    get_subscription_id,
)

_CU_KINDS = frozenset({"aiservices", "contentunderstanding"})


@dataclass(frozen=True)
class ResolvedResource:
    arm_id: str
    region: str
    endpoint: str
    subscription_id: str
    resource_group: str
    account_name: str


def parse_arm_id(value: str) -> tuple[str, str, str]:
    parts = value.strip("/").split("/")
    if (
        len(parts) != 8
        or parts[0].lower() != "subscriptions"
        or parts[2].lower() != "resourcegroups"
        or parts[4].lower() != "providers"
        or parts[5].lower() != "microsoft.cognitiveservices"
        or parts[6].lower() != "accounts"
    ):
        raise ValidationError(
            "resource selector is not a Microsoft.CognitiveServices/accounts ARM ID.",
            hint=(
                "Use an account name, Foundry endpoint, or full "
                "/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/... ID."
            ),
        )
    return parts[1], parts[3], parts[7]


def _endpoint(account: Any) -> str:
    properties = getattr(account, "properties", None)
    endpoints = getattr(properties, "endpoints", None)
    if isinstance(endpoints, dict):
        for key in ("Content Understanding", "ContentUnderstanding", "OpenAI"):
            if endpoints.get(key):
                return str(endpoints[key]).rstrip("/") + "/"
    endpoint = getattr(properties, "endpoint", None)
    if endpoint:
        return str(endpoint).rstrip("/") + "/"
    return f"https://{account.name}.services.ai.azure.com/"


def _resolved(account: Any) -> ResolvedResource:
    kind = str(getattr(account, "kind", "") or "")
    if kind.lower() not in _CU_KINDS:
        raise ValidationError(
            f"account '{account.name}' has kind '{kind}', which is not Content Understanding-capable."
        )
    subscription, resource_group, name = parse_arm_id(str(account.id))
    arm_id = (
        f"/subscriptions/{subscription}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{name}"
    )
    return ResolvedResource(
        arm_id=arm_id,
        region=str(account.location),
        endpoint=_endpoint(account),
        subscription_id=subscription,
        resource_group=resource_group,
        account_name=name,
    )


def _management_client(cmd: Any, subscription_id: str) -> Any:
    credential = get_cli_credential_for_subscription(cmd.cli_ctx, subscription_id)
    return get_mgmt_service_client(
        cmd.cli_ctx,
        CognitiveServicesManagementClient,
        subscription_id=subscription_id,
        credential=credential,
    )


def _translate_discovery_error(exc: HttpResponseError, subscription_id: str) -> None:
    status = getattr(exc, "status_code", None)
    if status in {401, 403}:
        raise AuthenticationError(
            f"the signed-in Azure CLI identity cannot discover resources in subscription "
            f"'{subscription_id}'.",
            hint="Grant Reader access for discovery and Cognitive Services User for copy.",
        ) from exc


def resolve_resource(
    cmd: Any,
    selector: str,
    *,
    subscription_id: str | None = None,
    resource_group: str | None = None,
) -> ResolvedResource:
    """Resolve an endpoint, account name, or ARM ID in host subscription context."""

    ensure_supported_cloud(cmd.cli_ctx)
    value = selector.strip()
    if not value:
        raise ValidationError("resource selector cannot be empty.")
    if value.lower().startswith("/subscriptions/"):
        subscription, group, name = parse_arm_id(value)
        try:
            return _resolved(_management_client(cmd, subscription).accounts.get(group, name))
        except ResourceNotFoundError as exc:
            raise NotFoundError(f"Content Understanding account '{name}' was not found.") from exc
        except HttpResponseError as exc:
            _translate_discovery_error(exc, subscription)
            raise

    subscription = subscription_id or get_subscription_id(cmd.cli_ctx)
    hostname = None
    if value.lower().startswith(("https://", "http://")):
        parsed = urlparse(value)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise ValidationError("resource endpoint must be an absolute HTTPS URL.")
        hostname = parsed.hostname.lower()
        name_hint = hostname.split(".", 1)[0]
    else:
        if "/" in value or any(character.isspace() for character in value):
            raise ValidationError("resource selector must be an account name, endpoint, or ARM ID.")
        name_hint = value

    client = _management_client(cmd, subscription)
    try:
        accounts = (
            client.accounts.list_by_resource_group(resource_group)
            if resource_group
            else client.accounts.list()
        )
        candidates = [
            account
            for account in accounts
            if str(getattr(account, "name", "")).lower() == name_hint.lower()
        ]
    except HttpResponseError as exc:
        _translate_discovery_error(exc, subscription)
        raise
    if hostname is not None:
        candidates = [
            account
            for account in candidates
            if (urlparse(_endpoint(account)).hostname or "").lower() == hostname
        ]
    if not candidates:
        raise NotFoundError(
            f"no Content Understanding account matched '{value}'.",
            hint="Check the active subscription or pass an explicit subscription and resource group.",
        )
    if len(candidates) > 1:
        raise ValidationError(
            f"multiple accounts matched '{value}'; refusing to guess.",
            hint="Pass the full ARM ID or narrow discovery with a resource group.",
        )
    return _resolved(candidates[0])


def resources_equal(left: ResolvedResource, right: ResolvedResource) -> bool:
    return left.arm_id.casefold() == right.arm_id.casefold()


def list_model_deployments(cmd: Any, endpoint: str) -> list[dict[str, Any]]:
    """List live model deployments for the Foundry resource at ``endpoint``."""

    resource = resolve_resource(cmd, endpoint)
    deployments = _management_client(cmd, resource.subscription_id).deployments.list(
        resource.resource_group,
        resource.account_name,
    )
    result: list[dict[str, Any]] = []
    for deployment in deployments:
        properties = getattr(deployment, "properties", None)
        model = getattr(properties, "model", None)
        sku = getattr(deployment, "sku", None)
        result.append(
            {
                "name": str(getattr(deployment, "name", "") or ""),
                "model": str(getattr(model, "name", "") or ""),
                "version": str(getattr(model, "version", "") or ""),
                "sku": str(getattr(sku, "name", "") or ""),
                "capacity": getattr(sku, "capacity", None),
            }
        )
    return sorted(result, key=lambda item: item["name"].casefold())