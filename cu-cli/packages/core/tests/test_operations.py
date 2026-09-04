# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from unittest.mock import Mock

import pytest

from cu_cli_core.operations.analyzers import get_analyzer

pytestmark = pytest.mark.unit


def test_get_analyzer_delegates_to_injected_client():
    client = Mock()
    client.get_analyzer.return_value = {"analyzerId": "invoice-v1"}

    result = get_analyzer(client, "invoice-v1")

    client.get_analyzer.assert_called_once_with("invoice-v1")
    assert result == {"analyzerId": "invoice-v1"}
