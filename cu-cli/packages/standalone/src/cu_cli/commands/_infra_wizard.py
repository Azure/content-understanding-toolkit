# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Infrastructure wizard for ``cu infra generate``.

Drops a self-contained `azd` template under the requested output directory so
the developer can run `azd up` to provision Foundry, discover the live
CU model catalog, and optionally deploy selected models.

Surface:
  - run_wizard(target, *, interactive, env, location, api_version, models, assign_roles,
               force) -> bool   # True if files were written
  - InfraChoices                                # dataclass of resolved inputs

The wizard is *advisory* — calling code (`cu infra generate`) is responsible for
deciding whether to invoke it (TTY check, --no-infra flag, etc.).
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import rich_click as click
from cu_cli_core import infra as core_infra
from cu_cli_core.errors import CuCoreError

from ..errors import CuCliError
from ..output import console


@dataclass
class InfraChoices:
    env: str
    location: str
    api_version: str
    subscription_id: str
    subscription_name: str
    tenant_id: str
    foundry_account_prefix: str | None
    foundry_endpoint: str | None
    foundry_resource_group: str | None
    model_selection: str
    assign_roles: bool
    force_profile_setup: bool


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_wizard(
    target: Path,
    *,
    interactive: bool,
    already_opted_in: bool = False,
    env: str | None,
    location: str | None,
    api_version: str,
    subscription_id: str,
    subscription_name: str,
    tenant_id: str,
    foundry_account_prefix: str | None,
    foundry_endpoint: str | None,
    foundry_resource_group: str | None,
    models: list[str] | None,
    assign_roles: bool | None,
    force: bool,
) -> bool:
    """Prompt the user (if interactive) and materialize an azd template.

    Returns True if anything was written, False if the user declined or no
    template files exist.
    """
    choices = _resolve_choices(
        interactive=interactive,
        already_opted_in=already_opted_in,
        env=env,
        location=location,
        api_version=api_version,
        subscription_id=subscription_id,
        subscription_name=subscription_name,
        tenant_id=tenant_id,
        foundry_account_prefix=foundry_account_prefix,
        foundry_endpoint=foundry_endpoint,
        foundry_resource_group=foundry_resource_group,
        models=models,
        assign_roles=assign_roles,
        force_profile_setup=force,
    )
    if choices is None:
        return False

    _write_template(target, choices, force=force)
    _print_next_steps(target, choices)
    return True


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------

DEFAULT_ENV = core_infra.DEFAULT_ENVIRONMENT
DEFAULT_LOCATION = core_infra.DEFAULT_LOCATION
AZD_ENV_NAME_MAX_LENGTH = core_infra.AZD_ENV_NAME_MAX_LENGTH
CU_REGION_SUPPORT_URL = core_infra.CU_REGION_SUPPORT_URL

# Regions where Content Understanding is available (GA).
# Keep this list in sync with the current availability at CU_REGION_SUPPORT_URL.
CU_SUPPORTED_REGIONS = list(core_infra.CU_SUPPORTED_REGIONS)

def _resolve_choices(
    *,
    interactive: bool,
    already_opted_in: bool = False,
    env: str | None,
    location: str | None,
    api_version: str,
    subscription_id: str,
    subscription_name: str,
    tenant_id: str,
    foundry_account_prefix: str | None,
    foundry_endpoint: str | None,
    foundry_resource_group: str | None,
    models: list[str] | None,
    assign_roles: bool | None,
    force_profile_setup: bool,
) -> InfraChoices | None:
    """Combine CLI flags with interactive prompts. Returns None if the user declines."""

    if interactive and not already_opted_in:
        console.print()
        proceed = click.confirm(
            "Provision a Microsoft Foundry resource, optionally deploy selected supported "
            "large language models (LLMs) and embeddings models, and configure "
            "Content Understanding defaults now?\n"
            "  This writes an `azd` template under ./provision/ that you run yourself.",
            default=True,
        )
        if not proceed:
            return None

    resolved_env = env or (
        _prompt_env()
        if interactive else DEFAULT_ENV
    )
    resolved_env = _validate_azd_environment_name(resolved_env)
    use_existing_foundry = bool(foundry_endpoint)
    resolved_location = location or (
        _prompt_location()
        if interactive and not use_existing_foundry else DEFAULT_LOCATION
    )
    if resolved_location not in CU_SUPPORTED_REGIONS:
        raise CuCliError(
            f"'{resolved_location}' is not a CU-supported region",
            hint=(
                "supported: " + ", ".join(CU_SUPPORTED_REGIONS)
                + f"\nSee {CU_REGION_SUPPORT_URL}"
            ),
        )
    resolved_prefix = None if use_existing_foundry else _resolve_foundry_account_prefix(
        foundry_account_prefix,
        interactive=interactive,
    )

    model_selection = _resolve_model_selection(models, interactive=interactive)

    resolved_assign_roles = False if use_existing_foundry else (
        assign_roles if assign_roles is not None
        else (_prompt_assign_roles() if interactive else False)
    )
    return InfraChoices(
        env=resolved_env,
        location=resolved_location.strip(),
        api_version=api_version,
        subscription_id=subscription_id,
        subscription_name=subscription_name,
        tenant_id=tenant_id,
        foundry_account_prefix=resolved_prefix,
        foundry_endpoint=foundry_endpoint,
        foundry_resource_group=foundry_resource_group,
        model_selection=model_selection,
        assign_roles=resolved_assign_roles,
        force_profile_setup=force_profile_setup,
    )


