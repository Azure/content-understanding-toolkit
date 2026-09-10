# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from cu_cli_core.contracts import ExistingResultPolicy, InputOrigin, ResultView, SelectionMode
from cu_cli_core.errors import UsageError, ValidationError
from cu_cli_core.input_planning import (
    plan_inputs,
    plan_outputs,
    redact_input_reference,
)

pytestmark = pytest.mark.unit


def test_positional_files_preserve_order_and_measure_content(tmp_path):
    second = tmp_path / "second.xyz"
    first = tmp_path / "first.pdf"
    second.write_bytes(b"22")
    first.write_bytes(b"1")

    plan = plan_inputs(positional=[second, first])

    assert plan.mode is SelectionMode.POSITIONAL
    assert [item.path for item in plan.inputs] == [second.resolve(), first.resolve()]
    assert plan.total_bytes == 3
    assert plan.extension_counts == {".pdf": 1, ".xyz": 1}


@pytest.mark.parametrize(
    ("selection", "mode", "origin"),
    [
        ("positional", SelectionMode.POSITIONAL, InputOrigin.POSITIONAL_URL),
        ("urls", SelectionMode.NAMED_URLS, InputOrigin.NAMED_URL),
    ],
)
def test_https_url_is_preserved_without_local_file_access(selection, mode, origin):
    url = "https://storage.example.test/container/sample.pdf"

    plan = plan_inputs(**{selection: [url]})

    assert plan.mode is mode
    assert len(plan.inputs) == 1
    assert plan.inputs[0].origin is origin
    assert plan.inputs[0].path is None
    assert plan.inputs[0].url == url
    assert plan.inputs[0].reference == url
    assert plan.inputs[0].relative_path == Path("sample.pdf")
    assert plan.total_bytes == 0
    assert plan.extension_counts == {".pdf": 1}


@pytest.mark.parametrize("selection", ["positional", "urls"])
def test_sas_url_preserves_query_parameters(selection):
    url = (
        "https://storage.example.test/container/video.mp4"
        "?sv=2026-01-01&sp=r&sig=a%2Bb%2Fc%3D"
    )

    plan = plan_inputs(**{selection: [url]})

    assert plan.inputs[0].url == url
    assert plan.inputs[0].relative_path == Path("video.mp4")


def test_named_urls_preserve_selection_order():
    urls = [
        "https://example.test/video.mp4?sig=first%2Btoken",
        "https://example.test/document.pdf?sig=second%3Dtoken",
    ]

    plan = plan_inputs(urls=urls)

    assert [item.url for item in plan.inputs] == urls
    assert all(item.origin is InputOrigin.NAMED_URL for item in plan.inputs)


@pytest.mark.parametrize(
    "value",
    ["", "./document.pdf", "example.test/document.pdf", "C:\\documents\\document.pdf"],
    ids=["empty", "local", "relative-url", "windows-path"],
)
def test_named_url_requires_an_absolute_https_url(value):
    with pytest.raises(ValidationError, match="--url must identify an absolute HTTPS URL"):
        plan_inputs(urls=[value])


def test_duplicate_named_urls_are_rejected_without_echoing_query():
    url = "https://example.test/document.pdf?sig=duplicate-secret"

    with pytest.raises(UsageError, match="--url was provided more than once") as error:
        plan_inputs(urls=[url, url])

    assert "duplicate-secret" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "https:/container/input.pdf?sv=1&sig=secret",
        "https://[invalid/container/input.pdf?sv=1&sig=secret",
        "https://user:password@[invalid/input.pdf?sig=secret",
        "https://user:password@example.test/input.pdf?sig=secret",
    ],
)
def test_redact_input_reference_hides_secrets_from_malformed_urls(url):
    redacted = redact_input_reference(url)

    assert "secret" not in redacted
    assert "password" not in redacted


@pytest.mark.parametrize("selection", ["positional", "urls"])
def test_invalid_url_port_is_rejected_without_echoing_query(selection):
    url = "https://example.test:not-a-port/input.pdf?sig=secret"

    with pytest.raises(ValidationError, match="not a valid URL") as error:
        plan_inputs(**{selection: [url]})

    assert "secret" not in str(error.value)


