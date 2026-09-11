# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Framework-neutral infrastructure project generation."""

from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Iterable

from .errors import LocalIOError, ValidationError

DEFAULT_ENVIRONMENT = "dev"
DEFAULT_LOCATION = "eastus2"
AZD_ENV_NAME_MAX_LENGTH = 64
CU_REGION_SUPPORT_URL = (
    "https://learn.microsoft.com/azure/ai-services/content-understanding/"
    "language-region-support"
)
CU_SUPPORTED_REGIONS = (
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
)
_AZD_ENV_NAME_RE = re.compile(r"^[a-z0-9()_.-]{1,64}$")
_AZD_ENV_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*="
)
AZD_ENV_MANAGED_KEYS = (
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


@dataclass(frozen=True)
class AzureAccount:
    """Azure subscription context used by an infrastructure project."""

    subscription_id: str
    subscription_name: str
    tenant_id: str


@dataclass
class InfraChoices:
    """Fully resolved, frontend-independent infrastructure choices."""

    environment: str
    location: str
    api_version: str
    account: AzureAccount
    foundry_prefix: str | None
    foundry_endpoint: str | None
    foundry_resource_group: str | None
    model_selection: str
    assign_roles: bool = False
    force_profile_setup: bool = False


def validate_environment(value: str) -> str:
    """Normalize and validate an azd environment name."""

    name = value.strip().lower()
    if name in {".", ".."} or not _AZD_ENV_NAME_RE.fullmatch(name):
        raise ValidationError(
            "invalid azd environment name.",
            hint=(
                f"Use 1-{AZD_ENV_NAME_MAX_LENGTH} letters, numbers, hyphens, underscores, "
                "periods, or parentheses; '.' and '..' are not allowed."
            ),
        )
    return name


def validate_location(value: str) -> str:
    """Normalize and validate a Content Understanding region."""

    location = value.strip().lower().replace(" ", "")
    if location not in CU_SUPPORTED_REGIONS:
        raise ValidationError(
            f"'{value}' is not a CU-supported region.",
            hint=f"Supported: {', '.join(CU_SUPPORTED_REGIONS)}. See {CU_REGION_SUPPORT_URL}",
        )
    return location


def validate_foundry_prefix(value: str | None) -> str | None:
    """Normalize and validate an optional Foundry account prefix."""

    if value is None or not value.strip():
        return None
    prefix = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,18}[a-z0-9])?", prefix):
        raise ValidationError(
            "invalid Microsoft Foundry resource prefix.",
            hint="Use 1-20 lowercase letters, numbers, or internal hyphens.",
        )
    return prefix


def normalize_model_selection(
    models: str | Iterable[str] | None, *, prompt_when_unspecified: bool = False
) -> str:
    """Normalize deferred or explicit model selection consistently across frontends."""

    if models is None:
        return "prompt" if prompt_when_unspecified else "recommended"
    raw_parts = models.split(",") if isinstance(models, str) else models
    parts = [str(part).strip() for part in raw_parts]
    if not parts or any(not part for part in parts):
        raise ValidationError("--models contains an empty entry.")
    special = {part.casefold() for part in parts} & {"none", "recommended", "prompt"}
    if special and len(parts) != 1:
        raise ValidationError(
            "'none', 'recommended', and 'prompt' cannot be combined with other models; "
            "each must be used alone with --models."
        )
    return parts[0].casefold() if special else ",".join(parts)


def template_root() -> Traversable:
    """Return the canonical bundled azd template."""

    root = resources.files("cu_cli_core").joinpath("resources").joinpath("azd_template")
    if not root.is_dir():
        raise LocalIOError("the infrastructure template is missing from the core package.")
    return root


def iter_template_files(root: Traversable | None = None) -> Iterable[tuple[str, bytes]]:
    """Yield canonical template files in deterministic relative-path order."""

    root = root or template_root()

    def walk(node: Traversable, prefix: str) -> Iterable[tuple[str, bytes]]:
        for child in sorted(node.iterdir(), key=lambda item: item.name):
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if child.is_dir():
                yield from walk(child, relative)
            else:
                yield relative, child.read_bytes()

    yield from walk(root, "")


