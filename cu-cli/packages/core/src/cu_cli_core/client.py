# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Lazy Content Understanding client construction with injected credentials."""

from __future__ import annotations

from typing import Any

from .errors import ValidationError

LRO_POLLING_INTERVAL_SECONDS = 1


def build_content_understanding_client(
    *,
    endpoint: str,
    credential: Any,
    api_version: str,
    user_agent: str = "",
    polling_interval: int = LRO_POLLING_INTERVAL_SECONDS,
) -> Any:
    normalized_endpoint = endpoint.strip().rstrip("/")
    if not normalized_endpoint:
        raise ValidationError("Content Understanding endpoint cannot be empty")
    if not api_version.strip():
        raise ValidationError("Content Understanding API version cannot be empty")
    if credential is None:
        raise ValidationError("Content Understanding credential cannot be empty")

    from azure.ai.contentunderstanding import ContentUnderstandingClient

    return ContentUnderstandingClient(
        endpoint=normalized_endpoint,
        credential=credential,
        api_version=api_version,
        user_agent=user_agent,
        polling_interval=polling_interval,
    )
