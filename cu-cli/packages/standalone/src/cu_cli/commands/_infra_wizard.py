"""Infrastructure wizard for ``cu provision``.

Drops a self-contained `azd` template under the requested output directory so
the developer can run `azd up` to provision Foundry, discover the live
CU model catalog, and optionally deploy selected models.

Surface:
  - run_wizard(target, *, interactive, env, location, api_version, models, assign_roles,
               force) -> bool   # True if files were written
  - InfraChoices                                # dataclass of resolved inputs

The wizard is *advisory* — calling code (`cu provision`) is responsible for
deciding whether to invoke it (TTY check, --no-infra flag, etc.).
"""

from __future__ import annotations

import json
import re
import shlex
import stat
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources as ir
from pathlib import Path
from typing import Iterable

import rich_click as click

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

DEFAULT_ENV = "dev"
DEFAULT_LOCATION = "eastus2"
AZD_ENV_NAME_MAX_LENGTH = 64
_AZD_ENV_NAME_RE = re.compile(r"^[a-z0-9()_.-]{1,64}$")
_AZD_ENV_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*="
)
_AZD_ENV_MANAGED_KEYS = (
    "AZURE_ENV_NAME",
    "AZURE_LOCATION",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_TENANT_ID",
    "CU_API_VERSION",
    "CU_MODEL_SELECTION",
    "CU_MODEL_SETUP_COMPLETE",
    "FOUNDRY_RESOURCE_PREFIX",
    "FOUNDRY_EXISTING_ENDPOINT",
    "FOUNDRY_EXISTING_RESOURCE_GROUP",
    "AZD_ASSIGN_ROLES",
    "CU_PROFILE_SETUP_FORCE",
)

CU_REGION_SUPPORT_URL = (
    "https://learn.microsoft.com/azure/ai-services/content-understanding/"
    "language-region-support"
)

# Regions where Content Understanding is available (GA).
# Keep this list in sync with the current availability at CU_REGION_SUPPORT_URL.
CU_SUPPORTED_REGIONS: list[str] = [
    "australiaeast",
    "eastus",
    "eastus2",
    "japaneast",
    "northeurope",
    "southcentralus",
    "southeastasia",
    "swedencentral",
    "uksouth",
    "westeurope",
    "westus",
    "westus3",
]

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
        "[bold]`cu provision`[/bold] generates an [cyan]azd[/cyan] template. After "
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
    candidate = raw.strip().lower()
    if not candidate:
        return None

    if len(candidate) > 20:
        raise CuCliError(
            "invalid Microsoft Foundry resource prefix",
            hint="use 1-20 chars: lowercase letters, digits, hyphen (no leading or trailing hyphen)",
        )
    if candidate[0] == "-" or candidate[-1] == "-":
        raise CuCliError(
            "invalid Microsoft Foundry resource prefix",
            hint="prefix cannot start or end with '-'.",
        )
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if any(ch not in allowed for ch in candidate):
        raise CuCliError(
            "invalid Microsoft Foundry resource prefix",
            hint="use only lowercase letters (a-z), digits (0-9), and hyphen (-).",
        )

    return candidate


def _prompt_assign_roles() -> bool:
    console.print()
    console.print(
        "[bold]RBAC roles[/bold]: required for Entra-based auth from `cu`. "
        "Needs Owner or User Access Administrator on the subscription. "
        "Pick 'n' if you only have Contributor — cu can use the resource "
        "API key instead."
    )
    return click.confirm("Assign RBAC roles to your user on the Microsoft Foundry resource?",
                         default=False)


def _resolve_model_selection(models: list[str] | None, *, interactive: bool) -> str:
    """Describe how the post-provision live model picker should behave."""
    if not models:
        return "prompt" if interactive else "recommended"
    normalized = [model.strip() for model in models if model.strip()]
    none_selected = [model for model in normalized if model.lower() == "none"]
    if none_selected:
        if len(normalized) != 1:
            raise CuCliError(
                "'none' cannot be combined with model names in --models."
            )
        return "none"
    return ",".join(normalized)


# ---------------------------------------------------------------------------
# File materialization
# ---------------------------------------------------------------------------

def _template_root():
    """importlib.resources Traversable for the bundled azd_template."""
    return ir.files("cu_cli.resources").joinpath("azd_template")


def _iter_template_files(root) -> Iterable[tuple[str, bytes]]:
    """Yield (relative_path_with_forward_slashes, bytes) for every bundled file."""
    def _walk(node, prefix: str):
        for child in node.iterdir():
            rel = f"{prefix}/{child.name}" if prefix else child.name
            if child.is_dir():
                yield from _walk(child, rel)
            else:
                yield rel, child.read_bytes()
    yield from _walk(root, "")


