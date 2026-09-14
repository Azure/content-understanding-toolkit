#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Ensure frontend packages consume the CU SDK only through ``cu-cli-core``."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
SDK_MODULE = "azure.ai.contentunderstanding"
SDK_DISTRIBUTION = "azure-ai-contentunderstanding"
FRONTEND_SOURCE_ROOTS = (
    ROOT / "packages/standalone/src/cu_cli",
    ROOT / "packages/standalone/tests",
    ROOT / "packages/azure-cli-extension/azext_content_understanding",
    ROOT / "packages/azure-cli-extension/tests",
)
FRONTEND_PROJECTS = (
    ROOT / "packages/standalone/pyproject.toml",
    ROOT / "packages/azure-cli-extension/pyproject.toml",
)


def _canonicalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _dependency_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return _canonicalize_name(match.group(1)) if match else ""


def _dependency_groups(project: dict[str, Any]) -> list[str]:
    dependencies = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        dependencies.extend(group)
    return dependencies


def find_violations(root: Path = ROOT) -> list[str]:
    """Return direct frontend CU SDK references and dependency declarations."""
    violations: list[str] = []
    source_roots = tuple(root / path.relative_to(ROOT) for path in FRONTEND_SOURCE_ROOTS)
    projects = tuple(root / path.relative_to(ROOT) for path in FRONTEND_PROJECTS)

    for source_root in source_roots:
        for path in sorted(source_root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    references = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    references = [node.module or ""]
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    references = [node.value]
                else:
                    continue
                if any(SDK_MODULE in reference for reference in references):
                    relative = path.relative_to(root)
                    violations.append(f"{relative}:{node.lineno}: direct CU SDK reference")

    for path in projects:
        project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
        for requirement in _dependency_groups(project):
            if _dependency_name(requirement) == SDK_DISTRIBUTION:
                relative = path.relative_to(root)
                violations.append(f"{relative}: direct CU SDK dependency: {requirement}")
    return violations


def main() -> int:
    violations = find_violations()
    if violations:
        print("Frontend packages must access the CU SDK through cu-cli-core:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    print("Validated frontend CU SDK boundary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
