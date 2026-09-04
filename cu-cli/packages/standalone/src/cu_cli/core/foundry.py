"""Foundry endpoint helpers (Click-free, pure).

Small URL helpers shared by ``cu infra generate`` and ``cu profile`` for endpoint
normalization and host-label matching. The az-CLI account-resolution functions
that shell out live in the command modules (they are coupled to
process/environment state); these pure helpers are the reusable core.
"""

from __future__ import annotations

from urllib.parse import urlparse

from ..errors import CuCliError


def endpoint_host(value: str) -> str:
    """Return the lowercased host portion of *value* (no scheme, no trailing /)."""
    parsed = urlparse(value)
    return (parsed.netloc or parsed.path).strip().lower().rstrip("/")


def host_label(host: str) -> str:
    """Return the first dotted label of *host* (e.g. ``x`` from ``x.foo.com``)."""
    return host.split(".", 1)[0].strip().lower()


def normalize_foundry_endpoint(raw: str, *, auth_mode: str | None = None) -> str:
    """Validate and canonicalize an endpoint to ``https://<host>/``.

    Accept any valid HTTPS hostname instead of requiring a specific domain
    suffix, so custom domains are supported.
    """
    candidate = raw.strip()
    if not candidate:
        raise CuCliError("foundry endpoint cannot be empty.")
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme and parsed.scheme.lower() != "https":
        if auth_mode == "login":
            raise CuCliError(
                "authentication mode 'login' requires an HTTPS endpoint.",
                hint="update the endpoint to use https://, or select a different endpoint.",
            )
        raise CuCliError(
            "foundry endpoint must use https.",
            hint="example: https://<account>.services.ai.azure.com/",
        )
    if parsed.username is not None or parsed.password is not None:
        raise CuCliError(
            "foundry endpoint must not include username or password information.",
            hint="provide only the service URL, for example: "
            "https://<account>.services.ai.azure.com/",
        )
    hostname = parsed.hostname
    if hostname is None:
        host = ""
    else:
        host = hostname.lower()
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
    if not host or "." not in host:
        raise CuCliError(
            f"invalid foundry endpoint '{raw}'.",
            hint="example: https://<account>.services.ai.azure.com/",
        )
    return f"https://{host}/"
