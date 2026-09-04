"""``cu upgrade`` — pip-convention self-update helper.

``cu upgrade --check`` reports whether the installed update provider has a newer
release without changing anything. ``cu upgrade`` prints the exact ``pip``
command and, on a TTY, offers to run it. The CLI **never auto-updates** — the
user is always in control.
"""

from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

import rich_click as click

from .. import __version__
from ..errors import friendly_errors
from ..output import console
from ..update_check import fetch_latest_version_detailed, is_newer, upgrade_hint
from ..update_provider import get_update_provider, pip_install_args
from ..windows_self_upgrade import is_windows, run_windows_upgrade


@click.command(
    "upgrade",
    help="Check for and install a newer cu-cli release (never automatic).",
    epilog="[bold cyan]Common commands:[/bold cyan]\n\n"
           "[bold green]cu upgrade[/bold green] [bold cyan]--check[/bold cyan]\n\n"
           "[white]\u00a0\u00a0Check for a newer release without installing it.[/white]\n\n"
           "[bold green]cu upgrade[/bold green]\n\n"
           "[white]\u00a0\u00a0Check for a newer release and offer to install it.[/white]",
)
@click.option("--check", is_flag=True,
              help="Only report whether a newer version exists; don't install.")
@click.option("--yes", is_flag=True, help="Run the upgrade without prompting.")
@friendly_errors
def cmd_upgrade(check: bool, yes: bool) -> None:
    console.print(f"[bold]current:[/bold] cu-cli {__version__}")
    provider = get_update_provider()
    latest, reason = fetch_latest_version_detailed(use_cache=False)

    if latest is None:
        if reason == "not_published":
            console.print(f"[yellow]cu-cli is not published to {provider.name} yet.[/yellow]")
            console.print(
                f"[dim]install or update from source:[/dim] {provider.source_install_hint}"
            )
        elif reason == "disabled":
            console.print("[dim]update checks are disabled (CU_NO_UPDATE_CHECK).[/dim]")
        else:
            console.print(
                f"[yellow]could not reach {provider.name} to check for updates.[/yellow]"
            )
            console.print(f"[dim]check your network, or install from source:[/dim] "
                          f"{provider.source_install_hint}")
        return

    if not is_newer(latest):
        console.print(f"[green]up to date[/green] (latest: {latest}).")
        return

    console.print(upgrade_hint(latest, provider.release_notes_url))
    pip_args = pip_install_args(latest)
    if check:
        # `--check` is report-only; exit 0 so scripts can parse the message.
        return

    if not yes:
        if not sys.stdin.isatty():
            console.print(f"[dim]run:[/dim] {' '.join(pip_args)}")
            return
        if not click.confirm(f"Upgrade cu-cli {__version__} -> {latest} now?", default=True):
            console.print(f"[dim]skipped. Upgrade later with:[/dim] {' '.join(pip_args)}")
            return

    console.print(f"[dim]source:[/dim] {provider.name}")

    if is_windows():
        # On Windows, `cu.exe` holds an exclusive lock on its own executable
        # image while running. `pip install --upgrade` is non-atomic
        # (uninstall then install), so running it in-process here can
        # uninstall the current cu-cli and then fail to replace the locked
        # file, leaving the environment without an importable cu_cli at all
        # (regression). Instead, hand off to a detached helper process that
        # waits for this process to exit before upgrading, and rolls back to
        # the current version automatically if the upgrade fails.
        try:
            core_version = _pkg_version("cu-cli-core")
        except PackageNotFoundError:
            core_version = None
        exit_code, log_path = run_windows_upgrade(
            current_version=__version__,
            core_version=core_version,
            pip_args=pip_args,
            pip_env=provider.pip_environment(),
        )
        console.print(
            "[dim]upgrade will continue after cu exits (Windows cannot replace "
            "its own running executable in-process).[/dim]"
        )
        console.print(f"[dim]progress log:[/dim] {log_path}")
        console.print(
            f"[green]ok[/green] upgrade to {latest} started. "
            f"Run [bold]cu --version[/bold] after a moment to confirm."
        )
        sys.exit(exit_code)

    console.print(f"[dim]running:[/dim] {' '.join(pip_args)}")
    result = subprocess.run(pip_args, env={**os.environ, **provider.pip_environment()})
    if result.returncode == 0:
        console.print(f"[green]ok[/green] upgraded to {latest}. "
                      f"Release notes: {provider.release_notes_url}")
    else:
        console.print("[yellow]pip exited non-zero; upgrade may not have completed.[/yellow]")
        sys.exit(result.returncode)
