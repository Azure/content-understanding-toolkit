# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the record/playback harness in :mod:`support.recording`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from runpy import run_path
import time
from types import SimpleNamespace

import pytest

from support.recording import _before_record_request, _before_record_response, write_cloud_profile

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("selected_mode", ["playback", "record", "live"])
def test_cloud_project_only_skips_polling_in_playback(monkeypatch, request, selected_mode):
    original_sleep = time.sleep
    monkeypatch.setenv("CU_TEST_REC_MODE", selected_mode)
    monkeypatch.setenv("CU_TEST_REC_ENDPOINT", "https://sanitized.services.ai.azure.com/")
    monkeypatch.setenv("CU_TEST_REC_AUTH", "entra")
    request.getfixturevalue("cloud_project")
    assert (time.sleep is original_sleep) == (selected_mode != "playback")


@pytest.mark.parametrize("selected_mode", ["playback", "record", "live"])
def test_isolate_env_preserves_live_identity_but_not_profile_writes(tmp_path, selected_mode):
    from cu_cli import profile as standalone_profile
    from cu_cli_core import profiles as core_profiles

    original_home = Path.home()
    original_home_env = {name: os.getenv(name) for name in ("HOME", "USERPROFILE")}
    login_cache = tmp_path / "login-cache"
    login_cache.mkdir()
    original_config = login_cache / "config"
    original_config.write_text("[external]\nprotected = true\n", encoding="utf-8")
    original_bytes = original_config.read_bytes()
    isolated = tmp_path / "nested-fixture"
    isolated.mkdir()
    fixture = run_path(str(Path(__file__).resolve().parents[1] / "conftest.py"))["_isolate_env"]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CU_TEST_REC_MODE", selected_mode)
        patch.setenv("CU_TEST_REC_ENDPOINT", "https://sanitized.services.ai.azure.com/")
        patch.setenv("CU_TEST_REC_AUTH", "entra")
        patch.setenv("AZURE_CONFIG_DIR", str(login_cache))
        generator = fixture.__wrapped__(isolated, patch)
        try:
            next(generator)
            expected_config = isolated / "home" / ".azure" / "config"
            assert standalone_profile.azure_config_path() == expected_config
            assert core_profiles.azure_config_path() == expected_config
            if selected_mode == "playback":
                assert Path.home() == isolated / "home"
                assert os.environ["AZURE_CONFIG_DIR"] == str(expected_config.parent)
            else:
                assert Path.home() == original_home
                assert {name: os.getenv(name) for name in original_home_env} == original_home_env
                assert os.environ["AZURE_CONFIG_DIR"] == str(login_cache)
            write_cloud_profile(Path.cwd())
            assert expected_config.is_file()
            assert original_config.read_bytes() == original_bytes
        finally:
            generator.close()


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
