# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared pytest fixtures.

CU profiles and the cwd are isolated from developer settings. Offline tests
also isolate login directories; live tests retain the real credential environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from runpy import run_path
import shlex
import socket

import pytest

from support import command_catalog
from support.command_catalog import CommandCatalog, _ACTIVE, _REGIONS


_CATALOG = pytest.StashKey[CommandCatalog]()
_CATALOG_PATH = pytest.StashKey[Path]()
_MATRIX_PATH = pytest.StashKey[Path]()
_DOCUMENTATION_TESTS = pytest.StashKey[set[tuple[Path, str]]]()
_REGION_SOURCES = pytest.StashKey[dict]()
_TEST_ROOT = Path(__file__).parent
_DOC_SCRIPT = Path(command_catalog.__file__).resolve().parents[4] / "scripts" / "update-snippet.py"
_DISCOVERY = run_path(str(_DOC_SCRIPT))
discover_snippet_regions = _DISCOVERY["discover_snippet_regions"]


def pytest_addoption(parser):
    parser.addoption("--command-catalog", metavar="PATH", help="Export tested CLI invocations.")
    parser.addoption("--command-matrix", metavar="PATH", help="Export the command coverage matrix.")
    parser.addoption(
        "--require-command-coverage", action="store_true",
        help="Fail on public commands or option spellings without non-help test invocations.",
    )


def pytest_configure(config):
    target = config.getoption("--command-catalog")
    if target:
        config.stash[_CATALOG_PATH] = Path(target).resolve()
    matrix = config.getoption("--command-matrix")
    if matrix:
        if not target:
            raise pytest.UsageError("--command-matrix requires --command-catalog")
        config.stash[_MATRIX_PATH] = Path(matrix).resolve()
    if config.getoption("--require-command-coverage") and not target:
        raise pytest.UsageError("--require-command-coverage requires --command-catalog")


def pytest_collection_finish(session):
    try:
        regions = discover_snippet_regions(_TEST_ROOT)
    except (OSError, SyntaxError, ValueError) as exc:
        raise pytest.UsageError(f"Cannot discover documentation sources: {exc}") from exc
    session.config.stash[_REGION_SOURCES] = regions
    session.config.stash[_DOCUMENTATION_TESTS] = {
        (path.resolve(), function) for path, _start, _end, function in regions.values()
    }
    if _CATALOG_PATH in session.config.stash:
        from cu_cli.cli import main

        session.config.stash[_CATALOG] = CommandCatalog(main)


def _case_id(item) -> str:
    return f"{item.path.relative_to(_TEST_ROOT).as_posix()}::{item.name}"


def _is_documentation_source(item) -> bool:
    function = getattr(item, "originalname", None) or item.name
    return (item.path.resolve(), function) in item.config.stash.get(_DOCUMENTATION_TESTS, set())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if (
        report.skipped
        and _is_documentation_source(item)
        and _CATALOG in item.config.stash
    ):
        report.outcome = "failed"
        report.longrepr = (
            str(item.path), item.location[1],
            "Documentation source tests cannot skip; restore required fixtures or recordings.",
        )
    if _CATALOG in item.config.stash:
        catalog = item.config.stash[_CATALOG]
        catalog.outcomes.setdefault(_case_id(item), []).append(report.outcome)


def pytest_sessionfinish(session):
    if _CATALOG in session.config.stash:
        session.config.stash[_CATALOG].export(session.config.stash[_CATALOG_PATH])
        if _MATRIX_PATH in session.config.stash:
            target = session.config.stash[_MATRIX_PATH]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(session.config.stash[_CATALOG].matrix(), encoding="utf-8")
        if session.config.getoption("--require-command-coverage"):
            gaps = session.config.stash[_CATALOG].invocation_gaps()
            if gaps:
                reporter = session.config.pluginmanager.get_plugin("terminalreporter")
                if reporter:
                    reporter.write_sep("=", "Command invocation coverage gaps")
                    for gap in gaps:
                        reporter.write_line(gap)
                session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(autouse=True)
