# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pathlib import Path

import pytest

from azext_content_understanding import _infra
from cu_cli_core.infra import materialize_project

from .test_infra import _choices

pytestmark = pytest.mark.unit


def test_azure_frontend_materialization_matches_core(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    direct = tmp_path / "direct"

    _infra._write_project(frontend, _choices(), force=False)
    materialize_project(direct, _choices(), force=False)

    frontend_files = {
        path.relative_to(frontend): path.read_bytes()
        for path in frontend.rglob("*")
        if path.is_file()
    }
    direct_files = {
        path.relative_to(direct): path.read_bytes()
        for path in direct.rglob("*")
        if path.is_file()
    }
    assert frontend_files == direct_files