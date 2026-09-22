# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from click import unstyle
import pytest

from support.command_catalog import invoke_cli
from support.recording import copy_sample_invoice

pytestmark = pytest.mark.unit


def _run(
    *args: str,
    placeholder_values: dict[str, str] | None = None,
):
    return invoke_cli(args, placeholder_values=placeholder_values)


@pytest.fixture
def analyze_runtime(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (
            job,
            {"status": "Succeeded", "result": {"analyzerId": job.analyzer_id}},
        ),
    )


def test_help_exposes_preview_contract_and_removes_replaced_options():
    result = _run("analyze", "--help")

    assert result.exit_code == 0
    for option in (
        "--file",
        "--source",
        "--url",
        "--pattern",
        "--recursive",
        "--llm-input",
        "--json",
        "--output-file",
        "--output-dir",
        "--on-existing",
        "--dry-run",
        "--report-file",
        "--auth-mode",
    ):
        assert option in result.output
    for replaced in ("--out ", "--output ", "--force", "--skip-existing", "--report "):
        assert replaced not in result.output


@pytest.mark.parametrize(
    "args",
    [
        ("input.pdf", "--file", "other.pdf"),
        ("input.pdf", "--source", "documents"),
        ("--file", "input.pdf", "--source", "documents"),
        ("--file", "input.pdf", "--pattern", "*.pdf"),
        ("input.pdf", "--url", "https://example.test/input.pdf"),
        ("--file", "input.pdf", "--url", "https://example.test/input.pdf"),
        ("--source", "documents", "--url", "https://example.test/input.pdf"),
        ("--url", "https://example.test/input.pdf", "--pattern", "*.pdf"),
        ("--url", "https://example.test/input.pdf", "--recursive"),
    ],
)
def test_invalid_selection_modes_fail_before_config_or_client(monkeypatch, args):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run("analyze", *args)

    assert result.exit_code == 2


def test_positional_wildcard_is_not_interpreted_by_cu(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )

    result = _run("analyze", "*.pdf")

    assert result.exit_code == 2
    assert "wildcard patterns aren't accepted" in result.output
    assert "--source" in result.output
    assert "--pattern" in result.output


@pytest.mark.parametrize("input_option", [(), ("--url",)], ids=["positional", "named"])
def test_https_sas_url_reaches_url_runner_without_secret_in_display(
    analyze_runtime,
    monkeypatch,
    input_option,
):
    url = (
        "https://storage.example.test/container/video.mp4"
        "?sv=2026-01-01&sp=r&sig=a%2Bb%2Fc%3D"
    )
    captured = []

    def run_one(_client, job):
        captured.append(job)
        return job, {"status": "Succeeded", "result": {"analyzerId": job.analyzer_id}}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)

    result = _run("analyze", *input_option, url, "--json")

    assert result.exit_code == 0, result.output
    assert captured[0].input_url == url
    assert captured[0].input_ref.endswith("video.mp4?REDACTED")
    assert "a%2Bb%2Fc%3D" not in result.output


@pytest.mark.parametrize(
    "url_suffix",
    ["input.pdf?sv=1", "bob's/input.pdf?sv=1", "input.pdf?sv=1&rscc=it's-private"],
)
def test_success_json_redacts_sas_echoed_by_service(analyze_runtime, monkeypatch, url_suffix):
    secret = "success-json-secret"
    url = f"https://storage.example.test/c/{url_suffix}&sig={secret}"
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"warning": f"Downloaded {job.input_url}"}),
    )

    result = _run("analyze", url, "--json")

    assert result.exit_code == 0, result.output
    assert secret not in result.output
    assert json.loads(result.output)["warning"].endswith("input.pdf?REDACTED")


@pytest.mark.parametrize(
    "url_suffix",
    ["input.pdf?sv=1", "bob's/input.pdf?sv=1", "input.pdf?sv=1&rscc=it's-private"],
)
def test_success_markdown_redacts_sas_echoed_by_service(
    analyze_runtime, monkeypatch, url_suffix,
):
    secret = "success-markdown-secret"
    url = f"https://storage.example.test/c/{url_suffix}&sig={secret}"
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"contents": [{
            "kind": "document", "markdown": f"Source: {job.input_url}\n",
        }]}),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.render_markdown",
        lambda result: result["contents"][0]["markdown"],
    )

    result = _run("analyze", url)

    assert result.exit_code == 0, result.output
    assert secret not in result.output
    assert "input.pdf?REDACTED" in result.output


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("write_file", [False, True])
@pytest.mark.parametrize("query", ["", "?sv=1&sig=output-secret", "?rscc=it's-private&sig=output-secret"])
def test_remote_result_preserves_unrelated_links_and_markdown(
    analyze_runtime, monkeypatch, json_output, write_file, query,
):
    url = f"https://storage.example.test/c/bob's.pdf{query}"
    public_link = "[invoice](https://example.test/view?id=42&lang=en)"
    body = f"{public_link}\n[source]({url}) after\n"
    expected_url = "https://storage.example.test/c/bob's.pdf" + (
        "?REDACTED" if query else ""
    )
    expected_body = f"{public_link}\n[source]({expected_url}) after\n"
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"contents": [{"markdown": body}], "source": url}),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.render_markdown",
        lambda result: result["contents"][0]["markdown"],
    )
    output_dir = Path("results")
    args = ["analyze", url]
    if json_output:
        args.append("--json")
    if write_file:
        args.extend(["--output-dir", str(output_dir)])

    result = _run(*args)

    assert result.exit_code == 0, result.output
    if write_file:
        outputs = list(output_dir.iterdir())
        assert len(outputs) == 1
        text = outputs[0].read_text(encoding="utf-8")
    else:
        text = result.stdout
    if json_output:
        assert json.loads(text) == {
            "contents": [{"markdown": expected_body}], "source": expected_url,
        }
    else:
        assert text == expected_body
    assert "output-secret" not in text


