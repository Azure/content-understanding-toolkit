# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from collections import Counter
from fnmatch import fnmatch
import hashlib
import os
from pathlib import Path
import posixpath
import re
from typing import Iterable, Sequence
from urllib.parse import urlsplit, urlunsplit

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
_MAX_GENERATED_RESULT_NAME_BYTES = 240
_MAX_URL_LENGTH = 8192
_WINDOWS_DRIVE_PATH = re.compile(r"^[a-zA-Z]:[\\/]")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def redact_input_reference(value: str | Path) -> str:
    """Return an input reference that is safe to display or persist."""
    text = os.fspath(value)
    try:
        parsed = urlsplit(text)
    except ValueError:
        if "://" not in text and not text.lower().startswith(("http:", "https:")):
            return text
        base = text.split("#", 1)[0].split("?", 1)[0]
        scheme, separator, location = base.partition("://")
        if separator and "@" in location:
            base = f"{scheme}://{location.rsplit('@', 1)[-1]}"
        return f"{base}?REDACTED" if "?" in text else base
    if (
        parsed.scheme.lower() not in {"http", "https"}
        and "://" not in text
    ):
        return text
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    query = "REDACTED" if parsed.query else ""
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))


_HTTPS_URL_IN_TEXT = re.compile(r"https://[^\s\"<>]+", re.IGNORECASE)


def redact_sensitive_urls(text: str) -> str:
    """Redact query strings from HTTPS URLs embedded in arbitrary text."""
    return _HTTPS_URL_IN_TEXT.sub(
        lambda match: redact_input_reference(match.group(0)),
        text,
    )


def _validated_https_url(value: str, *, option: str) -> str | None:
    """Return an HTTPS URL unchanged, or ``None`` for a local path."""
    if _WINDOWS_DRIVE_PATH.match(value):
        return None
    lowered = value.lower()
    url_like = "://" in value or lowered.startswith(("http:", "https:"))
    if not url_like:
        return None
    if "://" not in value and Path(value).exists():
        return None
    if any(character.isspace() for character in value):
        raise ValidationError(
            f"{option} is not a valid URL.",
            hint="percent-encode spaces and provide an absolute HTTPS URL.",
        )
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValidationError(
            f"{option} is not a valid URL: {redact_input_reference(value)}",
            hint="provide an absolute HTTPS URL such as https://host/path/file.pdf.",
        ) from exc
    if parsed.scheme.lower() != "https":
        scheme = parsed.scheme or "(missing)"
        raise ValidationError(
            f"{option} uses unsupported URL scheme '{scheme}'.",
            hint="Content Understanding remote inputs require an HTTPS URL.",
        )
    if not parsed.netloc or not hostname:
        raise ValidationError(
            f"{option} is not a valid HTTPS URL: {redact_input_reference(value)}",
            hint="include a host, for example https://host/path/file.pdf.",
        )
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError(
            f"{option} must not contain embedded user credentials.",
            hint="use an HTTPS URL or Azure Blob SAS URL without URL user info.",
        )
    if len(value) > _MAX_URL_LENGTH:
        raise ValidationError(
            f"{option} URL exceeds the {_MAX_URL_LENGTH}-character service limit."
        )
    return value


def _remote_relative_path(url: str) -> Path:
    raw_name = posixpath.basename(urlsplit(url).path.rstrip("/")) or "remote-input"
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw_name).rstrip(" .")
    if not safe_name or safe_name in {".", ".."}:
        safe_name = "remote-input"
    if safe_name.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        safe_name = f"_{safe_name}"
    return Path(safe_name)