def _block_documentation_network(request, monkeypatch):
    if not _is_documentation_source(request.node):
        return
    if (os.getenv("CU_TEST_REC_MODE") or "playback").strip().lower() != "playback":
        return

    def reject_connection(*_args, **_kwargs):
        pytest.fail("documentation examples must not open live network connections")

    monkeypatch.setattr(socket.socket, "connect", reject_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_connection)
    monkeypatch.setenv("AZURE_CORE_COLLECT_TELEMETRY", "no")


@pytest.fixture(autouse=True)
def _capture_snippet_regions(request):
    function = getattr(request.node, "originalname", None) or request.node.name
    regions = {
        identifier: region for identifier, region in request.config.stash.get(_REGION_SOURCES, {}).items()
        if region[0].resolve() == request.node.path.resolve() and region[3] == function
    }
    token = _REGIONS.set(regions)
    try:
        yield
    finally:
        _REGIONS.reset(token)


@pytest.fixture(autouse=True)
def _capture_cli_calls(request, monkeypatch):
    if _CATALOG not in request.config.stash:
        yield
        return
    from click.testing import CliRunner
    from cu_cli.cli import main

    catalog = request.config.stash[_CATALOG]
    test = _case_id(request.node)
    original = CliRunner.invoke

    def invoke(runner, cli, args=None, **kwargs):
        result = original(runner, cli, args, **kwargs)
        if cli is main:
            arguments = shlex.split(args) if isinstance(args, str) else list(args or ())
            catalog.record_call(test, arguments, result.exit_code)
        return result

    token = _ACTIVE.set((catalog, test))
    monkeypatch.setattr(CliRunner, "invoke", invoke)
    yield
    _ACTIVE.reset(token)


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from cu_cli import profile as standalone_profile

    original_home = Path.home()
    original_azure_config_dir = os.getenv("AZURE_CONFIG_DIR") or str(original_home / ".azure")
    rec_mode = (os.getenv("CU_TEST_REC_MODE") or "playback").strip().lower()
    home = tmp_path / "home"
    home.mkdir()
    if rec_mode not in {"live", "record"}:
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    isolated_config = home / ".azure" / "config"
    monkeypatch.setattr(
        "cu_cli_core.profiles.azure_config_path",
        lambda: isolated_config,
    )
    monkeypatch.setattr(standalone_profile, "azure_config_path", lambda: isolated_config)
    # In live/record mode, keep Azure CLI pointed at the real login cache so
    # AzureCliCredential can obtain tokens after `az login`. ProfileStore remains
    # patched to the isolated path above and never mutates the real config.
    if rec_mode in {"live", "record"}:
        monkeypatch.setenv("AZURE_CONFIG_DIR", original_azure_config_dir)
    else:
        monkeypatch.setenv("AZURE_CONFIG_DIR", str(home / ".azure"))
    # Strip any CU_* env so tests control precedence explicitly, but preserve
    # the CU_TEST_REC_* recording-harness vars (record/live modes rely on them).
    for key in list(os.environ):
        if key.startswith("CU_TEST_REC_"):
            continue
        if key.startswith("CU_") or key.startswith("CONTENTUNDERSTANDING_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CU_NO_UPDATE_CHECK", "1")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    yield work


@pytest.fixture(autouse=True)
def _fixed_cli_width(monkeypatch: pytest.MonkeyPatch):
    """Pin rich-click rendering so CLI-output assertions are deterministic.

    Rich derives the console width from the real std streams — a TTY locally
    (capped at ``MAX_WIDTH``) but none in CI, where it falls back to 80. That
    changes wrapping, while GitHub Actions forces terminal styling that inserts
    ANSI sequences into captured output. Disable terminal styling and force a
    fixed width so local and CI render identically.
    """
    import rich_click
    from cu_cli.output import console, result_console

    monkeypatch.setattr(rich_click.rich_click, "FORCE_TERMINAL", False, raising=False)
    monkeypatch.setattr(rich_click.rich_click, "WIDTH", 100, raising=False)
    monkeypatch.setattr(rich_click.rich_click, "MAX_WIDTH", 100, raising=False)
    for output_console in (console, result_console):
        monkeypatch.setattr(output_console, "_force_terminal", False)
        monkeypatch.setattr(output_console, "_color_system", None)
        monkeypatch.setattr(output_console, "_width", 100)
