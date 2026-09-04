from __future__ import annotations

import os
from pathlib import Path

import pytest

from cu_cli_core.contracts import ExistingResultPolicy, ResultView, SelectionMode
from cu_cli_core.errors import UsageError, ValidationError
from cu_cli_core.input_planning import plan_inputs, plan_outputs

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
