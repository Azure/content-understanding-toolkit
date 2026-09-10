# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Unit tests for cu_cli_core.rich_markdown (id map, marker injection, resolve)."""

from __future__ import annotations

import copy

import pytest

from cu_cli_core.rich_markdown import (
    MAP_SCHEMA,
    RESOLVE_SCHEMA,
    RichMarkdownError,
    build_id_map,
    inject_ids,
    parse_bbox,
    resolve_ids,
    strip_ids,
    unwrap_result,
    with_rich_markdown,
)

MARKDOWN = "# Title\n\nFirst para.\n\n<table><tr><td>a</td></tr></table>\n\nLast para.\n"
# Offsets (code points) into MARKDOWN.
TITLE = MARKDOWN.index("# Title")
FIRST = MARKDOWN.index("First")
TABLE = MARKDOWN.index("<table>")
LAST = MARKDOWN.index("Last")


def _content() -> dict:
    return {
        "kind": "document",
        "unit": "inch",
        "markdown": MARKDOWN,
        "pages": [
            {"pageNumber": 1, "width": 8.5, "height": 11, "spans": [{"offset": 0, "length": TABLE}]},
            {
                "pageNumber": 2,
                "width": 8.5,
                "height": 11,
                "spans": [{"offset": TABLE, "length": len(MARKDOWN) - TABLE}],
            },
        ],
        "paragraphs": [
            {
                "role": "title",
                "content": "Title",
                "span": {"offset": TITLE, "length": 7},
                "source": "D(1,1,1,2,1,2,1.5,1,1.5)",
            },
            {
                "content": "First para.",
                "span": {"offset": FIRST, "length": 11},
                "source": "D(1,1,2,3,2,3,2.5,1,2.5)",
            },
            {
                "content": "Last para.",
                "span": {"offset": LAST, "length": 10},
                "source": "D(2,1,5,3,5,3,5.5,1,5.5)",
            },
        ],
        "tables": [
            {
                "rowCount": 1,
                "columnCount": 1,
                "span": {"offset": TABLE, "length": len("<table><tr><td>a</td></tr></table>")},
                "source": "D(2,1,1,4,1,4,2,1,2)",
                "caption": {"content": "Table 1"},
            }
        ],
        "figures": [],
        "sections": [
            {
                "span": {"offset": 0, "length": len(MARKDOWN)},
                "elements": ["/paragraphs/0", "/sections/1"],
            },
            {
                "span": {"offset": FIRST, "length": len(MARKDOWN) - FIRST},
                "elements": ["/paragraphs/1", "/tables/0", "/paragraphs/2"],
            },
        ],
    }


def _result() -> dict:
    return {"id": "op-123", "status": "Succeeded", "result": {"contents": [_content()]}}


# ------------------------------------------------------------------- helpers
def test_parse_bbox_returns_page_and_axis_aligned_box():
    assert parse_bbox("D(3,1,2,4,2,4,3,1,3)") == {"page": 3, "x": 1.0, "y": 2.0, "w": 3.0, "h": 1.0}


def test_parse_bbox_accepts_compact_left_top_width_height_form():
    assert parse_bbox("D(1,10,20,3,4)") == {"page": 1, "x": 10, "y": 20, "w": 3, "h": 4}


def test_with_rich_markdown_shifts_segment_spans_for_sdk_models_too():
    from azure.ai.contentunderstanding import to_llm_input
    from azure.ai.contentunderstanding.models import AnalysisResult

    payload = {"contents": [{
        "kind": "document", "markdown": "AAAA\n\nBBBB", "startPageNumber": 1, "endPageNumber": 2,
        "paragraphs": [{"content": "AAAA", "span": {"offset": 0, "length": 4}},
                       {"content": "BBBB", "span": {"offset": 6, "length": 4}}],
        "segments": [{"segmentId": "1", "category": "a", "span": {"offset": 0, "length": 6},
                      "startPageNumber": 1, "endPageNumber": 1},
                     {"segmentId": "2", "category": "b", "span": {"offset": 6, "length": 4},
                      "startPageNumber": 2, "endPageNumber": 2}],
    }]}
    for source in (payload, AnalysisResult(payload)):
        rich = with_rich_markdown(source, "paragraph")
        rendered = to_llm_input(AnalysisResult(dict(rich)))
        assert "<!--p0-->AAAA" in rendered and "<!--p1-->BBBB" in rendered
        assert "<!--p" not in rendered.replace("<!--p0-->AAAA", "").replace("<!--p1-->BBBB", "")


def test_parse_bbox_tolerates_missing_or_malformed_source():
    assert parse_bbox(None) is None
    assert parse_bbox("") is None
    assert parse_bbox("nonsense") is None


def test_unwrap_result_accepts_envelope_and_bare_result():
    bare = {"contents": [_content()]}
    assert unwrap_result(_result())["contents"][0]["markdown"] == MARKDOWN
    assert unwrap_result(bare) is bare


# ------------------------------------------------------------------- id map
def test_build_id_map_coarse_has_sections_tables_figures_only():
    id_map = build_id_map(_content(), "coarse")

    assert id_map["schema"] == MAP_SCHEMA
    assert id_map["level"] == "coarse"
    assert id_map["stringEncoding"] == "codePoint"
    assert id_map["pageCount"] == 2
    assert set(id_map["ids"]) == {"s0", "s1", "t0"}
    assert id_map["ids"]["t0"]["bbox"] == {"page": 2, "x": 1.0, "y": 1.0, "w": 3.0, "h": 1.0}
    assert id_map["ids"]["t0"]["rows"] == 1
    assert id_map["ids"]["t0"]["caption"] == "Table 1"
    # Children only reference ids that exist in this map (no dangling paragraphs).
    assert id_map["ids"]["s0"]["children"] == ["s1"]
    assert id_map["ids"]["s1"]["children"] == ["t0"]


