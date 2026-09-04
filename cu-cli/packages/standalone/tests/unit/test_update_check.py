from __future__ import annotations

import json
from dataclasses import dataclass

import cu_cli.update_check as update_check
from cu_cli.update_check import is_newer
from cu_cli.update_provider import (
    PyPIUpdateProvider,
    get_update_provider,
    pip_install_args,
)

import pytest

pytestmark = pytest.mark.unit


class _FakeProvider:
    def __init__(
        self, name: str, responses: list[tuple[str | None, str]]
    ) -> None:
        self.name = name
        self.responses = responses
        self.calls = 0

    def fetch_latest_version(self) -> tuple[str | None, str]:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def _configure_cache_test(
    monkeypatch: pytest.MonkeyPatch, tmp_path, provider: _FakeProvider, now: list[float]
) -> None:
    monkeypatch.delenv("CU_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(update_check, "_CACHE_PATH", tmp_path / "update-check.json")
    monkeypatch.setattr(update_check, "get_update_provider", lambda: provider)
    monkeypatch.setattr(update_check.time, "time", lambda: now[0])


def test_is_newer_handles_prerelease_and_stable_versions() -> None:
    assert is_newer("1.0.0", "1.0.0rc1") is True
    assert is_newer("1.0.0rc1", "1.0.0") is False


def test_is_newer_handles_post_and_dev_releases() -> None:
    assert is_newer("1.0.0.post1", "1.0.0") is True
    assert is_newer("1.0.0.dev1", "1.0.0") is False


def test_is_newer_falls_back_for_non_pep440_strings() -> None:
    assert is_newer("2.0.0-preview", "1.9.9") is True


def test_update_provider_defaults_to_pypi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cu_cli.update_provider.entry_points", lambda **_: ())
    assert isinstance(get_update_provider(), PyPIUpdateProvider)


def test_update_provider_loads_single_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @dataclass
    class FakeProvider:
        name: str = "private feed"
        release_notes_url: str = "https://example.test/releases"
        source_install_hint: str = "install privately"

        def fetch_latest_version(self):
            return "1.2.3", "ok"

        def pip_environment(self):
            return {"PIP_INDEX_URL": "https://example.test/simple/"}

    class FakeEntryPoint:
        name = "private"

        @staticmethod
        def load():
            return FakeProvider

    monkeypatch.setattr(
        "cu_cli.update_provider.entry_points", lambda **_: (FakeEntryPoint(),)
    )
    provider = get_update_provider()
    assert provider.name == "private feed"
    assert provider.fetch_latest_version() == ("1.2.3", "ok")


def test_pip_install_args_pin_discovered_version() -> None:
    args = pip_install_args("1.2.3")
    assert args[-2:] == ["--upgrade", "cu-cli==1.2.3"]


def test_update_cache_uses_descriptive_timestamps(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    cache_path = tmp_path / "update-check.json"
    monkeypatch.setattr(update_check, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(update_check.time, "time", lambda: 1234.0)

    update_check._write_cache("private feed", "1.2.3")

    data = json.loads(cache_path.read_text(encoding="utf-8"))
    assert data == {
        "provider": "private feed",
        "last_attempt_timestamp": 1234.0,
        "latest": "1.2.3",
        "last_success_timestamp": 1234.0,
    }


def test_failed_update_check_is_not_retried_for_24_hours(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    provider = _FakeProvider("private feed", [(None, "network_error")])
    now = [1234.0]
    _configure_cache_test(monkeypatch, tmp_path, provider, now)

    assert update_check.fetch_latest_version() is None
    assert update_check.fetch_latest_version() is None
    assert provider.calls == 1
    assert json.loads(update_check._CACHE_PATH.read_text(encoding="utf-8")) == {
        "provider": "private feed",
        "last_attempt_timestamp": 1234.0,
    }


def test_successful_update_check_is_reused_for_24_hours(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    provider = _FakeProvider("private feed", [("1.2.3", "ok")])
    now = [1234.0]
    _configure_cache_test(monkeypatch, tmp_path, provider, now)

    assert update_check.fetch_latest_version_detailed() == ("1.2.3", "ok")
    now[0] += update_check._CACHE_TTL_SECONDS - 1
    assert update_check.fetch_latest_version_detailed() == ("1.2.3", "ok")
    assert provider.calls == 1


def test_update_check_retries_when_cache_expires(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    provider = _FakeProvider(
        "private feed",
        [("1.2.3", "ok"), ("1.2.4", "ok")],
    )
    now = [1234.0]
    _configure_cache_test(monkeypatch, tmp_path, provider, now)

    assert update_check.fetch_latest_version() == "1.2.3"
    now[0] += update_check._CACHE_TTL_SECONDS
    assert update_check.fetch_latest_version() == "1.2.4"
    assert provider.calls == 2


def test_update_check_can_bypass_recent_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    provider = _FakeProvider(
        "private feed",
        [("1.2.3", "ok"), ("1.2.4", "ok")],
    )
    now = [1234.0]
    _configure_cache_test(monkeypatch, tmp_path, provider, now)

    assert update_check.fetch_latest_version() == "1.2.3"
    assert update_check.fetch_latest_version(use_cache=False) == "1.2.4"
    assert provider.calls == 2


def test_update_cache_is_isolated_by_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    internal = _FakeProvider(
        "Internal Feed",
        [("0.1.0.dev2026081506+internal", "ok")],
    )
    pypi = _FakeProvider("PyPI", [("0.1.0", "ok")])
    selected = [internal]
    now = [1234.0]
    _configure_cache_test(monkeypatch, tmp_path, internal, now)
    monkeypatch.setattr(update_check, "get_update_provider", lambda: selected[0])

    assert update_check.fetch_latest_version() == "0.1.0.dev2026081506+internal"
    selected[0] = pypi
    assert update_check.fetch_latest_version() == "0.1.0"
    assert internal.calls == 1
    assert pypi.calls == 1
    assert json.loads(update_check._CACHE_PATH.read_text(encoding="utf-8"))[
        "provider"
    ] == "PyPI"


def test_failed_refresh_preserves_last_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    provider = _FakeProvider(
        "private feed",
        [("1.2.3", "ok"), (None, "network_error")],
    )
    now = [1234.0]
    _configure_cache_test(monkeypatch, tmp_path, provider, now)

    assert update_check.fetch_latest_version() == "1.2.3"
    now[0] += 60
    assert update_check.fetch_latest_version(use_cache=False) is None

    data = json.loads(update_check._CACHE_PATH.read_text(encoding="utf-8"))
    assert data["last_attempt_timestamp"] == 1294.0
    assert data["last_success_timestamp"] == 1234.0
    assert data["latest"] == "1.2.3"
    assert update_check.fetch_latest_version() == "1.2.3"
    assert provider.calls == 2
