# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
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
_FENCE = re.compile(
    r"^ {0,3}(?P<fence>(?P<backticks>`{3,})|~{3,})"
    r"[ \t]*(?P<info>(?(backticks)[^`\r\n]*|[^\r\n]*))\r?\n?$"
)


@dataclass(frozen=True)
class Snippet:
    identifier: str
    content: str
    source: Path
    line: int
    language: str = ""
    members: tuple[str, ...] = ()
    test: str = ""
    step: int = -1
    verification: dict = field(default_factory=dict)
    fixtures: tuple[dict, ...] = ()
    last_step: int = -1


def _closes_fence(line: str, opening: str) -> bool:
    return re.fullmatch(
        rf" {{0,3}}{re.escape(opening[0])}{{{len(opening)},}}[ \t]*", line.rstrip("\r\n"),
    ) is not None


def discover_snippet_regions(test_root: Path) -> dict[str, tuple[Path, int, int, str]]:
    regions: dict[str, tuple[Path, int, int, str]] = {}
    for path in sorted(test_root.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]
        pending = []
        for token in tokenize.generate_tokens(StringIO(text).readline):
            if token.type != tokenize.COMMENT:
                continue
            line, column = token.start
            marker = _REGION_START.fullmatch(token.string)
            closing = _REGION_END.fullmatch(token.string)
            if marker is None and closing is None:
                if re.match(r"#\s*region\s+Snippet\b", token.string):
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


def discover_executable_examples(test_root: Path) -> dict[str, tuple[Path, int, str]]:
    return {
        identifier: (path, start, function)
        for identifier, (path, start, _end, function) in discover_snippet_regions(test_root).items()
    }


def discover_scenarios(test_root: Path) -> dict[str, tuple[Path, int, tuple[str, ...]]]:
    scenarios: dict[str, tuple[Path, int, tuple[str, ...]]] = {}
    for path in sorted(test_root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for assignment in tree.body:
            if not isinstance(assignment, ast.Assign) or not any(
                isinstance(target, ast.Name) and target.id == "DOC_SCENARIOS"
                for target in assignment.targets
            ):
                continue
            if not isinstance(assignment.value, ast.Dict):
                raise ValueError(f"{path}:{assignment.lineno}: DOC_SCENARIOS must be a literal mapping")
            for key, value in zip(assignment.value.keys, assignment.value.values):
                name, members = ast.literal_eval(key), ast.literal_eval(value)
                if not isinstance(name, str) or not re.fullmatch(_ID, name) or name.startswith("test_"):
                    raise ValueError(f"{path}:{value.lineno}: invalid scenario name {name!r}")
                if name in scenarios:
                    raise ValueError(f"{path}:{value.lineno}: duplicate scenario {name!r}")
                if not isinstance(members, (tuple, list)) or len(members) < 2 or any(
                    not isinstance(member, str) or not re.fullmatch(_ID, member) for member in members
                ):
                    raise ValueError(
                        f"{path}:{value.lineno}: scenario {name!r} must contain at least two "
                        "source names; reference single examples directly"
                    )
                scenarios[name] = (path, value.lineno, tuple(members))
    return scenarios


def compose_scenarios(
    snippets: dict[str, Snippet], scenarios: dict[str, tuple[Path, int, tuple[str, ...]]],
) -> dict[str, Snippet]:
    composed = dict(snippets)
    for name, (path, line, members) in scenarios.items():
        if name in snippets:
            raise ValueError(f"{path}:{line}: scenario {name!r} duplicates an example name")
        missing = set(members) - snippets.keys()
        if missing:
            raise ValueError(
                f"{path}:{line}: scenario {name!r} has no executed source: {', '.join(sorted(missing))}"
            )
        sources = [snippets[member] for member in members]
        languages = {source.language for source in sources}
        if len(languages) != 1:
            raise ValueError(f"{path}:{line}: scenario {name!r} mixes source languages")
        same_test = bool(sources[0].test) and all(source.test == sources[0].test for source in sources)
        continuous = same_test and all(source.step >= 0 for source in sources) and all(
            following.step == (current.last_step if current.last_step >= 0 else current.step) + 1
            for current, following in zip(sources, sources[1:])
        ) and all(source.verification.get("consecutive", True) for source in sources)
        verification = {
            "mode": "continuous" if continuous else "composed",
            "source_modes": {source.identifier: source.verification.get("mode", "unclassified") for source in sources},
            "workflow_test": sources[0].test if continuous else None,
        }
        composed[name] = Snippet(
            name, "\n\n".join(source.content for source in sources), path, line,
            sources[0].language, members, verification=verification,
        )
    return composed


def execute_test_examples(product_root: Path, test_root: Path) -> dict[str, Snippet]:
    sources = discover_executable_examples(test_root)
    if not sources:
        return {}
    targets = sorted({f"{path}::{function}" for path, _line, function in sources.values()})
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("CU_", "CONTENTUNDERSTANDING_"))
    }
    environment.update(CU_TEST_REC_MODE="playback", CU_NO_UPDATE_CHECK="1")
    with tempfile.TemporaryDirectory(prefix="cu-doc-examples-") as directory:
        catalog_path = Path(directory) / "catalog.json"
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", "-q", "--tb=short", "--strict-markers",
                "-c", str(product_root / "packages/standalone/pyproject.toml"),
                "--command-catalog", str(catalog_path), *targets,
            ],
            cwd=product_root, env=environment, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            raise ValueError(f"documentation source tests failed:\n{result.stdout}\n{result.stderr}")
        if not catalog_path.exists():
            raise ValueError("documentation tests did not export a command catalog")
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    exported = catalog["examples"]
    missing = sources.keys() - exported.keys()
    if missing:
        raise ValueError(
            f"documentation examples did not execute successfully: {', '.join(sorted(missing))}; "
            "restore the source tests and required offline fixtures/recordings"
        )
    snippets = {
        identifier: Snippet(
            identifier, exported[identifier]["content"], path, line,
            exported[identifier]["language"],
            test=exported[identifier]["test"], step=exported[identifier].get("step", -1),
            verification=exported[identifier].get("verification", {}),
            fixtures=tuple(exported[identifier].get("fixtures", [])),
            last_step=exported[identifier].get("last_step", -1),
        )
        for identifier, (path, line, _function) in sources.items()
    }
    return compose_scenarios(snippets, discover_scenarios(test_root))


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
                    f"{path}:{index + 1}: code block has no Snippet ID; "
                    "export its command from a test and add a Snippet marker"
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
            errors.append(f"{path}:{index + 1}: snippet {identifier!r} has no tested source")
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


