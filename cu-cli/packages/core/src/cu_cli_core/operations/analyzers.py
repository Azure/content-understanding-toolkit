# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Client-injected analyzer operations."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any

from ..contracts import AnalyzerListResult
from ..errors import ConflictError, NotFoundError, ServiceError, ValidationError


_CONTINUATION_TOKEN_VERSION = 1
_MAX_CONTINUATION_TOKEN_LENGTH = 4096
_SORT_KEYS = {
    "analyzerId": ("analyzer_id", "analyzerId"),
    "createdAt": ("created_at", "createdAt"),
    "lastModifiedAt": ("last_modified_at", "lastModifiedAt"),
}


def _value(analyzer: Any, *keys: str) -> str:
    for key in keys:
        value = getattr(analyzer, key, None)
        if value is not None:
            return str(value)
    value = analyzer.as_dict() if hasattr(analyzer, "as_dict") else {}
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) is not None:
                return str(value[key])
    return ""


def list_analyzers(
    client: Any,
    *,
    kind: str = "all",
    sort_by: str = "analyzerId",
    analyzer_id: str | None = None,
    id_prefix: str | None = None,
    limit: int | None = None,
    continuation_token: str | None = None,
) -> AnalyzerListResult:
    query_fingerprint = _query_fingerprint(kind, sort_by, analyzer_id, id_prefix)
    cursor = (
        _decode_continuation_token(continuation_token, query_fingerprint)
        if continuation_token is not None
        else None
    )

    if analyzer_id is None:
        items = list(client.list_analyzers())
    else:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            items = [client.get_analyzer(analyzer_id)]
        except ResourceNotFoundError:
            items = []

    if kind != "all":
        items = [item for item in items if analyzer_kind(item) == kind]
    if id_prefix is not None:
        items = [
            item
            for item in items
            if _value(item, "analyzer_id", "analyzerId").startswith(id_prefix)
        ]

    items.sort(key=lambda item: _sort_key(item, sort_by))
    if cursor is not None:
        items = [item for item in items if _sort_key(item, sort_by) > cursor]

    page_items = items if limit is None else items[:limit]
    next_token = None
    if limit is not None and len(items) > limit:
        next_token = _encode_continuation_token(
            _sort_key(page_items[-1], sort_by),
            query_fingerprint,
        )
    return AnalyzerListResult(tuple(page_items), next_token)


def _sort_key(analyzer: Any, sort_by: str) -> tuple[str, str]:
    analyzer_id = _value(analyzer, "analyzer_id", "analyzerId")
    return _value(analyzer, *_SORT_KEYS[sort_by]), analyzer_id


def _query_fingerprint(
    kind: str,
    sort_by: str,
    analyzer_id: str | None,
    id_prefix: str | None,
) -> str:
    query = json.dumps(
        {
            "analyzerId": analyzer_id,
            "idPrefix": id_prefix,
            "kind": kind,
            "sortBy": sort_by,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(query).hexdigest()


def _encode_continuation_token(cursor: tuple[str, str], query_fingerprint: str) -> str:
    payload = json.dumps(
        {
            "version": _CONTINUATION_TOKEN_VERSION,
            "query": query_fingerprint,
            "after": list(cursor),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_continuation_token(
    token: str,
    query_fingerprint: str,
) -> tuple[str, str]:
    if len(token) > _MAX_CONTINUATION_TOKEN_LENGTH:
        raise ValidationError("invalid continuation token.")
    try:
        padding = "=" * (-len(token) % 4)
        decoded = base64.b64decode(
            (token + padding).encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, UnicodeError, ValueError):
        raise ValidationError("invalid continuation token.") from None

    if not isinstance(payload, dict) or payload.get("version") != _CONTINUATION_TOKEN_VERSION:
        raise ValidationError("invalid continuation token.")
    if payload.get("query") != query_fingerprint:
        raise ValidationError(
            "continuation token does not match the current analyzer filters and sort order."
        )
    cursor = payload.get("after")
    if (
        not isinstance(cursor, list)
        or len(cursor) != 2
        or not all(isinstance(value, str) for value in cursor)
    ):
        raise ValidationError("invalid continuation token.")
    return cursor[0], cursor[1]


def analyzer_kind(analyzer: Any) -> str:
    analyzer_id = _value(analyzer, "analyzer_id", "analyzerId")
    return "prebuilt" if analyzer_id.startswith("prebuilt-") else "custom"


def get_analyzer(client: Any, analyzer_id: str) -> Any:
    return client.get_analyzer(analyzer_id)


def create_analyzer(client: Any, analyzer_id: str, body: dict[str, Any]) -> Any:
    from azure.core.exceptions import HttpResponseError

    try:
        poller = client.begin_create_analyzer(analyzer_id, body)
        result = poller.result()
    except HttpResponseError as exc:
        if exc.status_code == 409:
            raise ConflictError(
                f"analyzer '{analyzer_id}' already exists.",
                hint="Delete the existing analyzer explicitly or choose a versioned name.",
                status_code=409,
            ) from exc
        raise
    status = getattr(result, "status", None)
    if status and str(status).lower().endswith("failed"):
        raise ServiceError(
            f"analyzer '{getattr(result, 'analyzer_id', analyzer_id)}' "
            "was created but its status is FAILED."
        )
    return result


def delete_analyzer(client: Any, analyzer_id: str) -> None:
    from azure.core.exceptions import ResourceNotFoundError

    try:
        client.get_analyzer(analyzer_id)
    except ResourceNotFoundError as exc:
        raise NotFoundError(
            f"analyzer '{analyzer_id}' was not found; nothing was deleted.",
            status_code=404,
        ) from exc
    client.delete_analyzer(analyzer_id)