def _ensure_executable_if_shell_script(path: Path, rel_path: str) -> None:
    if not rel_path.endswith('.sh'):
        return
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_template(target: Path, choices: InfraChoices, *, force: bool) -> None:
    choices.env = _validate_azd_environment_name(choices.env)
    env_dir = _safe_env_directory(target, choices.env)

    target_has_content = target.exists() and any(target.iterdir())
    is_existing_template = (
        (target / "azure.yaml").exists()
        and (target / "infra" / "main.bicep").exists()
    )
    if target_has_content and not force and not is_existing_template:
        raise CuCliError(
            f"{target} already exists and is non-empty",
            hint=(
                "use an existing `provision/` directory, pass --force to overwrite it, "
                "or move/remove the directory."
            ),
        )
    reused_existing = target_has_content and is_existing_template and not force
    env_path = env_dir / ".env"
    config_path = target / ".azure" / "config.json"
    existing_env = _read_existing_azd_env(env_path) if reused_existing else None
    azd_config = _load_existing_azd_config(config_path) if reused_existing else {}
    azd_config.update({"version": 1, "defaultEnvironment": choices.env})

    target.mkdir(parents=True, exist_ok=True)
    template_root = _template_root()
    written: list[str] = []
    if not reused_existing:
        for rel, data in _iter_template_files(template_root):
            dest = target / Path(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            _ensure_executable_if_shell_script(dest, rel)
            written.append(rel)

    # The first azd provision creates the resource without models. The
    # post-provision hook fills this file from live CU + ARM discovery.
    models_path = target / "infra" / "models.json"
    if not models_path.exists() or force:
        models_path.write_text("[]\n", encoding="utf-8")

    # Pre-populate `.azure/<env>/.env` with the resolved choices so `azd up`
    # picks them up without further `azd env set` calls.
    env_dir.mkdir(parents=True, exist_ok=True)
    env_body = (
        _merge_azd_env(existing_env, choices)
        if existing_env is not None
        else _render_azd_env(choices)
    )
    _write_utf8(env_path, env_body)
    _write_utf8(config_path, json.dumps(azd_config, indent=2) + "\n")

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
    name = raw.strip().lower()
    if name in {".", ".."} or not _AZD_ENV_NAME_RE.fullmatch(name):
        raise CuCliError(
            "invalid azd environment name.",
            hint=(
                f"use 1-{AZD_ENV_NAME_MAX_LENGTH} letters, numbers, hyphens (-), "
                "underscores (_), periods (.), or parentheses; '.' and '..' are not allowed."
            ),
        )
    return name


def _safe_env_directory(target: Path, env_name: str) -> Path:
    """Return the direct `.azure/<env>` child after resolving existing symlinks."""
    target_root = target.resolve(strict=False)
    azure_root = target_root / ".azure"
    resolved_azure_root = azure_root.resolve(strict=False)
    resolved_env_dir = (azure_root / env_name).resolve(strict=False)
    if resolved_azure_root != azure_root or resolved_env_dir.parent != azure_root:
        raise CuCliError(
            "refusing to write the azd environment outside provision/.azure.",
            hint="remove path redirections under provision/.azure and try again.",
        )
    return azure_root / env_name


def _read_existing_azd_env(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            return stream.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise CuCliError(
            f"could not read existing azd environment file: {path}",
            hint="repair or remove the file, or pass --force to replace it.",
        ) from exc


def _load_existing_azd_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CuCliError(
            f"could not read existing azd config: {path}",
            hint="repair or remove the file, or pass --force to replace it.",
        ) from exc
    if not isinstance(value, dict):
        raise CuCliError(
            f"existing azd config must contain a JSON object: {path}",
            hint="repair or remove the file, or pass --force to replace it.",
        )
    return value


def _write_utf8(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(content)


def _render_azd_env(choices: InfraChoices) -> str:
    return "\n".join([*_render_azd_env_assignments(choices).values(), ""])


def _render_azd_env_assignments(choices: InfraChoices) -> dict[str, str]:
    values = (
        choices.env,
        choices.location,
        choices.subscription_id,
        choices.tenant_id,
        choices.api_version,
        choices.model_selection,
        "false",
        choices.foundry_account_prefix or "",
        choices.foundry_endpoint or "",
        choices.foundry_resource_group or "",
        str(choices.assign_roles).lower(),
        str(choices.force_profile_setup).lower(),
    )
    return {
        key: f'{key}="{value}"'
        for key, value in zip(_AZD_ENV_MANAGED_KEYS, values)
    }


def _merge_azd_env(existing: str, choices: InfraChoices) -> str:
    """Update CU-managed assignments while preserving all other dotenv content."""
    assignments = _render_azd_env_assignments(choices)
    seen: set[str] = set()
    output: list[str] = []
    newline = "\r\n" if "\r\n" in existing else "\n"

    for line in existing.splitlines(keepends=True):
        match = _AZD_ENV_ASSIGNMENT_RE.match(line)
        key = match.group("key") if match else None
        if key not in assignments:
            output.append(line)
            continue
        if key not in seen:
            line_ending = "\r\n" if line.endswith("\r\n") else (
                "\n" if line.endswith("\n") else newline
            )
            output.append(
                line
                if key == "CU_MODEL_SETUP_COMPLETE"
                else assignments[key] + line_ending
            )
            seen.add(key)

    missing = [key for key in _AZD_ENV_MANAGED_KEYS if key not in seen]
    if missing and output and not output[-1].endswith(("\r", "\n")):
        output.append(newline)
    output.extend(assignments[key] + newline for key in missing)
    return "".join(output)


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
