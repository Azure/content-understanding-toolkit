"""Telemetry.

The CLI's only telemetry is the Azure-SDK ``User-Agent`` header on CU service
calls. The CLI stamps an application-id prefix ``cu-cli/<version>`` for adoption
attribution; the Azure SDK (azure-core) then appends its standard
``azsdk-python-<package>/<version> Python/<version> (<platform>)`` identifier.
**No customer content, and no usage/analytics data, is collected.**

``CU_TELEMETRY=off`` (or ``0``/``false``/``no``) drops only the ``cu-cli``
prefix. It does **not** (and cannot) remove the Azure SDK's own
``azsdk-python-...`` User-Agent — azure-core always sends one, per the Azure SDK
telemetry policy (https://azure.github.io/azure-sdk/general_azurecore.html). To
customize the header further, use the standard azure-core ``AZURE_HTTP_USER_AGENT``
environment variable, which the SDK appends.
"""

from __future__ import annotations

import os

from . import __version__

USER_AGENT = f"cu-cli/{__version__}"
_OPT_OUT_VALUES = {"off", "0", "false", "no"}


def telemetry_enabled() -> bool:
    return os.getenv("CU_TELEMETRY", "on").strip().lower() not in _OPT_OUT_VALUES


def user_agent() -> str:
    """The ``User-Agent`` prefix stamped on CU API calls (respecting opt-out).

    When opted out we return an empty prefix. azure-core never sends an empty
    header — it falls back to its standard ``azsdk-python-...`` User-Agent, so
    the request carries no ``cu-cli`` marker and is stable across cu-cli
    versions.
    """
    return USER_AGENT if telemetry_enabled() else ""