@pytest.mark.skipif(os.name == "nt", reason="colon is not valid in a Windows filename")
def test_existing_https_colon_filename_remains_a_local_input(tmp_path):
    local_file = tmp_path / "https:invoice.pdf"
    local_file.write_text("input")

    plan = plan_inputs(positional=[local_file])

    assert plan.inputs[0].path == local_file.resolve()
    assert plan.inputs[0].url is None


def test_windows_drive_spelling_is_not_treated_as_url():
    with pytest.raises(ValidationError, match="does not exist") as error:
        plan_inputs(positional=["C://does-not-exist/input.pdf"])

    assert "unsupported URL scheme" not in str(error.value)


@pytest.mark.parametrize("selection", ["positional", "urls"])
@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("http://example.test/sample.pdf", "unsupported URL scheme 'http'"),
        ("ftp://example.test/sample.pdf", "unsupported URL scheme 'ftp'"),
        ("https:/sample.pdf", "not a valid HTTPS URL"),
    ],
)
def test_unsupported_url_has_actionable_error(url, message, selection):
    with pytest.raises(ValidationError, match=message) as error:
        plan_inputs(**{selection: [url]})

    assert "HTTPS" in (error.value.hint or "") or "host" in (error.value.hint or "")


@pytest.mark.parametrize("selection", ["files", "sources"])
def test_named_local_input_rejects_https_url_with_named_hint(selection):
    with pytest.raises(UsageError, match="local .* only") as error:
        plan_inputs(**{selection: ["https://example.test/sample.pdf"]})

    assert "--url" in (error.value.hint or "")


@pytest.mark.parametrize("selection", ["positional", "urls"])
def test_url_over_service_length_limit_is_rejected(selection):
    url = "https://example.test/" + ("a" * 8192)

    with pytest.raises(ValidationError, match="8192-character service limit"):
        plan_inputs(**{selection: [url]})


def test_named_files_require_literal_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValidationError, match="must identify a file"):
        plan_inputs(files=[source])


def test_positional_directory_is_nonrecursive_by_default(tmp_path):
    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    immediate = source / "b.pdf"
    nested_file = nested / "a.pdf"
    immediate.write_text("b")
    nested_file.write_text("a")

    plan = plan_inputs(positional=[source])

    assert [item.path for item in plan.inputs] == [immediate.resolve()]
    assert plan.inputs[0].relative_path == Path("b.pdf")


def test_recursive_source_is_sorted_by_source_relative_path(tmp_path):
    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    (source / "z.pdf").write_text("z")
    (nested / "a.pdf").write_text("a")

    plan = plan_inputs(sources=[source], recursive=True)

    assert [item.relative_path.as_posix() for item in plan.inputs] == [
        "nested/a.pdf",
        "z.pdf",
    ]


def test_pattern_filters_every_named_source(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "a.pdf").write_text("a")
    (first / "a.txt").write_text("a")
    (second / "b.pdf").write_text("b")

    plan = plan_inputs(sources=[first, second], pattern="*.pdf")

    assert [item.path.name for item in plan.inputs] == ["a.pdf", "b.pdf"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"positional": ["a"], "files": ["b"]},
            "positional inputs cannot be combined with --file",
        ),
        (
            {"positional": ["a"], "sources": ["b"]},
            "positional inputs cannot be combined with --source",
        ),
        ({"files": ["a"], "sources": ["b"]}, "--file and --source"),
        ({"files": ["a"], "pattern": "*.pdf"}, "--pattern is valid only"),
        (
            {"positional": ["a"], "urls": ["https://example.test/b.pdf"]},
            "positional inputs cannot be combined with --url",
        ),
        (
            {"files": ["a"], "urls": ["https://example.test/b.pdf"]},
            "--url cannot be combined with --file or --source",
        ),
        (
            {"sources": ["a"], "urls": ["https://example.test/b.pdf"]},
            "--url cannot be combined with --file or --source",
        ),
        (
            {"urls": ["https://example.test/a.pdf"], "pattern": "*.pdf"},
            "--pattern is valid only",
        ),
        (
            {"urls": ["https://example.test/a.pdf"], "recursive": True},
            "--recursive is valid only",
        ),
        ({}, "provide positional inputs"),
    ],
)
def test_selection_modes_are_rejected_before_discovery(kwargs, message):
    with pytest.raises(UsageError, match=message):
        plan_inputs(**kwargs)


