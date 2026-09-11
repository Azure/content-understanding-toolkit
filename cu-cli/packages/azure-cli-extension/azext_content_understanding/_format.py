# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Azure CLI table projections for Content Understanding results."""

from __future__ import annotations

from typing import Any


def analyzer_list_table(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project analyzer results into stable table columns without changing JSON output."""

    return [
        {
            "AnalyzerId": item.get("analyzerId"),
            "Description": item.get("description"),
            "CreatedAt": item.get("createdAt"),
            "LastModifiedAt": item.get("lastModifiedAt"),
        }
        for item in results
    ]


def defaults_table(result: dict[str, Any]) -> list[dict[str, str]]:
    """Project model deployment mappings into one row per model."""

    mappings = result.get("modelDeployments") or result.get("model_deployments") or {}
    if not isinstance(mappings, dict):
        return []
    return [
        {"Model": str(model), "Deployment": str(deployment)}
        for model, deployment in sorted(mappings.items())
    ]


def profile_list_table(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"Name": item.get("name"), "Active": item.get("active", False)}
        for item in results
    ]


def environment_table(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "Name": item.get("name"),
            "Value": item.get("value"),
            "Scope": item.get("scope"),
            "Sensitive": item.get("sensitive", False),
        }
        for item in results
    ]