def _prompt_env() -> str:
    console.print()
    console.print(
        "[bold]`cu infra generate`[/bold] generates an [cyan]azd[/cyan] template. After "
        "the Microsoft Foundry resource is provisioned, its post-provision script "
        "can optionally deploy supported chat completion and embeddings models for "
        "prebuilt analyzers such as [cyan]prebuilt-invoice[/cyan] and for custom analyzers."
    )
    console.print(
        "[dim]It doesn't create any Azure resources itself — you run "
        "[/dim][cyan]azd up[/cyan][dim] afterwards to do the actual provisioning.[/dim]"
    )
    console.print()
    console.print("Input your [bold]azd environment name[/bold]. An azd environment name:")
    console.print(
        "  [dim]•[/dim] lets azd store this deployment's config + outputs under "
        "[cyan]provision/.azure/<env>/[/cyan]."
    )
    console.print(
        "  [dim]•[/dim] seeds your Azure resource names "
        "(e.g. [cyan]rg-<env>[/cyan], [cyan]proj-<env>[/cyan])."
    )
    console.print(
        "  [dim]•[/dim] keeps separate stacks apart, such as "
        "[cyan]dev[/cyan], [cyan]test[/cyan], or [cyan]prod[/cyan]."
    )
    return click.prompt(
        "Enter your environment name (1-64 letters, numbers, -, _, ., or parentheses)",
        default=DEFAULT_ENV,
        show_default=True,
    )


def _prompt_location() -> str:
    console.print()
    console.print("[bold]Content Understanding supported regions[/bold]")
    console.print(
        f"[dim]Check the latest region support at {CU_REGION_SUPPORT_URL}[/dim]"
    )
    console.print()
    cols = 3
    for i in range(0, len(CU_SUPPORTED_REGIONS), cols):
        row = CU_SUPPORTED_REGIONS[i : i + cols]
        console.print("  " + "   ".join(f"{r:<20}" for r in row))
    console.print()
    while True:
        raw = click.prompt(
            "Azure region (where the Foundry resource is created)",
            default=DEFAULT_LOCATION,
            show_default=True,
        )
        candidate = raw.strip().lower()
        if candidate in CU_SUPPORTED_REGIONS:
            return candidate
        console.print(
            f"[red]'{candidate}' is not a CU-supported region.[/red] "
            "Choose one from the list above."
        )


def _resolve_foundry_account_prefix(
    prefix: str | None,
    *,
    interactive: bool,
) -> str | None:
    if prefix is not None:
        return _validate_foundry_account_prefix(prefix)

    if not interactive:
        return None

    console.print()
    console.print(
        "[bold]Microsoft Foundry resource naming[/bold]: the resource name becomes part of the "
        "public endpoint host (for example, [cyan]https://<name>.services.ai.azure.com[/cyan]), "
        "so it must be globally unique."
    )
    console.print(
        "[dim]If you provide a prefix, azd constructs the resource name as "
        "<prefix>-<unique-suffix>. Without a prefix, it uses aif-<unique-suffix>.[/dim]"
    )
    raw = click.prompt(
        "Optional Microsoft Foundry resource name prefix "
        "(lowercase letters, numbers, hyphen; blank to skip)",
        default="",
        show_default=False,
    )
    return _validate_foundry_account_prefix(raw)


def _validate_foundry_account_prefix(raw: str) -> str | None:
    return _translate_core_error(core_infra.validate_foundry_prefix, raw)


def _prompt_assign_roles() -> bool:
    console.print()
    console.print(
        "[bold]RBAC roles[/bold]: required for Entra-based auth from `cu`. "
        "Needs Owner, User Access Administrator, or Role Based Access Control "
        "Administrator on the subscription. "
        "Pick 'n' if you only have Contributor — cu can use the resource "
        "API key instead."
    )
    return click.confirm("Assign RBAC roles to your user on the Microsoft Foundry resource?",
                         default=False)


def _resolve_model_selection(models: list[str] | None, *, interactive: bool) -> str:
    """Describe how the post-provision live model picker should behave."""
    return _translate_core_error(
        core_infra.normalize_model_selection,
        models,
        prompt_when_unspecified=interactive,
    )


# ---------------------------------------------------------------------------
# File materialization
# ---------------------------------------------------------------------------