@pytest.mark.parametrize("write_file", [False, True])
def test_remote_markdown_redacts_before_sdk_yaml_escaping(
    analyze_runtime, monkeypatch, write_file,
):
    from cu_cli.output import render_markdown

    url = "https://example.test/bob's.pdf?sv=1&sig=render-secret"
    safe_url = "https://example.test/bob's.pdf?REDACTED"
    public_link = "[invoice](https://example.test/view?id=42)"

    def make_result(source):
        return {"contents": [{
            "mimeType": "application/pdf",
            "metadata": {"source": f"Downloaded: {source}"},
            "markdown": f"{public_link}\n[source]({source}) after",
        }]}

    original = make_result(url)
    expected = render_markdown(make_result(safe_url))
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one", lambda _client, job: (job, original),
    )
    args = ["analyze", url]
    if write_file:
        args.extend(["--output-file", "output.md"])

    result = _run(*args)

    assert result.exit_code == 0, result.output
    text = Path("output.md").read_text(encoding="utf-8") if write_file else result.stdout
    assert text.rstrip("\n") == expected.rstrip("\n")
    assert "render-secret" not in text
    assert public_link in text
    assert original["contents"][0]["metadata"]["source"] == f"Downloaded: {url}"


@pytest.mark.parametrize("json_output", [False, True], ids=["markdown", "json"])
@pytest.mark.parametrize("write_file", [False, True])
@pytest.mark.parametrize("classification", [False, True], ids=["pages", "classification"])
@pytest.mark.parametrize(
    "query", ["?q=1", "?sv=1&sig=" + "x" * 90], ids=["longer-redaction", "shorter-redaction"],
)
def test_remote_result_redaction_preserves_span_boundaries(
    analyze_runtime, monkeypatch, tmp_path, json_output, write_file, classification, query,
):
    from cu_cli.output import render_markdown

    url = f"https://example.test/bob's.pdf{query}"
    safe_url = "https://example.test/bob's.pdf?REDACTED"
    public_link = "[invoice](https://example.test/view?id=42&lang=en)"

    def make_result(source):
        first_page = f"[source]({source})\n\n{public_link}\n\n"
        second_page = f"SECOND_PAGE_UNIQUE_BODY\n[source]({source})\n"
        content = {
            "kind": "document",
            "mimeType": "application/pdf",
            "path": "input1",
            "metadata": {"source": f"Downloaded: {source}"},
            "markdown": first_page + second_page,
        }
        spans = [
            {"offset": 0, "length": len(first_page)},
            {"offset": len(first_page), "length": len(second_page)},
        ]
        if classification:
            content["segments"] = [
                {
                    "segmentId": str(page_number),
                    "category": category,
                    "startPageNumber": page_number,
                    "endPageNumber": page_number,
                    "span": span,
                }
                for page_number, category, span in zip(
                    [1, 2], ["receipt", "invoice"], spans, strict=True,
                )
            ]
        else:
            content["pages"] = [
                {"pageNumber": page_number, "spans": [span]}
                for page_number, span in enumerate(spans, start=1)
            ]
        return {"contents": [content]}

    original = make_result(url)
    snapshot = copy.deepcopy(original)
    expected_result = make_result(safe_url)
    expected = render_markdown(expected_result)
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one", lambda _client, job: (job, original),
    )
    args = ["analyze", url]
    if json_output:
        args.append("--json")
    destination = tmp_path / ("result.json" if json_output else "result.md")
    if write_file:
        args.extend(["--output-file", str(destination)])

    result = _run(*args)

    assert result.exit_code == 0, result.output
    text = destination.read_text(encoding="utf-8") if write_file else result.stdout
    if json_output:
        exported = json.loads(text)
        assert exported == expected_result
        rendered = render_markdown(exported)
    else:
        rendered = text
    assert rendered.rstrip("\n") == expected.rstrip("\n")
    assert public_link in text
    assert original == snapshot


@pytest.mark.parametrize("write_file", [False, True])
@pytest.mark.parametrize(
    "query", ["?q=1", "?sig=" + "x" * 90], ids=["longer-redaction", "shorter-redaction"],
)
def test_remote_json_redaction_preserves_nested_spans(
    analyze_runtime, monkeypatch, tmp_path, write_file, query,
):
    from cu_cli.output import render_markdown

    url = f"https://example.test/input.pdf{query}"
    safe_url = "https://example.test/input.pdf?REDACTED"

    def make_result(source):
        prefix = "Before \u4e2d\U0001f680\n"
        tail = "SECOND_CONTENT"
        markdown = f"{prefix}{source}\n{tail}"
        url_span = {"offset": len(prefix), "length": len(source)}
        tail_span = {"offset": len(prefix) + len(source) + 1, "length": len(tail)}
        opaque = {"span": {"offset": 100, "length": 20}, "spans": [1, 2], "url": source}
        return {
            "stringEncoding": "unicodeCodePoint",
            "contents": [{
                "kind": "document",
                "mimeType": "application/pdf",
                "markdown": markdown,
                "metadata": {"span": "business metadata", "source": source},
                "pages": [{
                    "pageNumber": 1,
                    "spans": [{"offset": 0, "length": len(markdown)}],
                    "lines": [{"content": source, "span": url_span}],
                    "words": [{"content": tail, "span": tail_span}],
                }],
                "paragraphs": [{"content": tail, "span": tail_span}],
                "tables": [{
                    "rowCount": 1, "columnCount": 1, "span": tail_span,
                    "cells": [{
                        "rowIndex": 0, "columnIndex": 0, "content": tail, "span": tail_span,
                    }],
                }],
                "annotations": [{"kind": "highlight", "spans": [tail_span]}],
                "chunks": [{"content": tail, "spans": [tail_span]}],
                "figures": [{"kind": "chart", "span": tail_span, "content": opaque}],
                "fields": {
                    "metadata": {"type": "object", "valueObject": {
                        "spans": {"type": "string", "valueString": source, "spans": [url_span]},
                        "data": {"type": "json", "valueJson": opaque, "spans": [url_span]},
                    }},
                    "rows": {"type": "array", "valueArray": [
                        {"type": "string", "valueString": tail, "spans": [tail_span]},
                    ]},
                },
            }, {
                "kind": "document",
                "mimeType": "application/pdf",
                "markdown": tail,
                "pages": [{"pageNumber": 2, "spans": [{"offset": 0, "length": len(tail)}]}],
            }],
        }

    original = make_result(url)
    snapshot = copy.deepcopy(original)
    expected = make_result(safe_url)
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one", lambda _client, job: (job, original),
    )
    args = ["analyze", url, "--json"]
    destination = tmp_path / "result.json"
    if write_file:
        args.extend(["--output-file", str(destination)])

    result = _run(*args)

    assert result.exit_code == 0, result.output
    text = destination.read_text(encoding="utf-8") if write_file else result.stdout
    exported = json.loads(text)
    assert exported == expected
    assert render_markdown(exported) == render_markdown(expected)
    assert original == snapshot


