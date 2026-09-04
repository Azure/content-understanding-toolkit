# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``friendly_errors`` surfaces the SDK's inner error details.

Regression coverage for the reviewer's finding (PR #4, analyzers.py): the CU
service nests the actionable failure under ``error.innererror`` while the
top-level ``error.message`` is only a generic ``"Invalid Request."``. These
payloads mirror what the live service returns for an invalid analyzer id,
an invalid schema, and a missing analyzer (see the live probe in the PR).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from azure.core.exceptions import (
    HttpResponseError,
    ODataV4Format,
    ResourceNotFoundError,
)
from cu_cli_core.errors import ValidationError

from cu_cli.errors import CuCliError, _format_service_error, friendly_errors

pytestmark = pytest.mark.unit


# Real payload captured from the live service (invalid baseAnalyzerId).
INVALID_REQUEST = {
    "code": "InvalidRequest",
    "message": "Invalid Request.",
    "innererror": {
        "code": "InvalidFieldSchema",
        "message": "One or more errors encountered while processing the field schema.",
        "details": [
            {
                "code": "InvalidBaseAnalyzerId",
                "message": "Unsupported 'baseAnalyzerId' value: 'prebuilt-documentAnalyzer'",
                "target": "/baseAnalyzerId",
            }
        ],
    },
}

NOT_FOUND = {
    "code": "NotFound",
    "message": "Resource not found.",
    "innererror": {
        "code": "ModelNotFound",
        "message": "Analyzer 'nope' was not found.",
    },
}


def _http_error(status, payload, cls=HttpResponseError):
    exc = cls()
    exc.status_code = status
    exc.error = ODataV4Format(payload)
    return exc


def test_format_surfaces_inner_error_and_details():
    exc = _http_error(400, INVALID_REQUEST)
    msg = _format_service_error(exc)

    assert "service responded 400 (InvalidRequest): Invalid Request." in msg
    # the generic top message is not the end of the story — inner detail wins
    assert "InvalidFieldSchema" in msg
    assert "InvalidBaseAnalyzerId" in msg
    assert "/baseAnalyzerId" in msg
    assert "Unsupported 'baseAnalyzerId' value: 'prebuilt-documentAnalyzer'" in msg


def test_format_tolerates_missing_error_body():
    exc = SimpleNamespace(status_code=500, error=None, message="boom")
    msg = _format_service_error(exc)
    assert "service responded 500" in msg
    assert "boom" in msg


def test_wrapper_4xx_surfaces_detail_and_drops_doctor_hint():
    @friendly_errors
    def boom():
        raise _http_error(400, INVALID_REQUEST)

    with pytest.raises(CuCliError) as ei:
        boom()
    assert "InvalidFieldSchema" in ei.value.message
    assert "InvalidBaseAnalyzerId" in ei.value.message
    # a 'cu doctor' nudge is misleading for a request-validation error
    assert ei.value.hint is None


def test_wrapper_404_surfaces_model_not_found():
    @friendly_errors
    def boom():
        raise _http_error(404, NOT_FOUND, cls=ResourceNotFoundError)

    with pytest.raises(CuCliError) as ei:
        boom()
    assert "ModelNotFound" in ei.value.message
    assert "Analyzer 'nope' was not found." in ei.value.message
    assert ei.value.hint is None


def test_wrapper_5xx_keeps_doctor_hint():
    payload = {"code": "ServiceUnavailable", "message": "Try again later."}

    @friendly_errors
    def boom():
        raise _http_error(503, payload)

    with pytest.raises(CuCliError) as ei:
        boom()
    assert "service responded 503 (ServiceUnavailable)" in ei.value.message
    assert ei.value.hint is not None
    assert "cu doctor" in ei.value.hint


def test_format_message_embeds_hint():
    # Regression: rich-click renders errors via format_message (not our show()), so
    # the hint must be part of format_message or it is silently dropped.
    with_hint = CuCliError("something failed.", hint="do X to recover.")
    rendered = with_hint.format_message()
    assert "something failed." in rendered
    assert "hint: do X to recover." in rendered


def test_format_message_without_hint_is_just_the_message():
    plain = CuCliError("something failed.")
    assert plain.format_message() == "something failed."


def test_wrapper_translates_core_error_without_losing_hint():
    @friendly_errors
    def boom():
        raise ValidationError("invalid request", hint="fix the supplied value")

    with pytest.raises(CuCliError) as error:
        boom()

    assert error.value.message == "invalid request"
    assert error.value.hint == "fix the supplied value"
