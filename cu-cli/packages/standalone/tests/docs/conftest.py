# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Fixtures for the tests that are the source of README and usage-guide code blocks."""

from __future__ import annotations

from functools import cache
import json
import os
from pathlib import Path
from runpy import run_path
import shutil
import socket
import time

from azure.core.credentials import AccessToken
import pytest

from support import snippets
from support.recording import mode, write_cloud_profile

_PRODUCT_ROOT = Path(snippets.__file__).resolve().parents[4]
_SCRIPT = run_path(str(_PRODUCT_ROOT / "scripts" / "update-snippet.py"))
# Read at import time because _isolate_env removes CU_* variables while each test runs.
_OUTPUT = os.environ.get(_SCRIPT["OUTPUT_ENVIRONMENT"])
_PUBLISHED = pytest.StashKey[dict[str, dict[str, dict]]]()
_OUTCOMES = pytest.StashKey[list[str]]()
_PARTS = pytest.StashKey[dict[str, list[dict]]]()


@cache
def _regions(path: Path) -> dict[str, tuple[Path, int, int, str]]:
    return _SCRIPT["discover_snippet_regions"](path)


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate CU profiles; record/live runs keep the real sign-in cache for new recordings."""
    from cu_cli import profile as standalone_profile

    original_home = Path.home()
    original_azure_config_dir = os.getenv("AZURE_CONFIG_DIR") or str(original_home / ".azure")
    rec_mode = mode()
    home = tmp_path / "home"
    home.mkdir()
    if rec_mode not in {"live", "record"}:
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    isolated_config = home / ".azure" / "config"
    monkeypatch.setattr("cu_cli_core.profiles.azure_config_path", lambda: isolated_config)
    monkeypatch.setattr(standalone_profile, "azure_config_path", lambda: isolated_config)
    if rec_mode in {"live", "record"}:
        monkeypatch.setenv("AZURE_CONFIG_DIR", original_azure_config_dir)
    else:
        monkeypatch.setenv("AZURE_CONFIG_DIR", str(home / ".azure"))
    for key in list(os.environ):
        if key.startswith("CU_TEST_REC_"):
            continue
        if key.startswith(("CU_", "CONTENTUNDERSTANDING_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CU_NO_UPDATE_CHECK", "1")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    yield work


@pytest.fixture(autouse=True)
def _fixed_cli_width(monkeypatch: pytest.MonkeyPatch):
    """Render help and output without terminal styling at a fixed width."""
    import rich_click
    from cu_cli.output import console, result_console

    monkeypatch.setattr(rich_click.rich_click, "FORCE_TERMINAL", False, raising=False)
    monkeypatch.setattr(rich_click.rich_click, "WIDTH", 100, raising=False)
    monkeypatch.setattr(rich_click.rich_click, "MAX_WIDTH", 100, raising=False)
    for output_console in (console, result_console):
        monkeypatch.setattr(output_console, "_force_terminal", False)
        monkeypatch.setattr(output_console, "_color_system", None)
        monkeypatch.setattr(output_console, "_width", 100)


@pytest.fixture(autouse=True)
def _offline_playback(monkeypatch: pytest.MonkeyPatch):
    if mode() != "playback":
        return

    def reject_connection(*_args, **_kwargs):
        pytest.fail("documentation tests must not open network connections during playback")

    monkeypatch.setattr(socket.socket, "connect", reject_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_connection)
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("AZURE_CORE_COLLECT_TELEMETRY", "no")


@pytest.fixture(autouse=True)
def _snippet_regions(request: pytest.FixtureRequest):
    function = getattr(request.node, "originalname", None) or request.node.name
    regions = {
        identifier: region for identifier, region in _regions(request.node.path.resolve()).items()
        if region[3] == function
    }
    region_token = snippets._REGIONS.set(regions)
    parts_token = snippets._PARTS.set(request.node.stash.setdefault(_PARTS, {}))
    yield
    snippets._PARTS.reset(parts_token)
    snippets._REGIONS.reset(region_token)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    report = (yield).get_result()
    if report.skipped:
        report.outcome = "failed"
        report.longrepr = (
            f"{item.nodeid}: documentation tests cannot skip; "
            "restore the required fixtures or recordings."
        )
    outcomes = item.stash.setdefault(_OUTCOMES, [])
    outcomes.append(report.outcome)
    if report.when != "teardown" or outcomes != ["passed", "passed", "passed"]:
        return
    published = item.config.stash.setdefault(_PUBLISHED, {}).setdefault(item.path.name, {})
    for identifier, parts in item.stash.get(_PARTS, {}).items():
        if identifier in published:
            report.outcome = "failed"
            report.longrepr = f"{item.nodeid}: Snippet region {identifier!r} ran in more than one test"
            return
        published[identifier] = {
            "language": parts[0]["language"],
            "content": "\n".join(part["content"] for part in parts),
        }


def pytest_sessionfinish(session: pytest.Session):
    if _OUTPUT:
        target = Path(_OUTPUT)
        target.parent.mkdir(parents=True, exist_ok=True)
        published = session.config.stash.get(_PUBLISHED, {})
        target.write_text(json.dumps(published, indent=2) + "\n", encoding="utf-8")


@pytest.fixture
def copy_invoice(_isolate_env: Path):
    """Copy the public sample invoice to the paths used by the examples."""

    def copy(destination: str | Path = "sample_invoice.pdf") -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_PRODUCT_ROOT / "sample_files" / "sample_invoice.pdf", target)
        return target

    return copy


@pytest.fixture
def sample_invoice(copy_invoice) -> Path:
    """Copy the public sample invoice referenced by the documents into the working directory."""
    return copy_invoice()


@pytest.fixture
def cloud_profile(_isolate_env: Path) -> None:
    """Configure the ready default profile that examples after connection setup assume."""
    write_cloud_profile(Path.cwd())


class _SignedInAzureCli:
    def get_token(self, *_scopes, **_kwargs) -> AccessToken:
        return AccessToken("playback-token", int(time.time()) + 3600)


@pytest.fixture
def azure_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for ``az login`` during playback; record/live runs use the real sign-in."""
    if mode() == "playback":
        monkeypatch.setattr(
            "azure.identity.DefaultAzureCredential", lambda *_args, **_kwargs: _SignedInAzureCli(),
        )
