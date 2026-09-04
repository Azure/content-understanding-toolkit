# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Update source abstraction used by the shared upgrade workflow."""

from __future__ import annotations

import json
import sys
from importlib.metadata import entry_points
from typing import Mapping, Protocol, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PYPI_URL = "https://pypi.org/pypi/cu-cli/json"
RELEASE_NOTES_URL = "https://github.com/Azure/content-understanding-toolkit/releases"
SOURCE_INSTALL_HINT = (
    "git clone https://github.com/Azure/content-understanding-toolkit && "
    "pip install -e content-understanding-toolkit/cu-cli"
)
_NETWORK_TIMEOUT = 1.5


class UpdateProvider(Protocol):
    """Supply release discovery and pip configuration to the upgrade engine."""

    name: str
    release_notes_url: str
    source_install_hint: str

    def fetch_latest_version(self) -> Tuple[str | None, str]: ...

    def pip_environment(self) -> Mapping[str, str]: ...


class PyPIUpdateProvider:
    """Default update provider for public releases."""

    name = "PyPI"
    release_notes_url = RELEASE_NOTES_URL
    source_install_hint = SOURCE_INSTALL_HINT

    def fetch_latest_version(self) -> Tuple[str | None, str]:
        try:
            req = Request(PYPI_URL, headers={"Accept": "application/json"})
            with urlopen(req, timeout=_NETWORK_TIMEOUT) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
            latest = payload.get("info", {}).get("version")
            return (latest, "ok") if latest else (None, "network_error")
        except HTTPError as exc:
            return None, "not_published" if exc.code == 404 else "network_error"
        except Exception:
            return None, "network_error"

    def pip_environment(self) -> Mapping[str, str]:
        return {}


def get_update_provider() -> UpdateProvider:
    """Load one installed update-provider extension, or use public PyPI."""
    providers = list(entry_points(group="cu_cli.update_providers"))
    if not providers:
        return PyPIUpdateProvider()
    if len(providers) != 1:
        names = ", ".join(sorted(provider.name for provider in providers))
        raise RuntimeError(f"Expected one cu-cli update provider, found: {names}")
    provider = providers[0].load()()
    if not all(
        hasattr(provider, attribute)
        for attribute in (
            "name",
            "release_notes_url",
            "source_install_hint",
            "fetch_latest_version",
            "pip_environment",
        )
    ):
        raise RuntimeError(f"Invalid cu-cli update provider: {providers[0].name}")
    return provider


def pip_install_args(latest: str) -> list[str]:
    """Return the shared, exact-version pip upgrade arguments."""
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        f"cu-cli=={latest}",
    ]
