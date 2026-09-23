# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from io import StringIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tokenize

from markdown_it import MarkdownIt


_ID = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"
_DOC_MARKER = re.compile(rf"^<!-- Snippet:(?P<id>{_ID}) -->$")
_REGION_START = re.compile(rf"#\s*region\s+Snippet:(?P<id>{_ID})\s*$")
_REGION_END = re.compile(r"#\s*endregion\s*$")
_ANY_REGION = re.compile(r"#\s*region\s+Snippet\b")
_FENCE = re.compile(
    r"^ {0,3}(?P<fence>(?P<backticks>`{3,})|~{3,})"
    r"[ \t]*(?P<info>(?(backticks)[^`\r\n]*|[^\r\n]*))\r?\n?$"
)
_TEST_ROOT = Path("packages/standalone/tests")
DOCUMENTS = {
    Path("README.md"): _TEST_ROOT / "docs/test_readme.py",
    Path("docs/usage-guide.md"): _TEST_ROOT / "docs/test_usage_guide.py",
}
OUTPUT_ENVIRONMENT = "CU_DOC_SNIPPETS_OUTPUT"


@dataclass(frozen=True)
class Snippet:
    identifier: str
    content: str
    source: Path
    line: int
    language: str = ""
    nested: bool = False


def _closes_fence(line: str, opening: str) -> bool:
    return re.fullmatch(
        rf" {{0,3}}{re.escape(opening[0])}{{{len(opening)},}}[ \t]*", line.rstrip("\r\n"),
    ) is not None


def discover_snippet_regions(path: Path) -> dict[str, tuple[Path, int, int, str]]:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    regions: dict[str, tuple[Path, int, int, str]] = {}
    pending = []
    for token in tokenize.generate_tokens(StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        line, column = token.start
        marker = _REGION_START.fullmatch(token.string)
        closing = _REGION_END.fullmatch(token.string)
        if marker is None and closing is None:
            if _ANY_REGION.match(token.string):
                raise ValueError(f"{path}:{line}: malformed Snippet region")
            continue
        if token.line[:column].strip():
            raise ValueError(f"{path}:{line}: Snippet region markers must be on their own lines")
        if marker is not None:
            identifier = marker.group("id")
            if identifier.startswith("test_"):
                raise ValueError(f"{path}:{line}: use a semantic Snippet name without test_")
            owner = next((
                function for function in functions
                if function.lineno < line <= function.end_lineno and column > function.col_offset
            ), None)
            if owner is None:
                raise ValueError(f"{path}:{line}: Snippet region must be inside a test function")
            if identifier in regions or any(item[0] == identifier for item in pending):
                raise ValueError(f"{path}:{line}: duplicate Snippet region {identifier!r}")
            pending.append((identifier, line, column, owner))
            continue
        if not pending:
            raise ValueError(f"{path}:{line}: endregion has no matching Snippet region")
        identifier, start, indentation, owner = pending.pop()
        if column != indentation or any(start < node.lineno < line for node in tree.body):
            raise ValueError(f"{path}:{line}: Snippet region {identifier!r} crosses a test boundary")
        if not any(isinstance(node, ast.Call) and start < node.lineno < line for node in ast.walk(owner)):
            raise ValueError(f"{path}:{start}: Snippet region {identifier!r} contains no calls")
        if any(
            isinstance(node, ast.Call) and start < node.lineno < line <= node.end_lineno
            for node in ast.walk(owner)
        ):
            raise ValueError(f"{path}:{line}: Snippet region {identifier!r} splits a multiline call")
        regions[identifier] = (path, start, line, owner.name)
    if pending:
        identifier, start, _indentation, _owner = pending[-1]
        raise ValueError(f"{path}:{start}: unclosed Snippet region {identifier!r}")
    return regions


def nested_regions(regions: dict[str, tuple[Path, int, int, str]]) -> set[str]:
    return {
        identifier for identifier, (_path, start, end, _function) in regions.items()
        if any(
            outer_start < start and end < outer_end
            for other, (_outer_path, outer_start, outer_end, _outer_function) in regions.items()
            if other != identifier
        )
    }


def find_stray_regions(test_root: Path, sources: set[Path]) -> list[str]:
    allowed = ", ".join(sorted(source.name for source in sources))
    errors: list[str] = []
    for path in sorted(test_root.rglob("*.py")):
        if path.resolve() in sources:
            continue
        for token in tokenize.generate_tokens(StringIO(path.read_text(encoding="utf-8")).readline):
            if token.type == tokenize.COMMENT and _ANY_REGION.match(token.string):
                errors.append(
                    f"{path}:{token.start[0]}: Snippet regions belong only in the documentation "
                    f"tests ({allowed}); move this example there"
                )
    return errors


def execute_documentation_tests(product_root: Path, sources: list[Path]) -> dict[str, dict[str, dict]]:
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("CU_", "CONTENTUNDERSTANDING_"))
    }
    environment.update(CU_TEST_REC_MODE="playback", CU_NO_UPDATE_CHECK="1")
    with tempfile.TemporaryDirectory(prefix="cu-doc-snippets-") as directory:
        output = Path(directory) / "snippets.json"
        environment[OUTPUT_ENVIRONMENT] = str(output)
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", "-q", "--tb=short", "--strict-markers",
                "-c", str(product_root / "packages/standalone/pyproject.toml"),
                *(str(source) for source in sources),
            ],
            cwd=product_root, env=environment, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            raise ValueError(f"documentation tests failed:\n{result.stdout}\n{result.stderr}")
        if not output.exists():
            raise ValueError("documentation tests did not export their Snippet regions")
        return json.loads(output.read_text(encoding="utf-8"))


