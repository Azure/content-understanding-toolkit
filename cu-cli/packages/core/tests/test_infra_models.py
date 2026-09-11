# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path
from types import SimpleNamespace

import pytest

from cu_cli_core.errors import ValidationError
from cu_cli_core.infra_models import (
    deployable_models,
    recommended_models,
    select_requested_models,
    supported_model_names,
    write_models_file,
)

pytestmark = pytest.mark.unit


def _catalog() -> list[dict]:
    return [
        {
            "name": "gpt-5.2",
            "version": "2025-01-01",
            "format": "OpenAI",
            "isDefaultVersion": True,
            "skus": [{"name": "Standard", "capacity": {"default": 2}}],
        },
        {
            "name": "text-embedding-3-large",
            "version": "1",
            "format": "OpenAI",
            "skus": [{"name": "GlobalStandard", "capacity": {"default": 1}}],
        },
    ]


def _candidates():
    supported = supported_model_names(
        SimpleNamespace(supported_models={"completion": ["gpt-5.2"], "embedding": ["text-embedding-3-large"]})
    )
    return deployable_models(_catalog(), supported)


def test_normalizes_sdk_models_and_selects_preferred_skus():
    candidates = _candidates()

    assert [(model.name, model.sku_name, model.sku_capacity) for model in candidates] == [
        ("gpt-5.2", "Standard", 2),
        ("text-embedding-3-large", "GlobalStandard", 1),
    ]
    assert [model.name for model in recommended_models(candidates)] == [
        "gpt-5.2",
        "text-embedding-3-large",
    ]


def test_rejects_ambiguous_or_duplicate_model_families():
    candidates = _candidates()
    candidates.append(
        candidates[0].__class__(
            "gpt-5.2", "2025-02-01", "OpenAI", "completion", "Standard", 1
        )
    )

    with pytest.raises(ValidationError, match="multiple deployable versions"):
        select_requested_models(candidates, ["gpt-5.2"])
    with pytest.raises(ValidationError, match="selected more than once"):
        select_requested_models(_candidates(), ["gpt-5.2", "gpt-5.2@2025-01-01"])


def test_writes_canonical_bicep_model_shape_atomically(tmp_path: Path):
    output = tmp_path / "infra" / "models.json"

    write_models_file(output, _candidates())

    assert output.read_text(encoding="utf-8") == (
        '[\n'
        '  {\n'
        '    "name": "gpt-5.2",\n'
        '    "model": "gpt-5.2",\n'
        '    "version": "2025-01-01",\n'
        '    "format": "OpenAI",\n'
        '    "skuName": "Standard",\n'
        '    "skuCapacity": 2\n'
        '  },\n'
        '  {\n'
        '    "name": "text-embedding-3-large",\n'
        '    "model": "text-embedding-3-large",\n'
        '    "version": "1",\n'
        '    "format": "OpenAI",\n'
        '    "skuName": "GlobalStandard",\n'
        '    "skuCapacity": 1\n'
        '  }\n'
        ']\n'
    )
