# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceNotFoundError

from cu_cli_core.errors import ValidationError
from cu_cli_core.operations.analyzers import get_analyzer, list_analyzers

pytestmark = pytest.mark.unit


def test_get_analyzer_delegates_to_injected_client():
    client = Mock()
    client.get_analyzer.return_value = {"analyzerId": "invoice-v1"}

    result = get_analyzer(client, "invoice-v1")

    client.get_analyzer.assert_called_once_with("invoice-v1")
    assert result == {"analyzerId": "invoice-v1"}


def _analyzer(
    analyzer_id: str,
    created_at: str = "2026-01-01",
    last_modified_at: str = "2026-01-01",
):
    return SimpleNamespace(
        analyzer_id=analyzer_id,
        created_at=created_at,
        last_modified_at=last_modified_at,
    )


class _PagedAnalyzerClient:
    def __init__(self, pages):
        self.pages = pages
        self.list_calls = 0
        self.get_calls = []

    def list_analyzers(self):
        self.list_calls += 1
        return (item for page in self.pages for item in page)

    def get_analyzer(self, analyzer_id):
        self.get_calls.append(analyzer_id)
        for page in self.pages:
            for item in page:
                if item.analyzer_id == analyzer_id:
                    return item
        raise ResourceNotFoundError("not found")


def _ids(result):
    return [item.analyzer_id for item in result.items]


def test_list_analyzers_pages_filtered_results_without_duplicates_or_gaps():
    client = _PagedAnalyzerClient(
        [
            [_analyzer("invoice_c"), _analyzer("other")],
            [_analyzer("invoice_a"), _analyzer("invoice_b")],
        ]
    )

    first = list_analyzers(client, id_prefix="invoice_", limit=2)
    second = list_analyzers(
        client,
        id_prefix="invoice_",
        limit=2,
        continuation_token=first.continuation_token,
    )

    assert _ids(first) == ["invoice_a", "invoice_b"]
    assert first.continuation_token is not None
    assert _ids(second) == ["invoice_c"]
    assert second.continuation_token is None
    assert client.list_calls == 2


def test_list_analyzers_exact_id_uses_get_and_honors_kind():
    client = _PagedAnalyzerClient([[_analyzer("custom_v1"), _analyzer("prebuilt-layout")]])

    found = list_analyzers(client, analyzer_id="custom_v1", kind="custom")
    excluded = list_analyzers(client, analyzer_id="custom_v1", kind="prebuilt")
    missing = list_analyzers(client, analyzer_id="missing")

    assert _ids(found) == ["custom_v1"]
    assert _ids(excluded) == []
    assert _ids(missing) == []
    assert client.get_calls == ["custom_v1", "custom_v1", "missing"]
    assert client.list_calls == 0


def test_list_analyzers_rejects_invalid_token_before_service_call():
    client = _PagedAnalyzerClient([[_analyzer("custom_v1")]])

    with pytest.raises(ValidationError, match="invalid continuation token"):
        list_analyzers(client, limit=1, continuation_token="not-a-token")

    assert client.list_calls == 0


def test_list_analyzers_rejects_token_when_query_changes():
    client = _PagedAnalyzerClient([[_analyzer("a"), _analyzer("b")]])
    first = list_analyzers(client, limit=1)

    with pytest.raises(ValidationError, match="does not match"):
        list_analyzers(
            client,
            kind="custom",
            limit=1,
            continuation_token=first.continuation_token,
        )


def test_list_analyzers_uses_id_as_stable_sort_tiebreaker():
    client = _PagedAnalyzerClient(
        [[_analyzer("b", created_at="same"), _analyzer("a", created_at="same")]]
    )

    first = list_analyzers(client, sort_by="createdAt", limit=1)
    second = list_analyzers(
        client,
        sort_by="createdAt",
        limit=1,
        continuation_token=first.continuation_token,
    )

    assert _ids(first) == ["a"]
    assert _ids(second) == ["b"]
