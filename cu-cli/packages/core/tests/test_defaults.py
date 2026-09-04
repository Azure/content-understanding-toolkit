# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cu_cli_core.defaults import (
    apply_defaults,
    extract_model_deployments,
    parse_model_kv,
    with_prebuilt_default_mappings,
)
from cu_cli_core.errors import ValidationError

pytestmark = pytest.mark.unit


def test_parse_model_kv_validates_and_normalizes_values():
    assert parse_model_kv((" gpt-5.2 = deployment ",)) == {
        "gpt-5.2": "deployment"
    }
    with pytest.raises(ValidationError, match="invalid --model mapping"):
        parse_model_kv(("missing-separator",))


def test_with_prebuilt_default_mappings_adds_service_aliases():
    mappings = with_prebuilt_default_mappings(
        {
            "gpt-5.2": "completion",
            "text-embedding-3-large": "embedding",
        }
    )

    assert mappings["prebuilt-analyzer-completion"] == "completion"
    assert mappings["prebuilt-analyzer-completion-mini"] == "completion"
    assert mappings["prebuilt-analyzer-embedding"] == "embedding"


def test_apply_defaults_merges_existing_values():
    class Client:
        def get_defaults(self):
            return SimpleNamespace(model_deployments={"existing": "old"})

        def update_defaults(self, *, model_deployments):
            return SimpleNamespace(model_deployments=model_deployments)

    updated, merged = apply_defaults(
        Client(),
        {"gpt-5.2": "completion"},
        replace=False,
    )

    assert merged["existing"] == "old"
    assert extract_model_deployments(updated) == merged
