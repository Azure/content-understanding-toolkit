"""Shared model setup guidance for Content Understanding commands."""

from __future__ import annotations

from ..output import console


def print_model_setup_steps(
    endpoint: str,
    *,
    profile_name: str | None = None,
    heading: str = "Next steps:",
) -> None:
    sync_command = "cu profile sync-defaults"
    if profile_name:
        sync_command += f" --name {profile_name}"
    console.print(
        f"\n[bold]{heading}[/bold]\n\n"
        "1. If the required models are not already deployed, provision the "
        "recommended models:\n\n"
        "   [cyan]cu infra generate \\\n"
        f"     --foundry-endpoint {endpoint} \\\n"
        "     --models recommended[/cyan]\n\n"
        "   [cyan]cd provision\n"
        "   azd up[/cyan]\n\n"
        "   Omit [cyan]--models recommended[/cyan] to choose your own models in "
        "the text-based wizard.\n\n"
        "2. Configure Content Understanding defaults. Replace both model names "
        "and deployment names with the models and deployments you selected:\n\n"
        "   [cyan]cu defaults set \\\n"
        "     --model gpt-5.2=<your-gpt-5.2-deployment> \\\n"
        "     --model text-embedding-3-large=<your-embedding-deployment>[/cyan]\n\n"
        "3. Copy the resource's Content Understanding defaults into the "
        "selected local profile:\n\n"
        f"   [cyan]{sync_command}[/cyan]"
    )


def print_model_free_analyzers() -> None:
    console.print(
        "\n[bold]Available without model deployments:[/bold]\n"
        "  prebuilt-digitalParse, prebuilt-read, prebuilt-layout"
    )
