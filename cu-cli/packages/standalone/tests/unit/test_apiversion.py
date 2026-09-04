# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""API-version resolution, support checks, and conflict handling."""

from __future__ import annotations

import pytest

from cu_cli.apiversion import (API_VERSIONS, DEFAULT_API_VERSION,
                              SUPPORTED_API_VERSIONS,
                              ensure_supported, is_preview_version,
                              is_supported, resolve_api_version,
                              supports_api_feature)
from cu_cli.errors import CuCliError

pytestmark = pytest.mark.unit

GA_VERSION = "2025-11-01"
PREVIEW_VERSION = "2026-06-01-preview"


def test_default_is_ga():
    assert DEFAULT_API_VERSION == GA_VERSION == "2025-11-01"
    assert is_supported(GA_VERSION)
    assert not is_supported("1999-01-01")


def test_june_2026_preview_is_explicitly_supported():
    assert [(item.value, item.label) for item in API_VERSIONS] == [
        (GA_VERSION, "GA"),
        (PREVIEW_VERSION, "preview"),
    ]
    assert SUPPORTED_API_VERSIONS == (GA_VERSION, PREVIEW_VERSION)
    assert is_supported(PREVIEW_VERSION)
    assert ensure_supported(PREVIEW_VERSION) == PREVIEW_VERSION
    assert supports_api_feature(PREVIEW_VERSION, "inline-analysis")
    assert not supports_api_feature(GA_VERSION, "inline-analysis")


def test_ensure_supported_rejects_unknown():
    with pytest.raises(CuCliError):
        ensure_supported("nope")


def test_future_preview_pattern_is_allowed():
    preview = "2099-12-31-preview"
    assert is_preview_version(preview)
    assert is_supported(preview)
    assert ensure_supported(preview) == preview
    assert resolve_api_version(flag=preview) == preview


def test_preview_dot_suffix_is_rejected():
    preview = "2026-06-01.preview"
    assert not is_preview_version(preview)
    assert not is_supported(preview)
    with pytest.raises(CuCliError):
        ensure_supported(preview)


def test_resolution_returns_ga_from_any_source():
    # With a single supported version, every source resolves to GA.
    assert resolve_api_version(flag=GA_VERSION) == GA_VERSION
    assert resolve_api_version(schema_pinned=GA_VERSION) == GA_VERSION
    assert resolve_api_version(profile=GA_VERSION) == GA_VERSION
    assert resolve_api_version(env=GA_VERSION) == GA_VERSION
    # nothing -> default.
    assert resolve_api_version() == DEFAULT_API_VERSION


def test_env_precedence_beats_profile():
    preview = "2026-06-01-preview"
    assert resolve_api_version(profile=GA_VERSION, env=preview) == preview


def test_flag_schema_conflict_raises_exit_2():
    with pytest.raises(CuCliError) as ei:
        resolve_api_version(flag="2099-12-31", schema_pinned=GA_VERSION)
    assert ei.value.exit_code == 2


def test_flag_equals_schema_is_fine():
    assert resolve_api_version(flag=GA_VERSION, schema_pinned=GA_VERSION) == GA_VERSION