@pytest.mark.parametrize("input_option", [(), ("--url",)], ids=["positional", "named"])
@pytest.mark.parametrize("inline", [False, True], ids=["lro", "inline"])
@pytest.mark.parametrize("write_file", [False, True], ids=["stdout", "file"])
@pytest.mark.parametrize("show_usage", [False, True], ids=["without-usage", "with-usage"])
def test_remote_json_preserves_sdk_response_envelope(
    monkeypatch, tmp_path, inline, write_file, show_usage, input_option,
):
    from cu_cli.output import render_markdown

    url = "https://example.test/bob's.pdf?sv=1&sig=raw-response-secret"
    safe_url = "https://example.test/bob's.pdf?REDACTED"
    usage_key = "documentPagesMinimalInline" if inline else "documentPagesStandard"
    usage = {usage_key: 2}

    def make_response(source):
        first_page = f"Source: {source}\n\n"
        second_page = "SECOND_PAGE_UNIQUE_BODY\n"
        second_span = {"offset": len(first_page), "length": len(second_page)}
        response = {
            "status": "Succeeded",
            "usage": usage,
            "serviceOnly": {"message": f"Downloaded {source}", "number": 42},
            "result": {
                "analyzerId": "prebuilt-layout",
                "apiVersion": "2026-06-01-preview",
                "contents": [{
                    "kind": "document",
                    "mimeType": "application/pdf",
                    "markdown": first_page + second_page,
                    "metadata": {"source": source},
                    "pages": [
                        {"pageNumber": 1, "spans": [{"offset": 0, "length": len(first_page)}]},
                        {"pageNumber": 2, "spans": [second_span]},
                    ],
                    "paragraphs": [{"content": second_page, "span": second_span}],
                    "fields": {"note": {
                        "type": "string", "valueString": second_page, "spans": [second_span],
                    }},
                }],
            },
        }
        if not inline:
            response["id"] = "operation-id"
        return response

    raw_response = make_response(url)
    sdk_result = raw_response["result"]
    calls = []

    def sdk_analyze(*, analyzer_id, inputs, cls=None):
        assert analyzer_id == "prebuilt-layout"
        assert cls is not None
        calls.append(inputs[0].url)
        pipeline = SimpleNamespace(http_response=SimpleNamespace(json=lambda: raw_response))
        response = SimpleNamespace(result=sdk_result, usage=usage) if inline else sdk_result
        completed = cls(pipeline, response, {})
        return completed if inline else SimpleNamespace(result=lambda: completed, usage=usage)

    method_name = "analyze_inline" if inline else "begin_analyze"
    client = SimpleNamespace(**{method_name: sdk_analyze})
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout", api_version="2026-06-01-preview",
        ),
    )
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_args, **_kwargs: client)
    args = ["analyze", *input_option, url, "--json"]
    if inline:
        args.append("--inline")
    if show_usage:
        args.append("--usage")
    destination = tmp_path / "result.json"
    if write_file:
        args.extend(["--output-file", str(destination)])

    result = _run(*args)

    assert result.exit_code == 0, result.output
    assert calls == [url]
    text = destination.read_text(encoding="utf-8") if write_file else result.stdout
    exported = json.loads(text)
    expected = make_response(safe_url)
    assert exported == expected
    assert render_markdown(exported["result"]) == render_markdown(expected["result"])
    assert "raw-response-secret" not in result.output + text
    assert raw_response == make_response(url)
    assert sdk_result == raw_response["result"]
    if show_usage:
        assert usage_key in result.stderr


@pytest.mark.parametrize(
    "query", ["?q=1", "?sig=" + "x" * 90], ids=["longer-redaction", "shorter-redaction"],
)
def test_remote_rendering_spans_remain_contiguous_inside_replaced_urls(query):
    from cu_cli.commands.analyze import _redact_output_payload, _remap_rendering_spans

    url = f"https://example.test/input.pdf{query}"
    safe_url = "https://example.test/input.pdf?REDACTED"
    prefix = "Before \u4e2d\n"
    middle = "\nMiddle\n"
    markdown = f"{prefix}{url}{middle}{url}\nAfter"
    first_start = len(prefix)
    second_start = first_start + len(url) + len(middle)
    boundaries = [
        0, first_start, first_start + len(url) - 2, first_start + len(url),
        second_start, second_start + len(url), len(markdown),
    ]
    spans = [
        {"offset": start, "length": end - start}
        for start, end in zip(boundaries[:-1], boundaries[1:], strict=True)
    ]
    redacted = _redact_output_payload({
        "markdown": markdown,
        "pages": [{"spans": [span]} for span in spans],
        "segments": [{"span": span} for span in spans],
    }, input_url=url)

    _remap_rendering_spans(redacted, markdown=markdown, input_url=url)

    length_delta = len(safe_url) - len(url)
    expected_boundaries = [
        0, first_start, first_start + min(len(url) - 2, len(safe_url)),
        first_start + len(safe_url), second_start + length_delta,
        second_start + len(url) + 2 * length_delta, len(redacted["markdown"]),
    ]
    expected_spans = [
        {"offset": start, "length": end - start}
        for start, end in zip(expected_boundaries[:-1], expected_boundaries[1:], strict=True)
    ]
    for remapped in (
        [page["spans"][0] for page in redacted["pages"]],
        [segment["span"] for segment in redacted["segments"]],
    ):
        assert remapped == expected_spans
        assert "".join(
            redacted["markdown"][span["offset"]:span["offset"] + span["length"]]
            for span in remapped
        ) == markdown.replace(url, safe_url)


