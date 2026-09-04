# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from importlib.metadata import version

import pytest

from cu_cli_core import __version__

pytestmark = pytest.mark.unit


def test_runtime_version_matches_package_metadata():
    assert __version__ == version("cu-cli-core")
