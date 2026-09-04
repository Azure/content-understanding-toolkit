# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Package update check.

Follows the pip convention: compare the installed version against the latest
version from the installed update provider and, when a newer one exists, prompt
the user to upgrade with the exact command and a release-notes pointer. The
public default provider uses PyPI. **Never auto-updates.** The check is cached
and also runs implicitly at the end of every command.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Tuple

from packaging.version import InvalidVersion, Version

from . import __version__
from .update_provider import (
    RELEASE_NOTES_URL,
    get_update_provider,
)
_CACHE_PATH = Path.home() / ".cu" / ".update-check.json"
_CACHE_TTL_SECONDS = 24 * 60 * 60
_NETWORK_TIMEOUT = 1.5


def _checks_disabled() -> bool:
    return os.getenv("CU_NO_UPDATE_CHECK", "").strip().lower() in {"1", "true", "yes", "on"}


def _read_cache(provider_name: str) -> tuple[bool, Optional[str]]:
    try:
        import json

        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        if data.get("provider") != provider_name:
            return False, None

        last_attempt = float(data.get("last_attempt_timestamp", 0))
        if time.time() - last_attempt >= _CACHE_TTL_SECONDS:
            return False, None

        latest = data.get("latest")
        if isinstance(latest, str) and latest:
            return True, latest
        return True, None
    except Exception:
        return False, None


def _write_cache(provider_name: str, latest: Optional[str]) -> None:
    try:
        import json

        now = time.time()
        data: dict[str, object] = {}
        try:
            existing = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and existing.get("provider") == provider_name:
                data = existing
        except (OSError, ValueError):
            pass

        data.update(
            {
                "provider": provider_name,
                "last_attempt_timestamp": now,
            }
        )
        if latest:
            data["latest"] = latest
            data["last_success_timestamp"] = now

        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(data),
            encoding="utf-8",
        )
    except Exception:
        pass


def fetch_latest_version(*, use_cache: bool = True) -> Optional[str]:
    """Return the latest ``cu-cli`` version, or ``None`` on any failure.

    Network failures are swallowed so an update check never breaks a command.
    """
    return fetch_latest_version_detailed(use_cache=use_cache)[0]


def fetch_latest_version_detailed(*, use_cache: bool = True) -> Tuple[Optional[str], str]:
    """Like :func:`fetch_latest_version` but also return a reason code.

    Reason is one of ``"ok"``, ``"disabled"``, ``"not_published"``, or
    ``"network_error"`` so callers can give accurate, non-misleading advice.
    """
    if _checks_disabled():
        return None, "disabled"
    provider = get_update_provider()
    if use_cache:
        is_recent, latest = _read_cache(provider.name)
        if is_recent:
            return latest, "ok" if latest else "network_error"
    latest, reason = provider.fetch_latest_version()
    _write_cache(provider.name, latest)
    return latest, reason


def _parse(version: str) -> tuple:
    parts = []
    for chunk in version.split(".")[:3]:
        num = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer(latest: Optional[str], current: str = __version__) -> bool:
    if not latest:
        return False
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        # Fallback for any unexpected non-PEP440 version strings.
        return _parse(latest) > _parse(current)
    except Exception:
        return False


def upgrade_hint(latest: str, release_notes_url: str = RELEASE_NOTES_URL) -> str:
    return (
        f"A new release of cu-cli is available: {__version__} -> {latest}.\n"
        f"  Upgrade with:  cu upgrade\n"
        f"  Release notes: {release_notes_url}"
    )


def maybe_notify(*, stream=None) -> None:
    """Implicit end-of-command check. Cached + time-limited; never blocks long."""
    if _checks_disabled():
        return
    latest = fetch_latest_version(use_cache=True)
    if latest and is_newer(latest):
        from .output import console
        provider = get_update_provider()
        console.print(
            f"[dim]{upgrade_hint(latest, provider.release_notes_url)}[/dim]"
        )
