# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Input discovery and result-path planning for ``cu analyze`` (Click-free).

Expands user-supplied inputs (files, directories, globs) into concrete local
file paths and plans where each result file is written. Soft warnings (empty
directories, non-matching globs) are returned as **data** on
:class:`ExpandResult` so the command layer can render them; the hard case (no
inputs matched at all) raises :class:`~cu_cli.errors.CuCliError`.

Result files are written next to the input with a ``.result`` suffix so they
never clobber the source: ``report.pdf`` -> ``report.pdf.result.md`` /
``report.pdf.result.json``. The full filename (extension included) is kept so
inputs that share a stem but differ by extension (``note.mp3`` vs ``note.pdf``)
never collide.
"""

from __future__ import annotations

import glob as _glob
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ..errors import CuCliError
from ..modality import KNOWN_SERVICE_INPUT_EXTS

RESULT_SUFFIXES = (".result.md", ".result.json")


@dataclass
class ExpandResult:
    """Concrete input files and their source-relative output paths."""

    files: list[str] = field(default_factory=list)
    source_relative_paths: dict[str, Path] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    # (path, reason) for inputs dropped during a directory walk for a reportable
    # reason (unsupported extension, or a hidden file at a visible path —
    # regardless of extension) so the command layer can name them instead of
    # dropping them silently (regression).
    skipped: list[tuple[str, str]] = field(default_factory=list)


def is_result_file(name: str) -> bool:
    """True for the CLI's own ``*.result.md`` / ``*.result.json`` outputs."""
    low = name.lower()
    return any(low.endswith(suffix) for suffix in RESULT_SUFFIXES)


def _unsupported_reason(path: Path) -> str:
    ext = path.suffix.lower() or "no extension"
    return f"unsupported file type ({ext})"


def _is_supported_local_file(path: Path) -> bool:
    return path.suffix.lower() in KNOWN_SERVICE_INPUT_EXTS


def _glob_source_root(pattern: str) -> Path:
    """Return the non-pattern path prefix that anchors a glob's result layout."""
    prefix: list[str] = []
    for part in Path(pattern).parts:
        if any(ch in part for ch in "*?["):
            break
        prefix.append(part)
    return Path(*prefix) if prefix else Path(".")


def expand_dir(path: Path, skipped: list[tuple[str, str]] | None = None) -> list[str]:
    """Recursively collect supported files under *path*.

    Skips hidden directories/files discovered during the walk (``.git``,
    ``.venv``, ``.cu`` …) and never re-ingests the CLI's own ``*.result.*``
    outputs — either would silently amplify cost on reruns.

    When *skipped* is provided, files dropped for a **reportable** reason — an
    unsupported extension, or a hidden file sitting at an otherwise-visible path
    (e.g. ``.hidden.pdf`` **or** ``.DS_Store``, regardless of extension) — are
    appended as ``(path, reason)`` so the command layer can name them. Files
    buried under a hidden *directory* stay quiet to avoid infrastructure noise
    (``.git`` etc.).
    """
    out: list[str] = []
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        if is_result_file(p.name):
            continue
        rel_parts = p.relative_to(path).parts
        if any(part.startswith(".") for part in rel_parts[:-1]):
            continue  # buried under a hidden directory — always silent
        supported = _is_supported_local_file(p)
        if p.name.startswith("."):
            # A hidden file at an otherwise-visible path is skipped regardless of
            # its extension; report it either way so nothing is dropped silently
            # (Regression: e.g. ``.DS_Store`` was previously omitted because it also
            # lacks a supported extension). Files buried under a hidden *directory*
            # were already filtered above and stay quiet (infrastructure noise).
            if skipped is not None:
                skipped.append((str(p), "hidden file skipped"))
            continue
        if not supported:
            if skipped is not None:
                ext = p.suffix.lower() or "no extension"
                skipped.append((str(p), f"unsupported file type ({ext})"))
            continue
        out.append(str(p))
    return out


def expand_inputs(items: Iterable[str]) -> ExpandResult:
    """Expand directories and globs into concrete local file paths.

    URLs are rejected — the MVP is local-only for now (URL support is deferred).
    Returns an :class:`ExpandResult` with the deduped file list and any soft
    warnings; raises :class:`~cu_cli.errors.CuCliError` when nothing matched.
    """
    out: list[str] = []
    source_relative_paths: dict[str, Path] = {}
    warnings: list[str] = []
    unmatched: list[str] = []
    skipped: list[tuple[str, str]] = []

    def add(ref: str, relative_path: Path) -> None:
        out.append(ref)
        source_relative_paths.setdefault(ref, relative_path)

    for it in items:
        low = it.lower()
        if low.startswith(("http://", "https://")):
            raise CuCliError(
                f"URL inputs are not supported in this release: {it}",
                hint="MVP analyzes local files, directories, and globs only. "
                     "Download the file first, or wait for URL support (Phase 2).",
            )
        if any(ch in it for ch in "*?["):
            matches = sorted(_glob.glob(it, recursive=True))
            if not matches:
                unmatched.append(it)
            source_root = _glob_source_root(it)
            for m in matches:
                p = Path(m)
                if p.is_dir():
                    for ref in expand_dir(p, skipped):
                        add(ref, Path(ref).relative_to(source_root))
                elif is_result_file(p.name):
                    continue  # don't re-ingest our own outputs on a glob
                elif _is_supported_local_file(p):
                    add(m, p.relative_to(source_root))
                else:
                    skipped.append((str(p), _unsupported_reason(p)))
        else:
            p = Path(it)
            if p.is_dir():
                expanded = expand_dir(p, skipped)
                if expanded:
                    for ref in expanded:
                        add(ref, Path(ref).relative_to(p))
                else:
                    warnings.append(f"no supported files in '{it}'.")
            elif p.exists():
                # An explicitly named file reflects user intent. Let the service
                # authoritatively validate formats that this client may not know
                # yet; the allowlist is only a safety filter for discovery.
                add(it, Path(p.name))
            else:
                unmatched.append(it)
    if unmatched and not out:
        raise CuCliError(f"no files matched: {', '.join(unmatched)}",
                         hint="check the path or glob pattern.")
    for pat in unmatched:
        warnings.append(f"no matches for '{pat}' — skipping.")
    seen: set[str] = set()
    deduped: list[str] = []
    deduped_relative_paths: dict[str, Path] = {}
    for it in out:
        if it not in seen:
            seen.add(it)
            deduped.append(it)
            deduped_relative_paths[it] = source_relative_paths[it]
    # Dedupe the skip list and never report a path that also resolved to a real
    # input (a file reachable both directly and via a directory walk).
    file_set = set(deduped)
    seen_skip: set[str] = set()
    deduped_skipped: list[tuple[str, str]] = []
    for spath, reason in skipped:
        if spath in file_set or spath in seen_skip:
            continue
        seen_skip.add(spath)
        deduped_skipped.append((spath, reason))
    return ExpandResult(
        files=deduped,
        source_relative_paths=deduped_relative_paths,
        warnings=warnings,
        skipped=deduped_skipped,
    )


def result_path(ref: str, fmt: str) -> Path:
    """``report.pdf`` -> ``report.pdf.result.md`` / ``report.pdf.result.json``.

    The full input filename (extension included) is preserved so same-stem
    inputs with different extensions never overwrite each other's results.
    """
    p = Path(ref)
    ext = "md" if fmt == "markdown" else "json"
    return p.with_name(f"{p.name}.result.{ext}")