def _template_root():
    """Return the canonical core template (legacy helper alias)."""
    return core_infra.template_root()


def _iter_template_files(root):
    """Iterate canonical files (legacy helper alias)."""
    yield from core_infra.iter_template_files(root)


def _write_template(target: Path, choices: InfraChoices, *, force: bool) -> None:
    core_choices = _core_choices(choices)
    try:
        written, reused_existing = core_infra.materialize_project(
            target, core_choices, force=force
        )
    except CuCoreError as exc:
        raise CuCliError(exc.message, hint=exc.hint) from exc
    choices.env = core_choices.environment

    console.print()
    heading = "updated" if reused_existing else "wrote"
    console.print(f"[bold]{heading}[/bold] [cyan]{target}[/cyan]")
    for rel in sorted(written):
        console.print(f"  [green]created[/green]            provision/{rel}")
    if reused_existing:
        console.print("  [cyan]reused[/cyan]             existing provision directory")
        console.print("  [cyan]preserved[/cyan]          provision/infra/models.json")
        console.print(f"  [green]merged[/green]             provision/.azure/{choices.env}/.env")
        console.print("  [green]updated[/green]            provision/.azure/config.json")
    else:
        console.print("  [green]created[/green]            provision/infra/models.json"
                      " [dim](live selection runs after the Foundry resource exists)[/dim]")
        console.print(f"  [green]created[/green]            provision/.azure/{choices.env}/.env")
        console.print("  [green]created[/green]            provision/.azure/config.json")


def _validate_azd_environment_name(raw: str) -> str:
    """Return the normalized azd environment name or reject unsafe input."""
    return _translate_core_error(core_infra.validate_environment, raw)


def _safe_env_directory(target: Path, env_name: str) -> Path:
    """Return the direct `.azure/<env>` child after resolving existing symlinks."""
    return _translate_core_error(core_infra.safe_environment_directory, target, env_name)


def _render_azd_env(choices: InfraChoices) -> str:
    return core_infra.render_env(_core_choices(choices))


def _render_azd_env_assignments(choices: InfraChoices) -> dict[str, str]:
    return core_infra.render_env_assignments(_core_choices(choices))


def _merge_azd_env(existing: str, choices: InfraChoices) -> str:
    """Update CU-managed assignments while preserving all other dotenv content."""
    return core_infra.merge_env(existing, _core_choices(choices))


def _core_choices(choices: InfraChoices) -> core_infra.InfraChoices:
    return core_infra.InfraChoices(
        environment=choices.env,
        location=choices.location,
        api_version=choices.api_version,
        account=core_infra.AzureAccount(
            choices.subscription_id, choices.subscription_name, choices.tenant_id
        ),
        foundry_prefix=choices.foundry_account_prefix,
        foundry_endpoint=choices.foundry_endpoint,
        foundry_resource_group=choices.foundry_resource_group,
        model_selection=choices.model_selection,
        assign_roles=choices.assign_roles,
        force_profile_setup=choices.force_profile_setup,
    )


def _translate_core_error(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except CuCoreError as exc:
        raise CuCliError(exc.message, hint=exc.hint) from exc


def _print_next_steps(target: Path, choices: InfraChoices) -> None:
    sep = "\\" if sys.platform == "win32" else "/"
    try:
        relative = target.relative_to(Path.cwd())
        rel = str(relative).replace("/", sep)
    except ValueError:
        rel = str(target)
    quoted_rel = (
        subprocess.list2cmdline([rel])
        if sys.platform == "win32"
        else shlex.quote(rel)
    )
    console.print()
    console.print("[bold]Next:[/bold]")
    console.print(f"  [cyan]cd {quoted_rel}[/cyan]")
    console.print("  [cyan]azd auth login[/cyan]        [dim](one-time)[/dim]")
    if choices.foundry_endpoint:
        console.print(
            f"  [cyan]azd up[/cyan]                [dim]configures Content Understanding and "
            "optionally deploys selected supported LLMs and embeddings models on the "
            f"existing Microsoft Foundry resource "
            f"({choices.foundry_endpoint})[/dim]"
        )
    else:
        action = (
            "provisions a Microsoft Foundry resource without model deployments"
            if choices.model_selection == "none"
            else "provisions a Microsoft Foundry resource, optionally deploys selected "
                 "supported LLMs and embeddings models, and configures Content Understanding "
                 "defaults"
        )
        console.print(f"  [cyan]azd up[/cyan]                [dim]{action}[/dim]")
    if choices.model_selection not in {"none", "prompt", "recommended"}:
        console.print(
            "  [dim]The explicit model names are validated against the live "
            "CU-supported model catalog during azd up, after the Microsoft Foundry "
            "resource is available.[/dim]"
        )
    console.print(
        "  [dim]The post-provision hook prints verified Content Understanding setup "
        "and test commands.[/dim]"
    )
