# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


_REGION_START = re.compile(r"^\s*# \[START (?P<id>[a-z][a-z0-9]*(?:_[a-z0-9]+)*)\]\s*$")
_REGION_END = re.compile(r"^\s*# \[END (?P<id>[a-z][a-z0-9]*(?:_[a-z0-9]+)*)\]\s*$")
_DOC_MARKER = re.compile(r"^<!-- Snippet:(?P<id>[a-z][a-z0-9]*(?:_[a-z0-9]+)*) -->$")


@dataclass(frozen=True)
class Snippet:
    identifier: str
    content: str
    source: Path
    line: int


def extract_test_snippets(test_root: Path) -> dict[str, Snippet]:
    snippets: dict[str, Snippet] = {}
    for path in sorted(test_root.rglob("test_*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            match = _REGION_START.match(lines[index])
            if match is None:
                index += 1
                continue

            identifier = match.group("id")
            start_line = index + 1
            body: list[str] = []
            index += 1
            while index < len(lines):
                end_match = _REGION_END.match(lines[index])
                if end_match is not None:
                    if end_match.group("id") != identifier:
                        raise ValueError(
                            f"{path}:{index + 1}: region {identifier!r} closes as "
                            f"{end_match.group('id')!r}"
                        )
                    break
                body.append(lines[index])
                index += 1
            else:
                raise ValueError(f"{path}:{start_line}: unclosed snippet region {identifier!r}")

            if identifier in snippets:
                previous = snippets[identifier]
                raise ValueError(
                    f"{path}:{start_line}: duplicate snippet {identifier!r}; first defined at "
                    f"{previous.source}:{previous.line}"
                )

            module = ast.parse("\n".join(body))
            assignments = [node for node in module.body if isinstance(node, ast.Assign)]
            if len(module.body) != 1 or len(assignments) != 1:
                raise ValueError(
                    f"{path}:{start_line}: snippet region {identifier!r} must contain exactly "
                    "one string assignment"
                )
            value = assignments[0].value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                raise ValueError(
                    f"{path}:{start_line}: snippet region {identifier!r} must assign a string"
                )
            snippets[identifier] = Snippet(
                identifier=identifier,
                content=value.value.rstrip("\n"),
                source=path,
                line=start_line,
            )
            index += 1
    return snippets


def synchronize_document(
    path: Path,
    snippets: dict[str, Snippet],
    *,
    update: bool,
) -> list[str]:
    original = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()
    output = list(lines)
    errors: list[str] = []
    seen: set[str] = set()
    index = 0

    while index < len(lines):
        marker = _DOC_MARKER.match(lines[index])
        if marker is None:
            index += 1
            continue

        identifier = marker.group("id")
        if identifier in seen:
            errors.append(f"{path}:{index + 1}: duplicate document snippet {identifier!r}")
            index += 1
            continue
        seen.add(identifier)
        snippet = snippets.get(identifier)
        if snippet is None:
            errors.append(f"{path}:{index + 1}: no test region defines snippet {identifier!r}")
            index += 1
            continue
        if index + 1 >= len(lines) or not lines[index + 1].startswith("```"):
            errors.append(f"{path}:{index + 1}: snippet marker must be followed by a code fence")
            index += 1
            continue

        fence_end = index + 2
        while fence_end < len(lines) and lines[fence_end] != "```":
            fence_end += 1
        if fence_end == len(lines):
            errors.append(f"{path}:{index + 2}: unclosed code fence for snippet {identifier!r}")
            break

        expected = snippet.content.splitlines()
        actual = lines[index + 2:fence_end]
        if actual != expected:
            if update:
                output[index + 2:fence_end] = expected
                delta = len(expected) - len(actual)
                lines[index + 2:fence_end] = expected
                fence_end += delta
            else:
                errors.append(
                    f"{path}:{index + 1}: snippet {identifier!r} differs from "
                    f"{snippet.source}:{snippet.line}; run "
                    "'python scripts/check_doc_snippets.py update'"
                )
        index = fence_end + 1

    if update:
        rendered = newline.join(output) + (newline if original.endswith(("\n", "\r")) else "")
        if rendered != original:
            path.write_text(rendered, encoding="utf-8", newline="")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize tested snippets with public docs.")
    parser.add_argument("mode", choices=("check", "update"))
    args = parser.parse_args(argv)

    product_root = Path(__file__).resolve().parents[1]
    test_root = product_root / "packages" / "standalone" / "tests"
    documents = (product_root / "README.md", product_root / "docs" / "usage-guide.md")
    try:
        snippets = extract_test_snippets(test_root)
        errors = [
            error
            for document in documents
            for error in synchronize_document(document, snippets, update=args.mode == "update")
        ]
    except (OSError, SyntaxError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"{args.mode}: synchronized {len(snippets)} tested documentation snippet(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())