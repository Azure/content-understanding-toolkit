"""Convert CU and Azure SDK values into frontend-neutral plain values."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import ValidationError


def to_plain_value(value: Any) -> Any:
    """Recursively convert supported values to dictionaries, lists, and scalars."""

    return _to_plain_value(value, seen=set())


def _to_plain_value(value: Any, *, seen: set[int]) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return _to_plain_value(value.value, seen=seen)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)

    identity = id(value)
    if identity in seen:
        raise ValidationError("cannot serialize a cyclic result value")

    if hasattr(value, "as_dict"):
        seen.add(identity)
        try:
            converted = value.as_dict()
        except Exception as exc:
            raise ValidationError(
                f"failed to serialize {type(value).__name__} through as_dict()"
            ) from exc
        finally:
            seen.remove(identity)
        return _to_plain_value(converted, seen=seen)

    if is_dataclass(value) and not isinstance(value, type):
        seen.add(identity)
        try:
            converted = asdict(value)
        finally:
            seen.remove(identity)
        return _to_plain_value(converted, seen=seen)

    if isinstance(value, Mapping):
        seen.add(identity)
        try:
            return {
                str(key): _to_plain_value(item, seen=seen)
                for key, item in value.items()
            }
        finally:
            seen.remove(identity)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        seen.add(identity)
        try:
            return [_to_plain_value(item, seen=seen) for item in value]
        finally:
            seen.remove(identity)

    raise ValidationError(f"unsupported result value: {type(value).__name__}")
