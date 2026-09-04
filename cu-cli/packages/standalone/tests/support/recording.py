# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Record / playback test harness for cloud-gated CU CLI commands.

Implements the three-mode model the dev plan borrows from the CU SDK:

* **playback** (default, CI) — replay sanitized cassettes under
  ``tests/integration/recordings/``; no network, no secrets.
* **record**   — hit a real CU endpoint once and (re)generate the cassette.
* **live**     — hit a real endpoint without writing a cassette (smoke).

Mode + live credentials come from ``CU_TEST_REC_*`` environment variables. The
autouse ``_isolate_env`` fixture strips ``CU_*`` env but explicitly preserves
these recording vars so record/live modes work:

    CU_TEST_REC_MODE      playback | record | live      (default: playback)
    CU_TEST_REC_ENDPOINT  https://<resource>.services.ai.azure.com/
    CU_TEST_REC_AUTH      entra | key                    (default: key if CU_TEST_REC_KEY set)
    CU_TEST_REC_KEY       <api-key>                       (key auth)

Cassettes are host-agnostic (matched on method + path + query) and have every
secret / real hostname scrubbed, so they are safe to commit and replay anywhere.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

try:
    import vcr as _vcr
except Exception:  # pragma: no cover - vcrpy is a dev dependency
    _vcr = None

RECORDINGS_DIR = Path(__file__).parent.parent / "integration" / "recordings"
PLACEHOLDER_ENDPOINT = "https://sanitized.services.ai.azure.com/"
_PLACEHOLDER_HOST = urlsplit(PLACEHOLDER_ENDPOINT).netloc

_SENSITIVE_HEADERS = [
    "authorization", "ocp-apim-subscription-key", "api-key",
    "x-ms-client-request-id", "x-ms-request-id", "set-cookie",
    "subscription-key",
]
_SENSITIVE_QUERY = [
    "sig",
    "code",
    "subscription-key",
    "api-key",
    # Common Azure Storage SAS tokens and key identifiers.
    "sv",
    "st",
    "se",
    "sr",
    "sp",
    "spr",
    "srt",
    "skoid",
    "sktid",
    "skt",
    "ske",
    "sks",
    "skv",
    "si",
    "sip",
]


def mode() -> str:
    return (os.getenv("CU_TEST_REC_MODE") or "playback").strip().lower()


def _real_host() -> str:
    ep = os.getenv("CU_TEST_REC_ENDPOINT", "")
    return urlsplit(ep).netloc if ep else ""


def _scrub_host(text: str) -> str:
    host = _real_host()
    if host and text:
        return text.replace(host, _PLACEHOLDER_HOST)
    return text


_URL_RE = re.compile(r"https?://[^\s\"'\\]+")