@pytest.mark.parametrize("policy", ["error", "skip", "reanalyze"])
@pytest.mark.parametrize(
    "next_url",
    [
        "https://one.example.test/input.pdf?sig=renewed-secret",
        "https://two.example.test/input.pdf?sig=different-secret",
    ],
    ids=["renewed-sas", "different-source"],
)
def test_remote_same_basename_follows_existing_policy_across_invocations(
    analyze_runtime, monkeypatch, policy, next_url,
):
    urls = ["https://one.example.test/input.pdf?sig=original-secret", next_url]
    calls = []

    def run_one(_client, job):
        calls.append(job.input_url)
        return job, {"document": urls.index(job.input_url)}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)
    first = _run("analyze", "--url", urls[0], "--json", "--output-dir", "results")
    assert first.exit_code == 0, first.output
    if policy != "reanalyze":
        monkeypatch.setattr(
            "cu_cli.commands.analyze.build_client",
            lambda *_args, **_kwargs: pytest.fail("client must not build"),
        )

    repeated = _run(
        "analyze", "--url", next_url, "--json", "--output-dir", "results",
        "--on-existing", policy,
    )

    assert repeated.exit_code == (2 if policy == "error" else 0), repeated.output
    assert calls == (urls if policy == "reanalyze" else urls[:1])
    outputs = list(Path("results").glob("*.result.json"))
    assert outputs == [Path("results/input.pdf.result.json")]
    assert json.loads(outputs[0].read_text())["document"] == (1 if policy == "reanalyze" else 0)
    assert "secret" not in first.output + repeated.output


def test_remote_legacy_hash_result_is_not_reused(analyze_runtime, monkeypatch, tmp_path):
    url = "https://example.test/input.pdf?sig=secret"
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    legacy = output_dir / f"input.pdf.{digest}.result.json"
    legacy.write_text('{"legacy": true}')
    calls = []

    def run_one(_client, job):
        calls.append(job.input_url)
        return job, {"legacy": False}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)

    result = _run(
        "analyze", "--url", url, "--json", "--output-dir", str(output_dir),
        "--on-existing", "skip",
    )

    assert result.exit_code == 0, result.output
    assert calls == [url]
    assert json.loads(legacy.read_text()) == {"legacy": True}
    assert json.loads((output_dir / "input.pdf.result.json").read_text()) == {"legacy": False}


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("character", ["a", "\u4e2d"], ids=["ascii", "unicode"])
@pytest.mark.parametrize("explicit_output", [False, True], ids=["byte-limit", "explicit-short"])
def test_remote_result_filename_is_written_and_reused(
    analyze_runtime, monkeypatch, tmp_path, json_output, character, explicit_output,
):
    from cu_cli.output import render_markdown

    suffix = ".result.json" if json_output else ".result.md"
    stem_budget = 240 - len(suffix) - len(".pdf")
    character_count, remainder = divmod(stem_budget, len(character.encode("utf-8")))
    basename = character * character_count + "a" * remainder + ".pdf"
    if explicit_output:
        basename = character + basename
    url = f"https://example.test/{basename}?sig=secret"
    original = {"contents": [{"mimeType": "application/pdf", "markdown": "Example"}]}
    calls = []

    def run_one(_client, job):
        calls.append(job.input_url)
        return job, original

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)
    output_dir = tmp_path / "results"
    expected_name = f"custom{suffix}" if explicit_output else f"{basename}{suffix}"
    args = ["analyze", "--url", url]
    if explicit_output:
        args.extend(["--output-file", str(output_dir / expected_name)])
    else:
        args.extend(["--output-dir", str(output_dir)])
    if json_output:
        args.append("--json")

    result = _run(*args)
    assert result.exit_code == 0, result.output
    repeated = _run(*args, "--on-existing", "skip")
    assert repeated.exit_code == 0, repeated.output
    assert calls == [url]
    outputs = list(output_dir.iterdir())
    assert outputs == [output_dir / expected_name]
    if not explicit_output:
        assert len(outputs[0].name.encode("utf-8")) == 240
    text = outputs[0].read_text(encoding="utf-8")
    if json_output:
        assert json.loads(text) == original
    else:
        assert text == render_markdown(original)


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("dry_run", [False, True], ids=["execute", "dry-run"])
@pytest.mark.parametrize(
    "basename", ["a" * 230 + ".pdf", "\u4e2d" * 100 + ".pdf"], ids=["ascii", "unicode"],
)
def test_remote_overlong_filename_fails_before_client_or_writes(
    monkeypatch, tmp_path, json_output, dry_run, basename,
):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )
    output_dir = tmp_path / "results"
    report = tmp_path / "report.json"
    args = [
        "analyze", "--url", f"https://example.test/{basename}?sig=secret",
        "--output-dir", str(output_dir), "--report-file", str(report),
    ]
    if json_output:
        args.append("--json")
    if dry_run:
        args.append("--dry-run")

    result = _run(*args)

    assert result.exit_code == 2, result.output
    assert "240-byte UTF-8 limit" in result.output
    assert "--output-file" in result.output
    assert "secret" not in result.output
    assert not output_dir.exists()
    assert not report.exists()


@pytest.mark.parametrize("input_mode", ["named", "positional", "mixed"])
@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("dry_run", [False, True], ids=["execute", "dry-run"])
@pytest.mark.parametrize("policy", ["error", "skip", "reanalyze"])
def test_remote_output_collision_fails_before_client_or_writes(
    monkeypatch, tmp_path, input_mode, json_output, dry_run, policy,
):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )
    url = "https://one.example.test/input.pdf?sig=first-secret"
    other_url = "https://two.example.test/input.pdf?sig=second-secret"
    local = tmp_path / "input.pdf"
    if input_mode == "named":
        input_args = ["--url", url, "--url", other_url]
    elif input_mode == "mixed":
        local.write_text("local input")
        input_args = [str(local), url]
    else:
        input_args = [url, other_url]
    output_dir = tmp_path / "results"
    report = tmp_path / "report.json"
    args = [
        "analyze", *input_args, "--output-dir", str(output_dir),
        "--report-file", str(report), "--on-existing", policy,
    ]
    if json_output:
        args.append("--json")
    if dry_run:
        args.append("--dry-run")

    result = _run(*args)

    assert result.exit_code == 2, result.output
    assert "same result output path" in result.output
    assert "one.example.test" in result.output
    assert "--output-file" in result.output
    assert "secret" not in result.output
    assert not output_dir.exists()
    assert not report.exists()
    if input_mode == "mixed":
        assert local.read_text() == "local input"


