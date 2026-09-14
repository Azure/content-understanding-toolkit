#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Check or update the generated public-document Snippet inventory."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (Path("README.md"), Path("docs/usage-guide.md"))
INVENTORY = Path("docs/snippet-inventory.json")
FENCE_RE = re.compile(
    r"^```(?P<language>\S+)\s+Snippet:"
    r"(?P<identifier>[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)\s*$"
)


def build_inventory(root: Path) -> list[dict[str, object]]:
    inventory = []
    seen: dict[str, str] = {}
    for relative_path in DOCUMENTS:
        path = root / relative_path
        in_fence = False
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.startswith("```"):
                continue
            if in_fence:
                in_fence = False
                continue
            in_fence = True
            match = FENCE_RE.fullmatch(line)
            if match is None:
                raise ValueError(
                    f"{relative_path.as_posix()}:{line_number}: fence is missing a valid "
                    "Snippet ID"
                )
            identifier = match.group("identifier")
            location = f"{relative_path.as_posix()}:{line_number}"
            if previous := seen.get(identifier):
                raise ValueError(
                    f"Snippet:{identifier} is duplicated at {previous} and {location}"
                )
            seen[identifier] = location
            inventory.append(
                {
                    "id": identifier,
                    "language": match.group("language"),
                    "document": relative_path.as_posix(),
                }
            )
        if in_fence:
            raise ValueError(f"{relative_path.as_posix()}: unclosed Snippet fence")
    return inventory


def render_inventory(root: Path) -> str:
    payload = {
        "generatedFrom": [path.as_posix() for path in DOCUMENTS],
        "snippets": build_inventory(root),
    }
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def update_inventory(root: Path) -> None:
    path = root / INVENTORY
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_inventory(root)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(path)


def check_inventory(root: Path) -> bool:
    path = root / INVENTORY
    expected = render_inventory(root)
    actual = path.read_text(encoding="utf-8") if path.exists() else None
    if actual == expected:
        return True
    print(
        f"{INVENTORY.as_posix()} is out of date with README.md and "
        "docs/usage-guide.md."
    )
    print("Run: python scripts/check_doc_snippets.py update")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "update"))
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        if args.mode == "update":
            update_inventory(args.root)
            print(f"Updated {INVENTORY.as_posix()}.")
            return 0
        return 0 if check_inventory(args.root) else 1
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())