from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
from pathlib import Path

import pytest

from cu_cli_core.errors import ValidationError
from cu_cli_core.serialization import to_plain_value

pytestmark = pytest.mark.unit


class _Status(Enum):
    READY = "ready"


@dataclass
class _Record:
    path: Path
    status: _Status


class _SdkModel:
    def as_dict(self):
        return {
            "record": _Record(Path("result.json"), _Status.READY),
            "dates": (
                date(2026, 8, 29),
                datetime(2026, 8, 29, 12, 30, tzinfo=timezone.utc),
                time(12, 30),
            ),
        }


def test_to_plain_value_recursively_serializes_supported_values():
    assert to_plain_value(_SdkModel()) == {
        "record": {"path": "result.json", "status": "ready"},
        "dates": ["2026-08-29", "2026-08-29T12:30:00+00:00", "12:30:00"],
    }


def test_to_plain_value_stringifies_mapping_keys():
    assert to_plain_value({1: Path("one"), _Status.READY: True}) == {
        "1": "one",
        "_Status.READY": True,
    }


def test_to_plain_value_rejects_cycles():
    value: list[object] = []
    value.append(value)

    with pytest.raises(ValidationError, match="cyclic"):
        to_plain_value(value)


def test_to_plain_value_surfaces_as_dict_failure():
    class _Broken:
        def as_dict(self):
            raise RuntimeError("broken")

    with pytest.raises(ValidationError, match="through as_dict"):
        to_plain_value(_Broken())


def test_to_plain_value_rejects_unknown_objects():
    with pytest.raises(ValidationError, match="unsupported result value"):
        to_plain_value(object())
