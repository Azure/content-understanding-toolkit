"""Build a ContentUnderstandingClient honoring config precedence + api-version.

The CLI is cloud-only: every client build requires an endpoint. The
``User-Agent`` telemetry header is stamped here so
every CU call carries it (opt-out honored — see ``telemetry.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from cu_cli_core.client import (
    LRO_POLLING_INTERVAL_SECONDS,
    build_content_understanding_client,
)

from .apiversion import ensure_supported
from .core.foundry import normalize_foundry_endpoint
from .profile import Profile
from .errors import CuCliError
from .telemetry import user_agent

@dataclass
class ResolvedAuth:
    endpoint: str
    auth_mode: str  # "entra" | "key"
    api_version: str
    api_key: Optional[str] = None


def resolve(
    profile: Profile,
    *,
    endpoint_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
    api_version_override: Optional[str] = None,
    force_entra: bool | str = False,
    auth_mode_override: Optional[str] = None,
) -> ResolvedAuth:
    endpoint = endpoint_override or profile.endpoint
    if not endpoint:
        raise CuCliError(
            f"No CU endpoint configured for CU CLI profile '{profile.profile_name}'.",
            hint="set one with `cu profile set endpoint <URL>`, select another saved "
                 "CU CLI profile with `cu profile set-active <name>`, or pass "
                 "`--endpoint`. Run `cu profile show` to inspect the effective profile.",
        )

    api_version = ensure_supported(api_version_override or profile.api_version)

    requested_mode = auth_mode_override
    if requested_mode is None and isinstance(force_entra, str):
        requested_mode = force_entra
    elif requested_mode is None and force_entra:
        requested_mode = "login"

    endpoint = normalize_foundry_endpoint(
        endpoint,
        auth_mode=requested_mode or profile.auth_mode,
    )

    if requested_mode == "login":
        return ResolvedAuth(endpoint=endpoint, auth_mode="entra",
                            api_version=api_version, api_key=None)
    if api_key_override or requested_mode == "key":
        key = api_key_override or profile.api_key
        if not key:
            raise CuCliError(
                "--auth-mode key requires an API key.",
                hint="pass --api-key or configure api_key in the selected CU CLI profile.",
            )
        return ResolvedAuth(endpoint=endpoint, auth_mode="key",
                            api_version=api_version, api_key=key)
    if profile.auth_mode == "key":
        if not profile.api_key:
            raise CuCliError(
                "auth is 'key' but no api_key is configured.",
                hint="run 'cu profile set api_key <KEY>' or switch to login auth with "
                     "'cu profile set auth_mode login' (then 'az login').",
            )
        return ResolvedAuth(endpoint=endpoint, auth_mode="key",
                            api_version=api_version, api_key=profile.api_key)
    return ResolvedAuth(endpoint=endpoint, auth_mode="entra",
                        api_version=api_version, api_key=None)


def build_client(
    profile: Profile,
    *,
    endpoint_override: Optional[str] = None,
    api_key_override: Optional[str] = None,
    api_version_override: Optional[str] = None,
    force_entra: bool | str = False,
    auth_mode_override: Optional[str] = None,
) -> Any:
    """Construct a ``ContentUnderstandingClient`` for the resolved auth/version."""
    from azure.core.credentials import AzureKeyCredential
    from azure.identity import DefaultAzureCredential

    if api_key_override:
        # The value came from --api-key on argv, which is visible to `ps` and
        # recorded in shell history. Nudge users toward safer alternatives.
        from .output import console
        console.print(
            "[yellow]warning:[/yellow] --api-key on the command line is visible via "
            "`ps`/shell history. Prefer the CU_API_KEY env var or "
            "`cu profile set api_key`."
        )
        if force_entra is True or force_entra == "login" or auth_mode_override == "login":
            console.print(
                "[dim]note:[/dim] --auth-mode login overrides --api-key; "
                "the provided key is ignored."
            )

    auth = resolve(
        profile,
        endpoint_override=endpoint_override,
        api_key_override=api_key_override,
        api_version_override=api_version_override,
        force_entra=force_entra,
        auth_mode_override=auth_mode_override,
    )
    credential = (
        AzureKeyCredential(auth.api_key or "")
        if auth.auth_mode == "key"
        else DefaultAzureCredential()
    )
    return build_content_understanding_client(
        endpoint=auth.endpoint,
        credential=credential,
        api_version=auth.api_version,
        user_agent=user_agent(),
        polling_interval=LRO_POLLING_INTERVAL_SECONDS,
    )
