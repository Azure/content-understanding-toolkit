# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path
import shutil
import subprocess

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.skipif(os.name == "nt", reason="POSIX stubs")]

HOOKS = Path(str(resources.files("cu_cli_core").joinpath("resources/azd_template/hooks")))


def _command(path: Path, log: Path, label: str) -> None:
    path.write_text(
        f'#!/bin/sh\nprintf \'%s\\n\' "{label} $*" >> \'{log}\'\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


@pytest.mark.parametrize(
    ("frontends", "expected"),
    [
        (("cu-cli", "az"), "standalone _infra-postprovision-v1"),
        (("cu",), "standalone _infra-postprovision-v1"),
        (("az",), "azure cu infra _postprovision-v1"),
    ],
)
def test_posix_launcher_selects_one_available_frontend(tmp_path, frontends, expected):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls"
    for frontend in frontends:
        _command(bin_dir / frontend, log, "azure" if frontend == "az" else "standalone")

    result = subprocess.run(
        ["/bin/sh", str(HOOKS / "postprovision.sh")],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert log.read_text(encoding="utf-8").strip() == expected


def test_posix_launcher_fails_when_no_frontend_is_installed(tmp_path):
    result = subprocess.run(
        ["/bin/sh", str(HOOKS / "postprovision.sh")],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0


def test_launchers_are_policy_free_and_reference_both_frontends():
    posix = (HOOKS / "postprovision.sh").read_text(encoding="utf-8")
    powershell = (HOOKS / "postprovision.ps1").read_text(encoding="utf-8")
    for content in (posix, powershell):
        assert "_infra-postprovision-v1" in content
        assert "_postprovision-v1" in content
    assert shutil.which("pwsh") is None or "exit $LASTEXITCODE" in powershell
