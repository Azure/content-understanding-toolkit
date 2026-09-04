#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Check or add the required Microsoft copyright header to source files."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (
    ROOT / "packages/core/src",
    ROOT / "packages/core/tests",
    ROOT / "packages/standalone/src",
    ROOT / "packages/standalone/tests",
    ROOT / "scripts",
)
COMMENT_PREFIX = {
    ".bicep": "//",
    ".ps1": "#",
    ".py": "#",
    ".sh": "#",
}
COPYRIGHT = "Copyright (c) Microsoft Corporation."
LICENSE = "Licensed under the MIT license."


def source_files() -> list[Path]:
    return sorted(
        path
        for source_root in SOURCE_ROOTS
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix in COMMENT_PREFIX
    )


def header_index(lines: list[str]) -> int:
    index = 1 if lines and lines[0].startswith("#!") else 0
    while index < len(lines) and lines[index].casefold().startswith("#requires "):
        index += 1
    return index


def expected_header(path: Path) -> list[str]:
    prefix = COMMENT_PREFIX[path.suffix]
    return [f"{prefix} {COPYRIGHT}\n", f"{prefix} {LICENSE}\n"]


def has_header(path: Path, lines: list[str]) -> bool:
    index = header_index(lines)
    return lines[index : index + 2] == expected_header(path)


def add_header(path: Path, lines: list[str]) -> None:
    index = header_index(lines)
    updated = lines[:index] + expected_header(path) + ["\n"] + lines[index:]
    path.write_text("".join(updated), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="add missing headers instead of failing",
    )
    args = parser.parse_args()

    missing: list[Path] = []
    for path in source_files():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if has_header(path, lines):
            continue
        if args.fix:
            add_header(path, lines)
        else:
            missing.append(path)

    if missing:
        print("Missing required copyright header:")
        for path in missing:
            print(f"  {path.relative_to(ROOT)}")
        return 1

    action = "Updated" if args.fix else "Checked"
    print(f"{action} copyright headers in {len(source_files())} source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
