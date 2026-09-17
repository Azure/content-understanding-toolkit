# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import os
from pathlib import Path
from runpy import run_path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

pytestmark = pytest.mark.unit

_MODULE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "update-snippet.py"
_MODULE = SimpleNamespace(**run_path(str(_MODULE_PATH)))
synchronize_document = _MODULE.synchronize_document


def test_region_discovery_handles_multiline_calls_and_nested_regions(tmp_path):
    source = tmp_path / "test_regions.py"
    source.write_text(
        "def test_workflow():\n"
        "    text = '# region Snippet:not_a_region'\n"
        "    # region Snippet:workflow\n"
        "    # region Snippet:help\n"
        "    _run(\n        '--help',\n    )\n"
        "    # endregion\n"
        "    _run('--version')\n"
        "    # endregion\n",
        encoding="utf-8",
    )

    assert _MODULE.discover_snippet_regions(tmp_path) == {
        "help": (source, 4, 8, "test_workflow"),
        "workflow": (source, 3, 10, "test_workflow"),
    }


@pytest.mark.parametrize(
    "body",
    [
        "    # region Snippet:help\n    _run('--help')\n",
        "    _run('--help')\n    # endregion\n",
        "    # region Snippet:bad-name\n    _run('--help')\n    # endregion\n",
        "    # region Snippet:test_help\n    _run('--help')\n    # endregion\n",
        "    # region Snippet:help\n    value = 1\n    # endregion\n",
        "    # region Snippet:help\n    _run('--help')\n  # endregion\n",
        "    # region Snippet:help\n    _run('--help')\n    # endregion\n"
        "    # region Snippet:help\n    _run('--help')\n    # endregion\n",
        "    # region Snippet:help\n    _run(\n    # endregion\n        '--help'\n    )\n",
    ],
    ids=["unclosed", "unmatched", "invalid-name", "test-prefix", "empty", "indentation", "duplicate", "split-call"],
)
def test_region_discovery_rejects_invalid_boundaries(tmp_path, body):
    source = tmp_path / "test_regions.py"
    source.write_text("def test_workflow():\n" + body, encoding="utf-8")

    with pytest.raises(ValueError, match="Snippet|endregion"):
        _MODULE.discover_snippet_regions(tmp_path)


def test_region_capture_exports_only_calls_inside_the_named_block(tmp_path):
    test_root = Path(__file__).resolve().parents[1]
    shutil.copyfile(test_root / "conftest.py", tmp_path / "conftest.py")
    source = tmp_path / "test_region_capture.py"
    source.write_text(
        "from support.command_catalog import invoke_cli, record_output, record_external\n"
        "def _run(*args):\n    return invoke_cli(args)\n"
        "def test_commands():\n"
        "    _run('profile', 'list')\n"
        "    # region Snippet:cli_help\n"
        "    first = _run('--help')\n"
        "    second = _run('--version')\n"
        "    # endregion\n"
        "    assert first.exit_code == second.exit_code == 0\n"
        "    _run('profile', 'show')\n"
        "def test_output():\n"
        "    # region Snippet:json_output\n"
        "    record_output('{}', language='json')\n"
        "    # endregion\n"
        "def test_external():\n"
        "    # region Snippet:login\n"
        "    record_external(['az', 'login'], reason='External interactive prerequisite')\n"
        "    # endregion\n",
        encoding="utf-8",
    )
    catalog = tmp_path / "catalog.json"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-c", str(test_root.parent / "pyproject.toml"),
         "--confcutdir", str(tmp_path), "--command-catalog", str(catalog), str(source)],
        cwd=tmp_path, env=dict(os.environ, CU_TEST_REC_MODE="playback", PYTEST_ADDOPTS=""),
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    exported = json.loads(catalog.read_text(encoding="utf-8"))["examples"]
    assert set(exported) == {"cli_help", "json_output", "login"}
    assert exported["json_output"]["content"] == "{}"
    assert exported["json_output"]["verification"]["output_validation"] == "json"
    assert exported["login"]["verification"]["mode"] == "external"
    assert exported["cli_help"]["content"] == "cu --help\n\ncu --version"
    assert exported["cli_help"]["verification"]["consecutive"] is True
    assert exported["cli_help"]["last_step"] == exported["cli_help"]["step"] + 1


