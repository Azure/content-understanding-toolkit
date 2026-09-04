# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared Click option decorators and small render helpers for commands.

This is command-layer (Click) glue, deliberately kept out of ``cu_cli.core``.
It removes the auth-option boilerplate that was duplicated across the
``analyzer`` and ``defaults`` command groups.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterator

import rich_click as click

from ..output import console
from ..apiversion import API_VERSION_HELP

_COMMAND_STARTED_META_KEY = "cu_command_started"


def _record_command_start(ctx: click.Context, _param: Any, value: bool) -> bool:
    if value:
        ctx.meta[_COMMAND_STARTED_META_KEY] = perf_counter()
    return value


CALLING_TIME_OPTION = click.option(
    "--time",
    "show_calling_time",
    is_flag=True,
    callback=_record_command_start,
    help="Show elapsed CU service and total command time on stderr.",
)

AUTH_OPTIONS = [
    click.option("--endpoint", default=None, help="Override configured endpoint."),
    click.option("--api-key", default=None, help="Override configured API key."),
    click.option("--api-version", "api_version", default=None,
                 help=API_VERSION_HELP),
    click.option(
        "--auth-mode",
        "entra",
        type=click.Choice(["login", "key"]),
        default=None,
        help="Authentication mode; defaults to the selected CU CLI profile.",
    ),
    click.option("-p", "--profile", "profile_name", default=None,
                 help="Named CU CLI profile to use (from cu profile)."),
    click.option("--info", "show_runtime_context", is_flag=True,
                 help="Print resolved endpoint/auth/api-version/profile before execution."),
    CALLING_TIME_OPTION,
]


def with_auth_options(fn):
    """Attach the standard endpoint/auth/API/config/info/time options."""
    for opt in reversed(AUTH_OPTIONS):
        fn = opt(fn)
    return fn


@contextmanager
def calling_time(enabled: bool) -> Iterator[CallingTimer]:
    """Measure a CU service operation; callers choose the final render point."""
    timer = CallingTimer(enabled=enabled)
    started = perf_counter()
    try:
        yield timer
    finally:
        timer.elapsed = perf_counter() - started


@dataclass
class CallingTimer:
    """Elapsed CU service time that can be rendered after command output."""

    enabled: bool
    elapsed: float | None = None

    def print(self) -> None:
        if self.enabled and self.elapsed is not None:
            ctx = click.get_current_context(silent=True)
            command_started = (
                ctx.meta.get(_COMMAND_STARTED_META_KEY)
                if ctx is not None
                else None
            )
            console.print("\n")
            console.print(
                f"[bold cyan]CU service calling time:[/bold cyan] {self.elapsed:.3f}s",
                highlight=False,
            )
            if isinstance(command_started, (int, float)):
                total_elapsed = perf_counter() - command_started
                console.print(
                    f"[bold cyan]Total command time:[/bold cyan] {total_elapsed:.3f}s",
                    highlight=False,
                )


def print_runtime_context(auth: Any, profile: Any) -> None:
    """Print the resolved endpoint/auth/API version/profile (the ``--info`` block)."""
    console.print(f"[bold]endpoint:[/bold] {auth.endpoint}")
    console.print(f"[bold]auth mode:[/bold] {auth.auth_mode}")
    console.print(f"[bold]api-version:[/bold] {auth.api_version}")
    console.print(f"[bold]CU CLI profile:[/bold] {profile.profile_name}")
    console.print(f"[bold]settings:[/bold] {profile.path}")