def render_env_assignments(choices: InfraChoices) -> dict[str, str]:
    """Render CU-managed azd environment assignments."""

    values = (
        choices.environment,
        choices.location,
        choices.account.subscription_id,
        choices.account.tenant_id,
        choices.api_version,
        choices.model_selection,
        "false",
        choices.foundry_prefix or "",
        choices.foundry_endpoint or "",
        choices.foundry_resource_group or "",
        str(choices.assign_roles).lower(),
        str(choices.force_profile_setup).lower(),
    )
    return {
        key: f'{key}="{value}"'
        for key, value in zip(AZD_ENV_MANAGED_KEYS, values)
    }


def render_env(choices: InfraChoices) -> str:
    """Render a new azd environment file."""

    return "\n".join((*render_env_assignments(choices).values(), ""))


def merge_env(existing: str | None, choices: InfraChoices) -> str:
    """Merge managed values while preserving unknown azd state and newline style."""

    if existing is None:
        return render_env(choices)
    assignments = render_env_assignments(choices)
    newline = "\r\n" if "\r\n" in existing else "\n"
    seen: set[str] = set()
    output: list[str] = []
    for line in existing.splitlines(keepends=True):
        match = _AZD_ENV_ASSIGNMENT_RE.match(line)
        key = match.group("key") if match else None
        if key not in assignments:
            output.append(line)
        elif key not in seen:
            ending = "\r\n" if line.endswith("\r\n") else (
                "\n" if line.endswith("\n") else newline
            )
            output.append(line if key == "CU_MODEL_SETUP_COMPLETE" else assignments[key] + ending)
            seen.add(key)
    missing = [key for key in AZD_ENV_MANAGED_KEYS if key not in seen]
    if missing and output and not output[-1].endswith(("\r", "\n")):
        output.append(newline)
    output.extend(assignments[key] + newline for key in missing)
    return "".join(output)


def safe_environment_directory(target: Path, environment: str) -> Path:
    """Reject redirects that would place azd state outside the target."""

    target_root = target.resolve(strict=False)
    azure_root = target_root / ".azure"
    if azure_root.resolve(strict=False) != azure_root:
        raise LocalIOError("refusing to write the azd environment outside provision/.azure.")
    environment_dir = azure_root / environment
    if environment_dir.resolve(strict=False).parent != azure_root:
        raise LocalIOError("refusing to write the azd environment outside .azure.")
    return environment_dir


def _read_text(path: Path, description: str) -> str | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            return stream.read()
    except (OSError, UnicodeError) as exc:
        raise LocalIOError(f"could not read existing {description}: {path}") from exc


def _load_config(path: Path) -> dict[str, Any]:
    text = _read_text(path, "azd config")
    if text is None:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LocalIOError(f"could not read existing azd config: {path}") from exc
    if not isinstance(value, dict):
        raise LocalIOError(f"existing azd config must be a JSON object: {path}")
    return value


def materialize_project(
    target: Path, choices: InfraChoices, *, force: bool
) -> tuple[list[str], bool]:
    """Materialize the canonical project and merge azd state safely."""

    choices.environment = validate_environment(choices.environment)
    choices.location = validate_location(choices.location)
    environment_dir = safe_environment_directory(target, choices.environment)
    has_content = target.exists() and any(target.iterdir())
    existing_template = (
        (target / "azure.yaml").is_file() and (target / "infra" / "main.bicep").is_file()
    )
    if has_content and not force and not existing_template:
        raise LocalIOError(
            f"'{target}' already exists and is non-empty.",
            hint="Use an existing provision directory, choose another directory, or pass --force.",
        )
    reused = has_content and existing_template and not force
    env_path = environment_dir / ".env"
    config_path = target / ".azure" / "config.json"

    # Validate all reusable state before mutating the filesystem.
    existing_env = _read_text(env_path, "azd environment file") if reused else None
    config = _load_config(config_path) if reused else {}
    config.update({"version": 1, "defaultEnvironment": choices.environment})
    bundled = list(iter_template_files()) if not reused else []

    target.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for relative, content in bundled:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        if relative.endswith(".sh"):
            destination.chmod(
                destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
        written.append(relative)

    models_path = target / "infra" / "models.json"
    if force or not models_path.exists():
        models_path.parent.mkdir(parents=True, exist_ok=True)
        models_path.write_text("[]\n", encoding="utf-8")
        written.append("infra/models.json")
    environment_dir.mkdir(parents=True, exist_ok=True)
    with env_path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(merge_env(existing_env, choices))
    with config_path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(config, indent=2) + "\n")
    written.extend((f".azure/{choices.environment}/.env", ".azure/config.json"))
    return sorted(set(written)), reused