# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from collections import Counter
from fnmatch import fnmatch
import hashlib
import os
from pathlib import Path
from typing import Iterable, Sequence

from .contracts import (
    ExecutionPlan,
    ExistingResultPolicy,
    InputOrigin,
    InputPlan,
    PlannedInput,
    PlannedOutput,
    ResultView,
    SelectionMode,
    SkippedInput,
)
from .errors import UsageError, ValidationError

_WILDCARD_CHARS = frozenset("*?[")
_RESULT_SUFFIX = {
    ResultView.LLM_INPUT: ".result.md",
    ResultView.FULL: ".result.json",
}
_GENERATED_RESULT_SUFFIXES = tuple(_RESULT_SUFFIX.values())


def _reject_direct_duplicates(values: Sequence[str | Path], option: str) -> None:
    rendered = [os.fspath(value) for value in values]
    duplicates = sorted(value for value, count in Counter(rendered).items() if count > 1)
    if duplicates:
        joined = ", ".join(duplicates)
        raise UsageError(f"{option} was provided more than once for: {joined}")


def _file_identity(path: Path) -> object:
    stat = path.stat()
    if stat.st_ino:
        return (stat.st_dev, stat.st_ino)
    return os.path.normcase(os.fspath(path.resolve()))


def _validated_file(path: Path, *, option: str) -> tuple[Path, int]:
    if not path.exists():
        raise ValidationError(f"{option} does not exist: {path}")
    if not path.is_file():
        raise ValidationError(f"{option} must identify a file: {path}")
    try:
        stat = path.stat()
    except OSError as exc:
        raise ValidationError(f"{option} cannot be read: {path}") from exc
    return path.resolve(), stat.st_size


def _validated_source(path: Path, *, option: str) -> Path:
    if not path.exists():
        raise ValidationError(f"{option} does not exist: {path}")
    if not path.is_dir():
        raise ValidationError(f"{option} must identify a directory: {path}")
    return path.resolve()


def _directory_files(
    source: Path,
    *,
    recursive: bool,
    pattern: str,
    skipped: dict[Path, SkippedInput],
) -> Iterable[Path]:
    candidates = source.rglob("*") if recursive else source.iterdir()
    files = (path for path in candidates if path.is_file())
    selected: list[Path] = []
    for path in files:
        relative_path = path.relative_to(source)
        if not fnmatch(relative_path.as_posix(), pattern):
            continue
        if path.name.endswith(_GENERATED_RESULT_SUFFIXES):
            continue
        if any(part.startswith(".") for part in relative_path.parts[:-1]):
            continue
        if path.name.startswith("."):
            skipped.setdefault(
                path,
                SkippedInput(path=path, reason="hidden file skipped"),
            )
            continue
        selected.append(path)
    return sorted(selected, key=lambda path: path.relative_to(source).as_posix())


