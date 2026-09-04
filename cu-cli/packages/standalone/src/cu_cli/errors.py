"""Friendly error handling for CLI commands.

``CuCliError`` is a ``ClickException`` that prints a single-line ``error:`` with
an optional ``hint:`` and honors the exit-code convention in ``exit_codes.py``.
The ``friendly_errors`` decorator turns raw SDK / network / filesystem
exceptions into clean, actionable CLI errors.
"""

from __future__ import annotations

import functools
import sys
from typing import Callable, Optional

import click
from cu_cli_core.errors import CuCoreError, UsageError, ValidationError
from rich.console import Console

from .exit_codes import GENERIC_ERROR, VALIDATION_FAILURE

err_console = Console(stderr=True)


class CuCliError(click.ClickException):
    """A clean, single-line CLI error with an optional hint."""

    def __init__(self, message: str, hint: Optional[str] = None, exit_code: int = GENERIC_ERROR):
        super().__init__(message)
        self.hint = hint
        self.exit_code = exit_code

    def show(self, file=None) -> None:  # type: ignore[override]
        err_console.print(f"[bold red]error:[/bold red] {self.message}")
        if self.hint:
            err_console.print(f"[dim]hint:[/dim] {self.hint}")

    def format_message(self) -> str:  # type: ignore[override]
        """Render the message together with the hint.

        rich-click renders a ``ClickException`` through ``format_message`` (see
        ``write_error``), **not** through our ``show`` override — so a hint
        placed only in ``show`` is silently dropped in the CLI's error panel.
        Embedding it here guarantees the resolution guidance always reaches the
        user (reported previously).
        """
        if self.hint:
            return f"{self.message}\nhint: {self.hint}"
        return self.message


def _attr(obj: object, key: str) -> object:
    """Read *key* from a mapping or an object (SDK errors mix both shapes)."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _walk_service_error(node: object, lines: list, indent: int) -> None:
    """Append ``code: message`` lines from an (inner)error node and its details.

    The CU service nests the actionable failure under ``error.innererror`` (a
    mapping) with an optional ``details`` list; each detail carries its own
    ``code``/``message``/``target``. The top-level ``error.message`` is only a
    generic string (e.g. ``"Invalid Request."``), so we surface the nested
    detail instead of dropping it.
    """
    if node is None:
        return
    code = _attr(node, "code")
    message = _attr(node, "message")
    if code or message:
        pad = "  " * indent
        label = f"{code}: " if code else ""
        lines.append(f"{pad}{label}{message or ''}".rstrip())
    details = _attr(node, "details") or []
    if isinstance(details, (list, tuple)):
        for d in details:
            dcode = _attr(d, "code")
            dtarget = _attr(d, "target")
            dmsg = _attr(d, "message")
            pad = "  " * (indent + 1)
            loc = f" ({dtarget})" if dtarget else ""
            label = f"{dcode}{loc}: " if dcode else (f"({dtarget}) " if dtarget else "")
            lines.append(f"{pad}{label}{dmsg or ''}".rstrip())
    _walk_service_error(_attr(node, "innererror"), lines, indent + 1)


def _format_service_error(exc: object) -> str:
    """Build a multi-line message that surfaces the SDK's inner error details."""
    status = _attr(exc, "status_code") or "?"
    err = _attr(exc, "error")
    top_code = _attr(err, "code")
    top_msg = _attr(err, "message") or _attr(exc, "message") or str(exc)
    head = f"service responded {status}"
    if top_code:
        head += f" ({top_code})"
    lines = [f"{head}: {top_msg}"]
    _walk_service_error(_attr(err, "innererror"), lines, 1)
    top_details = _attr(err, "details") or []
    if isinstance(top_details, (list, tuple)):
        for d in top_details:
            _walk_service_error(d, lines, 1)
    return "\n".join(lines)


def friendly_errors(fn: Callable) -> Callable:
    """Decorator: turn SDK / network exceptions into clean CLI errors."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except CuCoreError as exc:
            exit_code = (
                VALIDATION_FAILURE
                if isinstance(exc, (UsageError, ValidationError))
                else GENERIC_ERROR
            )
            raise CuCliError(exc.message, hint=exc.hint, exit_code=exit_code) from exc
        except CuCliError:
            raise
        except click.ClickException:
            raise
        except click.exceptions.Abort:
            raise
        except KeyboardInterrupt:
            err_console.print("[yellow]aborted[/yellow]")
            sys.exit(130)
        except FileNotFoundError as exc:
            raise CuCliError(
                f"file not found: {exc.filename or exc}",
                hint="check the path; globs that match no files are reported.",
            ) from exc
        except PermissionError as exc:
            raise CuCliError(f"permission denied: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — translate to a friendly error
            try:
                from azure.core.exceptions import (
                    ClientAuthenticationError,
                    HttpResponseError,
                    ServiceRequestError,
                )
            except Exception:  # pragma: no cover - azure always present at runtime
                ClientAuthenticationError = HttpResponseError = ServiceRequestError = ()  # type: ignore

            if isinstance(exc, ClientAuthenticationError):
                raise CuCliError(
                    "Authentication failed. Run 'cu doctor' to diagnose, or "
                    "'az login' to re-authenticate.",
                ) from exc
            if isinstance(exc, HttpResponseError):
                status = getattr(exc, "status_code", None)
                # For client (4xx) errors the surfaced inner detail *is* the
                # actionable guidance; a 'cu doctor' nudge only makes sense for
                # auth/connectivity/service (non-4xx) failures.
                client_error = isinstance(status, int) and 400 <= status < 500
                raise CuCliError(
                    _format_service_error(exc),
                    hint=None if client_error else
                    "run 'cu doctor' to verify endpoint, auth, and model deployments.",
                ) from exc
            if isinstance(exc, ServiceRequestError):
                raise CuCliError(
                    f"Could not reach the endpoint: {exc}. Check the URL and your "
                    "network. 'cu doctor' can verify connectivity.",
                ) from exc
            raise CuCliError(f"unexpected error: {exc}") from exc

    return wrapper