@pytest.mark.parametrize("policy", ["error", "skip", "reanalyze"])
def test_remote_mixed_collision_does_not_modify_existing_results(monkeypatch, tmp_path, policy):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )
    local = tmp_path / "input.pdf"
    local.write_text("local input")
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    existing = output_dir / "input.pdf.result.json"
    existing.write_text("existing result")

    result = _run(
        "analyze", "https://example.test/input.pdf?sig=secret", str(local),
        "--json", "--output-dir", str(output_dir), "--on-existing", policy,
    )

    assert result.exit_code == 2, result.output
    assert "same result output path" in result.output
    assert existing.read_text() == "existing result"
    assert list(output_dir.iterdir()) == [existing]
    assert local.read_text() == "local input"


@pytest.mark.parametrize("url", ["http://example.test/a.pdf", "ftp://example.test/a.pdf"])
def test_unsupported_remote_scheme_fails_before_config_or_client(monkeypatch, url):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: pytest.fail("config must not load"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run("analyze", url)

    assert result.exit_code == 2
    assert "unsupported URL scheme" in result.output
    assert "HTTPS" in result.output


@pytest.mark.parametrize("input_option", [(), ("--url",)], ids=["positional", "named"])
def test_sas_url_dry_run_redacts_secret_and_reports_unavailable_size(
    analyze_runtime, input_option,
):
    url = "https://storage.example.test/container/input.pdf?sv=1&sp=r&sig=secret"

    result = _run(
        "analyze",
        *input_option,
        url,
        "--json",
        "--output-dir",
        "results",
        "--dry-run",
    )

    assert result.exit_code == 0, result.output
    assert "input.pdf?REDACTED" in result.output
    assert "secret" not in result.output
    assert "1 remote size(s) unavailable" in result.output
    assert "input.pdf.result.json" in result.output
    assert not Path("results").exists()


@pytest.mark.parametrize(
    "url_suffix",
    ["input.pdf?sv=1", "bob's/input.pdf?sv=1", "input.pdf?sv=1&rscc=it's-private"],
)
@pytest.mark.parametrize("output_args", [(), ("--output-dir", "results")])
def test_remote_service_error_redacts_sas_in_output_and_report(
    analyze_runtime,
    monkeypatch,
    url_suffix,
    output_args,
):
    from azure.core.exceptions import HttpResponseError

    secret = "top-secret-signature"
    url = f"https://storage.example.test/c/{url_suffix}&sp=r&sig={secret}"
    service_error = HttpResponseError(message=f"Could not download {url}")
    service_error.status_code = 403

    def raise_service_error(_client, _job):
        raise service_error

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", raise_service_error)

    result = _run(
        "analyze",
        url,
        "--json",
        *output_args,
        "--report-file",
        "report.json",
        "--yes",
    )

    assert result.exit_code == 1, result.output
    assert secret not in result.output
    assert "Remote input could not be read" in result.output
    assert "sp=r" in result.output
    assert "storage network rules" in result.output
    report_text = Path("report.json").read_text(encoding="utf-8")
    assert secret not in report_text
    report = json.loads(report_text)
    assert report["results"][0]["input"].endswith("input.pdf?REDACTED")


@pytest.mark.parametrize("input_option", [(), ("--url",)], ids=["positional", "named"])
def test_remote_batch_writes_safe_distinct_results(analyze_runtime, input_option):
    urls = (
        "https://one.example.test/c/input.pdf?sig=first-secret",
        "https://two.example.test/c/input.png?sig=second-secret",
    )
    input_args = [argument for url in urls for argument in (*input_option, url)]

    result = _run(
        "analyze",
        *input_args,
        "--json",
        "--output-dir",
        "results",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    outputs = list(Path("results").glob("*.result.json"))
    assert {path.name for path in outputs} == {"input.pdf.result.json", "input.png.result.json"}
    assert "secret" not in result.output
    assert all("secret" not in path.name for path in outputs)


def test_source_pattern_is_nonrecursive_and_accepts_unknown_extensions(
    analyze_runtime,
):
    source = Path("documents")
    source.mkdir()
    nested = source / "nested"
    nested.mkdir()
    (source / "immediate.new").write_text("immediate")
    (source / "ignored.pdf").write_text("ignored")
    (nested / "nested.new").write_text("nested")

    result = _run(
        "analyze",
        "--source",
        str(source),
        "--pattern",
        "*.new",
        "--json",
        "--output-dir",
        "results",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    assert Path("results/immediate.new.result.json").exists()
    assert not Path("results/nested/nested.new.result.json").exists()


@pytest.mark.parametrize("recursive_option", ["--recursive", "-r"])
@pytest.mark.parametrize("output_option", ["--output-dir", "-d"])
def test_recursive_source_preserves_relative_output_path(
    analyze_runtime, recursive_option, output_option,
):
    nested = Path("documents/nested")
    nested.mkdir(parents=True)
    (nested / "input.pdf").write_text("input")

    result = _run(
        "analyze",
        "--source",
        "documents",
        recursive_option,
        "--json",
        output_option,
        "results",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    assert Path("results/nested/input.pdf.result.json").exists()


def test_explicit_llm_input_uses_markdown_renderer(analyze_runtime, monkeypatch):
    Path("input.pdf").write_text("input")
    markdown = "# Extracted content\n"
    analysis = {"contents": [{
        "kind": "document", "mimeType": "application/pdf", "path": "input1",
        "markdown": markdown,
        "pages": [{"pageNumber": 1, "spans": [{"offset": 0, "length": len(markdown)}]}],
    }]}
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one", lambda _client, job: (job, analysis),
    )
    result = _run("analyze", "input.pdf", "--llm-input")
    assert result.exit_code == 0, result.output
    assert markdown in result.stdout
    default = _run("analyze", "input.pdf")
    assert default.exit_code == 0, default.output
    assert result.stdout == default.stdout


def test_llm_input_and_json_are_mutually_exclusive_before_service(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not be built"),
    )
    result = _run("analyze", "input.pdf", "--llm-input", "--json")
    assert result.exit_code == 2
    assert "--llm-input and --json cannot be combined" in result.output


def test_output_file_writes_single_primary_payload(analyze_runtime):
    Path("input.pdf").write_text("input")

    result = _run(
        "analyze",
        "--file",
        "input.pdf",
        "--json",
        "--output-file",
        "custom.json",
    )

    assert result.exit_code == 0, result.output
    assert json.loads(Path("custom.json").read_text())["status"] == "Succeeded"


@pytest.mark.parametrize("input_mode", ["positional", "file", "source", "url"])
@pytest.mark.parametrize("view", ["markdown", "json"])
@pytest.mark.parametrize("destination", ["stdout", "file", "directory"])
def test_input_view_and_destination_combinations(
    analyze_runtime, monkeypatch, input_mode, view, destination,
):
    from cu_cli.output import render_markdown

    copy_sample_invoice("documents/sample_invoice.pdf")
    url = "https://storage.example.test/sample_invoice.pdf"
    inputs = {
        "positional": ("documents/sample_invoice.pdf",),
        "file": ("--file", "documents/sample_invoice.pdf"),
        "source": ("--source", "documents", "--pattern", "*.pdf"),
        "url": ("--url", url),
    }[input_mode]
    markdown = "# Controlled contract result\n"
    analysis = {"analyzerId": "prebuilt-layout", "contents": [{
        "kind": "document", "mimeType": "application/pdf", "path": "input1", "markdown": markdown,
        "pages": [{"pageNumber": 1, "spans": [{"offset": 0, "length": len(markdown)}]}],
    }]}
    response = {"status": "Succeeded", "result": analysis}
    jobs = []

    def run_one(_client, job):
        jobs.append(job)
        return job, response if view == "json" else analysis

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)
    suffix = "json" if view == "json" else "md"
    path = Path(f"results/custom.{suffix}" if destination == "file" else f"results/sample_invoice.pdf.result.{suffix}")
    output_arguments = {
        "stdout": (), "file": ("--output-file", str(path)), "directory": ("--output-dir", "results"),
    }[destination]
    result = _run("analyze", *inputs, "--json" if view == "json" else "--llm-input", *output_arguments)

    assert result.exit_code == 0, result.output
    assert len(jobs) == 1
    assert jobs[0].analyzer_id == "prebuilt-layout"
    if input_mode == "url":
        assert jobs[0].input_url == url
    else:
        assert Path(jobs[0].input_ref).read_bytes() == Path("documents/sample_invoice.pdf").read_bytes()
    text = result.stdout if destination == "stdout" else path.read_text(encoding="utf-8")
    if view == "json":
        assert json.loads(text) == response
    else:
        assert text.rstrip("\n") == render_markdown(analysis).rstrip("\n")
    if destination == "stdout":
        assert not Path("results").exists()
    else:
        assert result.stdout == ""
        assert list(Path("results").rglob("*.*")) == [path]


@pytest.mark.parametrize("input_mode", ["positional", "file", "source", "url"])
@pytest.mark.parametrize("view", ["--json", "--llm-input"])
def test_multiple_inputs_with_single_output_fail_before_service(monkeypatch, input_mode, view):
    copy_sample_invoice("documents/first.pdf")
    copy_sample_invoice("documents/second.pdf")
    inputs = {
        "positional": ("documents/first.pdf", "documents/second.pdf"),
        "file": ("--file", "documents/first.pdf", "--file", "documents/second.pdf"),
        "source": ("--source", "documents", "--pattern", "*.pdf"),
        "url": ("--url", "https://storage.example.test/first.pdf", "--url", "https://storage.example.test/second.pdf"),
    }[input_mode]
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("invalid output combination must not create a client"),
    )

    result = _run(
        "analyze", *inputs, view, "--analyzer", "prebuilt-layout", "--output-file", "result.json",
        "--report-file", "report.json",
    )

    assert result.exit_code == 2, result.output
    assert "exactly one file" in result.output
    assert not Path("result.json").exists()
    assert not Path("report.json").exists()


@pytest.mark.parametrize(
    ("output_args", "directory"),
    [
        (("--output-dir", "results"), "results"),
        (("--report-file", "reports/report.json"), "reports"),
    ],
)
def test_output_write_preflight_prevents_service_call(
    analyze_runtime,
    monkeypatch,
    output_args,
    directory,
):
    Path("input.pdf").write_text("input")
    checked_directories = []

    def reject_write_check(*_args, **kwargs):
        checked_directories.append(Path(kwargs["dir"]))
        raise PermissionError("read-only output directory")

    monkeypatch.setattr(
        "cu_cli.commands.analyze.tempfile.NamedTemporaryFile",
        reject_write_check,
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run("analyze", "input.pdf", "--json", *output_args)

    assert result.exit_code == 1
    assert "permission denied" in result.output
    assert checked_directories == [Path(directory).resolve()]


@pytest.mark.parametrize(
    "output_args",
    [
        ("--output-dir", "parent-file/results"),
        ("--report-file", "parent-file/reports/report.json"),
    ],
)
def test_output_write_preflight_rejects_file_ancestor_before_service_call(
    analyze_runtime,
    monkeypatch,
    output_args,
):
    Path("input.pdf").write_text("input")
    Path("parent-file").write_text("not a directory")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run("analyze", "input.pdf", "--json", *output_args)
    output = result.output.lower()

    assert result.exit_code == 2
    assert "output parent path is a file" in output
    assert "parent-file" in output
    assert "unexpected error" not in output
    assert "winerror" not in output


def test_single_stdout_analysis_uses_registered_core_operation(
    analyze_runtime,
    monkeypatch,
):
    from cu_cli_core.operations.analysis import execute_analyze

    Path("input.pdf").write_text("input")
    resolved = []

    def resolve(identifier):
        resolved.append(identifier)
        return execute_analyze

    monkeypatch.setattr("cu_cli.commands.analyze.resolve_identifier", resolve)

    result = _run("analyze", "input.pdf", "--json")

    assert result.exit_code == 0, result.output
    assert resolved == ["cu_cli_core.operations.analysis#execute_analyze"]


def test_output_file_rejects_multiple_inputs_before_client(monkeypatch):
    Path("first.pdf").write_text("first")
    Path("second.pdf").write_text("second")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    result = _run(
        "analyze",
        "--file",
        "first.pdf",
        "--file",
        "second.pdf",
        "--output-file",
        "custom.json",
    )

    assert result.exit_code == 2
    assert "exactly one file" in result.output


def test_dry_run_makes_no_client_call_or_file_write(monkeypatch):
    source = Path("documents")
    source.mkdir()
    copy_sample_invoice(source / "sample_invoice.pdf")
    (source / ".DS_Store").write_text("metadata")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not build"),
    )

    # region Snippet:analyze_dry_run
    result = _run(
        "analyze",
        "--source",
        str(source),
        "--analyzer",
        "prebuilt-layout",
        "--json",
        "--output-dir",
        "results",
        "--report-file",
        "report.json",
        "--dry-run",
    )
    # endregion

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert "Skipped during discovery: 1" in result.output
    rendered = "".join(result.output.split())
    assert ".DS_Store:hiddenfileskipped" in rendered
    assert "No service calls or files were written" in result.output
    assert not Path("results").exists()
    assert not Path("report.json").exists()


@pytest.mark.parametrize("selection_mode", ["files", "sources"])
def test_explicit_multi_input_previews_preserve_selection(monkeypatch, selection_mode):
    from cu_cli_core import input_planning

    if selection_mode == "files":
        sample_paths = ("invoice one.pdf", "invoice two.pdf")
        selection = ("--file", sample_paths[0], "--file", sample_paths[1])
        output_dir = "selected-results"
    else:
        sample_paths = ("incoming/first.pdf", "archive/second.pdf")
        selection = ("--source", "incoming", "--source", "archive", "--pattern", "*.pdf")
        output_dir = "combined-results"
    for sample in sample_paths:
        copy_sample_invoice(sample)
    copy_sample_invoice("unselected.pdf")
    if selection_mode == "sources":
        copy_sample_invoice("incoming/nested/excluded.pdf")
        Path("incoming/excluded.txt").write_text("not a PDF", encoding="utf-8")

    selections = []
    original_plan_inputs = input_planning.plan_inputs

    def capture_selection(**kwargs):
        plan = original_plan_inputs(**kwargs)
        selections.append({item.path for item in plan.inputs})
        return plan

    monkeypatch.setattr(input_planning, "plan_inputs", capture_selection)
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("dry-run must not create a service client"),
    )
    arguments = (
        "analyze", *selection, "--analyzer", "prebuilt-layout", "--output-dir", output_dir,
        "--json", "--dry-run",
    )
    if selection_mode == "files":
        # region Snippet:analyze_files_preview
        result = _run(*arguments)
        # endregion
    else:
        # region Snippet:analyze_sources_preview
        result = _run(*arguments)
        # endregion

    assert result.exit_code == 0, result.output
    assert selections == [{Path(sample).resolve() for sample in sample_paths}]
    assert "Selected: 2 input(s)" in result.output
    assert "No service calls or files were written" in result.output
    assert not Path(output_dir).exists()
    assert list(Path.cwd().rglob("*.result.*")) == []