def plan_inputs(
    *,
    positional: Sequence[str | Path] = (),
    files: Sequence[str | Path] = (),
    sources: Sequence[str | Path] = (),
    pattern: str | None = None,
    recursive: bool = False,
) -> InputPlan:
    """Validate and expand one invocation's local input selection."""
    if positional and (files or sources):
        conflicts = []
        if files:
            conflicts.append("--file")
        if sources:
            conflicts.append("--source")
        raise UsageError(
            "positional inputs cannot be combined with " + " or ".join(conflicts) + "."
        )
    if files and sources:
        raise UsageError("--file and --source cannot be combined.")
    if pattern is not None and not sources:
        raise UsageError("--pattern is valid only with --source.")
    if not positional and not files and not sources:
        raise UsageError("provide positional inputs, --file, or --source.")

    if positional:
        mode = SelectionMode.POSITIONAL
        direct = positional
        option = "positional input"
    elif files:
        mode = SelectionMode.NAMED_FILES
        direct = files
        option = "--file"
    else:
        mode = SelectionMode.NAMED_SOURCES
        direct = sources
        option = "--source"
    _reject_direct_duplicates(direct, option)

    selected: list[PlannedInput] = []
    seen: set[object] = set()
    skipped: dict[Path, SkippedInput] = {}
    includes_directory = bool(sources)

    def add_file(
        path: Path,
        *,
        source_root: Path,
        relative_path: Path,
        origin: InputOrigin,
    ) -> None:
        resolved, size = _validated_file(path, option=option)
        identity = _file_identity(resolved)
        if identity in seen:
            return
        seen.add(identity)
        selected.append(
            PlannedInput(
                path=resolved,
                source_root=source_root,
                relative_path=relative_path,
                origin=origin,
                size_bytes=size,
            )
        )

    if positional:
        for value in positional:
            text = os.fspath(value)
            if any(char in text for char in _WILDCARD_CHARS):
                raise UsageError(
                    f"wildcard patterns aren't accepted as positional inputs: {text}",
                    hint='Use --source with --pattern, for example: --source . --pattern "*.pdf"',
                )
            path = Path(value)
            if not path.exists():
                raise ValidationError(f"positional input does not exist: {path}")
            if path.is_dir():
                includes_directory = True
                source = _validated_source(path, option=option)
                for child in _directory_files(
                    source,
                    recursive=recursive,
                    pattern="*",
                    skipped=skipped,
                ):
                    add_file(
                        child,
                        source_root=source,
                        relative_path=child.relative_to(source),
                        origin=InputOrigin.POSITIONAL_SOURCE,
                    )
            else:
                resolved, _ = _validated_file(path, option=option)
                add_file(
                    resolved,
                    source_root=resolved.parent,
                    relative_path=Path(resolved.name),
                    origin=InputOrigin.POSITIONAL_FILE,
                )
    elif files:
        for value in files:
            path, _ = _validated_file(Path(value), option=option)
            add_file(
                path,
                source_root=path.parent,
                relative_path=Path(path.name),
                origin=InputOrigin.NAMED_FILE,
            )
    else:
        effective_pattern = pattern if pattern is not None else "*"
        if not effective_pattern:
            raise UsageError("--pattern cannot be empty.")
        for value in sources:
            source = _validated_source(Path(value), option=option)
            for child in _directory_files(
                source,
                recursive=recursive,
                pattern=effective_pattern,
                skipped=skipped,
            ):
                add_file(
                    child,
                    source_root=source,
                    relative_path=child.relative_to(source),
                    origin=InputOrigin.NAMED_SOURCE,
                )

    if recursive and not includes_directory:
        raise UsageError("--recursive is valid only when input selection includes a directory.")
    if not selected:
        if skipped:
            details = ", ".join(
                f"{item.path} ({item.reason})"
                for item in skipped.values()
            )
            raise ValidationError(
                "input selection did not find any analyzable files. "
                f"Skipped during discovery: {details}."
            )
        raise ValidationError("input selection did not find any files.")

    extension_counts = Counter(
        item.path.suffix.lower() or "(none)" for item in selected
    )
    return InputPlan(
        mode=mode,
        inputs=tuple(selected),
        recursive=recursive,
        pattern=pattern,
        total_bytes=sum(item.size_bytes for item in selected),
        extension_counts=dict(sorted(extension_counts.items())),
        skipped=tuple(
            skipped[path]
            for path in sorted(skipped, key=lambda path: os.fspath(path))
        ),
    )


def _result_path(path: Path, view: ResultView) -> Path:
    return Path(f"{path}{_RESULT_SUFFIX[view]}")


def plan_outputs(
    input_plan: InputPlan,
    *,
    view: ResultView,
    output_file: str | Path | None = None,
    output_dir: str | Path | None = None,
    on_existing: ExistingResultPolicy = ExistingResultPolicy.ERROR,
    stream_single: bool = True,
    dry_run: bool = False,
) -> ExecutionPlan:
    """Resolve result destinations, collisions, and existing-file actions."""
    if output_file is not None and output_dir is not None:
        raise UsageError("--output-file and --output-dir cannot be combined.")
    if output_file is not None and len(input_plan.inputs) != 1:
        raise UsageError("--output-file is valid only when exactly one file is selected.")

    destinations: list[Path | None] = []
    for item in input_plan.inputs:
        if output_file is not None:
            destination = Path(output_file)
        elif output_dir is not None:
            relative = item.relative_path
            if relative.is_absolute() or ".." in relative.parts:
                raise ValidationError(
                    f"source-relative output path is invalid: {relative}"
                )
            destination = _result_path(Path(output_dir) / relative, view)
        elif stream_single and len(input_plan.inputs) == 1:
            destination = None
        else:
            destination = _result_path(item.path, view)
        destinations.append(destination)

    counts = Counter(path for path in destinations if path is not None)
    collided = {path for path, count in counts.items() if count > 1}
    for index, destination in enumerate(destinations):
        if destination not in collided:
            continue
        digest = hashlib.sha1(
            os.fspath(input_plan.inputs[index].path).encode("utf-8")
        ).hexdigest()[:8]
        suffix = _RESULT_SUFFIX[view]
        assert destination is not None
        base = destination.name[: -len(suffix)]
        destinations[index] = destination.with_name(f"{base}.{digest}{suffix}")

    outputs: list[PlannedOutput] = []
    for item, destination in zip(input_plan.inputs, destinations, strict=True):
        exists = destination is not None and destination.exists()
        outputs.append(
            PlannedOutput(
                source=item,
                path=destination,
                exists=exists,
                skipped=exists and on_existing is ExistingResultPolicy.SKIP,
            )
        )
    return ExecutionPlan(
        input_plan=input_plan,
        outputs=tuple(outputs),
        on_existing=on_existing,
        dry_run=dry_run,
    )
