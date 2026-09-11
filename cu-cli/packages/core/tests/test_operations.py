# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from unittest.mock import Mock
from types import SimpleNamespace

import pytest
from azure.core.exceptions import ResourceNotFoundError

from cu_cli_core.errors import NotFoundError, ValidationError
from cu_cli_core.operations.analyzers import get_analyzer, update_analyzer

pytestmark = pytest.mark.unit


def test_get_analyzer_delegates_to_injected_client():
    client = Mock()
    client.get_analyzer.return_value = {"analyzerId": "invoice-v1"}

    result = get_analyzer(client, "invoice-v1")

    client.get_analyzer.assert_called_once_with("invoice-v1")
    assert result == {"analyzerId": "invoice-v1"}


@pytest.mark.parametrize(
    ("description", "tags", "existing_tags", "expected_patch"),
    [
        ("Updated", None, None, {"description": "Updated"}),
        (
            None,
            {"owner": "cu-cli"},
            {"scenario": "existing"},
            {"tags": {"owner": "cu-cli", "scenario": "existing"}},
        ),
        (
            "Updated",
            {"owner": "cu-cli"},
            None,
            {"description": "Updated", "tags": {"owner": "cu-cli"}},
        ),
    ],
)
def test_update_analyzer_sends_only_requested_metadata(
    description,
    tags,
    existing_tags,
    expected_patch,
):
    client = Mock()
    client.get_analyzer.return_value = SimpleNamespace(tags=existing_tags)
    client.update_analyzer.return_value = {"analyzerId": "invoice_v1"}

    result = update_analyzer(
        client,
        "invoice_v1",
        description=description,
        tags=tags,
    )

    client.update_analyzer.assert_called_once_with("invoice_v1", expected_patch)
    if tags:
        client.get_analyzer.assert_called_once_with("invoice_v1")
    else:
        client.get_analyzer.assert_not_called()
    assert set(expected_patch) <= {"description", "tags"}
    assert "fieldSchema" not in expected_patch
    assert result == {"analyzerId": "invoice_v1"}


def test_update_analyzer_rejects_noop_before_service_call():
    client = Mock()

    with pytest.raises(ValidationError, match="at least one metadata change"):
        update_analyzer(client, "invoice_v1")

    client.update_analyzer.assert_not_called()


def test_update_analyzer_translates_missing_analyzer():
    client = Mock()
    client.update_analyzer.side_effect = ResourceNotFoundError("not found")

    with pytest.raises(NotFoundError, match="nothing was updated") as exc_info:
        update_analyzer(client, "missing", description="Updated")

    assert "analyzer list --info" in (exc_info.value.hint or "")


def test_update_analyzer_translates_missing_analyzer_before_tag_merge():
    client = Mock()
    client.get_analyzer.side_effect = ResourceNotFoundError("not found")

    with pytest.raises(NotFoundError, match="nothing was updated"):
        update_analyzer(client, "missing", tags={"owner": "cu-cli"})

    client.update_analyzer.assert_not_called()


def test_update_analyzer_preserves_tags_from_mapping_analyzer():
    client = Mock()
    client.get_analyzer.return_value = {"tags": {"scenario": "existing"}}

    update_analyzer(client, "invoice_v1", tags={"owner": "cu-cli"})

    client.update_analyzer.assert_called_once_with(
        "invoice_v1",
        {"tags": {"scenario": "existing", "owner": "cu-cli"}},
    )


def test_update_analyzer_preserves_tags_from_as_dict_analyzer():
    client = Mock()
    client.get_analyzer.return_value = SimpleNamespace(
        as_dict=lambda: {"tags": {"scenario": "existing"}}
    )

    update_analyzer(client, "invoice_v1", tags={"owner": "cu-cli"})

    client.update_analyzer.assert_called_once_with(
        "invoice_v1",
        {"tags": {"scenario": "existing", "owner": "cu-cli"}},
    )