def test_discovery_skips_are_in_batch_report(analyze_runtime):
    source = Path("documents")
    source.mkdir()
    (source / "input.pdf").write_text("input")
    (source / ".DS_Store").write_text("metadata")

    result = _run(
        "analyze",
        "--source",
        str(source),
        "--json",
        "--output-dir",
        "results",
        "--report-file",
        "report.json",
        "--yes",
    )

    assert result.exit_code == 0, result.output
    assert "1 skipped (discovery)" in result.output
    report = json.loads(Path("report.json").read_text())
    assert report["counts"] == {
        "succeeded": 1,
        "failed": 0,
        "skipped": 1,
        "total": 2,
    }
    skipped = next(item for item in report["results"] if item["status"] == "skipped")
    assert Path(skipped["input"]).name == ".DS_Store"
    assert skipped["reason"] == "hidden file skipped"


def test_dry_run_and_yes_are_mutually_exclusive():
    Path("input.pdf").write_text("input")

    result = _run("analyze", "input.pdf", "--dry-run", "--yes")

    assert result.exit_code == 2
    assert "--dry-run and --yes cannot be combined" in result.output


@pytest.mark.parametrize(
    ("policy", "expected_calls", "expected_code"),
    [("error", 0, 2), ("skip", 0, 0), ("reanalyze", 1, 0)],
)
def test_on_existing_policy(analyze_runtime, monkeypatch, policy, expected_calls, expected_code):
    copy_sample_invoice("input.pdf")
    output = Path("result.json")
    output.write_text("existing")
    calls = {"count": 0}

    def run_one(_client, job):
        calls["count"] += 1
        return job, {"status": "Succeeded"}

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", run_one)

    result = _run(
        "analyze",
        "input.pdf",
        "--json",
        "--output-file",
        str(output),
        "--on-existing",
        policy,
    )

    assert result.exit_code == expected_code, result.output
    assert calls["count"] == expected_calls


