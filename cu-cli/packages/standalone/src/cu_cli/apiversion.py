"""Central API-version resolution and validation.

The CLI explicitly tests ``2025-11-01`` and ``2026-06-01-preview``. Any
``YYYY-MM-DD-preview`` version is also accepted for forward compatibility,
while feature detection remains limited to explicitly known versions.

Resolution precedence (highest -> lowest):
  1. ``--api-version`` flag on the command (per-invocation override)
  2. schema-pinned ``apiVersion`` (schema-scoped commands only)
  3. ``CU_API_VERSION`` environment variable
  4. selected or active profile
  5. built-in default (``2025-11-01`` GA)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

from cu_cli_core.service_options import DEFAULT_API_VERSION

from .errors import CuCliError


@dataclass(frozen=True)
class ApiVersion:
    value: str
    label: str
    features: frozenset[str] = frozenset()


API_VERSIONS = (
    ApiVersion("2025-11-01", "GA"),
    ApiVersion(
        "2026-06-01-preview",
        "preview",
        frozenset({"inline-analysis"}),
    ),
)

SUPPORTED_API_VERSIONS = tuple(item.value for item in API_VERSIONS)
_PREVIEW_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-preview$")
_KNOWN_VERSION_LABELS = tuple(
    f"{item.value} ({item.label})" for item in API_VERSIONS
)
_KNOWN_VERSIONS_HELP = (
    _KNOWN_VERSION_LABELS[0]
    if len(_KNOWN_VERSION_LABELS) == 1
    else f"{', '.join(_KNOWN_VERSION_LABELS[:-1])} and {_KNOWN_VERSION_LABELS[-1]}"
)
API_VERSION_HELP = (
    f"Content Understanding API version. Known versions: {_KNOWN_VERSIONS_HELP}; "
    "any YYYY-MM-DD-preview version is also accepted."
)

if API_VERSIONS[0].value != DEFAULT_API_VERSION:
    raise RuntimeError("default API version must be the first supported API version")


def _supported_list() -> str:
    return ", ".join(f"{item.value} ({item.label})" for item in API_VERSIONS)


def is_preview_version(version: Optional[str]) -> bool:
    """Return whether *version* has the forward-compatible preview shape."""
    return bool(version and _PREVIEW_VERSION_PATTERN.fullmatch(version))


def is_supported(version: Optional[str]) -> bool:
    return version in SUPPORTED_API_VERSIONS or is_preview_version(version)


def ensure_supported(version: Optional[str]) -> str:
    """Return *version* if supported, else raise the design-doc error."""
    if not is_supported(version):
        raise CuCliError(
            f"API version {version} is not supported by this CLI build. "
            f"Supported: {_supported_list()} (or any YYYY-MM-DD-preview version).",
        )
    assert version is not None
    return version


def supports_api_feature(version: Optional[str], feature: str) -> bool:
    """Return whether an explicitly supported API version provides *feature*."""
    canonical = ensure_supported(version)
    return any(item.value == canonical and feature in item.features for item in API_VERSIONS)


def resolve_api_version(
    *,
    flag: Optional[str] = None,
    schema_pinned: Optional[str] = None,
    profile: Optional[str] = None,
    env: Optional[str] = None,
    default: str = DEFAULT_API_VERSION,
) -> str:
    """Resolve the effective api-version per the precedence chain.

    ``env`` defaults to ``CU_API_VERSION`` when not passed explicitly.

    When both ``flag`` and ``schema_pinned`` are present and disagree, this is a
    hard, fail-fast conflict: schema-scoped commands
    must never silently diverge from the version their schema declares.
    """
    if env is None:
        env = os.getenv("CU_API_VERSION")

    if flag is not None and schema_pinned is not None and flag != schema_pinned:
        raise CuCliError(
            f"Schema pins apiVersion '{schema_pinned}' but --api-version "
            f"'{flag}' was passed. Remove the flag or align the schema.",
            exit_code=2,
        )

    for candidate in (flag, schema_pinned, env, profile):
        if candidate:
            return ensure_supported(candidate)
    return ensure_supported(default)
