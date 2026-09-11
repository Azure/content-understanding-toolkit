# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _load_validator() -> ModuleType:
    script_path = Path(__file__).resolve().parents[4] / "scripts" / "validate_release.py"
    spec = importlib.util.spec_from_file_location("validate_release", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_release = _load_validator()
SHA = "a" * 40


def _write_project(path: Path, *, name: str, version: str, dependencies: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dependency_lines = ",\n".join(f'    "{dependency}"' for dependency in dependencies)
    path.write_text(
        f"""
[project]
name = "{name}"
version = "{version}"
dependencies = [
{dependency_lines}
]
""".lstrip(),
        encoding="utf-8",
    )


def _write_release_tree(
    root: Path,
    *,
    core_version: str = "0.1.0b1",
    dated_changelog: bool = True,
) -> None:
    core_major, core_minor, _ = core_version.split(".")
    core_upper_bound = f"{core_major}.{int(core_minor) + 1}.0"
    _write_project(
        root / "packages/core/pyproject.toml",
        name="cu-cli-core",
        version=core_version,
        dependencies=[],
    )
    _write_project(
        root / "packages/standalone/pyproject.toml",
        name="cu-cli",
        version="0.1.0b1",
        dependencies=[f"cu-cli-core>={core_version},<{core_upper_bound}"],
    )
    _write_project(
        root / "packages/azure-cli-extension/pyproject.toml",
        name="content-understanding",
        version="0.1.0b1",
        dependencies=[f"cu-cli-core>={core_version},<{core_upper_bound}"],
    )
    template_root = root / "packages/core/src/cu_cli_core/resources/azd_template"
    for relative_path in validate_release.CANONICAL_TEMPLATE_FILES:
        path = template_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("canonical\n", encoding="utf-8")
    status = "2026-09-04" if dated_changelog else "Unreleased"
    (root / "CHANGELOG.md").write_text(
        f"# Release History\n\n## 0.1.0b1 ({status})\n",
        encoding="utf-8",
    )


def _validate(root: Path, **overrides: object) -> None:
    arguments = {
        "root": root,
        "index": "pypi",
        "package": "core",
        "expected_version": "0.1.0b1",
        "expected_commit": SHA,
        "actual_commit": SHA,
        "repository": "Azure/content-understanding-toolkit",
        "ref": "refs/heads/main",
        "verify_core_on_index": False,
    }
    arguments.update(overrides)
    validate_release.validate_release(**arguments)


def test_validates_core_release(tmp_path: Path) -> None:
    _write_release_tree(tmp_path)

    _validate(tmp_path)


def test_validates_extension_release_metadata(tmp_path: Path) -> None:
    _write_release_tree(tmp_path)

    _validate(tmp_path, package="extension", expected_version="0.1.0b1")


def test_rejects_duplicate_frontend_template(tmp_path: Path) -> None:
    _write_release_tree(tmp_path)
    duplicate = tmp_path / "packages/standalone/src/cu_cli/resources/azd_template"
    duplicate.mkdir(parents=True)

    with pytest.raises(ValueError, match="duplicate azd templates"):
        _validate(tmp_path)


def test_rejects_incomplete_canonical_template(tmp_path: Path) -> None:
    _write_release_tree(tmp_path)
    (tmp_path / "packages/core/src/cu_cli_core/resources/azd_template/azure.yaml").unlink()

    with pytest.raises(ValueError, match="canonical azd template files"):
        _validate(tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("repository", "someone/fork", "releases must run in"),
        ("ref", "refs/heads/feature", "releases must run from"),
        ("expected_commit", "short", "40-character SHA"),
        ("actual_commit", "b" * 40, "does not match workflow commit"),
        ("expected_version", "0.1.1", "does not match"),
    ],
)
def test_rejects_unapproved_context(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    _write_release_tree(tmp_path)

    with pytest.raises(ValueError, match=message):
        _validate(tmp_path, **{field: value})


def test_cli_requires_dated_changelog(tmp_path: Path) -> None:
    _write_release_tree(tmp_path, dated_changelog=False)

    with pytest.raises(ValueError, match="must date"):
        _validate(
            tmp_path,
            package="cli",
            expected_version="0.1.0b1",
        )


def test_cli_requires_stable_core_dependency(tmp_path: Path) -> None:
    _write_release_tree(tmp_path)
    _write_project(
        tmp_path / "packages/standalone/pyproject.toml",
        name="cu-cli",
        version="0.1.0b1",
        dependencies=["cu-cli-core>=0.1.0.dev0,<0.2.0"],
    )

    with pytest.raises(ValueError, match="bounded compatible core requirement"):
        _validate(
            tmp_path,
            package="cli",
            expected_version="0.1.0b1",
        )


def test_cli_derives_upper_bound_from_core_minor_version(tmp_path: Path) -> None:
    _write_release_tree(tmp_path, core_version="0.2.0b1")

    _validate(
        tmp_path,
        package="cli",
        expected_version="0.1.0b1",
    )


@pytest.mark.parametrize(
    ("index", "expected_url"),
    [
        ("pypi", "https://pypi.org/pypi/cu-cli-core/json"),
        ("testpypi", "https://test.pypi.org/pypi/cu-cli-core/json"),
    ],
)
def test_cli_requires_core_on_selected_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    index: str,
    expected_url: str,
) -> None:
    _write_release_tree(tmp_path)
    requested_urls: list[str] = []

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"releases": {}}).encode()

    def open_index(url: str, **_kwargs: object) -> Response:
        requested_urls.append(url)
        return Response()

    monkeypatch.setattr(validate_release, "urlopen", open_index)

    with pytest.raises(ValueError, match=f"published to {index}"):
        _validate(
            tmp_path,
            index=index,
            package="cli",
            expected_version="0.1.0b1",
            verify_core_on_index=True,
        )

    assert requested_urls == [expected_url]