def test_positional_wildcard_has_actionable_error():
    with pytest.raises(UsageError, match="wildcard patterns aren't accepted") as error:
        plan_inputs(positional=["*.pdf"])

    assert "--source" in (error.value.hint or "")
    assert "--pattern" in (error.value.hint or "")


@pytest.mark.parametrize("mode", ["positional", "files", "sources"])
def test_direct_duplicate_arguments_are_rejected(tmp_path, mode):
    value = tmp_path / ("source" if mode == "sources" else "input.pdf")
    value.mkdir() if mode == "sources" else value.write_text("input")

    with pytest.raises(UsageError, match="provided more than once"):
        plan_inputs(**{mode: [value, value]})


def test_relative_absolute_and_symlink_overlap_is_silently_deduplicated(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.pdf"
    target.write_text("input")
    alias = tmp_path / "alias.pdf"
    alias.symlink_to(target)
    monkeypatch.chdir(tmp_path)

    plan = plan_inputs(positional=[Path("source/input.pdf"), target.resolve(), alias])

    assert len(plan.inputs) == 1


def test_hardlink_overlap_from_sources_is_silently_deduplicated(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    target = first / "input.pdf"
    target.write_text("input")
    os.link(target, second / "same.pdf")

    plan = plan_inputs(sources=[first, second])

    assert len(plan.inputs) == 1


def test_recursive_is_rejected_for_named_files(tmp_path):
    input_file = tmp_path / "input.pdf"
    input_file.write_text("input")

    with pytest.raises(UsageError, match="valid only"):
        plan_inputs(files=[input_file], recursive=True)


def test_unknown_extension_is_selected_without_local_rejection(tmp_path):
    input_file = tmp_path / "input.brandnew"
    input_file.write_text("input")

    plan = plan_inputs(files=[input_file])

    assert plan.extension_counts == {".brandnew": 1}


def test_directory_discovery_excludes_hidden_and_generated_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    visible = source / "visible.brandnew"
    hidden = source / ".hidden.pdf"
    markdown_result = source / "report.pdf.result.md"
    json_result = source / "report.pdf.result.json"
    for path in (visible, hidden, markdown_result, json_result):
        path.write_text(path.name)

    plan = plan_inputs(sources=[source])

    assert [item.path for item in plan.inputs] == [visible.resolve()]
    assert [(item.path, item.reason) for item in plan.skipped] == [
        (hidden.resolve(), "hidden file skipped")
    ]


def test_recursive_discovery_excludes_hidden_paths_and_generated_files(tmp_path):
    source = tmp_path / "source"
    visible = source / "visible" / "nested.pdf"
    hidden_file = source / "visible" / ".hidden.pdf"
    hidden_directory_file = source / ".hidden" / "nested.pdf"
    nested_result = source / "visible" / "nested.pdf.result.json"
    for path in (visible, hidden_file, hidden_directory_file, nested_result):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.name)

    plan = plan_inputs(sources=[source], recursive=True)

    assert [item.path for item in plan.inputs] == [visible.resolve()]
    assert [(item.path, item.reason) for item in plan.skipped] == [
        (hidden_file.resolve(), "hidden file skipped")
    ]


@pytest.mark.parametrize("filename", [".hidden.pdf", "report.pdf.result.md", "report.pdf.result.json"])
def test_explicit_files_allow_hidden_and_generated_files(tmp_path, filename):
    selected = tmp_path / filename
    selected.write_text(filename)

    plan = plan_inputs(files=[selected])

    assert [item.path for item in plan.inputs] == [selected.resolve()]


def test_empty_discovery_is_an_error(tmp_path):
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValidationError, match="did not find any files"):
        plan_inputs(sources=[source])


