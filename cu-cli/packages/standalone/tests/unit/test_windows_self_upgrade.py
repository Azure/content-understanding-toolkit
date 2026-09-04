# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for the Windows detached self-upgrade helper."""
from __future__ import annotations

import json

from cu_cli import windows_self_upgrade as wsu


def test_write_helper_files_writes_script_and_config(tmp_path, monkeypatch):
    monkeypatch.setattr(wsu.tempfile, "gettempdir", lambda: str(tmp_path))
    script_path = wsu.write_helper_files(
        parent_pid=1234,
        upgrade_args=["python", "-m", "pip", "install", "--upgrade", "cu-cli==9.9.9"],
        rollback_args=["python", "-m", "pip", "install", "--force-reinstall", "cu-cli==0.1.0"],
        env_overrides={"PIP_INDEX_URL": "https://example.test/simple/"},
        log_path=tmp_path / "upgrade.log",
    )

    assert script_path.exists()
    config_path = script_path.with_suffix(".json")
    assert config_path.exists()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["parent_pid"] == 1234
    assert config["upgrade_args"][-1] == "cu-cli==9.9.9"
    assert config["rollback_args"][-1] == "cu-cli==0.1.0"
    assert config["env_overrides"]["PIP_INDEX_URL"] == "https://example.test/simple/"
    assert config["log_path"] == str(tmp_path / "upgrade.log")

    # The helper script must not import cu_cli: it has to keep working even
    # while the cu-cli package itself is mid-uninstall/reinstall.
    source = script_path.read_text(encoding="utf-8")
    assert "import cu_cli" not in source
    assert "from cu_cli" not in source


def test_run_windows_upgrade_spawns_detached_and_returns_success(tmp_path):
    written = {}
    launched = {}

    def fake_write(**kwargs):
        written.update(kwargs)
        return tmp_path / "cu_upgrade_helper.py"

    def fake_launch(python_exe, script_path):
        launched["python_exe"] = python_exe
        launched["script_path"] = script_path
        return object()

    exit_code, log_path = wsu.run_windows_upgrade(
        current_version="0.1.0",
        core_version="0.1.0",
        pip_args=["python", "-m", "pip", "install", "--upgrade", "cu-cli==9.9.9"],
        pip_env={},
        python_exe="python",
        parent_pid=4321,
        write_helper=fake_write,
        launch=fake_launch,
        log_path=tmp_path / "upgrade.log",
    )

    assert exit_code == 0
    assert log_path == tmp_path / "upgrade.log"
    assert written["parent_pid"] == 4321
    assert written["upgrade_args"][-1] == "cu-cli==9.9.9"
    assert written["rollback_args"][-2] == "cu-cli==0.1.0"
    assert written["rollback_args"][-1] == "cu-cli-core==0.1.0"
    assert launched["python_exe"] == "python"
    assert launched["script_path"] == tmp_path / "cu_upgrade_helper.py"


def test_rollback_args_include_core_version_when_known():
    args = wsu._rollback_args("python", "0.1.0", "0.2.0")
    assert args == [
        "python",
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "cu-cli==0.1.0",
        "cu-cli-core==0.2.0",
    ]


def test_rollback_args_omit_core_version_when_unknown():
    args = wsu._rollback_args("python", "0.1.0", None)
    assert args == [
        "python",
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "cu-cli==0.1.0",
    ]


def test_is_windows_reflects_sys_platform(monkeypatch):
    monkeypatch.setattr(wsu.sys, "platform", "win32")
    assert wsu.is_windows() is True
    monkeypatch.setattr(wsu.sys, "platform", "linux")
    assert wsu.is_windows() is False
    monkeypatch.setattr(wsu.sys, "platform", "darwin")
    assert wsu.is_windows() is False