def test_report_uses_stable_statuses_and_is_written_after_success(analyze_runtime):
    Path("input.pdf").write_text("input")

    result = _run(
        "analyze",
        "input.pdf",
        "--json",
        "--report-file",
        "report.json",
    )

    assert result.exit_code == 0, result.output
    report = json.loads(Path("report.json").read_text())
    assert report["counts"] == {
        "succeeded": 1,
        "failed": 0,
        "skipped": 0,
        "total": 1,
    }
    assert report["results"][0]["status"] == "succeeded"


def test_auth_mode_is_forwarded_to_client_builder(monkeypatch):
    Path("input.pdf").write_text("input")
    captured = {}
    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )

    def build_client(*_args, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("cu_cli.commands.analyze.build_client", build_client)
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (job, {"status": "Succeeded"}),
    )

    result = _run("analyze", "input.pdf", "--json", "--auth-mode", "login")

    assert result.exit_code == 0, result.output
    assert captured["auth_mode_override"] == "login"


def test_batch_pattern_example_requires_source_and_writes_selected_outputs(analyze_runtime):
    source = Path("documents")
    source.mkdir()
    copy_sample_invoice(source / "sample_invoice.pdf")
    (source / "ignored.txt").write_text("ignored")
    nested = source / "nested"
    nested.mkdir()
    copy_sample_invoice(nested / "sample_invoice.pdf")

    _run(
        "analyze", "--source", "documents", "--pattern", "*.pdf",
        "--analyzer", "prebuilt-layout", "--output-dir", "results", "--json",
    )
    assert {path.name for path in Path("results").iterdir()} == {"sample_invoice.pdf.result.json"}
    _run(
        "analyze", "--source", "documents", "--pattern", "*.pdf", "--recursive",
        "--analyzer", "prebuilt-layout", "--output-dir", "recursive-results", "--json",
        "--report-file", "run-report.json", "--yes", "--concurrency", "8",
    )
    assert Path("recursive-results/nested/sample_invoice.pdf.result.json").is_file()
    report = json.loads(Path("run-report.json").read_text())
    assert report["counts"]["succeeded"] == 2
    assert report["counts"]["failed"] == 0