def test_hidden_only_discovery_names_skipped_file(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    hidden = source / ".DS_Store"
    hidden.write_text("metadata")

    with pytest.raises(ValidationError, match=r"\.DS_Store \(hidden file skipped\)"):
        plan_inputs(sources=[source])


def test_output_file_requires_exactly_one_input(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_text("a")
    second.write_text("b")
    inputs = plan_inputs(files=[first, second])

    with pytest.raises(UsageError, match="exactly one"):
        plan_outputs(inputs, view=ResultView.FULL, output_file=tmp_path / "out.json")


def test_output_file_and_directory_are_mutually_exclusive(tmp_path):
    input_file = tmp_path / "input.pdf"
    input_file.write_text("input")
    inputs = plan_inputs(files=[input_file])

    with pytest.raises(UsageError, match="cannot be combined"):
        plan_outputs(
            inputs,
            view=ResultView.FULL,
            output_file=tmp_path / "out.json",
            output_dir=tmp_path / "out",
        )


def test_single_input_streams_without_destination_by_default(tmp_path):
    input_file = tmp_path / "input.pdf"
    input_file.write_text("input")

    execution = plan_outputs(
        plan_inputs(files=[input_file]),
        view=ResultView.LLM_INPUT,
    )

    assert execution.outputs[0].path is None


@pytest.mark.parametrize("selection", ["positional", "urls"])
@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
def test_remote_input_uses_url_filename_under_output_directory(tmp_path, selection, view):
    url = "https://storage.example.test/container/sample.pdf?sv=1&sig=secret"

    execution = plan_outputs(
        plan_inputs(**{selection: [url]}),
        view=view,
        output_dir=tmp_path / "results",
    )

    suffix = ".result.json" if view is ResultView.FULL else ".result.md"
    assert execution.outputs[0].path == tmp_path / f"results/sample.pdf{suffix}"
    assert "secret" not in str(execution.outputs[0].path)


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
@pytest.mark.parametrize(
    "basename",
    ["a" * 230 + ".pdf", "\u4e2d" * 100 + ".pdf", "a" * 7000],
    ids=["ascii", "unicode", "long-url"],
)
def test_remote_generated_filename_over_byte_budget_is_rejected(tmp_path, view, basename):
    url = f"https://example.test/{basename}?sig=secret"
    output_dir = tmp_path / "results"

    with pytest.raises(ValidationError, match="240-byte UTF-8 limit") as error:
        plan_outputs(plan_inputs(urls=[url]), view=view, output_dir=output_dir)

    assert "--output-file" in (error.value.hint or "")
    assert "secret" not in str(error.value)
    assert not output_dir.exists()


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
@pytest.mark.parametrize("reverse_inputs", [False, True])
@pytest.mark.parametrize("policy", list(ExistingResultPolicy))
def test_mixed_collisions_are_rejected_before_existing_policy(
    tmp_path, view, reverse_inputs, policy,
):
    url = "https://example.test/input.pdf?id=one&sig=secret"
    output_dir = tmp_path / "results"
    suffix = ".result.json" if view is ResultView.FULL else ".result.md"
    local = tmp_path / "input.pdf"
    local.write_text("local input")
    inputs = [url, str(local)]
    if reverse_inputs:
        inputs.reverse()

    with pytest.raises(ValidationError, match="same result output path") as error:
        plan_outputs(
            plan_inputs(positional=inputs), view=view, output_dir=output_dir, on_existing=policy,
        )

    assert str(output_dir / f"input.pdf{suffix}") in str(error.value)
    assert str(local.resolve()) in str(error.value)
    assert redact_input_reference(url) in str(error.value)
    assert "secret" not in str(error.value)
    assert "--output-file" in (error.value.hint or "")
    assert not output_dir.exists()


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
@pytest.mark.parametrize("policy", list(ExistingResultPolicy))
@pytest.mark.parametrize(
    ("urls", "basename"),
    [
        (
            ("https://one.example.test/a/input.pdf", "https://two.example.test/b/input.pdf"),
            "input.pdf",
        ),
        (
            ("https://example.test/input.pdf?id=one", "https://example.test/input.pdf?id=two"),
            "input.pdf",
        ),
        (
            ("https://example.test/input:one.pdf", "https://example.test/input_one.pdf"),
            "input_one.pdf",
        ),
        (("https://example.test/CON.pdf", "https://example.test/_CON.pdf"), "_CON.pdf"),
        (("https://one.example.test/", "https://two.example.test/"), "remote-input"),
    ],
    ids=["basename", "query", "sanitized", "reserved", "empty-path"],
)
def test_remote_output_collisions_are_rejected(tmp_path, view, policy, urls, basename):
    signed_urls = [url + ("&" if "?" in url else "?") + "sig=secret" for url in urls]
    inputs = plan_inputs(urls=signed_urls)
    output_dir = tmp_path / "results"
    suffix = ".result.json" if view is ResultView.FULL else ".result.md"

    with pytest.raises(ValidationError, match="same result output path") as error:
        plan_outputs(inputs, view=view, output_dir=output_dir, on_existing=policy)

    assert str(output_dir / f"{basename}{suffix}") in str(error.value)
    assert all(redact_input_reference(url) in str(error.value) for url in signed_urls)
    assert "secret" not in str(error.value)
    assert not output_dir.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_remote_case_only_output_collision_is_rejected_on_windows(tmp_path):
    inputs = plan_inputs(urls=[
        "https://example.test/Invoice.pdf",
        "https://example.test/invoice.pdf",
    ])

    with pytest.raises(ValidationError, match="same result output path"):
        plan_outputs(inputs, view=ResultView.FULL, output_dir=tmp_path / "results")


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
def test_exhausted_local_collision_names_are_rejected(tmp_path, view):
    output_dir = tmp_path / "results"
    inputs = []
    for directory in ("first", "second"):
        local = tmp_path / directory / "input.pdf"
        local.parent.mkdir()
        local.write_text("local input")
        inputs.append(str(local))
    local = Path(inputs[0])
    digest = hashlib.sha1(str(local.resolve()).encode("utf-8")).hexdigest()
    for length in range(8, len(digest) + 1, 8):
        neighbor = local.with_name(f"{local.name}.{digest[:length]}")
        neighbor.write_text("neighbor input")
        inputs.append(str(neighbor))

    with pytest.raises(ValidationError, match="cannot resolve result output path collision"):
        plan_outputs(plan_inputs(positional=inputs), view=view, output_dir=output_dir)

    assert not output_dir.exists()


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
def test_local_digest_collisions_stay_stable_when_reordered(tmp_path, monkeypatch, view):
    inputs = []
    for directory in ("first", "second"):
        local = tmp_path / directory / "same.pdf"
        local.parent.mkdir()
        local.write_text(directory)
        inputs.append(local)
    digest = hashlib.sha1(b"collision")
    monkeypatch.setattr("cu_cli_core.input_planning.hashlib.sha1", lambda _value: digest)
    original = plan_outputs(
        plan_inputs(positional=inputs), view=view, output_dir=tmp_path / "results",
    )
    reordered = plan_outputs(
        plan_inputs(positional=list(reversed(inputs))),
        view=view, output_dir=tmp_path / "results",
    )

    original_paths = {output.source.reference: output.path for output in original.outputs}
    reordered_paths = {output.source.reference: output.path for output in reordered.outputs}
    assert len(set(original_paths.values())) == 2
    assert reordered_paths == original_paths


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
@pytest.mark.parametrize("basename", ["input.pdf", "a" * 7000], ids=["short", "long"])
def test_remote_explicit_output_file_is_unchanged(tmp_path, view, basename):
    output = tmp_path / "custom.json"
    execution = plan_outputs(
        plan_inputs(urls=[f"https://example.test/{basename}?sig=secret"]),
        view=view,
        output_file=output,
    )

    assert execution.outputs[0].path == output


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
def test_remote_long_filename_can_still_stream_to_stdout(view):
    execution = plan_outputs(
        plan_inputs(urls=[f"https://example.test/{'a' * 7000}?sig=secret"]), view=view,
    )

    assert execution.outputs[0].path is None


def test_remote_batch_requires_output_directory():
    inputs = plan_inputs(
        positional=[
            "https://one.example.test/a.pdf",
            "https://two.example.test/b.pdf",
        ]
    )

    with pytest.raises(UsageError, match="--output-dir is required"):
        plan_outputs(inputs, view=ResultView.FULL)


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
def test_distinct_remote_outputs_preserve_filenames_and_extensions(tmp_path, view):
    inputs = plan_inputs(
        urls=[
            "https://one.example.test/c/input.pdf?sig=first-secret",
            "https://two.example.test/c/input.png?sig=second-secret",
        ]
    )

    execution = plan_outputs(
        inputs,
        view=view,
        output_dir=tmp_path / "results",
    )

    paths = [output.path for output in execution.outputs]
    suffix = ".result.json" if view is ResultView.FULL else ".result.md"
    assert paths == [
        tmp_path / "results" / f"input.pdf{suffix}",
        tmp_path / "results" / f"input.png{suffix}",
    ]


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
@pytest.mark.parametrize("add_unrelated_input", [False, True])
@pytest.mark.parametrize("keep_single_input", [False, True])
def test_remote_paths_remain_stable_when_inputs_reordered(
    tmp_path, view, add_unrelated_input, keep_single_input,
):
    urls = [
        "https://example.test/one.pdf?sig=first-secret",
        "https://example.test/two.pdf?sig=second-secret",
    ]
    output_dir = tmp_path / "results"
    original = plan_outputs(
        plan_inputs(positional=urls), view=view, output_dir=output_dir,
    )
    original_paths = {output.source.url: output.path for output in original.outputs}
    assert len(set(original_paths.values())) == 2
    output_dir.mkdir()
    for output in original.outputs:
        assert output.path is not None
        assert "secret" not in output.path.name
        output.path.write_text(output.source.url, encoding="utf-8")

    reordered = list(reversed(urls))
    if keep_single_input:
        reordered = reordered[:1]
    if add_unrelated_input:
        reordered.insert(0, "https://example.test/other.pdf")
    execution = plan_outputs(
        plan_inputs(positional=reordered),
        view=view,
        output_dir=output_dir,
        on_existing=ExistingResultPolicy.SKIP,
    )

    for output in execution.outputs:
        if output.source.url not in original_paths:
            assert not output.exists
            assert not output.skipped
            continue
        assert output.path == original_paths[output.source.url]
        assert output.exists
        assert output.skipped
        assert output.path.read_text(encoding="utf-8") == output.source.url


@pytest.mark.parametrize("view", [ResultView.FULL, ResultView.LLM_INPUT])
@pytest.mark.parametrize("policy", list(ExistingResultPolicy))
def test_remote_result_path_is_unchanged_when_sas_is_renewed(tmp_path, view, policy):
    original_url = "https://example.test/input.pdf?sig=original-secret"
    renewed_url = "https://example.test/input.pdf?sig=renewed-secret"
    original = plan_outputs(
        plan_inputs(urls=[original_url]), view=view, output_dir=tmp_path,
    ).outputs[0].path
    assert original is not None
    original.write_text("existing result")

    output = plan_outputs(
        plan_inputs(urls=[renewed_url]), view=view, output_dir=tmp_path, on_existing=policy,
    ).outputs[0]

    assert output.path == original
    assert output.exists
    assert output.skipped is (policy is ExistingResultPolicy.SKIP)
    assert output.path.read_text() == "existing result"


def test_multiple_inputs_write_alongside_sources(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_text("a")
    second.write_text("b")

    execution = plan_outputs(
        plan_inputs(files=[first, second]),
        view=ResultView.FULL,
    )

    assert [output.path for output in execution.outputs] == [
        Path(f"{first.resolve()}.result.json"),
        Path(f"{second.resolve()}.result.json"),
    ]


def test_output_directory_preserves_source_relative_paths(tmp_path):
    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    input_file = nested / "input.pdf"
    input_file.write_text("input")

    execution = plan_outputs(
        plan_inputs(sources=[source], recursive=True),
        view=ResultView.LLM_INPUT,
        output_dir=tmp_path / "results",
    )

    assert execution.outputs[0].path == (
        tmp_path / "results" / "nested" / "input.pdf.result.md"
    )


def test_output_collisions_are_disambiguated_before_existing_policy(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "same.pdf").write_text("a")
    (second / "same.pdf").write_text("b")
    inputs = plan_inputs(sources=[first, second])

    execution = plan_outputs(
        inputs,
        view=ResultView.FULL,
        output_dir=tmp_path / "results",
    )

    paths = [output.path for output in execution.outputs]
    assert len(set(paths)) == 2
    assert all(path is not None and path.name.startswith("same.pdf.") for path in paths)


@pytest.mark.parametrize(
    ("policy", "skipped"),
    [
        (ExistingResultPolicy.ERROR, False),
        (ExistingResultPolicy.SKIP, True),
        (ExistingResultPolicy.REANALYZE, False),
    ],
)
def test_existing_output_policy_is_planned(tmp_path, policy, skipped):
    input_file = tmp_path / "input.pdf"
    output_file = tmp_path / "output.json"
    input_file.write_text("input")
    output_file.write_text("existing")

    execution = plan_outputs(
        plan_inputs(files=[input_file]),
        view=ResultView.FULL,
        output_file=output_file,
        on_existing=policy,
    )

    assert execution.outputs[0].exists
    assert execution.outputs[0].skipped is skipped
