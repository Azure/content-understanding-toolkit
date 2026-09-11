# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Safe artifact writers owned by the Azure CLI frontend."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from cu_cli_core.errors import ConflictError, LocalIOError
from cu_cli_core.serialization import to_plain_value


def require_available(path: Path | None, *, force: bool, description: str) -> None:
    if path is not None and path.exists() and not force:
        raise ConflictError(
            f"{description} already exists: {path}",
            hint="choose another path or pass --force to replace it.",
        )


def write_text(path: Path, content: str, *, overwrite: bool) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not overwrite:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
            return
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                stream.write(content)
                temporary = Path(stream.name)
            os.replace(temporary, path)
        except Exception:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise LocalIOError(f"could not write {path}: {exc}") from exc


def write_json(path: Path, value: Any, *, overwrite: bool) -> None:
    payload = json.dumps(to_plain_value(value), indent=2, ensure_ascii=False)
    write_text(path, payload + "\n", overwrite=overwrite)