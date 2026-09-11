#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Validate that a package-index release matches the selected source commit."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.request import urlopen

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_REPOSITORY = "Azure/content-understanding-toolkit"
CANONICAL_REF = "refs/heads/main"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
PACKAGE_PATHS = {
    "core": Path("packages/core/pyproject.toml"),
    "cli": Path("packages/standalone/pyproject.toml"),
    "extension": Path("packages/azure-cli-extension/pyproject.toml"),
}
CANONICAL_TEMPLATE_FILES = {
    "README.md",
    "azure.yaml",
    "hooks/postprovision.ps1",
    "hooks/postprovision.sh",
    "infra/main.bicep",
    "infra/main.parameters.json",
    "infra/models.json",
    "infra/modules/foundry.bicep",
}
PACKAGE_INDEX_API_URLS = {
    "pypi": "https://pypi.org/pypi",
    "testpypi": "https://test.pypi.org/pypi",
}


def load_project(path: Path) -> dict[str, object]:
    with path.open("rb") as stream:
        project = tomllib.load(stream).get("project")
    if not isinstance(project, dict):
        raise ValueError(f"{path} does not contain a [project] table")
    return project


def project_version(project: dict[str, object], path: Path) -> str:
    version = project.get("version")
    if not isinstance(version, str):
        raise ValueError(f"{path} does not define a string project.version")
    return version


def validate_request_context(
    *,
    expected_commit: str,
    actual_commit: str,
    repository: str,
    ref: str,
) -> None:
    if repository != CANONICAL_REPOSITORY:
        raise ValueError(
            f"releases must run in {CANONICAL_REPOSITORY}, not {repository}"
        )
    if ref != CANONICAL_REF:
        raise ValueError(f"releases must run from {CANONICAL_REF}, not {ref}")
    if SHA_PATTERN.fullmatch(expected_commit) is None:
        raise ValueError("expected commit must be a lowercase 40-character SHA")
    if expected_commit != actual_commit:
        raise ValueError(
            f"selected commit {expected_commit} does not match workflow commit "
            f"{actual_commit}"
        )


def validate_core_assets(root: Path) -> None:
    template_root = root / "packages/core/src/cu_cli_core/resources/azd_template"
    actual = {
        path.relative_to(template_root).as_posix()
        for path in template_root.rglob("*")
        if path.is_file()
    }
    if actual != CANONICAL_TEMPLATE_FILES:
        raise ValueError(
            "cu-cli-core must contain exactly the canonical azd template files; "
            f"expected {sorted(CANONICAL_TEMPLATE_FILES)}, found {sorted(actual)}"
        )
    duplicate_roots = (
        root / "packages/standalone/src/cu_cli/resources/azd_template",
        root / "packages/azure-cli-extension/azext_content_understanding/_infra_template",
    )
    duplicates = [path for path in duplicate_roots if path.exists()]
    if duplicates:
        raise ValueError(
            "frontend packages must not contain duplicate azd templates: "
            + ", ".join(str(path.relative_to(root)) for path in duplicates)
        )


def validate_frontend_metadata(root: Path, frontend: str) -> str:
    core_path = root / PACKAGE_PATHS["core"]
    core_version = project_version(load_project(core_path), core_path)
    core_version_match = re.fullmatch(
        r"(\d+)\.(\d+)\.(\d+)(?:(?:a|b|rc)\d+)?",
        core_version,
    )
    if core_version_match is None:
        raise ValueError(
            "cu-cli-core version must be a stable or preview PEP 440 release: "
            f"{core_version}"
        )
    core_major, core_minor, _ = (int(part) for part in core_version_match.groups())
    core_upper_bound = f"{core_major}.{core_minor + 1}.0"
    frontend_path = root / PACKAGE_PATHS[frontend]
    dependencies = load_project(frontend_path).get("dependencies")
    if not isinstance(dependencies, list) or not all(
        isinstance(dependency, str) for dependency in dependencies
    ):
        raise ValueError(f"{frontend_path} does not define string dependencies")

    expected_requirement = f"cu-cli-core>={core_version},<{core_upper_bound}"
    if expected_requirement not in dependencies:
        raise ValueError(
            f"{frontend} must require the selected core release exactly as "
            f"{expected_requirement}"
        )

    return core_version


def validate_cli_changelog(root: Path, cli_version: str) -> None:

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = re.search(
        rf"^## {re.escape(cli_version)} \(([^)]+)\)$",
        changelog,
        flags=re.MULTILINE,
    )
    if heading is None or heading.group(1).casefold() == "unreleased":
        raise ValueError(
            f"CHANGELOG.md must date the {cli_version} release as YYYY-MM-DD"
        )
    try:
        date.fromisoformat(heading.group(1))
    except ValueError as error:
        raise ValueError(
            f"CHANGELOG.md release date is invalid: {heading.group(1)}"
        ) from error


def verify_package_release(
    project_name: str,
    version: str,
    index: str,
) -> None:
    url = f"{PACKAGE_INDEX_API_URLS[index]}/{project_name}/json"
    with urlopen(url, timeout=30) as response:
        payload = json.load(response)
    releases = payload.get("releases")
    if not isinstance(releases, dict) or not releases.get(version):
        raise ValueError(
            f"{project_name} {version} must be published to {index} before cu-cli"
        )


def validate_release(
    *,
    root: Path,
    index: str,
    package: str,
    expected_version: str,
    expected_commit: str,
    actual_commit: str,
    repository: str,
    ref: str,
    verify_core_on_index: bool,
) -> None:
    validate_request_context(
        expected_commit=expected_commit,
        actual_commit=actual_commit,
        repository=repository,
        ref=ref,
    )
    project_path = root / PACKAGE_PATHS[package]
    actual_version = project_version(load_project(project_path), project_path)
    if expected_version != actual_version:
        raise ValueError(
            f"requested version {expected_version} does not match "
            f"{project_path}: {actual_version}"
        )
    validate_core_assets(root)
    if package in {"cli", "extension"}:
        core_version = validate_frontend_metadata(root, package)
        if package == "cli":
            validate_cli_changelog(root, actual_version)
        if verify_core_on_index:
            verify_package_release("cu-cli-core", core_version, index)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index", required=True, choices=sorted(PACKAGE_INDEX_API_URLS)
    )
    parser.add_argument("--package", required=True, choices=sorted(PACKAGE_PATHS))
    parser.add_argument("--version", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--actual-commit", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--verify-core-on-index", action="store_true")
    args = parser.parse_args()

    try:
        validate_release(
            root=ROOT,
            index=args.index,
            package=args.package,
            expected_version=args.version,
            expected_commit=args.expected_commit,
            actual_commit=args.actual_commit,
            repository=args.repository,
            ref=args.ref,
            verify_core_on_index=args.verify_core_on_index,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Validated {args.package} {args.version} for {args.index} at {args.actual_commit}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
