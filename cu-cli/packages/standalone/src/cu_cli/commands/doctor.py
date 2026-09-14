# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""``cu doctor`` — verify endpoint, auth, api-version, and model deployments.

Exits non-zero when a required check fails so scripts and coding agents can gate
on setup readiness.
"""

from __future__ import annotations

import rich_click as click
from cu_cli_core.command_spec import DOCTOR
from cu_cli_core.doctor import assess_doctor, resolve_doctor_request

from ..client import build_client, resolve
from ..profile import Profile
from ..errors import CuCliError, friendly_errors
from ..exit_codes import GENERIC_ERROR
from ..output import console
from ._options import CALLING_TIME_OPTION, calling_time
from ._help import common_commands
from ._model_setup import print_model_free_analyzers, print_model_setup_steps
from ._command_spec import with_command_arguments


@click.command(
    "doctor",
    help="Verify a Microsoft Foundry resource connection and Content Understanding defaults.",
    epilog=common_commands(
        ("cu doctor", "Check the active CU CLI profile and resource readiness."),
        ("cu doctor --profile NAME", "Check one profile without activating it."),
        ("cu doctor --fix-defaults", "Check readiness and apply profile mappings as defaults."),
    ),
)
@with_command_arguments(DOCTOR)
@CALLING_TIME_OPTION
@friendly_errors
def cmd_doctor(endpoint: str | None, api_key: str | None, api_version: str | None,
               auth_mode: str | None, profile_name: str | None, fix_defaults: bool,
               show_calling_time: bool) -> None:
    profile = Profile.load(profile_name=profile_name)
    request = resolve_doctor_request(
        profile,
        endpoint=endpoint,
        api_version=api_version,
        auth_mode=auth_mode,
        api_key=api_key,
        fix_defaults=fix_defaults,
    )

    console.print("[bold]CU CLI configuration[/bold]\n")
    console.print(f"[bold]API version:[/bold] {request.api_version} [green](supported)[/green]")

    auth = resolve(profile, endpoint_override=endpoint, api_key_override=api_key,
                   api_version_override=api_version, auth_mode_override=auth_mode)
    console.print(f"[bold]Microsoft Foundry resource:[/bold] {auth.endpoint}")
    console.print(f"[bold]Authentication:[/bold] {request.authentication}")
    if profile.default_analyzer:
        console.print(f"[bold]Default analyzer:[/bold] {profile.default_analyzer}")
    else:
        console.print("[bold]Default analyzer:[/bold] not configured")
        console.print(
            "  [dim]`cu analyze` requires --analyzer until you configure one:\n"
            "  cu profile set default_analyzer <analyzer-id>[/dim]"
        )

    with calling_time(show_calling_time) as calling_timer:
        console.print("\n[bold]Checking Content Understanding defaults...[/bold]\n")
        result = assess_doctor(
            request,
            lambda _request: build_client(
                profile,
                endpoint_override=endpoint,
                api_key_override=api_key,
                api_version_override=api_version,
                auth_mode_override=auth_mode,
            ),
        )
        if result.required_checks_passed:
            console.print("Connected to the Microsoft Foundry resource.")
            if result.model_deployments:
                console.print("[bold]Content Understanding defaults:[/bold]")
                for model, deployment in result.model_deployments.items():
                    console.print(f"  - {model} -> {deployment}")
            elif result.defaults_configured:
                console.print(
                    "[yellow]Content Understanding defaults have no model "
                    "deployment mappings.[/yellow]"
                )
            else:
                console.print(
                    "[yellow]Content Understanding defaults are not configured.[/yellow]"
                )
            if result.defaults_updated:
                console.print("\n[bold]Applying Content Understanding defaults...[/bold]")
                console.print("[green]Content Understanding defaults updated.[/green]")
        else:
            console.print("[red]Could not connect to the service (details below).[/red]")

        missing = result.missing_requirements

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

    if result.failures:
        console.print()
        for failure in result.failures:
            console.print(f"[bold red]x[/bold red] could not reach the service: {failure.message}")
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
