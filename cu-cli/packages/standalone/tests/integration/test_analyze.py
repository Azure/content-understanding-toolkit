# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Integration tests for the ``analyze`` command.

Covers single-file markdown output, directory batch with --output-dir, and prebuilt
analyzer JSON output (README scenarios §1 and §6).

Tests use the record/playback harness (playback by default in CI); set
``CU_TEST_REC_MODE=record`` to hit a real endpoint and regenerate cassettes.
"""

from __future__ import annotations

import shutil
import json
import re
from pathlib import Path

import pytest


from support.recording import copy_sample_invoice as _copy_sample
from support.recording import PLACEHOLDER_ENDPOINT, mode, use_cassette
from support.command_catalog import invoke_cli, record_output

pytestmark = pytest.mark.integration


def _run(*args, **kwargs):
    return invoke_cli(args, **kwargs)


@pytest.mark.parametrize("analyzer_option", ["--analyzer", "-a"], ids=["long", "short"])
def test_scenario_1_analyze_single_file_markdown(cloud_project, analyzer_option):
    _copy_sample()
    arguments = ["analyze", "sample_invoice.pdf", analyzer_option, "prebuilt-layout"]
    with use_cassette("analyze_single") as cassette:
        if analyzer_option == "--analyzer":
            # region Snippet:analyze_layout
            res = _run(
                *arguments,
                comment=(
                    "Generate Markdown from the analyzer result with the CU SDK's to_llm_input().\n"
                    "This is a billed service call; Markdown is written to standard output."
                ),
            )
            # endregion
        else:
            # region Snippet:analyze_layout_short
            res = _run(*arguments, comment="`-a` is the short form of `--analyzer`.")
            # endregion
    assert res.exit_code == 0, res.output
    if mode() == "playback":
        assert cassette.play_count > 0
    assert res.output.startswith("---")
    assert "mimeType:" in res.output
    assert "pages:" in res.output
    assert "<!-- InputPageNumber:" in res.output


def test_scenario_1_analyze_directory_writes_result_files(cloud_project):
    """`cu analyze <dir> --output-dir <dir>` writes Markdown result files."""
    source = Path("my_document_dir")
    source.mkdir()
    sample = _copy_sample()
    shutil.move(str(sample), str(source / "sample_invoice.pdf"))
    with use_cassette("analyze_batch") as cassette:
        # region Snippet:analyze_directory
        res = _run(
            "analyze",
            str(source),
            "--analyzer",
            "prebuilt-layout",
            "--output-dir",
            "out",
        )
        # endregion
    assert res.exit_code == 0, res.output
    if mode() == "playback":
        assert cassette.play_count > 0
    # Paths under --output-dir are relative to the selected source directory.
    output = Path("out") / "sample_invoice.pdf.result.md"
    assert list(Path("out").rglob("*.result.*")) == [output]
    content = output.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "mimeType:" in content
    assert "<!-- InputPageNumber:" in content


def test_scenario_3_analyze_prebuilt_invoice_json(cloud_project):
    """`cu analyze -a prebuilt-invoice --json`."""
    import json
    _copy_sample()
    with use_cassette("analyze_prebuilt_invoice_json"):
        # region Snippet:analyze_invoice
        res = _run("analyze", "sample_invoice.pdf",
                   "-a", "prebuilt-invoice", "--json")
        # endregion
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output[res.output.find("{"):])
    assert payload["status"] == "Succeeded"
    assert payload["result"]["analyzerId"] == "prebuilt-invoice"
    assert payload["result"]["contents"]
    assert "usage" in payload


def test_inline_preview_uses_real_sdk_and_invoice(cloud_project):
    sample = _copy_sample()
    with use_cassette("analyze_inline_preview"):
        # region Snippet:analyze_inline
        result = _run(
            "analyze", "--inline", "--api-version", "2026-06-01-preview",
            str(sample), "--analyzer", "prebuilt-layout", "--json",
        )
        # endregion
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["result"]["analyzerId"] == "prebuilt-layout"
    assert payload["result"]["contents"][0]["markdown"]
    assert payload["result"]["contents"][0]["kind"] == "document"


def test_public_video_url_uses_real_sdk(cloud_project):
    video_url = (
        "https://github.com/Azure-Samples/azure-ai-content-understanding-assets/"
        "raw/refs/heads/main/videos/sdk_samples/FlightSimulator.mp4"
    )
    with use_cassette("analyze_public_video_url"):
        # region Snippet:analyze_video_url
        result = _run(
            "analyze", "--url", video_url, "--analyzer", "prebuilt-videoSearch", "--json",
        )
        # endregion
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "Succeeded"
    assert payload["result"]["analyzerId"] == "prebuilt-videoSearch"
    contents = payload["result"]["contents"]
    assert contents and all(content["kind"] == "audioVisual" for content in contents)
    assert any(content.get("markdown") for content in contents)
    assert any(content["endTimeMs"] > content["startTimeMs"] for content in contents)


@pytest.mark.parametrize("view", ["markdown_file", "json_file", "json_stdout", "llm_input", "usage"])
def test_analysis_output_views_use_real_sdk_and_recordings(cloud_project, view):
    _copy_sample()
    options = {
        "markdown_file": ("--output-file", "results/invoice.md"),
        "json_file": ("--json", "--output-file", "results/invoice.json"),
        "json_stdout": ("--json",),
        "llm_input": ("--llm-input", "--time"),
        "usage": ("--json", "--usage", "--time"),
    }[view]
    arguments = ("analyze", "sample_invoice.pdf", "--analyzer", "prebuilt-layout", *options)
    with use_cassette("analyze_single") as cassette:
        if view == "markdown_file":
            # region Snippet:analyze_markdown_file
            result = _run(
                *arguments, comment="Save Markdown instead of printing it; parent directories are created.",
            )
            # endregion
        elif view == "json_file":
            # region Snippet:analyze_json_file
            result = _run(*arguments, comment="Save structured JSON instead of printing it.")
            # endregion
        elif view == "json_stdout":
            # region Snippet:analyze_json
            result = _run(*arguments, comment="Print the complete structured result as JSON to the terminal.")
            # endregion
        elif view == "usage":
            # region Snippet:analyze_usage
            result = _run(*arguments)
            # endregion
        else:
            # region Snippet:analyze_llm_input
            result = _run(*arguments, comment="Print service-call and total elapsed time for the analysis.")
            # endregion
    assert result.exit_code == 0, result.output
    if mode() == "playback":
        assert cassette.play_count > 0
    if view in {"json_file", "json_stdout", "usage"}:
        text = Path("results/invoice.json").read_text(encoding="utf-8") if view == "json_file" else result.stdout
        payload = json.loads(text)
        assert payload["status"] == "Succeeded"
        assert payload["result"]["analyzerId"] == "prebuilt-layout"
        assert payload["result"]["contents"][0]["markdown"]
    else:
        text = Path("results/invoice.md").read_text(encoding="utf-8") if view == "markdown_file" else result.stdout
        assert "mimeType:" in text and "<!-- InputPageNumber:" in text
    if view == "usage":
        usage_text = result.stderr.split("Usage:", 1)[1]
        assert "sample_invoice.pdf" in usage_text
        reported_usage, _end = json.JSONDecoder().raw_decode(usage_text[usage_text.index("{"):])
        assert reported_usage == payload["usage"]
        assert reported_usage
    if view in {"llm_input", "usage"}:
        timings = [line for line in result.stderr.splitlines() if "time:" in line]
        assert len(timings) == 2
        if view == "llm_input":
            # region Snippet:analysis_timing
            record_output(re.sub(r"\d+\.\d+s", "<seconds>s", "\n".join(timings)))
            # endregion


def test_configure_profile_then_analyze_without_preseeded_settings(monkeypatch):
    from cu_cli.profile import ProfileStore, azure_config_path

    monkeypatch.setenv("CU_TEST_REC_MODE", "playback")
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)
    _copy_sample()
    assert not azure_config_path().exists()
    # region Snippet:configure_key
    # region Snippet:profile_endpoint
    _run(
        "profile", "set", "endpoint", "https://<resource-name>.services.ai.azure.com/",
        placeholder_values={"resource-name": "sanitized"},
        comment="Save the endpoint on the active profile.",
    )
    # endregion
    # region Snippet:profile_key
    _run(
        "profile", "set", "api_key", "<key>",
        placeholder_values={"key": "playback-dummy-key"},
        comment="Save a resource key on the active profile and select key authentication.",
    )
    # endregion
    store = ProfileStore.load()
    assert store.get("endpoint") == PLACEHOLDER_ENDPOINT
    assert store.get("auth_mode") == "key"
    with use_cassette("doctor"):
        # region Snippet:doctor
        result = _run("doctor", comment="Check the active profile.")
        # endregion
    assert result.exit_code == 0, result.output
    # endregion
    # region Snippet:profile_default_analyzer
    _run(
        "profile", "set", "default_analyzer", "prebuilt-layout",
        comment="Save the default analyzer on the active profile.",
    )
    # endregion
    with use_cassette("analyze_single"):
        # region Snippet:analyze_default
        result = _run(
            "analyze", "sample_invoice.pdf", "--json",
            comment="Analyze one file using the saved default analyzer.",
        )
        # endregion
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "Succeeded"
    assert payload["result"]["analyzerId"] == "prebuilt-layout"
    assert payload["result"]["contents"][0]["markdown"]


@pytest.mark.parametrize("policy", ["skip", "reanalyze"])
def test_existing_recorded_result_is_skipped_or_reanalyzed(cloud_project, policy):
    _copy_sample()
    setup = _run("profile", "set", "default_analyzer", "prebuilt-layout")
    assert setup.exit_code == 0, setup.output
    arguments = ["analyze", "sample_invoice.pdf", "--json", "--output-file", "result.json"]
    with use_cassette("analyze_single"):
        original = _run(*arguments)
    assert original.exit_code == 0, original.output
    output = Path("result.json")
    content = output.read_bytes()
    modified = output.stat().st_mtime_ns
    assert json.loads(content)["result"]["contents"]

    with use_cassette("analyze_single") as cassette:
        if policy == "skip":
            # region Snippet:analyze_skip
            result = _run(*arguments, "--on-existing", policy)
            # endregion
        else:
            # region Snippet:analyze_reanalyze
            result = _run(*arguments, "--on-existing", policy)
            # endregion
    assert result.exit_code == 0, result.output
    if mode() == "playback":
        assert (cassette.play_count > 0) == (policy == "reanalyze")
    if policy == "skip":
        assert output.read_bytes() == content
        assert output.stat().st_mtime_ns == modified
    else:
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["status"] == "Succeeded"
        assert payload["result"]["analyzerId"] == "prebuilt-layout"
        assert payload["result"]["contents"]


@pytest.mark.parametrize(
    ("recursive", "with_report"), [(False, False), (True, False), (True, True)],
    ids=["immediate", "recursive", "nested-report"],
)
def test_directory_examples_use_recorded_invoice_content(cloud_project, recursive, with_report):
    source = Path("my_document_dir")
    sample = source / "nested/sample_invoice.pdf" if recursive else source / "sample_invoice.pdf"
    _copy_sample(sample)
    (source / "excluded.txt").write_text("excluded by the PDF filename pattern", encoding="utf-8")
    destination = Path("batch-results" if with_report else "recursive-results" if recursive else "results")
    arguments = ["analyze", "--source", str(source), "--pattern", "*.pdf"]
    if recursive:
        arguments.append("--recursive")
    analyzer_option = "--analyzer" if recursive else "-a"
    arguments.extend([analyzer_option, "prebuilt-layout", "--output-dir", str(destination)])
    if with_report:
        arguments.extend(["--report-file", "run-report.json", "--yes", "--concurrency", "8"])

    with use_cassette("analyze_batch") as cassette:
        if with_report:
            # region Snippet:analyze_recursive_report
            result = _run(
                *arguments,
                comment=(
                    "Analyze recursively, save one Markdown result per input, and record all statuses in JSON.\n"
                    "Process up to eight batch jobs concurrently instead of the default four."
                ),
            )
            # endregion
        elif recursive:
            # region Snippet:analyze_recursive
            result = _run(
                *arguments, comment="Quote the pattern so CU CLI, rather than the shell, applies it.",
            )
            # endregion
        else:
            # region Snippet:analyze_pattern
            result = _run(*arguments, comment="Analyze only matching files directly inside my_document_dir.")
            # endregion

    assert result.exit_code == 0, result.output
    if mode() == "playback":
        assert cassette.play_count > 0
    output = destination / (sample.relative_to(source).as_posix() + ".result.md")
    assert list(destination.rglob("*.result.*")) == [output]
    content = output.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "mimeType:" in content
    assert "<!-- InputPageNumber:" in content
    if with_report:
        report = json.loads(Path("run-report.json").read_text(encoding="utf-8"))
        assert report["counts"]["succeeded"] == 1
        assert report["counts"]["failed"] == 0
    elif recursive:
        # region Snippet:output_mapping
        record_output(f"{sample.as_posix()}\n  -> {output.as_posix()}")
        # endregion