def _scrub_sensitive_query(text: str) -> str:
    """Redact sensitive query values in all URLs found in *text*."""
    sensitive = {k.lower() for k in _SENSITIVE_QUERY}

    def _replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        parts = urlsplit(raw)
        if not parts.query:
            return raw
        items = parse_qsl(parts.query, keep_blank_values=True)
        redacted = [
            (k, "REDACTED" if k.lower() in sensitive else v)
            for k, v in items
        ]
        query = urlencode(redacted, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

    return _URL_RE.sub(_replace, text)


def _before_record_request(request):
    # Rewrite the request URI to the placeholder host and drop secret headers.
    parts = urlsplit(request.uri)
    request.uri = urlunsplit((parts.scheme, _PLACEHOLDER_HOST, parts.path,
                              parts.query, parts.fragment))
    for h in _SENSITIVE_HEADERS:
        if h in request.headers:
            request.headers[h] = "REDACTED"
    # Never store the uploaded document bytes.
    if request.body and not isinstance(request.body, str):
        request.body = b"<binary-scrubbed>"
    return request


def _before_record_response(response):
    headers = response.get("headers", {})
    for key in list(headers):
        low = key.lower()
        if low in _SENSITIVE_HEADERS:
            headers[key] = ["REDACTED"]
        elif low in ("operation-location", "location", "azure-asyncoperation"):
            headers[key] = [_scrub_host(v) for v in headers[key]]
    body = response.get("body", {})
    raw = body.get("string")
    if isinstance(raw, bytes):
        text = _scrub_host(raw.decode("utf-8", "replace"))
        body["string"] = _scrub_sensitive_query(text).encode("utf-8")
    elif isinstance(raw, str):
        body["string"] = _scrub_sensitive_query(_scrub_host(raw))
    return response


def _match_path(r1, r2) -> bool:
    """Host-agnostic matcher: method + path + query only."""
    if r1.method != r2.method:
        raise AssertionError(f"method {r1.method} != {r2.method}")
    p1, p2 = urlsplit(r1.uri), urlsplit(r2.uri)
    if p1.path != p2.path:
        raise AssertionError(f"path {p1.path} != {p2.path}")
    if parse_qs(p1.query) != parse_qs(p2.query):
        raise AssertionError(f"query {p1.query} != {p2.query}")
    return True


def build_vcr():
    if _vcr is None:  # pragma: no cover
        pytest.skip("vcrpy not installed")
    record_map = {"playback": "none", "record": "all", "live": "all"}
    v = _vcr.VCR(
        cassette_library_dir=str(RECORDINGS_DIR),
        record_mode=record_map.get(mode(), "none"),
        filter_headers=[(h, "REDACTED") for h in _SENSITIVE_HEADERS],
        filter_query_parameters=[(q, "REDACTED") for q in _SENSITIVE_QUERY],
        before_record_request=_before_record_request,
        before_record_response=_before_record_response,
        decode_compressed_response=True,
        # Never record the Entra/IMDS token exchange — those responses carry
        # access tokens in the body. Let them hit the network live instead.
        ignore_hosts=[
            "login.microsoftonline.com", "login.microsoft.com",
            "login.windows.net", "169.254.169.254", "localhost",
        ],
    )
    v.register_matcher("cu_path", _match_path)
    v.match_on = ["cu_path"]
    return v


def cassette_path(name: str) -> Path:
    return RECORDINGS_DIR / f"{name}.yaml"


def use_cassette(name: str):
    """Return the VCR cassette context manager for *name*.

    In ``live`` mode nothing is recorded/replayed (a real call is made).
    In ``playback`` mode a missing cassette skips the test so CI stays green
    until recordings are generated.
    """
    if mode() == "live":
        import contextlib
        return contextlib.nullcontext()
    if mode() == "playback" and not cassette_path(name).exists():
        pytest.skip(f"no cassette {name}.yaml (run with CU_TEST_REC_MODE=record to create)")
    return build_vcr().use_cassette(str(cassette_path(name)))


def write_cloud_profile(_root: Path) -> None:
    """Write the isolated default profile used by cloud-gated CLI tests.

    Playback uses a dummy key + placeholder endpoint (no Entra token fetch, no
    network); record/live read real credentials from ``CU_TEST_REC_*``.
    """
    from cu_cli.profile import ProfileStore

    if mode() == "playback":
        data = {"endpoint": PLACEHOLDER_ENDPOINT, "auth_mode": "key",
                "api_key": "playback-dummy-key", "api_version": "2025-11-01"}
    else:
        endpoint = os.getenv("CU_TEST_REC_ENDPOINT")
        if not endpoint:
            pytest.skip("CU_TEST_REC_ENDPOINT not set for record/live mode")
        auth = (
            os.getenv("CU_TEST_REC_AUTH")
            or ("key" if os.getenv("CU_TEST_REC_KEY") else "login")
        )
        if auth == "entra":
            auth = "login"
        data = {"endpoint": endpoint, "auth_mode": auth, "api_version": "2025-11-01"}
        if auth == "key":
            key = os.getenv("CU_TEST_REC_KEY")
            if not key:
                pytest.skip("CU_TEST_REC_KEY not set for key-auth record/live mode")
            data["api_key"] = key
    store = ProfileStore.load()
    for key, value in data.items():
        store.set(key, value)
    store.save()
