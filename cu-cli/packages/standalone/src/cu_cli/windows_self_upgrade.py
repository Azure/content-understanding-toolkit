# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Windows-only detached self-upgrade helper.

On Windows, a running ``cu.exe`` holds an exclusive file lock on its own
executable image. ``pip install --upgrade`` is non-atomic (uninstall, then
install); if the install step cannot replace the locked ``cu.exe``, the
uninstall has already completed and the environment is left with no
importable ``cu_cli`` module at all.

POSIX allows unlinking/replacing a file that is currently executing, so this
failure mode is Windows-specific — the fix below is only exercised there.

The fix: don't run pip synchronously from inside ``cu.exe``. Instead, write a
small, dependency-free helper script to disk and launch it as a fully
detached process, then let ``cu.exe`` return control to the shell (and exit)
immediately. The helper:

1. waits for the original ``cu.exe`` process to actually exit, releasing the
   file lock;
2. runs ``pip install --upgrade`` for the target version, retrying a few
   times in case another handle (AV scanning, indexing) still holds the file
   briefly;
3. rolls back to the previously installed, known-good ``cu-cli`` (and
   ``cu-cli-core``) version if the upgrade fails, so the environment is never
   left without an importable CLI;
4. logs progress/outcome to a log file for later inspection.

The helper script intentionally does not import ``cu_cli`` (or any of its
dependencies) — it must keep working even while the ``cu-cli`` package itself
is mid-uninstall/reinstall.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import uuid
from pathlib import Path
from typing import Callable, Mapping, Sequence

_LOG_DIR = Path.home() / ".cu"


def is_windows() -> bool:
    """Return whether the current platform needs the detached-helper path."""
    return sys.platform.startswith("win")


def default_log_path() -> Path:
    return _LOG_DIR / "upgrade.log"


def _rollback_args(python_exe: str, current_version: str, core_version: str | None) -> list[str]:
    args = [
        python_exe,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        f"cu-cli=={current_version}",
    ]
    if core_version:
        args.append(f"cu-cli-core=={core_version}")
    return args


_HELPER_SOURCE = textwrap.dedent(
    '''\
    """Detached helper for `cu upgrade` on Windows (auto-generated, no cu_cli import).

    Do not edit: regenerated on every `cu upgrade`. Safe to delete once the
    logged outcome shows "upgrade succeeded" or "rollback".
    """
    import json
    import os
    import subprocess
    import sys
    import time

    with open(__file__.rsplit(".", 1)[0] + ".json", "r", encoding="utf-8") as _f:
        _CONFIG = json.load(_f)

    PARENT_PID = _CONFIG["parent_pid"]
    UPGRADE_ARGS = _CONFIG["upgrade_args"]
    ROLLBACK_ARGS = _CONFIG["rollback_args"]
    ENV_OVERRIDES = _CONFIG["env_overrides"]
    LOG_PATH = _CONFIG["log_path"]
    WAIT_TIMEOUT_SECONDS = _CONFIG["wait_timeout_seconds"]
    RETRY_ATTEMPTS = _CONFIG["retry_attempts"]
    RETRY_DELAY_SECONDS = _CONFIG["retry_delay_seconds"]


    def _log(message):
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\\n")
        except OSError:
            pass


    def _wait_for_parent_exit(pid, timeout_seconds):
        try:
            import ctypes

            synchronize = 0x00100000
            query_limited = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                synchronize | query_limited, False, pid
            )
            if not handle:
                return  # already exited, or we can't see it: proceed anyway
            try:
                ctypes.windll.kernel32.WaitForSingleObject(
                    handle, int(timeout_seconds * 1000)
                )
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            # Best effort only: if the wait itself fails, fall through and
            # rely on the pip retry loop below.
            time.sleep(2)


    def _run_pip(args, attempts, delay_seconds):
        env = {**os.environ, **ENV_OVERRIDES}
        result = None
        for attempt in range(attempts):
            result = subprocess.run(args, env=env)
            if result.returncode == 0:
                return True
            _log(f"attempt {attempt + 1}/{attempts} failed (exit {result.returncode})")
            time.sleep(delay_seconds)
        return False


    def main():
        _log(f"waiting for parent pid {PARENT_PID} to exit")
        _wait_for_parent_exit(PARENT_PID, WAIT_TIMEOUT_SECONDS)
        _log(f"running: {' '.join(UPGRADE_ARGS)}")
        if _run_pip(UPGRADE_ARGS, RETRY_ATTEMPTS, RETRY_DELAY_SECONDS):
            _log("upgrade succeeded")
            return
        _log("upgrade failed; rolling back to previous version")
        if _run_pip(ROLLBACK_ARGS, RETRY_ATTEMPTS, RETRY_DELAY_SECONDS):
            _log("rollback succeeded; previous cu-cli remains usable")
        else:
            _log(
                "rollback FAILED - manual recovery required: "
                + " ".join(ROLLBACK_ARGS)
            )


    if __name__ == "__main__":
        main()
    '''
)


def write_helper_files(
    *,
    parent_pid: int,
    upgrade_args: Sequence[str],
    rollback_args: Sequence[str],
    env_overrides: Mapping[str, str],
    log_path: Path,
    wait_timeout_seconds: float = 30.0,
    retry_attempts: int = 5,
    retry_delay_seconds: float = 2.0,
) -> Path:
    """Write the helper script + its config to a temp dir; return the script path."""
    run_dir = Path(tempfile.gettempdir()) / f"cu-upgrade-{uuid.uuid4().hex}"
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path = run_dir / "cu_upgrade_helper.py"
    config_path = run_dir / "cu_upgrade_helper.json"

    config = {
        "parent_pid": parent_pid,
        "upgrade_args": list(upgrade_args),
        "rollback_args": list(rollback_args),
        "env_overrides": dict(env_overrides),
        "log_path": str(log_path),
        "wait_timeout_seconds": wait_timeout_seconds,
        "retry_attempts": retry_attempts,
        "retry_delay_seconds": retry_delay_seconds,
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    script_path.write_text(_HELPER_SOURCE, encoding="utf-8")
    return script_path


def launch_detached(python_exe: str, script_path: Path) -> subprocess.Popen:
    """Launch the helper fully detached so it outlives the current process."""
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    return subprocess.Popen(
        [python_exe, str(script_path)],
        creationflags=creationflags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def run_windows_upgrade(
    *,
    current_version: str,
    core_version: str | None,
    pip_args: Sequence[str],
    pip_env: Mapping[str, str],
    python_exe: str | None = None,
    parent_pid: int | None = None,
    write_helper: Callable[..., Path] = write_helper_files,
    launch: Callable[[str, Path], subprocess.Popen] = launch_detached,
    log_path: Path | None = None,
) -> tuple[int, Path]:
    """Start the detached Windows upgrade helper. Returns (exit_code, log_path).

    ``cu upgrade`` cannot synchronously guarantee the final outcome, because
    that would require pip to replace the file backing the process still
    running it. Spawning succeeds, so this returns exit code 0; the actual
    upgrade/rollback result is written to ``log_path``.
    """
    python_exe = python_exe or sys.executable
    parent_pid = parent_pid if parent_pid is not None else os.getpid()
    resolved_log_path = log_path or default_log_path()
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)

    rollback_args = _rollback_args(python_exe, current_version, core_version)
    script_path = write_helper(
        parent_pid=parent_pid,
        upgrade_args=list(pip_args),
        rollback_args=rollback_args,
        env_overrides=pip_env,
        log_path=resolved_log_path,
    )
    launch(python_exe, script_path)
    return 0, resolved_log_path
