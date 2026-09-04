"""Client-injected analyzer operations."""

from __future__ import annotations

from typing import Any

from ..errors import ConflictError, NotFoundError, ServiceError


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
) -> list[Any]:
    items = list(client.list_analyzers())
    if kind != "all":
        items = [item for item in items if analyzer_kind(item) == kind]
    sort_keys = {
        "analyzerId": ("analyzer_id", "analyzerId"),
        "createdAt": ("created_at", "createdAt"),
        "lastModifiedAt": ("last_modified_at", "lastModifiedAt"),
    }
    return sorted(items, key=lambda item: _value(item, *sort_keys[sort_by]))


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