def test_build_id_map_paragraph_adds_paragraphs_with_role():
    id_map = build_id_map(_content(), "paragraph")

    assert set(id_map["ids"]) == {"s0", "s1", "t0", "p0", "p1", "p2"}
    assert id_map["ids"]["p0"]["role"] == "title"
    assert "role" not in id_map["ids"]["p1"]
    assert id_map["ids"]["p2"]["bbox"]["page"] == 2
    assert id_map["ids"]["s1"]["children"] == ["p1", "t0", "p2"]


def test_build_id_map_paragraph_skips_paragraphs_inside_tables_and_figures():
    content = _content()
    cell_offset = MARKDOWN.index("<td>a") + len("<td>")
    content["paragraphs"].append(
        {"content": "a", "span": {"offset": cell_offset, "length": 1}, "source": "D(2,1,1,2,1,2,2,1,2)"}
    )

    id_map = build_id_map(content, "paragraph")

    # The cell is addressed through t0; no <!--p3--> is injected into the <td>.
    assert "p3" not in id_map["ids"]
    assert set(id_map["ids"]) == {"s0", "s1", "t0", "p0", "p1", "p2"}


def test_build_id_map_rejects_unknown_level():
    with pytest.raises(RichMarkdownError):
        build_id_map(_content(), "word")


# ------------------------------------------------------------------- inject
def test_inject_ids_places_markers_outer_first_and_round_trips():
    id_map = build_id_map(_content(), "paragraph")
    rich, shift = inject_ids(MARKDOWN, id_map)

    # Several elements starting at the same offset share one marker, outer first.
    assert rich.startswith("<!--s0,p0-->" + "# Title")
    assert "<!--s1,p1-->First para." in rich
    assert "<!--t0--><table>" in rich
    assert "<!--p2-->Last para." in rich
    # Stripping the markers restores the exact service markdown.
    assert strip_ids(rich) == MARKDOWN


def test_inject_ids_shift_treats_marker_at_offset_as_after():
    id_map = build_id_map(_content(), "paragraph")
    rich, shift = inject_ids(MARKDOWN, id_map)

    # Page 2 starts exactly where <!--t0--> is inserted: the marker must belong
    # to page 2 (so shift(TABLE) does not count it) ...
    assert rich[shift(TABLE):].startswith("<!--t0--><table>")
    # ... while offsets after the marker are pushed by its length.
    assert rich[shift(LAST):].startswith("<!--p2-->Last")
    assert shift(0) == 0


def test_with_rich_markdown_shifts_page_spans_and_leaves_input_untouched():
    result = _result()
    snapshot = copy.deepcopy(result)

    bare = with_rich_markdown(unwrap_result(result), "coarse")

    assert result == snapshot
    rich_md = bare["contents"][0]["markdown"]
    page2 = bare["contents"][0]["pages"][1]["spans"][0]
    assert rich_md[page2["offset"]:].startswith("<!--t0-->")
    assert strip_ids(rich_md) == MARKDOWN


# ------------------------------------------------------------------- resolve
def test_resolve_ids_from_full_result_returns_text_page_bbox():
    out = resolve_ids(_result(), ["p2"])

    assert out["schema"] == RESOLVE_SCHEMA
    (item,) = out["results"]
    assert item["id"] == "p2"
    assert item["kind"] == "paragraph"
    assert item["page"] == 2
    assert item["bbox"] == {"page": 2, "x": 1.0, "y": 5.0, "w": 2.0, "h": 0.5}
    assert item["text"] == "Last para."


def test_resolve_ids_around_returns_neighbours_in_markdown_order():
    out = resolve_ids(_result(), ["p1"], around=1)

    (item,) = out["results"]
    assert [p["id"] for p in item["before"]] == ["p0"]
    # Tables and figures are blocks too: the table right after p1 is its context.
    assert [p["id"] for p in item["after"]] == ["t0"]
    assert out["results"][0]["after"][0]["kind"] == "table"

    out = resolve_ids(_result(), ["p1"], around=2)
    assert [p["id"] for p in out["results"][0]["after"]] == ["t0", "p2"]


def test_resolve_ids_container_neighbours_are_outside_its_span():
    out = resolve_ids(_result(), ["t0", "s1"], around=2)

    table, section = out["results"]
    assert [p["id"] for p in table["before"]] == ["p0", "p1"]
    assert [p["id"] for p in table["after"]] == ["p2"]
    # s1 spans p1..end: only p0 is before it and nothing follows it.
    assert [p["id"] for p in section["before"]] == ["p0"]
    assert section["after"] == []



def test_resolve_ids_text_chars_truncates_and_zero_means_full():
    short = resolve_ids(_result(), ["p1"], text_chars=5)["results"][0]["text"]
    full = resolve_ids(_result(), ["p1"], text_chars=None)["results"][0]["text"]
    assert short == "First"
    assert full == "First para."



def test_resolve_ids_unknown_id_is_reported_not_raised():
    out = resolve_ids(_result(), ["p99"])
    assert out["results"][0] == {
        "id": "p99",
        "error": "unknown id",
        "hint": "check the id in the rich markdown (<!--id--> markers)",
    }



def test_resolve_ids_requires_markdown_content():
    with pytest.raises(RichMarkdownError):
        resolve_ids({"contents": [{"kind": "document"}]}, ["p0"])