def collect_snippets(product_root: Path) -> dict[Path, dict[str, Snippet]]:
    sources = {document: (product_root / source).resolve() for document, source in DOCUMENTS.items()}
    errors = find_stray_regions(product_root / _TEST_ROOT, set(sources.values()))
    missing_sources = [
        f"{source}: missing documentation test for {document.as_posix()}"
        for document, source in sources.items() if not source.is_file()
    ]
    if errors or missing_sources:
        raise ValueError("\n".join([*errors, *missing_sources]))
    regions = {document: discover_snippet_regions(source) for document, source in sources.items()}
    published = execute_documentation_tests(product_root, list(sources.values()))
    snippets: dict[Path, dict[str, Snippet]] = {}
    for document, source in sources.items():
        entries = published.get(source.name, {})
        unpublished = sorted(regions[document].keys() - entries.keys())
        if unpublished:
            errors.extend(
                f"{source}:{regions[document][identifier][1]}: Snippet region {identifier!r} "
                "published nothing; call a snippet helper inside it"
                for identifier in unpublished
            )
            continue
        snippets[document] = {
            identifier: Snippet(
                identifier, entries[identifier]["content"], source, start, entries[identifier]["language"],
                nested=identifier in nested,
            )
            for nested in (nested_regions(regions[document]),)
            for identifier, (_path, start, _end, _function) in regions[document].items()
        }
    if errors:
        raise ValueError("\n".join(errors))
    return snippets


