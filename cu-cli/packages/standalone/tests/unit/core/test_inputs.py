"""Unit tests for :mod:`cu_cli.core.inputs` — input expansion and result-path safety.

Regression coverage for directory-walk cost hazards and result-filename
collisions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cu_cli.core.inputs import (
    expand_dir as _expand_dir,
    expand_inputs as _expand_inputs_result,
    result_path as _result_path,
)
from cu_cli.errors import CuCliError

pytestmark = pytest.mark.unit


def _expand_inputs(items):
    """Compat shim: tests assert on the plain file list.

    ``core.inputs.expand_inputs`` returns an ``ExpandResult`` (files +
    warnings); tests here only care about the resolved files.
    """
    return _expand_inputs_result(items).files


def _touch(path: Path, data: bytes = b"%PDF-1.4 x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_expand_dir_skips_own_result_files(tmp_path):
    # Regression: never re-ingest the CLI's own .result.* outputs on a rerun.
    _touch(tmp_path / "a.pdf")
    _touch(tmp_path / "a.pdf.result.md", b"# result")
    _touch(tmp_path / "a.result.json", b"{}")
    names = {Path(p).name for p in _expand_dir(tmp_path)}
    assert names == {"a.pdf"}


def test_expand_dir_skips_hidden_directories(tmp_path):
    # Regression: hidden dirs discovered during recursion (.git/.venv/.cu) are skipped.
    _touch(tmp_path / "top.pdf")
    _touch(tmp_path / ".git" / "objects" / "buried.pdf")
    _touch(tmp_path / ".venv" / "lib" / "pkg.pdf")
    names = {Path(p).name for p in _expand_dir(tmp_path)}
    assert names == {"top.pdf"}


def test_expand_dir_recurses_visible_subdirectories(tmp_path):
    _touch(tmp_path / "top.pdf")
    _touch(tmp_path / "sub" / "nested.pdf")
    names = {Path(p).name for p in _expand_dir(tmp_path)}
    assert names == {"top.pdf", "nested.pdf"}


def test_expand_inputs_rejects_missing_explicit_path():
    # Regression: a nonexistent explicit path is "unmatched", not a phantom sample.
    with pytest.raises(CuCliError, match="no files matched"):
        _expand_inputs(["does-not-exist.pdf"])


def test_expand_inputs_skips_result_files_from_globs(tmp_path, monkeypatch):
    _touch(Path("keep.pdf"))
    _touch(Path("keep.pdf.result.md"), b"# result")
    got = _expand_inputs(["*.*"])
    assert [Path(p).name for p in got] == ["keep.pdf"]


def test_result_path_preserves_extension():
    # Regression: same stem + different extension must map to distinct result files.
    assert _result_path("note.mp3", "markdown").name == "note.mp3.result.md"
    assert _result_path("note.pdf", "markdown").name == "note.pdf.result.md"
    assert _result_path("note.pdf", "json").name == "note.pdf.result.json"


def test_expand_dir_reports_unsupported_and_visible_hidden_files(tmp_path):
    # Regression: unsupported files and hidden files at a visible path are surfaced
    # via the skipped out-param instead of being dropped silently. Files buried
    # under a hidden *directory* stay quiet (infrastructure noise).
    _touch(tmp_path / "good.pdf")
    _touch(tmp_path / "script.py", b"print('hello')\n")
    _touch(tmp_path / ".hidden.pdf")
    _touch(tmp_path / ".git" / "objects" / "buried.pdf")

    skipped: list[tuple[str, str]] = []
    files = _expand_dir(tmp_path, skipped)

    assert {Path(p).name for p in files} == {"good.pdf"}
    reasons = {Path(p).name: reason for p, reason in skipped}
    assert "unsupported" in reasons.get("script.py", "")
    assert "hidden" in reasons.get(".hidden.pdf", "")
    assert "buried.pdf" not in reasons


def test_expand_dir_reports_hidden_file_regardless_of_extension(tmp_path):
    # Regression: a hidden file at a visible path is reported even when it also lacks
    # a supported extension (e.g. .DS_Store, or a hidden file with no extension).
    # Previously only hidden files that *also* had a supported extension were
    # named, so junk like .DS_Store was dropped without a trace.
    _touch(tmp_path / "good.pdf")
    _touch(tmp_path / ".DS_Store", b"\x00\x01junk")   # hidden + unsupported ext
    _touch(tmp_path / ".env", b"SECRET=1")            # hidden + no extension

    skipped: list[tuple[str, str]] = []
    files = _expand_dir(tmp_path, skipped)

    assert {Path(p).name for p in files} == {"good.pdf"}
    reasons = {Path(p).name: reason for p, reason in skipped}
    assert "hidden" in reasons.get(".DS_Store", "")
    assert "hidden" in reasons.get(".env", "")


def test_expand_dir_without_skip_list_is_backward_compatible(tmp_path):
    # Callers that don't pass a skip list still get just the plain file list.
    _touch(tmp_path / "good.pdf")
    _touch(tmp_path / "script.py", b"x")
    assert {Path(p).name for p in _expand_dir(tmp_path)} == {"good.pdf"}


def test_expand_inputs_collects_skipped_from_directory():
    # Regression: a directory walk records unsupported inputs on ExpandResult.skipped.
    _touch(Path("corpus/good.pdf"))
    _touch(Path("corpus/notes.py"), b"x")
    result = _expand_inputs_result(["corpus"])
    assert [Path(p).name for p in result.files] == ["good.pdf"]
    assert any(
        Path(p).name == "notes.py" and "unsupported" in reason
        for p, reason in result.skipped
    )


def test_expand_inputs_tracks_paths_relative_to_absolute_directory(tmp_path):
    source = tmp_path / "invoices"
    sample = source / "2026" / "q1.pdf"
    _touch(sample)

    result = _expand_inputs_result([str(source)])

    assert result.files == [str(sample)]
    assert result.source_relative_paths == {str(sample): Path("2026/q1.pdf")}


def test_expand_inputs_tracks_explicit_file_relative_to_its_parent(tmp_path):
    sample = tmp_path / "invoices" / "q1.pdf"
    _touch(sample)

    result = _expand_inputs_result([str(sample)])

    assert result.source_relative_paths == {str(sample): Path("q1.pdf")}


def test_expand_inputs_tracks_each_directory_from_its_own_root(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_sample = first / "nested" / "a.pdf"
    second_sample = second / "b.pdf"
    _touch(first_sample)
    _touch(second_sample)

    result = _expand_inputs_result([str(first), str(second)])

    assert result.source_relative_paths == {
        str(first_sample): Path("nested/a.pdf"),
        str(second_sample): Path("b.pdf"),
    }


def test_expand_inputs_tracks_mixed_file_and_directory_sources(tmp_path):
    direct = tmp_path / "loose" / "a.pdf"
    source = tmp_path / "corpus"
    nested = source / "nested" / "b.pdf"
    _touch(direct)
    _touch(nested)

    result = _expand_inputs_result([str(direct), str(source)])

    assert result.source_relative_paths == {
        str(direct): Path("a.pdf"),
        str(nested): Path("nested/b.pdf"),
    }


def test_expand_inputs_tracks_glob_from_non_pattern_prefix(tmp_path):
    source = tmp_path / "invoices"
    sample = source / "2026" / "q1.pdf"
    _touch(sample)

    result = _expand_inputs_result([str(source / "**" / "*.pdf")])

    assert result.source_relative_paths == {str(sample): Path("2026/q1.pdf")}


def test_expand_inputs_allows_explicit_file_with_unknown_extension():
    _touch(Path("archive.zip"), b"PK\x03\x04")
    result = _expand_inputs_result(["archive.zip"])
    assert result.files == ["archive.zip"]
    assert result.skipped == []


def test_expand_inputs_skips_unsupported_glob_match():
    # Regression: unsupported files matched via glob are pre-filtered too.
    _touch(Path("a.zip"), b"PK\x03\x04")
    _touch(Path("b.pdf"))
    result = _expand_inputs_result(["*.*"])
    assert [Path(p).name for p in result.files] == ["b.pdf"]
    assert any(
        Path(p).name == "a.zip" and "unsupported" in reason
        for p, reason in result.skipped
    )


@pytest.mark.parametrize("extension", [".jpe", ".heif", ".heic", ".csv", ".m4v", ".opus"])
def test_expand_dir_accepts_documented_service_extensions(tmp_path, extension):
    sample = tmp_path / f"sample{extension}"
    _touch(sample)
    assert _expand_dir(tmp_path) == [str(sample)]


def test_expand_dir_skips_gif_but_explicit_gif_is_allowed(tmp_path):
    sample = tmp_path / "animation.gif"
    _touch(sample, b"GIF89a")
    skipped: list[tuple[str, str]] = []

    assert _expand_dir(tmp_path, skipped) == []
    assert skipped == [(str(sample), "unsupported file type (.gif)")]
    assert _expand_inputs_result([str(sample)]).files == [str(sample)]