def validate_document_references(documents, snippets: dict[str, Snippet]) -> list[str]:
    referenced: set[str] = set()
    errors: list[str] = []
    for path in documents:
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
            if marker is None:
                continue
            referenced.add(marker.group("id"))
    referenced.update(
        member for name in tuple(referenced) if name in snippets for member in snippets[name].members
    )
    for identifier in sorted(snippets.keys() - referenced):
        snippet = snippets[identifier]
        errors.append(
            f"{snippet.source}:{snippet.line}: exported example {identifier!r} is not used; "
            "add a document reference or remove its export ID"
        )
    return errors


def synchronize_documents(documents, snippets: dict[str, Snippet], *, update: bool) -> list[str]:
    errors = validate_document_references(documents, snippets)
    errors.extend(
        error for path in documents
        for error in synchronize_document(path, snippets, update=True, write=False)
    )
    if errors:
        return errors
    return [
        error for path in documents
        for error in synchronize_document(path, snippets, update=update)
    ]


def validate_report_path(report_path: Path, documents: tuple[Path, ...], test_root: Path) -> None:
    target = report_path.resolve()
    if target.is_dir():
        raise ValueError(f"--report must name a file, not a directory: {report_path}")
    protected = (Path(__file__), *documents, *test_root.rglob("*.py"))
    target_exists = target.exists()
    for source in protected:
        if target == source.resolve() or (target_exists and source.exists() and target.samefile(source)):
            raise ValueError(f"--report must not overwrite an input file: {report_path} ({source})")


def build_verification_report(snippets: dict[str, Snippet], product_root: Path, errors: list[str]) -> dict:
    examples = {}
    scenarios = {}
    for identifier, snippet in sorted(snippets.items()):
        source = snippet.source.relative_to(product_root).as_posix() if snippet.source.is_relative_to(product_root) else snippet.source.name
        entry = {
            "source": source,
            "line": snippet.line,
            "verification": snippet.verification,
        }
        if snippet.members:
            entry["members"] = list(snippet.members)
            scenarios[identifier] = entry
        else:
            entry.update(test=snippet.test, fixtures=list(snippet.fixtures))
            examples[identifier] = entry
    return {
        "status": "failed" if errors else "passed",
        "errors": errors,
        "examples": examples,
        "scenarios": scenarios,
        "notes": [
            "Source names are unique; documents may reuse them.",
            "Continuous means consecutive commands in one passing test, not live Azure execution.",
            "Mocked service examples are contract tests, not proof of real service behavior.",
            "Fixture hashes identify the input used by a test; scrubbed recordings do not prove original input identity.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize tested snippets with public docs.")
    parser.add_argument("mode", choices=("check", "update"))
    parser.add_argument("--report", type=Path, help="Write verification evidence to a JSON artifact.")
    args = parser.parse_args(argv)

    product_root = Path(__file__).resolve().parents[1]
    test_root = product_root / "packages" / "standalone" / "tests"
    documents = (product_root / "README.md", product_root / "docs" / "usage-guide.md")
    if args.report is not None:
        try:
            validate_report_path(args.report, documents, test_root)
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
    snippets: dict[str, Snippet] = {}
    try:
        snippets = execute_test_examples(product_root, test_root)
        errors = synchronize_documents(documents, snippets, update=args.mode == "update")
    except (OSError, SyntaxError, ValueError) as exc:
        errors = [str(exc)]

    if args.report is not None:
        try:
            validate_report_path(args.report, documents, test_root)
            report = build_verification_report(snippets, product_root, errors)
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError) as exc:
            errors.append(f"cannot write verification report: {exc}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    scenario_count = sum(bool(snippet.members) for snippet in snippets.values())
    print(
        f"{args.mode}: synchronized {len(snippets) - scenario_count} tested example(s) "
        f"and {scenario_count} named scenario(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())