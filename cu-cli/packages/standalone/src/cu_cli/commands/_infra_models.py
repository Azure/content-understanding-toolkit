"""Internal live model-setup command used by the generated azd hook."""

from __future__ import annotations

import sys
from pathlib import Path

import rich_click as click

from ..client import build_client, resolve
from ..profile import Profile
from ..core.infra_models import (
    DeployableModel,
    deploy_models,
    deployable_models,
    fetch_account_models,
    recommended_models,
    select_requested_models,
    supported_model_names,
    write_models_file,
)
from ..errors import CuCliError, friendly_errors
from ..output import console
from ._help import common_commands
from ._options import print_runtime_context, with_auth_options

NO_MODEL_ANALYZERS = (
    "prebuilt-digitalParse",
    "prebuilt-read",
    "prebuilt-layout",
)


def _parse_picker(raw: str, candidates: list[DeployableModel]) -> list[DeployableModel]:
    indices: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            index = int(chunk)
        except ValueError as exc:
            raise ValueError(f"'{chunk}' is not a number") from exc
        if index == 0:
            if len([part for part in raw.split(",") if part.strip()]) != 1:
                raise ValueError("0 (no models) cannot be combined with model selections")
            return []
        if not 1 <= index <= len(candidates):
            raise ValueError(f"'{index}' is out of range (0..{len(candidates)})")
        if index not in indices:
            indices.append(index)

    selected = [candidates[index - 1] for index in indices]
    names = [model.name.lower() for model in selected]
    if len(names) != len(set(names)):
        raise ValueError("select only one version of each model family")
    return selected


def _prompt_for_models(candidates: list[DeployableModel]) -> list[DeployableModel]:
    console.print("\n[bold]Select live CU-supported models to deploy[/bold]")
    console.print(
        "  [yellow][0][/yellow] None - "
        + ", ".join(NO_MODEL_ANALYZERS)
        + " only (no language or embeddings models)"
    )
    for index, model in enumerate(candidates, start=1):
        console.print(
            f"  [yellow][{index}][/yellow] {model.name:<30} {model.version:<12} "
            f"{model.kind:<10} {model.sku_name}"
        )
    try:
        recommended = recommended_models(candidates)
        default_choice = ",".join(
            str(candidates.index(model) + 1) for model in recommended
        )
    except CuCliError:
        default_choice = "0"
    while True:
        raw = click.prompt(
            "Enter numbers (comma-separated)", default=default_choice, show_default=True
        )
        try:
            return _parse_picker(raw, candidates)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")


def _client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context):
    profile = Profile.load(profile_name=profile_name)
    auth = resolve(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )
    if show_runtime_context:
        print_runtime_context(auth, profile)
    return build_client(
        profile,
        endpoint_override=endpoint,
        api_key_override=api_key,
        api_version_override=api_version,
        force_entra=entra,
    )


@click.command(
    "_infra-models",
    hidden=True,
    epilog=common_commands(
        (
            "cu _infra-models --selection none ...",
            "Skip model deployment for digitalParse, read, and layout.",
        ),
    ),
)
@click.option("--resource-group", required=True)
@click.option("--account", "account_name", required=True)
@click.option("--subscription", "subscription_id", required=True)
@click.option("--selection", required=True,
              help="prompt, recommended, none, or comma-separated model selectors.")
@click.option("--out", "out_path", required=True, type=click.Path(path_type=Path))
@click.option("--deploy/--no-deploy", default=True)
@with_auth_options
@friendly_errors
def cmd_infra_models(
    resource_group, account_name, subscription_id, selection, out_path, deploy, endpoint, api_key,
    api_version, entra, profile_name, show_runtime_context, show_calling_time,
) -> None:
    del show_calling_time
    normalized = selection.strip().lower()
    if normalized == "none":
        write_models_file(out_path, [])
        console.print(
            "[green]ok[/green] no model deployments selected; available analyzers: "
            + ", ".join(NO_MODEL_ANALYZERS)
        )
        return

    client = _client(
        endpoint, api_key, api_version, entra, profile_name, show_runtime_context
    )
    analyzer = client.get_analyzer("prebuilt-document")
    supported = supported_model_names(analyzer)
    candidates = deployable_models(
        fetch_account_models(resource_group, account_name, subscription_id),
        supported,
    )
    if not candidates:
        raise CuCliError(
            "no live Content Understanding-supported models are deployable on this "
            "Microsoft Foundry resource."
        )

    if normalized == "prompt":
        if not sys.stdin.isatty():
            raise CuCliError(
                "live model selection requires an interactive terminal.",
                hint="set --infra-models to 'none', 'recommended', or explicit model names.",
            )
        selected = _prompt_for_models(candidates)
    elif normalized == "recommended":
        selected = recommended_models(candidates)
    else:
        selected = select_requested_models(candidates, selection.split(","))

    if deploy:
        deploy_models(resource_group, account_name, subscription_id, selected)
    write_models_file(out_path, selected)
    if selected:
        console.print(
            "[green]ok[/green] configured live model deployments: "
            + ", ".join(model.selector for model in selected)
        )
    else:
        console.print(
            "[green]ok[/green] no model deployments selected; available analyzers: "
            + ", ".join(NO_MODEL_ANALYZERS)
        )