def synchronize_document(
    path: Path,
    snippets: dict[str, Snippet],
    *,
    update: bool,
    write: bool = True,
) -> list[str]:
    original = path.read_bytes().decode("utf-8")
    nested_fences = [
        f"{path}:{token.map[0] + 1}: nested code fence is not supported; "
        "move the code block and its Snippet marker outside lists and block quotes"
        for token in MarkdownIt("commonmark").parse(original)
        if token.type == "fence" and token.level > 0 and token.map is not None
    ]
    if nested_fences:
        return nested_fences
    lines = original.splitlines(keepends=True)
    output: list[str] = []
    errors: list[str] = []
    index = 0

    while index < len(lines):
        marker = _DOC_MARKER.fullmatch(lines[index].rstrip("\r\n"))
        if marker is None:
            if _FENCE.match(lines[index]):
                errors.append(
                    f"{path}:{index + 1}: code block has no Snippet ID; add a Snippet region "
                    "to the documentation test and a Snippet marker before this block"
                )
                opening = _FENCE.fullmatch(lines[index]).group("fence")
                output.append(lines[index])
                index += 1
                while index < len(lines):
                    output.append(lines[index])
                    closing = _closes_fence(lines[index], opening)
                    index += 1
                    if closing:
                        break
                continue
            if "<!-- Snippet:" in lines[index]:
                errors.append(f"{path}:{index + 1}: malformed Snippet marker")
            output.append(lines[index])
            index += 1
            continue

        identifier = marker.group("id")
        snippet = snippets.get(identifier)
        if snippet is None:
            errors.append(
                f"{path}:{index + 1}: snippet {identifier!r} has no Snippet region in the "
                "documentation test for this document"
            )
            output.append(lines[index])
            index += 1
            continue
        fence = _FENCE.fullmatch(lines[index + 1]) if index + 1 < len(lines) else None
        if fence is None:
            errors.append(f"{path}:{index + 1}: snippet marker must be followed by a code fence")
            output.append(lines[index])
            index += 1
            continue

        fence_end = index + 2
        opening = fence.group("fence")
        while fence_end < len(lines):
            if _closes_fence(lines[fence_end], opening):
                break
            fence_end += 1
        if fence_end == len(lines):
            errors.append(f"{path}:{index + 2}: unclosed code fence for snippet {identifier!r}")
            break

        info = fence.group("info").split(maxsplit=1)
        language = info[0] if info else ""
        if snippet.language and snippet.language != language:
            errors.append(
                f"{path}:{index + 1}: snippet {identifier!r} language differs from "
                f"tested source: expected {snippet.language!r}"
            )
        expected = snippet.content.splitlines()
        if any(_closes_fence(line, opening) for line in expected):
            errors.append(
                f"{path}:{index + 1}: snippet {identifier!r} content can close its enclosing "
                "code fence; use a longer or different fence"
            )
        actual = [line.rstrip("\r\n") for line in lines[index + 2:fence_end]]
        output.extend(lines[index:index + 2])
        if actual != expected:
            if not update:
                errors.append(
                    f"{path}:{index + 1}: snippet {identifier!r} differs from "
                    f"{snippet.source}:{snippet.line}; run "
                    "'python scripts/update-snippet.py update'"
                )
        if update and actual != expected:
            newline = "\r\n" if lines[index + 1].endswith("\r\n") else "\n"
            output.extend(line + newline for line in expected)
        else:
            output.extend(lines[index + 2:fence_end])
        output.append(lines[fence_end])
        index = fence_end + 1

    if update and write and not errors:
        rendered = "".join(output)
        if rendered != original:
            path.write_text(rendered, encoding="utf-8", newline="")
    return errors


def validate_document_references(path: Path, snippets: dict[str, Snippet]) -> list[str]:
    referenced: set[str] = set()
    opening = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if opening:
            if _closes_fence(line, opening):
                opening = ""
            continue
        fence = _FENCE.fullmatch(line)
        if fence:
            opening = fence.group("fence")
            continue
        marker = _DOC_MARKER.fullmatch(line)
        if marker is not None:
            referenced.add(marker.group("id"))
    return [
        f"{snippets[identifier].source}:{snippets[identifier].line}: Snippet region "
        f"{identifier!r} is not used by {path.name}; add a marker or remove the region"
        for identifier in sorted(snippets.keys() - referenced)
        if not snippets[identifier].nested
    ]


def synchronize_documents(
    product_root: Path, snippets: dict[Path, dict[str, Snippet]], *, update: bool,
) -> list[str]:
    errors: list[str] = []
    for document, items in snippets.items():
        errors.extend(validate_document_references(product_root / document, items))
        errors.extend(synchronize_document(product_root / document, items, update=True, write=False))
    if errors:
        return errors
    return [
        error for document, items in snippets.items()
        for error in synchronize_document(product_root / document, items, update=update)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize tested snippets with public docs.")
    parser.add_argument("mode", choices=("check", "update"))
    args = parser.parse_args(argv)

    product_root = Path(__file__).resolve().parents[1]
    snippets: dict[Path, dict[str, Snippet]] = {}
    try:
        snippets = collect_snippets(product_root)
        errors = synchronize_documents(product_root, snippets, update=args.mode == "update")
    except (OSError, SyntaxError, ValueError) as exc:
        errors = [str(exc)]

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    counts = ", ".join(f"{len(items)} in {document.as_posix()}" for document, items in snippets.items())
    print(f"{args.mode}: synchronized {sum(map(len, snippets.values()))} tested snippet(s) ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())