@pytest.mark.parametrize("failure", ["not-executed", "assertion", "cleanup", "repeated-call"])
def test_region_sources_must_execute_and_pass_before_export(tmp_path, failure):
    test_root = Path(__file__).resolve().parents[1]
    shutil.copyfile(test_root / "conftest.py", tmp_path / "conftest.py")
    source = tmp_path / "test_region_failure.py"
    bodies = {
        "not-executed": (
            "    if False:\n"
            "        # region Snippet:help\n"
            "        invoke_cli(['--help'])\n"
            "        # endregion\n"
        ),
        "assertion": (
            "    # region Snippet:help\n"
            "    invoke_cli(['--help'])\n"
            "    # endregion\n"
            "    assert False, 'post-command validation failed'\n"
        ),
        "cleanup": (
            "    # region Snippet:help\n"
            "    invoke_cli(['--help'])\n"
            "    # endregion\n"
        ),
        "repeated-call": (
            "    # region Snippet:help\n"
            "    for invocation in range(2):\n"
            "        invoke_cli(['--help'])\n"
            "    # endregion\n"
        ),
    }
    source.write_text(
        "import pytest\n"
        "from support.command_catalog import invoke_cli\n"
        "@pytest.fixture\n"
        "def cleanup():\n"
        "    yield\n"
        "    raise AssertionError('cleanup failed')\n"
        + ("def test_region(cleanup):\n" if failure == "cleanup" else "def test_region():\n")
        + bodies[failure],
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as caught:
        _MODULE.execute_test_examples(_MODULE_PATH.parents[1], tmp_path)

    message = str(caught.value)
    if failure == "not-executed":
        assert "did not execute successfully: help" in message
    else:
        assert "documentation source tests failed" in message


def test_region_names_must_be_unique_across_test_files(tmp_path):
    for filename in ("test_first.py", "test_second.py"):
        (tmp_path / filename).write_text(
            "def test_help():\n    # region Snippet:help\n    invoke_cli(['--help'])\n    # endregion\n",
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="duplicate Snippet region"):
        _MODULE.discover_snippet_regions(tmp_path)


def test_update_is_deterministic_and_check_detects_drift(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    document = tmp_path / "README.md"
    document.write_text(
        "<!-- Snippet:example -->\n```bash\nold command\n```\n",
        encoding="utf-8",
    )
    snippets = {
        "example": _MODULE.Snippet("example", "cu --help", tests / "test_example.py", 1),
    }

    errors = synchronize_document(document, snippets, update=False)
    assert errors == [
        f"{document}:1: snippet 'example' differs from {tests / 'test_example.py'}:1; "
        "run 'python scripts/update-snippet.py update'"
    ]

    assert synchronize_document(document, snippets, update=True) == []
    updated = document.read_text(encoding="utf-8")
    assert updated == "<!-- Snippet:example -->\n```bash\ncu --help\n```\n"
    assert synchronize_document(document, snippets, update=True) == []
    assert document.read_text(encoding="utf-8") == updated
    assert synchronize_document(document, snippets, update=False) == []


def test_unmarked_blocks_and_missing_test_sources_fail_without_writing(tmp_path):
    document = tmp_path / "README.md"
    original = "```bash\ncu analyze documents --pattern '*.pdf'\n```\n"
    document.write_text(original, encoding="utf-8")

    errors = synchronize_document(document, {}, update=True)

    assert any("no Snippet ID" in error for error in errors)
    assert document.read_text(encoding="utf-8") == original
    document.write_text("<!-- Snippet:missing -->\n```bash\ncu --help\n```\n")
    assert any("no tested source" in error for error in synchronize_document(document, {}, update=False))


@pytest.mark.parametrize(
    "opening", ["``` bash", "~~~ bash", "```bash title=example"],
    ids=["spaced-language", "tilde-fence", "extra-info"],
)
def test_unmarked_fences_with_markdown_info_cannot_bypass_validation(tmp_path, opening):
    document = tmp_path / "README.md"
    original = f"{opening}\ncu --help\n{opening[:3]}\n".encode()
    document.write_bytes(original)

    errors = synchronize_document(document, {}, update=True)

    assert any(":1: code block has no Snippet ID" in error for error in errors)
    assert document.read_bytes() == original


@pytest.mark.parametrize("update", [False, True], ids=["check", "update"])
@pytest.mark.parametrize(
    "nested",
    [
        '> ```bash\n> cu analyze documents --pattern "*.pdf"\n> ```\n',
        '> <!-- Snippet:help -->\n> ```bash\n> cu --help\n> ```\n',
        '1. Example\n\n    ```bash\n    cu analyze documents --pattern "*.pdf"\n    ```\n',
        '- ```bash\n  cu analyze documents --pattern "*.pdf"\n  ```\n',
    ],
    ids=["blockquote", "marked-blockquote", "ordered-list", "unordered-list"],
)
def test_nested_fences_are_rejected_before_either_document_is_written(tmp_path, update, nested):
    documents = (tmp_path / "README.md", tmp_path / "usage-guide.md")
    prefix = "<!-- Snippet:help -->\n```bash\nold\n```\n\n"
    documents[0].write_text(prefix, encoding="utf-8")
    documents[1].write_text(prefix + nested, encoding="utf-8")
    original = {path: path.read_bytes() for path in documents}
    source = _MODULE.Snippet("help", "cu --help", Path("test_cli.py"), 1, "bash")

    errors = _MODULE.synchronize_documents(documents, {"help": source}, update=update)

    assert any(error.startswith(f"{documents[1]}:") and "nested code fence" in error for error in errors)
    assert all(path.read_bytes() == content for path, content in original.items())


def test_nested_fence_syntax_inside_output_is_literal_content(tmp_path):
    document = tmp_path / "README.md"
    content = "> ```bash\n> cu --help\n> ```"
    document.write_text("<!-- Snippet:output -->\n```text\nold\n```\n", encoding="utf-8")
    source = _MODULE.Snippet("output", content, Path("test_cli.py"), 1, "text")

    assert _MODULE.synchronize_documents((document,), {"output": source}, update=True) == []
    assert _MODULE.synchronize_documents((document,), {"output": source}, update=False) == []
    assert document.read_text(encoding="utf-8") == f"<!-- Snippet:output -->\n```text\n{content}\n```\n"


@pytest.mark.parametrize(
    "opening", ["``` bash", "~~~ bash", "```bash title=example"],
    ids=["spaced-language", "tilde-fence", "extra-info"],
)
def test_marked_fences_preserve_info_and_prose_when_updated(tmp_path, opening):
    document = tmp_path / "README.md"
    original = (
        "# Handwritten heading\n\n<!-- Snippet:help -->\r\n"
        f"{opening}\r\nold\r\n{opening[:3]}\r\n\nHandwritten ending."
    ).encode()
    document.write_bytes(original)
    source = _MODULE.Snippet("help", "cu --help", Path("test_cli.py"), 1, "bash")

    assert _MODULE.synchronize_documents((document,), {"help": source}, update=True) == []
    assert document.read_bytes() == original.replace(b"old\r\n", b"cu --help\r\n")
    assert _MODULE.synchronize_documents((document,), {"help": source}, update=False) == []


@pytest.mark.parametrize("fence", ["```", "~~~"], ids=["backticks", "tildes"])
def test_source_cannot_close_its_document_fence_or_partially_update_documents(tmp_path, fence):
    first = tmp_path / "README.md"
    second = tmp_path / "usage-guide.md"
    first.write_text("<!-- Snippet:help -->\n```bash\nold\n```\n", encoding="utf-8")
    second.write_text(f"<!-- Snippet:output -->\n{fence}text\nold\n{fence}\n", encoding="utf-8")
    original = {path: path.read_bytes() for path in (first, second)}
    sources = {
        "help": _MODULE.Snippet("help", "cu --help", Path("test_cli.py"), 1, "bash"),
        "output": _MODULE.Snippet("output", f"result\n{fence}\nnot prose", Path("test_cli.py"), 2, "text"),
    }

    errors = _MODULE.synchronize_documents((first, second), sources, update=True)

    assert any("content can close" in error for error in errors)
    assert all(path.read_bytes() == content for path, content in original.items())


@pytest.mark.parametrize(
    ("fence", "content"),
    [("````", "```\ninner output\n```"), ("~~~", "```\ninner output\n```"),
     ("```", "    ```\n<!-- Snippet:not_a_reference -->")],
    ids=["longer-fence", "different-fence", "indented-content"],
)
def test_output_can_contain_fences_that_do_not_close_the_outer_block(tmp_path, fence, content):
    document = tmp_path / "README.md"
    document.write_text(f"<!-- Snippet:output -->\n{fence}text\nold\n{fence}\n")
    source = _MODULE.Snippet("output", content, Path("test_cli.py"), 1, "text")

    assert _MODULE.synchronize_documents((document,), {"output": source}, update=True) == []
    assert document.read_text() == f"<!-- Snippet:output -->\n{fence}text\n{content}\n{fence}\n"
    assert _MODULE.synchronize_documents((document,), {"output": source}, update=False) == []


def test_inline_backticks_in_prose_are_not_treated_as_a_fenced_block(tmp_path):
    document = tmp_path / "README.md"
    original = b"```this is an inline code span```\n"
    document.write_bytes(original)

    assert _MODULE.synchronize_documents((document,), {}, update=True) == []
    assert document.read_bytes() == original


def test_multiple_test_commands_generate_one_block_and_preserve_crlf(tmp_path):
    document = tmp_path / "README.md"
    document.write_bytes(b"<!-- Snippet:cli_setup -->\r\n```bash\r\nold\r\n```\r\n")
    sources = {
        "cli_setup": _MODULE.Snippet(
            "cli_setup", "cu --version\n\ncu --help", Path("test_cli.py"), 1, "bash",
        ),
    }

    assert synchronize_document(document, sources, update=True) == []
    updated = document.read_bytes()
    assert b"cu --version\r\n\r\ncu --help" in updated
    assert synchronize_document(document, sources, update=True) == []
    assert document.read_bytes() == updated
    assert synchronize_document(document, sources, update=False) == []


def test_source_discovery_uses_regions_and_ignores_unmarked_calls(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    path = tests / "test_examples.py"
    path.write_text(
        "def test_help():\n"
        "    # region Snippet:help\n"
        "    result = invoke_cli(['--help'])\n"
        "    # endregion\n"
        "def test_output():\n"
        "    # region Snippet:profile_output\n"
        "    record_output('{}', language='json')\n"
        "    # endregion\n"
        "def test_other():\n"
        "    invoke_cli(['--version'])\n"
        "def helper():\n"
        "    invoke_cli(['--help'])\n",
    )

    sources = _MODULE.discover_executable_examples(tests)

    assert sources == {
        "help": (path, 2, "test_help"),
        "profile_output": (path, 6, "test_output"),
    }


def test_source_discovery_includes_regions_in_each_conditional_branch(tmp_path):
    path = tmp_path / "test_examples.py"
    path.write_text(
        "def test_views(view):\n"
        "    if view == 'help':\n"
        "        # region Snippet:cli_help\n"
        "        invoke_cli(['--help'])\n"
        "        # endregion\n"
        "    elif view == 'json':\n"
        "        # region Snippet:output_json\n"
        "        record_output('{}', language='json')\n"
        "        # endregion\n"
        "    else:\n"
        "        # region Snippet:output_text\n"
        "        record_output('text')\n"
        "        # endregion\n",
    )

    sources = _MODULE.discover_executable_examples(tmp_path)

    assert set(sources) == {"cli_help", "output_json", "output_text"}
    assert all(source[0] == path and source[2] == "test_views" for source in sources.values())


@pytest.mark.parametrize(
    "call",
    [
        "record_output('{}', language='json')",
        "record_output(content='{}', language='json')",
        "record_output(language='json', content='{}')",
    ],
    ids=["positional", "keyword", "reordered-keywords"],
)
def test_source_discovery_accepts_output_content_call_styles(tmp_path, call):
    source = tmp_path / "test_output.py"
    source.write_text(
        f"def test_output():\n    # region Snippet:output\n    {call}\n    # endregion\n",
        encoding="utf-8",
    )

    assert _MODULE.discover_executable_examples(tmp_path) == {"output": (source, 2, "test_output")}


@pytest.mark.parametrize(
    "source_text",
    [
        "# region Snippet:output\nrecord_output('{}')\n# endregion\n",
        "def helper():\n    # region Snippet:output\n    record_output('{}')\n    # endregion\n",
        "def test_first():\n    # region Snippet:output\n    record_output('{}')\n"
        "def test_second():\n    record_output('{}')\n    # endregion\n",
        "def test_output():\n    record_output('{}')  # region Snippet:output\n    # endregion\n",
    ],
    ids=["outside-test", "helper", "cross-test", "inline-comment"],
)
def test_source_discovery_reports_invalid_region_placement_with_location(tmp_path, source_text):
    source = tmp_path / "test_output.py"
    source.write_text(source_text, encoding="utf-8")

    with pytest.raises(ValueError) as caught:
        _MODULE.discover_executable_examples(tmp_path)

    assert str(caught.value).startswith(f"{source}:")


def test_source_inventory_excludes_collector_self_tests():
    sources = _MODULE.discover_executable_examples(Path(__file__).resolve().parents[1])

    assert {"analyze_inline", "profile_endpoint", "runtime_info"} <= sources.keys()
    assert not any(path.name == "test_command_catalog.py" for path, _line, _function in sources.values())


def test_region_sources_share_network_and_skip_protections(tmp_path):
    test_root = Path(__file__).resolve().parents[1]
    shutil.copyfile(test_root / "conftest.py", tmp_path / "conftest.py")
    source = tmp_path / "test_source_protection.py"
    source.write_text(
        "import socket\n"
        "import pytest\n"
        "from support.command_catalog import invoke_cli, record_output\n\n"
        "def test_command():\n"
        "    # region Snippet:cli_help\n"
        "    result = invoke_cli(['--help'])\n"
        "    # endregion\n"
        "    assert result.exit_code == 0\n\n"
        "def test_output():\n"
        "    # region Snippet:json_output\n"
        "    record_output(content='{}', language='json')\n"
        "    # endregion\n\n"
        "@pytest.mark.parametrize('operation', ['connect', 'connect_ex'])\n"
        "def test_network(operation):\n"
        "    with socket.socket() as connection:\n"
        "        getattr(connection, operation)(None)\n"
        "    # region Snippet:network_probe\n"
        "    invoke_cli(['--help'])\n"
        "    # endregion\n\n"
        "@pytest.mark.parametrize('variant', ['first', 'second'])\n"
        "def test_source_skip(variant):\n"
        "    pytest.skip('source data unavailable')\n"
        "    if variant == 'first':\n"
        "        # region Snippet:skip_first\n"
        "        record_output('{}')\n"
        "        # endregion\n"
        "    else:\n"
        "        # region Snippet:skip_second\n"
        "        record_output('{}')\n"
        "        # endregion\n\n"
        "@pytest.fixture\n"
        "def missing_recording():\n"
        "    pytest.skip('missing recording')\n\n"
        "def test_setup_skip(missing_recording):\n"
        "    # region Snippet:setup_probe\n"
        "    invoke_cli(['--help'])\n"
        "    # endregion\n\n"
        "def test_ordinary_skip():\n"
        "    pytest.skip('ordinary skip remains allowed')\n\n"
        "def test_ordinary_socket_contract():\n"
        "    with socket.socket() as connection:\n"
        "        with pytest.raises(TypeError):\n"
        "            connection.connect(None)\n",
        encoding="utf-8",
    )
    catalog = tmp_path / "catalog.json"
    report = tmp_path / "results.xml"

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "--strict-markers", "--tb=short",
            "-c", str(test_root.parent / "pyproject.toml"), "--confcutdir", str(tmp_path),
            "--command-catalog", str(catalog), "--junitxml", str(report), str(source),
        ],
        cwd=tmp_path,
        env=dict(os.environ, CU_TEST_REC_MODE="playback", PYTEST_ADDOPTS=""),
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    cases = {case.attrib["name"]: case for case in ElementTree.parse(report).iter("testcase")}
    for operation in ("connect", "connect_ex"):
        failure = cases[f"test_network[{operation}]"].find("failure")
        assert failure is not None
        assert "must not open live network connections" in failure.attrib["message"]
    for variant in ("first", "second"):
        failure = cases[f"test_source_skip[{variant}]"].find("failure")
        assert failure is not None
        assert "Documentation source tests cannot skip" in failure.attrib["message"]
    error = cases["test_setup_skip"].find("error")
    assert error is not None and "Documentation source tests cannot skip" in error.attrib["message"]
    assert cases["test_ordinary_skip"].find("skipped") is not None
    for name in ("test_command", "test_output", "test_ordinary_socket_contract"):
        assert len(cases[name]) == 0
    exported = json.loads(catalog.read_text(encoding="utf-8"))
    assert set(exported["examples"]) == {"cli_help", "json_output"}


def test_named_scenario_comes_from_test_sources_and_preserves_command_order(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    path = tests / "test_workflows.py"
    path.write_text("DOC_SCENARIOS = {'cli_setup': ('version', 'help')}\n")
    sources = {
        "version": _MODULE.Snippet("version", "cu --version", path, 2, "bash"),
        "help": _MODULE.Snippet("help", "cu --help", path, 3, "bash"),
    }

    snippets = _MODULE.compose_scenarios(sources, _MODULE.discover_scenarios(tests))

    assert snippets["cli_setup"].content == "cu --version\n\ncu --help"
    assert snippets["cli_setup"].members == ("version", "help")
    document = tmp_path / "README.md"
    document.write_text("<!-- Snippet:cli_setup -->\n```bash\nold\n```\n")
    assert _MODULE.synchronize_documents((document,), snippets, update=True) == []
    assert _MODULE.synchronize_documents((document,), snippets, update=False) == []


@pytest.mark.parametrize("relationship", ["consecutive", "gap", "reordered", "different-test", "unrecorded"])
def test_scenario_report_distinguishes_continuous_execution_from_composition(relationship):
    path = Path("test_workflow.py")
    first_step, second_step = {
        "consecutive": (0, 1), "gap": (0, 2), "reordered": (1, 0),
        "different-test": (0, 1), "unrecorded": (-1, -1),
    }[relationship]
    sources = {
        "configure": _MODULE.Snippet(
            "configure", "cu profile set default_analyzer prebuilt-layout", path, 1, "bash",
            test="test_workflow", step=first_step, verification={"mode": "local"},
        ),
        "analyze": _MODULE.Snippet(
            "analyze", "cu analyze invoice.pdf", path, 2, "bash",
            test="test_other" if relationship == "different-test" else "test_workflow",
            step=second_step, verification={"mode": "playback"},
        ),
    }
    snippets = _MODULE.compose_scenarios(sources, {"workflow": (path, 1, ("configure", "analyze"))})

    report = _MODULE.build_verification_report(snippets, Path.cwd(), [])

    workflow = report["scenarios"]["workflow"]["verification"]
    assert workflow["mode"] == ("continuous" if relationship == "consecutive" else "composed")
    assert workflow["workflow_test"] == ("test_workflow" if relationship == "consecutive" else None)
    assert workflow["source_modes"] == {"configure": "local", "analyze": "playback"}
    assert report["status"] == "passed"
    assert "content" not in report["examples"]["analyze"]


def test_report_keeps_external_reason_and_errors_without_claiming_success(tmp_path):
    source = _MODULE.Snippet(
        "sign_in", "az login", tmp_path / "test_setup.py", 1, "bash",
        verification={"mode": "external", "reason": "Interactive prerequisite, not run in CI."},
    )

    report = _MODULE.build_verification_report({"sign_in": source}, tmp_path, ["document drift"])

    assert report["status"] == "failed"
    assert report["errors"] == ["document drift"]
    assert report["examples"]["sign_in"]["verification"]["mode"] == "external"
    assert report["examples"]["sign_in"]["source"] == "test_setup.py"


@pytest.mark.parametrize(
    "definition",
    [
        "{'cli_setup': ('help',)}",
        "{'test_cli_setup': ('help', 'version')}",
        "{'cli_setup': ('help', 'version'), 'cli_setup': ('version', 'help')}",
    ],
    ids=["single-source-alias", "test-prefix", "duplicate-name"],
)
def test_scenario_names_are_semantic_and_do_not_add_single_command_aliases(tmp_path, definition):
    (tmp_path / "test_workflows.py").write_text(f"DOC_SCENARIOS = {definition}\n")

    with pytest.raises(ValueError):
        _MODULE.discover_scenarios(tmp_path)


@pytest.mark.parametrize("defect", ["missing", "collision", "language"])
def test_scenario_requires_distinct_name_and_executed_same_language_sources(defect):
    path = Path("test_workflows.py")
    sources = {
        "version": _MODULE.Snippet("version", "cu --version", path, 2, "bash"),
        "help": _MODULE.Snippet("help", "cu --help", path, 3, "bash"),
    }
    name = "version" if defect == "collision" else "cli_setup"
    if defect == "missing":
        del sources["help"]
    if defect == "language":
        sources["help"] = _MODULE.Snippet("help", "cu --help", path, 3, "powershell")

    with pytest.raises(ValueError):
        _MODULE.compose_scenarios(sources, {name: (path, 1, ("version", "help"))})


def test_same_source_name_can_be_reused_across_documents(tmp_path):
    first = tmp_path / "README.md"
    second = tmp_path / "usage-guide.md"
    for path in (first, second):
        path.write_text("<!-- Snippet:cli_help -->\n```bash\ncu --help\n```\n")
    sources = {
        identifier: _MODULE.Snippet(identifier, "cu --help", Path("test_cli.py"), 1, "bash")
        for identifier in ("cli_help", "orphan")
    }

    errors = _MODULE.validate_document_references((first, second), sources)

    assert len(errors) == 1
    assert any("exported example 'orphan' is not used" in error for error in errors)
    del sources["orphan"]
    assert _MODULE.synchronize_documents((first, second), sources, update=False) == []


def test_repeated_source_updates_only_command_blocks_and_preserves_manual_prose(tmp_path):
    document = tmp_path / "README.md"
    before = b"# Manual heading\r\n\nDescription with `--flags` and trailing spaces.  \r\n"
    between = b"\nA manually revised explanation.\r\n\r\n"
    after = b"\r\nFinal description without a newline."
    first = b"<!-- Snippet:analyze_inline -->\r\n```bash\r\nold\r\n```\r\n"
    second = b"<!-- Snippet:analyze_inline -->\n```bash\nold\n```\n"
    document.write_bytes(before + first + between + second + after)
    command = "cu analyze --inline sample_invoice.pdf"
    source = _MODULE.Snippet("analyze_inline", command, Path("test_cli.py"), 1, "bash")

    assert _MODULE.synchronize_documents((document,), {"analyze_inline": source}, update=True) == []

    assert document.read_bytes() == (
        before + first.replace(b"old", command.encode())
        + between + second.replace(b"old", command.encode()) + after
    )
    document.write_bytes(document.read_bytes().replace(b"manually revised", b"newly handwritten"))
    assert _MODULE.synchronize_documents((document,), {"analyze_inline": source}, update=False) == []


def test_old_document_alias_format_is_rejected_without_writing(tmp_path):
    document = tmp_path / "README.md"
    original = "<!-- Snippet:readme_06 Examples:analyze_inline -->\n```bash\nold\n```\n"
    document.write_text(original, encoding="utf-8")
    source = _MODULE.Snippet("analyze_inline", "cu analyze --inline invoice.pdf", Path("test.py"), 1)

    errors = synchronize_document(document, {"analyze_inline": source}, update=True)

    assert any("malformed Snippet marker" in error for error in errors)
    assert document.read_text(encoding="utf-8") == original


def test_markers_inside_output_are_not_document_references(tmp_path):
    document = tmp_path / "README.md"
    document.write_text(
        "<!-- Snippet:output -->\n```text\n<!-- Snippet:not_a_reference -->\n```\n",
    )
    source = _MODULE.Snippet("output", "<!-- Snippet:not_a_reference -->", Path("test.py"), 1)
    assert _MODULE.validate_document_references((document,), {"output": source}) == []


@pytest.mark.parametrize("broken_name", ["README.md", "usage-guide.md"])
def test_update_validates_both_documents_before_writing_either(tmp_path, broken_name):
    documents = (tmp_path / "README.md", tmp_path / "usage-guide.md")
    for document in documents:
        document.write_text("<!-- Snippet:help -->\n```bash\nold\n```\n")
    broken = tmp_path / broken_name
    broken.write_text("```bash\ncu analyze documents --pattern '*.pdf'\n```\n")
    original = {path: path.read_bytes() for path in documents}
    source = _MODULE.Snippet("help", "cu --help", Path("test_cli.py"), 1, "bash")

    errors = _MODULE.synchronize_documents(documents, {"help": source}, update=True)

    assert any("no Snippet ID" in error for error in errors)
    assert all(path.read_bytes() == original[path] for path in documents)


@pytest.mark.parametrize("mode", ["check", "update"])
@pytest.mark.parametrize("source_failure", [False, True], ids=["document-drift", "source-failure"])
def test_main_exit_code_report_and_document_writes_are_consistent(
    tmp_path, monkeypatch, capsys, mode, source_failure,
):
    (tmp_path / "docs").mkdir()
    documents = (tmp_path / "README.md", tmp_path / "docs" / "usage-guide.md")
    for document in documents:
        document.write_bytes(b"# Manual heading\r\n<!-- Snippet:help -->\r\n```bash\r\nold\r\n```\r\n")
    original = {document: document.read_bytes() for document in documents}
    source = _MODULE.Snippet("help", "cu --help", tmp_path / "test_cli.py", 1, "bash")

    def execute_examples(product_root, test_root):
        assert product_root == tmp_path
        assert test_root == tmp_path / "packages" / "standalone" / "tests"
        if source_failure:
            raise ValueError("documentation source tests failed: intentional failure")
        return {"help": source}

    monkeypatch.setitem(_MODULE.main.__globals__, "__file__", str(tmp_path / "scripts" / "update-snippet.py"))
    monkeypatch.setitem(_MODULE.main.__globals__, "execute_test_examples", execute_examples)
    report_path = tmp_path / "artifacts" / "verification.json"

    exit_code = _MODULE.main([mode, "--report", str(report_path)])

    succeeded = mode == "update" and not source_failure
    assert exit_code == (0 if succeeded else 1)
    captured = capsys.readouterr()
    assert bool(captured.err) != succeeded
    assert "Traceback" not in captured.err
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == ("passed" if succeeded else "failed")
    assert bool(report["errors"]) != succeeded
    for document in documents:
        expected = original[document].replace(b"old\r\n", b"cu --help\r\n") if succeeded else original[document]
        assert document.read_bytes() == expected


@pytest.mark.parametrize("mode", ["check", "update"])
@pytest.mark.parametrize("target_kind", ["readme", "usage", "script", "test"])
@pytest.mark.parametrize("alias", ["direct", "relative", "symlink", "hardlink"])
def test_report_rejects_input_paths_and_aliases_before_running_tests(
    tmp_path, monkeypatch, capsys, mode, target_kind, alias,
):
    test_root = tmp_path / "packages" / "standalone" / "tests"
    inputs = {
        "readme": tmp_path / "README.md",
        "usage": tmp_path / "docs" / "usage-guide.md",
        "script": tmp_path / "scripts" / "update-snippet.py",
        "test": test_root / "test_source.py",
    }
    for path in inputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"original input\n")
    original = {path: path.read_bytes() for path in inputs.values()}
    source = inputs[target_kind]
    report_path = source
    if alias == "relative":
        monkeypatch.chdir(tmp_path)
        report_path = Path("docs") / ".." / source.relative_to(tmp_path)
    elif alias in {"symlink", "hardlink"}:
        report_path = tmp_path / "report.json"
        try:
            if alias == "symlink":
                report_path.symlink_to(source)
            else:
                report_path.hardlink_to(source)
        except OSError as exc:
            pytest.skip(f"file alias creation unavailable: {exc}")

    monkeypatch.setitem(_MODULE.main.__globals__, "__file__", str(inputs["script"]))
    monkeypatch.setitem(
        _MODULE.main.__globals__, "execute_test_examples",
        lambda *args: pytest.fail("invalid report paths must fail before source execution"),
    )

    assert _MODULE.main([mode, "--report", str(report_path)]) == 1

    assert "--report must not overwrite an input file" in capsys.readouterr().err
    assert all(path.read_bytes() == content for path, content in original.items())