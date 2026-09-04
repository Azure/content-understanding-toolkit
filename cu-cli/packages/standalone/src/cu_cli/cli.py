"""Top-level CLI: registers all command groups under ``cu`` / ``cu-cli``.

Uses ``rich-click`` for the help UX. Running ``cu`` with no subcommand prints
the full help.
"""

from __future__ import annotations

import sys

import rich_click as click

from . import __version__
from .apiversion import API_VERSION_HELP
from .commands.analyze import cmd_analyze
from .commands.analyzer import analyzer_group
from .commands.profile_cmd import profile_group
from .commands.defaults import defaults_group
from .commands.doctor import cmd_doctor
from .commands.env_var import env_var_group
from .commands.provision import cmd_provision
from .commands.upgrade import cmd_upgrade
from .commands._help import common_commands
from .commands._infra_models import cmd_infra_models


def _force_utf8_io() -> None:
    """Make stdout/stderr UTF-8 so redirects on Windows cmd don't crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_force_utf8_io()

# --- rich-click look & feel ------------------------------------------------
_rc = click.rich_click
_rc.MAX_WIDTH = 110
_rc.TEXT_MARKUP = "rich"
_rc.STYLE_OPTION = "bold cyan"
_rc.STYLE_COMMAND = "bold magenta"
_rc.STYLE_SWITCH = "bold cyan"
_rc.HEADER_TEXT = (
    "[bold cyan]CU CLI[/] — [white]Azure Content Understanding Command Line Interface[/]"
)
_rc.FOOTER_TEXT = ""

_COMMAND_GROUPS: list = [
    {"name": "Setup", "commands": ["provision", "profile", "doctor", "env-var"]},
    {"name": "Content Understanding", "commands": ["analyze", "analyzer", "defaults"]},
    {"name": "Maintenance", "commands": ["upgrade"]},
]
_rc.COMMAND_GROUPS = {"cu": _COMMAND_GROUPS, "cu-cli": _COMMAND_GROUPS}


CLI_HELP = (
    "Use Azure Content Understanding through a Microsoft Foundry resource to process files from the "
    "terminal. An analyzer processes a document, image, audio file, or video and "
    "returns an analyzer result with extracted content and structured fields. Use "
    "a ready-to-use prebuilt analyzer or create a custom analyzer for your scenario.\n\n"
    "[white] [/white]\n\n"
    "`cu provision` provisions the required Microsoft Foundry resource, optionally "
    "deploys selected supported large language models (LLMs) and embeddings models, "
    "and configures Content Understanding defaults that map model names to deployments. "
    "A local "
    "CU CLI profile stores the resource endpoint, authentication method, API version, "
    "and model mappings."
)

class OrderedHelpGroup(click.RichGroup):
    """Preserve command registration order in help output."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


@click.group(
    cls=OrderedHelpGroup,
    help=CLI_HELP,
    epilog=common_commands(
        (
            "cu provision",
            "Create and configure a Microsoft Foundry resource when you do not yet have "
            "a configured Content Understanding endpoint.",
        ),
        (
            "cu profile set endpoint https://<resource-name>.services.ai.azure.com/",
            "Connect CU CLI to an existing Microsoft Foundry resource endpoint. Replace "
            "<resource-name> with the name of your resource.",
        ),
        (
            "cu doctor",
            "Verify the active profile, authentication, resource connectivity, and "
            "Content Understanding defaults.",
        ),
        (
            "cu analyze sample.pdf -a prebuilt-layout",
            "Analyze a PDF with the prebuilt-layout analyzer and print its extracted text, "
            "document structure, and layout information as Markdown.",
        ),
    )
    + "\n\n[white]For environment-variable help, run "
      "[bold cyan]cu env-var -h[/bold cyan].[/white]\n\n"
      f"[bold]{API_VERSION_HELP}[/bold]",
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(__version__, "-V", "--version", prog_name="cu")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Root group. A bare ``cu`` prints help."""
    _force_utf8_io()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


main.add_command(cmd_provision)
main.add_command(profile_group)
main.add_command(cmd_doctor)
main.add_command(env_var_group)
main.add_command(cmd_analyze)
main.add_command(analyzer_group)
main.add_command(defaults_group)
main.add_command(cmd_upgrade)
main.add_command(cmd_infra_models)


if __name__ == "__main__":
    main()
