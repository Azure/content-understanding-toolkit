# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for Azure CLI table projections."""

import pytest

from azext_content_understanding._format import analyzer_list_table, defaults_table


@pytest.mark.unit
def test_analyzer_list_table_projects_known_columns() -> None:
    assert analyzer_list_table(
        [
            {
                "analyzerId": "prebuilt-layout",
                "description": "Layout",
                "createdAt": "2026-01-01T00:00:00Z",
                "lastModifiedAt": "2026-01-02T00:00:00Z",
                "extra": "not displayed",
            }
        ]
    ) == [
        {
            "AnalyzerId": "prebuilt-layout",
            "Description": "Layout",
            "CreatedAt": "2026-01-01T00:00:00Z",
            "LastModifiedAt": "2026-01-02T00:00:00Z",
        }
    ]


@pytest.mark.unit
def test_defaults_table_projects_sorted_model_mappings() -> None:
    assert defaults_table(
        {"modelDeployments": {"text-embedding-3-large": "embedding", "gpt-5.2": "chat"}}
    ) == [
        {"Model": "gpt-5.2", "Deployment": "chat"},
        {"Model": "text-embedding-3-large", "Deployment": "embedding"},
    ]