@pytest.mark.parametrize("concurrency", ["1", "4", "32"])
@pytest.mark.parametrize("option", ["--concurrency", "-j"])
def test_analyze_concurrency_boundaries_reach_runner(analyze_runtime, monkeypatch, concurrency, option):
    copy_sample_invoice("input.pdf")
    jobs = []
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (jobs.append(job) or (job, {"status": "Succeeded"})),
    )
    result = _run("analyze", "input.pdf", "--json", option, concurrency)
    assert result.exit_code == 0, result.output
    assert len(jobs) == 1


@pytest.mark.parametrize("concurrency", ["0", "33", "invalid"])
def test_analyze_concurrency_invalid_values_fail_before_client(monkeypatch, concurrency):
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("client must not be built"),
    )
    result = _run("analyze", "input.pdf", "--concurrency", concurrency)
    assert result.exit_code == 2


@pytest.mark.parametrize("source", ["documents", "./documents"])
def test_documented_pattern_without_source_is_rejected_before_client(monkeypatch, source):
    Path("documents").mkdir()
    Path("documents/input.pdf").write_text("input")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("invalid example must not call service"),
    )
    result = _run("analyze", source, "--pattern", "*.pdf")
    assert result.exit_code == 2
    assert "--source" in result.output


def test_url_documentation_preserves_sas_and_rejects_download(analyze_runtime, monkeypatch):
    url = "https://storage.example.net/container/video.mp4?sv=<version>&sp=r&sig=<signature>"
    bound_url = "https://storage.example.net/container/video.mp4?sv=2026-01-01&sp=r&sig=example"
    received = []
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (received.append(job.input_url) or (job, {"status": "Succeeded"})),
    )
    # region Snippet:analyze_url
    result = _run(
        "analyze", "--url", url, "-a", "prebuilt-videoSearch", "--json",
        placeholder_values={"version": "2026-01-01", "signature": "example"},
    )
    # endregion
    assert received == [bound_url]
    assert "sig=example" not in result.output
    video_url = (
        "https://github.com/Azure-Samples/azure-ai-content-understanding-assets/"
        "raw/refs/heads/main/videos/sdk_samples/FlightSimulator.mp4"
    )
    _run(
        "analyze", "--url", video_url, "--analyzer", "prebuilt-videoSearch", "--json",
    )
    assert received == [bound_url, video_url]
    sas_url = "https://<storage-account>.blob.core.windows.net/<container>/<blob>?<sas-token>"
    sas_token = "sv=2026-01-01&sp=r&sig=a%2Bb%2Fc%3D"
    bound_sas_url = "https://cuclitest.blob.core.windows.net/samples/video.mp4?" + sas_token
    # region Snippet:analyze_sas_url
    result = _run(
        "analyze", "--url", sas_url, "--analyzer", "prebuilt-videoSearch", "--json",
        placeholder_values={
            "storage-account": "cuclitest", "container": "samples", "blob": "video.mp4",
            "sas-token": sas_token,
        },
    )
    # endregion
    assert received == [bound_url, video_url, bound_sas_url]
    assert "a%2Bb%2Fc%3D" not in result.output
    # region Snippet:analyze_urls_preview
    result = _run(
        "analyze", "--url",
        "https://github.com/Azure-Samples/azure-ai-content-understanding-assets/"
        "raw/refs/heads/main/document/invoice.pdf",
        "--url", "https://github.com/Azure-Samples/azure-ai-content-understanding-assets/"
        "raw/refs/heads/main/document/receipt.png", "--output-dir", "results",
        "--analyzer", "prebuilt-layout", "--dry-run",
    )
    # endregion
    assert received == [bound_url, video_url, bound_sas_url]
    assert "2 remote size(s) unavailable" in unstyle(result.output)
    assert not Path("results").exists()


def test_analyze_uses_saved_default_analyzer(monkeypatch):
    invoke_cli(["profile", "set", "default_analyzer", "prebuilt-layout"])
    copy_sample_invoice()
    jobs = []
    monkeypatch.setattr("cu_cli.commands.analyze.build_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        "cu_cli.commands.analyze._run_one",
        lambda _client, job: (jobs.append(job) or (job, {"status": "Succeeded"})),
    )
    _run("analyze", "sample_invoice.pdf", "--json")
    assert jobs[0].analyzer_id == "prebuilt-layout"
    _run(
        "analyze", "sample_invoice.pdf", "--analyzer", "invoice_v1", "--json",
    )
    assert jobs[-1].analyzer_id == "invoice_v1"