def _reject_direct_duplicates(values: Sequence[str | Path], option: str) -> None:
    rendered = [os.fspath(value) for value in values]
    duplicates = sorted(value for value, count in Counter(rendered).items() if count > 1)
    if duplicates:
        joined = ", ".join(redact_input_reference(value) for value in duplicates)
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
    urls: Sequence[str] = (),
    pattern: str | None = None,
    recursive: bool = False,
) -> InputPlan:
    """Validate and expand one invocation's local or remote input selection."""
    if positional and (files or sources or urls):
        conflicts = []
        if files:
            conflicts.append("--file")
        if sources:
            conflicts.append("--source")
        if urls:
            conflicts.append("--url")
        raise UsageError(
            "positional inputs cannot be combined with " + " or ".join(conflicts) + "."
        )
    if files and sources:
        raise UsageError("--file and --source cannot be combined.")
    if urls and (files or sources):
        raise UsageError("--url cannot be combined with --file or --source.")
    if pattern is not None and not sources:
        raise UsageError("--pattern is valid only with --source.")
    if not positional and not files and not sources and not urls:
        raise UsageError("provide positional inputs, --file, --source, or --url.")

    if positional:
        mode = SelectionMode.POSITIONAL
        direct = positional
        option = "positional input"
    elif files:
        mode = SelectionMode.NAMED_FILES
        direct = files
        option = "--file"
    elif urls:
        mode = SelectionMode.NAMED_URLS
        direct = urls
        option = "--url"
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
        identity = ("file", _file_identity(resolved))
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

    def add_url(url: str, *, origin: InputOrigin) -> None:
        identity = ("url", url)
        if identity in seen:
            return
        seen.add(identity)
        selected.append(
            PlannedInput(
                path=None,
                source_root=None,
                relative_path=_remote_relative_path(url),
                origin=origin,
                size_bytes=None,
                url=url,
            )
        )

    if positional:
        for value in positional:
            text = os.fspath(value)
            url = _validated_https_url(text, option=option)
            if url is not None:
                add_url(url, origin=InputOrigin.POSITIONAL_URL)
                continue
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
    elif urls:
        for value in urls:
            url = _validated_https_url(value, option=option)
            if url is None:
                raise ValidationError(
                    "--url must identify an absolute HTTPS URL.",
                    hint="use --file for local files or --source for local directories.",
                )
            add_url(url, origin=InputOrigin.NAMED_URL)
    elif files:
        for value in files:
            if _validated_https_url(os.fspath(value), option=option) is not None:
                raise UsageError(
                    "--file accepts local files only.",
                    hint="pass an HTTPS URL with --url instead.",
                )
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
            if _validated_https_url(os.fspath(value), option=option) is not None:
                raise UsageError(
                    "--source accepts local directories only.",
                    hint="pass an HTTPS URL with --url instead.",
                )
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
        item.relative_path.suffix.lower() or "(none)" for item in selected
    )
    return InputPlan(
        mode=mode,
        inputs=tuple(selected),
        recursive=recursive,
        pattern=pattern,
        total_bytes=sum(item.size_bytes or 0 for item in selected),
        extension_counts=dict(sorted(extension_counts.items())),
        skipped=tuple(
            skipped[path]
            for path in sorted(skipped, key=lambda path: os.fspath(path))
        ),
    )


def _result_path(path: Path, view: ResultView) -> Path:
    return Path(f"{path}{_RESULT_SUFFIX[view]}")


def _hashed_result_path(path: Path, view: ResultView, digest: str) -> Path:
    suffix = f".{digest}{_RESULT_SUFFIX[view]}"
    name_budget = _MAX_GENERATED_RESULT_NAME_BYTES - len(suffix)
    name = path.name.encode("utf-8")[:name_budget].decode("utf-8", errors="ignore")
    return path.with_name(f"{name}{suffix}")


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
    if (
        output_file is None
        and output_dir is None
        and len(input_plan.inputs) > 1
        and any(item.is_remote for item in input_plan.inputs)
    ):
        raise UsageError(
            "--output-dir is required when multiple inputs include an HTTPS URL.",
            hint="remote results cannot be written next to their source URL.",
        )

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
            if (
                item.is_remote
                and len(destination.name.encode("utf-8")) > _MAX_GENERATED_RESULT_NAME_BYTES
            ):
                raise ValidationError(
                    "generated remote result filename exceeds the "
                    f"{_MAX_GENERATED_RESULT_NAME_BYTES}-byte UTF-8 limit.",
                    hint="use --output-file with a shorter name for this input.",
                )
        elif stream_single and len(input_plan.inputs) == 1:
            destination = None
        else:
            if item.path is None:
                raise UsageError(
                    "remote input requires --output-file or --output-dir when not streamed."
                )
            destination = _result_path(item.path, view)
        destinations.append(destination)

    counts = Counter(path for path in destinations if path is not None)
    collided = {path for path, count in counts.items() if count > 1}
    conflicting_sources: dict[Path, list[PlannedInput]] = {}
    for item, destination in zip(input_plan.inputs, destinations, strict=True):
        if destination is not None and destination in collided:
            conflicting_sources.setdefault(destination, []).append(item)
    for destination, sources in conflicting_sources.items():
        if any(item.is_remote for item in sources):
            references = ", ".join(redact_input_reference(item.reference) for item in sources)
            raise ValidationError(
                f"multiple inputs resolve to the same result output path: {destination} "
                f"({references}).",
                hint="analyze these inputs separately with distinct --output-file paths.",
            )

    reserved = set(counts)
    for index, destination in sorted(
        ((index, path) for index, path in enumerate(destinations) if path in collided),
        key=lambda entry: input_plan.inputs[entry[0]].reference,
    ):
        item = input_plan.inputs[index]
        if item.is_remote:
            continue
        digest = hashlib.sha1(item.reference.encode("utf-8")).hexdigest()
        suffix = _RESULT_SUFFIX[view]
        assert destination is not None
        base = destination.with_name(destination.name[: -len(suffix)])
        for digest_length in range(8, len(digest) + 1, 8):
            candidate = _hashed_result_path(base, view, digest[:digest_length])
            if candidate not in reserved:
                destinations[index] = candidate
                reserved.add(candidate)
                break
        else:
            raise ValidationError(
                "cannot resolve result output path collision.",
                hint="analyze these inputs separately with distinct --output-file paths.",
            )

    resolved = [path for path in destinations if path is not None]
    if len(set(resolved)) != len(resolved):
        raise ValidationError(
            "multiple inputs resolve to the same result output path.",
            hint="analyze these inputs separately with distinct --output-file paths.",
        )

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
