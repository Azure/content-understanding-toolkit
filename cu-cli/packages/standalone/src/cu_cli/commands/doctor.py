# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu doctor`` — verify endpoint, auth, api-version, and model deployments.

Exits non-zero when a required check fails so scripts and coding agents can gate
on setup readiness.
"""

from __future__ import annotations

import rich_click as click

from ..apiversion import API_VERSION_HELP, SUPPORTED_API_VERSIONS, is_supported
from ..client import build_client, resolve
from cu_cli_core.defaults import with_prebuilt_default_mappings
from ..profile import Profile
from ..core.defaults import is_defaults_not_set as _is_defaults_not_set
from ..core.doctor import missing_requirements as _missing_requirements
from ..errors import CuCliError, friendly_errors
from ..exit_codes import GENERIC_ERROR
from ..output import console
from ._options import CALLING_TIME_OPTION, calling_time
from ._help import common_commands
from ._model_setup import print_model_free_analyzers, print_model_setup_steps


@click.command(
    "doctor",
    help="Verify a Microsoft Foundry resource connection and Content Understanding defaults.",
    epilog=common_commands(
        ("cu doctor", "Check the active CU CLI profile and resource readiness."),
        ("cu doctor --profile NAME", "Check one profile without activating it."),
        ("cu doctor --fix-defaults", "Check readiness and apply profile mappings as defaults."),
    ),
)
@click.option("-p", "--profile", "profile_name", default=None,
              help="Named CU CLI profile to use (from cu profile).")
@click.option("--fix-defaults", is_flag=True,
              help="Configure Content Understanding defaults from profile model mappings.")
@click.option("--endpoint", default=None, help="Override configured endpoint.")
@click.option("--auth-mode", type=click.Choice(["login", "key"]), default=None,
              help="Authentication mode; defaults to the selected CU CLI profile.")
@click.option("--api-key", default=None, help="Override configured API key.")
@click.option("--api-version", "api_version", default=None,
              help=API_VERSION_HELP)
@CALLING_TIME_OPTION
@friendly_errors
def cmd_doctor(endpoint: str | None, api_key: str | None, api_version: str | None,
               auth_mode: str | None, profile_name: str | None, fix_defaults: bool,
               show_calling_time: bool) -> None:
    profile = Profile.load(profile_name=profile_name)
    failures: list[str] = []

    console.print("[bold]CU CLI configuration[/bold]\n")

    effective_version = api_version or profile.api_version
    if is_supported(effective_version):
        console.print(
            f"[bold]API version:[/bold] {effective_version} [green](supported)[/green]"
        )
    else:
        failures.append(
            f"api-version {effective_version} is not supported by this build "
            f"(supported: {', '.join(SUPPORTED_API_VERSIONS)})."
        )
        console.print(
            f"[bold]API version:[/bold] {effective_version} [red](unsupported)[/red]"
        )

    auth = resolve(profile, endpoint_override=endpoint, api_key_override=api_key,
                   api_version_override=api_version, auth_mode_override=auth_mode)
    authentication = (
        "Microsoft Entra ID" if auth.auth_mode == "entra" else "resource key"
    )
    console.print(f"[bold]Microsoft Foundry resource:[/bold] {auth.endpoint}")
    console.print(f"[bold]Authentication:[/bold] {authentication}")
    if profile.default_analyzer:
        console.print(f"[bold]Default analyzer:[/bold] {profile.default_analyzer}")
    else:
        console.print("[bold]Default analyzer:[/bold] not configured")
        console.print(
            "  [dim]`cu analyze` requires --analyzer until you configure one:\n"
            "  cu profile set default_analyzer <analyzer-id>[/dim]"
        )

    client = build_client(profile, endpoint_override=endpoint, api_key_override=api_key,
                          api_version_override=api_version, auth_mode_override=auth_mode)

    current: dict[str, str] = {}
    service_reachable = False
    with calling_time(show_calling_time) as calling_timer:
        console.print("\n[bold]Checking Content Understanding defaults...[/bold]\n")
        try:
            defaults = client.get_defaults()
            service_reachable = True
            current = getattr(defaults, "model_deployments", None) or {}
            console.print("Connected to the Microsoft Foundry resource.")
            if current:
                console.print("[bold]Content Understanding defaults:[/bold]")
                for model, deployment in current.items():
                    console.print(f"  - {model} -> {deployment}")
            else:
                console.print(
                    "[yellow]Content Understanding defaults have no model "
                    "deployment mappings.[/yellow]"
                )
        except Exception as exc:
            if _is_defaults_not_set(exc):
                service_reachable = True
                console.print("Connected to the Microsoft Foundry resource.")
                console.print(
                    "[yellow]Content Understanding defaults are not configured.[/yellow]"
                )
            else:
                failures.append(f"could not reach the service: {exc}")
                console.print("[red]Could not connect to the service (details below).[/red]")

        missing = _missing_requirements(current) if service_reachable else []
        if fix_defaults and service_reachable:
            merged = dict(current)
            merged.update(profile.model_deployments)
            merged = with_prebuilt_default_mappings(merged)
            if not merged:
                raise CuCliError(
                    "cannot set defaults: no model deployment mapping is configured",
                    hint="set model mappings first, e.g. `cu profile set "
                         "model_deployments.gpt-5.2 <deployment-name>` then rerun "
                         "`cu doctor --fix-defaults`.",
                )
            console.print("\n[bold]Applying Content Understanding defaults...[/bold]")
            client.update_defaults(model_deployments=merged)
            console.print("[green]Content Understanding defaults updated.[/green]")
            missing = _missing_requirements(merged)

    if missing:
        console.print(
            "\n[bold yellow]Setup needed for analyzers that use generative AI:"
            "[/bold yellow]"
        )
        for requirement in missing:
            console.print(f"  - {requirement}")
        print_model_setup_steps(
            auth.endpoint,
            profile_name=profile_name,
        )
        print_model_free_analyzers()

    if failures:
        console.print()
        for f in failures:
            console.print(f"[bold red]x[/bold red] {f}")
        calling_timer.print()
        raise CuCliError("doctor found problems; see above.", exit_code=GENERIC_ERROR)

    if missing:
        console.print(
            "\n[bold]Configuration check complete.[/bold]\n"
            "Content extraction analyzers are ready. Analyzers that use "
            "generative AI require the setup above."
        )
    else:
        console.print(
            "\n[bold green]Configuration check complete. CU CLI is ready.[/bold green]"
        )
    calling_timer.print()
