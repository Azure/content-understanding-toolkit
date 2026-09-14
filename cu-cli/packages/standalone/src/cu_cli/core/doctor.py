# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Backward-compatible exports for shared doctor policy."""

from __future__ import annotations

from cu_cli_core.doctor import missing_requirements as _shared_missing_requirements
from .defaults import is_defaults_not_set  # re-exported for callers

__all__ = ["missing_requirements", "is_defaults_not_set"]


def missing_requirements(mapped: dict[str, str]) -> list[str]:
    """Return shared readiness requirements using the legacy list shape."""

    return list(_shared_missing_requirements(mapped))
