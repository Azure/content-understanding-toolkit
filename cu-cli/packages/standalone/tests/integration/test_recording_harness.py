# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the record/playback harness in :mod:`support.recording`."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from support.recording import _before_record_request, _before_record_response

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "url_suffix",
    ["input.pdf?sv=1", "bob's/input.pdf?sv=1", "input.pdf?sv=1&rscc=it's-private"],
)
def test_before_record_request_scrubs_sas_url_in_json_body(url_suffix) -> None:
    request = SimpleNamespace(
        uri="https://realacct.services.ai.azure.com/contentunderstanding/analyze",
        headers={},
        body=json.dumps({"inputs": [{
            "url": f"https://storage.example.test/c/{url_suffix}&sp=r&sig=top-secret",
        }]}),
    )

    out = _before_record_request(request)

    assert "top-secret" not in out.body
    assert "sig=REDACTED" in out.body
    assert "sv=REDACTED" in out.body


@pytest.mark.parametrize(
    "url_suffix",
    ["input.pdf?sv=1", "bob's/input.pdf?sv=1", "input.pdf?sv=1&rscc=it's-private"],
)
@pytest.mark.parametrize("as_bytes", [False, True])
def test_before_record_response_scrubs_sas_with_apostrophes(url_suffix, as_bytes) -> None:
    payload = json.dumps({
        "message": f"Downloaded https://storage.example.test/c/{url_suffix}&sig=top-secret",
    })
    response = {
        "headers": {},
        "body": {"string": payload.encode("utf-8") if as_bytes else payload},
    }

    out = _before_record_response(response)

    body = out["body"]["string"]
    text = body.decode("utf-8") if as_bytes else body
    assert "top-secret" not in text
    assert "sig=REDACTED" in text
    assert "sv=REDACTED" in text


def test_before_record_response_scrubs_host_and_sensitive_query(monkeypatch) -> None:
    monkeypatch.setenv("CU_TEST_REC_ENDPOINT", "https://realacct.services.ai.azure.com/")
    response = {
        "headers": {},
        "body": {
            "string": (
                '{"containerUrl":"https://realacct.blob.core.windows.net/c?sv=2023-01-03&sig=abc123&sp=r"}'
            )
        },
    }

    out = _before_record_response(response)
    body = out["body"]["string"]
    assert "realacct.services.ai.azure.com" not in body
    assert "sig=REDACTED" in body
    assert "sv=REDACTED" in body


def test_before_record_response_handles_bytes_payload(monkeypatch) -> None:
    monkeypatch.setenv("CU_TEST_REC_ENDPOINT", "https://realacct.services.ai.azure.com/")
    response = {
        "headers": {},
        "body": {
            "string": b"https://realacct.services.ai.azure.com/path?code=abc"
        },
    }

    out = _before_record_response(response)
    body = out["body"]["string"]
    assert isinstance(body, bytes)
    assert b"sanitized.services.ai.azure.com" in body
    assert b"code=REDACTED" in body
