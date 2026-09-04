# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared rendering for command examples in terminal help."""

from __future__ import annotations

from rich.markup import escape


def common_commands(*examples: tuple[str, str]) -> str:
    """Render command-first examples with consistent syntax highlighting."""
    blocks = ["[bold cyan]Common commands:[/bold cyan]"]
    for command, description in examples:
        tokens = command.split()
        styled: list[str] = []
        command_path = True
        for token in tokens:
            safe = escape(token)
            if token.startswith("-"):
                style = "bold cyan"
                command_path = False
            elif token.isupper() or any(part.isupper() for part in token.split(".")):
                style = "bold yellow"
                command_path = False
            elif command_path:
                style = "bold green"
            else:
                style = "bold magenta"
            styled.append(f"[{style}]{safe}[/{style}]")
        blocks.append(" ".join(styled))
        blocks.append(f"[white]\u00a0\u00a0{escape(description)}[/white]")
    return "\n\n".join(blocks)
