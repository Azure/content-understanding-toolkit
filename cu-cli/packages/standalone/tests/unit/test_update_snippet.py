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
_TEST_ROOT = Path(__file__).resolve().parents[1]
synchronize_document = _MODULE.synchronize_document


def _snippet(identifier, content="cu --help", language="bash", **options):
    return _MODULE.Snippet(identifier, content, Path("test_readme.py"), 1, language, **options)


def _synchronize(root, documents, *, update):
    return _MODULE.synchronize_documents(root, documents, update=update)


def test_region_discovery_handles_multiline_calls_and_nested_regions(tmp_path):
    source = tmp_path / "test_readme.py"
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

    regions = _MODULE.discover_snippet_regions(source)

    assert regions == {
        "help": (source, 4, 8, "test_workflow"),
        "workflow": (source, 3, 10, "test_workflow"),
    }
    assert _MODULE.nested_regions(regions) == {"help"}


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
    source = tmp_path / "test_readme.py"
    source.write_text("def test_workflow():\n" + body, encoding="utf-8")

    with pytest.raises(ValueError, match="Snippet|endregion"):
        _MODULE.discover_snippet_regions(source)


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
def test_region_discovery_reports_invalid_placement_with_location(tmp_path, source_text):
    source = tmp_path / "test_readme.py"
    source.write_text(source_text, encoding="utf-8")

    with pytest.raises(ValueError) as caught:
        _MODULE.discover_snippet_regions(source)

    assert str(caught.value).startswith(f"{source}:")


def test_regions_outside_documentation_tests_are_rejected(tmp_path):
    allowed = tmp_path / "docs" / "test_readme.py"
    allowed.parent.mkdir()
    allowed.write_text("def test_help():\n    # region Snippet:help\n    run()\n    # endregion\n")
    stray = tmp_path / "unit" / "test_cli.py"
    stray.parent.mkdir()
    stray.write_text(
        "def test_help():\n    text = '# region Snippet:in_string'\n"
        "    # region Snippet:help\n    run()\n    # endregion\n",
        encoding="utf-8",
    )

    errors = _MODULE.find_stray_regions(tmp_path, {allowed.resolve()})

    assert errors == [
        f"{stray}:3: Snippet regions belong only in the documentation tests (test_readme.py); "
        "move this example there"
    ]


def test_each_document_uses_its_own_test_file():
    assert _MODULE.DOCUMENTS == {
        Path("README.md"): Path("packages/standalone/tests/docs/test_readme.py"),
        Path("docs/usage-guide.md"): Path("packages/standalone/tests/docs/test_usage_guide.py"),
    }


def test_update_is_deterministic_and_check_detects_drift(tmp_path):
    document = tmp_path / "README.md"
    document.write_text("<!-- Snippet:example -->\n```bash\nold command\n```\n", encoding="utf-8")
    snippets = {"example": _MODULE.Snippet("example", "cu --help", tmp_path / "test_readme.py", 1)}

    errors = synchronize_document(document, snippets, update=False)
    assert errors == [
        f"{document}:1: snippet 'example' differs from {tmp_path / 'test_readme.py'}:1; "
        "run 'python scripts/update-snippet.py update'"
    ]

    assert synchronize_document(document, snippets, update=True) == []
    updated = document.read_text(encoding="utf-8")
    assert updated == "<!-- Snippet:example -->\n```bash\ncu --help\n```\n"
    assert synchronize_document(document, snippets, update=True) == []
    assert document.read_text(encoding="utf-8") == updated
    assert synchronize_document(document, snippets, update=False) == []


def test_unmarked_blocks_and_missing_regions_fail_without_writing(tmp_path):
    document = tmp_path / "README.md"
    original = "```bash\ncu analyze documents --pattern '*.pdf'\n```\n"
    document.write_text(original, encoding="utf-8")

    errors = synchronize_document(document, {}, update=True)

    assert any("no Snippet ID" in error for error in errors)
    assert document.read_text(encoding="utf-8") == original
    document.write_text("<!-- Snippet:missing -->\n```bash\ncu --help\n```\n")
    assert any("has no Snippet region" in error for error in synchronize_document(document, {}, update=False))


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
    (tmp_path / "docs").mkdir()
    documents = (tmp_path / "README.md", tmp_path / "docs" / "usage-guide.md")
    prefix = "<!-- Snippet:help -->\n```bash\nold\n```\n\n"
    documents[0].write_text(prefix, encoding="utf-8")
    documents[1].write_text(prefix + nested, encoding="utf-8")
    original = {path: path.read_bytes() for path in documents}
    snippets = {Path("README.md"): {"help": _snippet("help")}, Path("docs/usage-guide.md"): {"help": _snippet("help")}}

    errors = _synchronize(tmp_path, snippets, update=update)

    assert any(error.startswith(f"{documents[1]}:") and "nested code fence" in error for error in errors)
    assert all(path.read_bytes() == content for path, content in original.items())


def test_nested_fence_syntax_inside_output_is_literal_content(tmp_path):
    document = tmp_path / "README.md"
    content = "> ```bash\n> cu --help\n> ```"
    document.write_text("<!-- Snippet:output -->\n```text\nold\n```\n", encoding="utf-8")
    snippets = {Path("README.md"): {"output": _snippet("output", content, "text")}}

    assert _synchronize(tmp_path, snippets, update=True) == []
    assert _synchronize(tmp_path, snippets, update=False) == []
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
    snippets = {Path("README.md"): {"help": _snippet("help")}}

    assert _synchronize(tmp_path, snippets, update=True) == []
    assert document.read_bytes() == original.replace(b"old\r\n", b"cu --help\r\n")
    assert _synchronize(tmp_path, snippets, update=False) == []


@pytest.mark.parametrize("fence", ["```", "~~~"], ids=["backticks", "tildes"])
def test_source_cannot_close_its_document_fence_or_partially_update_documents(tmp_path, fence):
    (tmp_path / "docs").mkdir()
    first = tmp_path / "README.md"
    second = tmp_path / "docs" / "usage-guide.md"
    first.write_text("<!-- Snippet:help -->\n```bash\nold\n```\n", encoding="utf-8")
    second.write_text(f"<!-- Snippet:output -->\n{fence}text\nold\n{fence}\n", encoding="utf-8")
    original = {path: path.read_bytes() for path in (first, second)}
    snippets = {
        Path("README.md"): {"help": _snippet("help")},
        Path("docs/usage-guide.md"): {"output": _snippet("output", f"result\n{fence}\nnot prose", "text")},
    }

    errors = _synchronize(tmp_path, snippets, update=True)

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
    snippets = {Path("README.md"): {"output": _snippet("output", content, "text")}}

    assert _synchronize(tmp_path, snippets, update=True) == []
    assert document.read_text() == f"<!-- Snippet:output -->\n{fence}text\n{content}\n{fence}\n"
    assert _synchronize(tmp_path, snippets, update=False) == []


def test_inline_backticks_in_prose_are_not_treated_as_a_fenced_block(tmp_path):
    document = tmp_path / "README.md"
    original = b"```this is an inline code span```\n"
    document.write_bytes(original)

    assert _synchronize(tmp_path, {Path("README.md"): {}}, update=True) == []
    assert document.read_bytes() == original


def test_multiple_commands_generate_one_block_and_preserve_crlf(tmp_path):
    document = tmp_path / "README.md"
    document.write_bytes(b"<!-- Snippet:cli_setup -->\r\n```bash\r\nold\r\n```\r\n")
    snippets = {"cli_setup": _snippet("cli_setup", "cu --version\n\ncu --help")}

    assert synchronize_document(document, snippets, update=True) == []
    updated = document.read_bytes()
    assert b"cu --version\r\n\r\ncu --help" in updated
    assert synchronize_document(document, snippets, update=True) == []
    assert document.read_bytes() == updated
    assert synchronize_document(document, snippets, update=False) == []


def test_unused_top_level_regions_fail_but_nested_steps_do_not(tmp_path):
    document = tmp_path / "README.md"
    document.write_text("<!-- Snippet:workflow -->\n```bash\ncu --version\ncu --help\n```\n")
    snippets = {
        "workflow": _snippet("workflow", "cu --version\ncu --help"),
        "version_step": _snippet("version_step", "cu --version", nested=True),
        "orphan": _snippet("orphan"),
    }

    errors = _MODULE.validate_document_references(document, snippets)

    assert errors == [
        "test_readme.py:1: Snippet region 'orphan' is not used by README.md; "
        "add a marker or remove the region"
    ]


def test_same_region_name_can_be_used_by_each_document(tmp_path):
    (tmp_path / "docs").mkdir()
    for path in (tmp_path / "README.md", tmp_path / "docs" / "usage-guide.md"):
        path.write_text("<!-- Snippet:cli_help -->\n```bash\nold\n```\n")
    snippets = {
        Path("README.md"): {"cli_help": _snippet("cli_help", "cu --help")},
        Path("docs/usage-guide.md"): {"cli_help": _snippet("cli_help", "cu --version")},
    }

    assert _synchronize(tmp_path, snippets, update=True) == []

    assert "cu --help" in (tmp_path / "README.md").read_text()
    assert "cu --version" in (tmp_path / "docs" / "usage-guide.md").read_text()


def test_repeated_references_update_only_command_blocks_and_preserve_manual_prose(tmp_path):
    document = tmp_path / "README.md"
    before = b"# Manual heading\r\n\nDescription with `--flags` and trailing spaces.  \r\n"
    between = b"\nA manually revised explanation.\r\n\r\n"
    after = b"\r\nFinal description without a newline."
    first = b"<!-- Snippet:analyze_inline -->\r\n```bash\r\nold\r\n```\r\n"
    second = b"<!-- Snippet:analyze_inline -->\n```bash\nold\n```\n"
    document.write_bytes(before + first + between + second + after)
    command = "cu analyze --inline sample_invoice.pdf"
    snippets = {Path("README.md"): {"analyze_inline": _snippet("analyze_inline", command)}}

    assert _synchronize(tmp_path, snippets, update=True) == []

    assert document.read_bytes() == (
        before + first.replace(b"old", command.encode())
        + between + second.replace(b"old", command.encode()) + after
    )
    document.write_bytes(document.read_bytes().replace(b"manually revised", b"newly handwritten"))
    assert _synchronize(tmp_path, snippets, update=False) == []


def test_malformed_markers_are_rejected_without_writing(tmp_path):
    document = tmp_path / "README.md"
    original = "<!-- Snippet:readme_06 Examples:analyze_inline -->\n```bash\nold\n```\n"
    document.write_text(original, encoding="utf-8")

    errors = synchronize_document(document, {"analyze_inline": _snippet("analyze_inline")}, update=True)

    assert any("malformed Snippet marker" in error for error in errors)
    assert document.read_text(encoding="utf-8") == original


def test_markers_inside_output_are_not_document_references(tmp_path):
    document = tmp_path / "README.md"
    document.write_text("<!-- Snippet:output -->\n```text\n<!-- Snippet:not_a_reference -->\n```\n")
    snippets = {"output": _snippet("output", "<!-- Snippet:not_a_reference -->", "text")}

    assert _MODULE.validate_document_references(document, snippets) == []


@pytest.mark.parametrize("broken_name", ["README.md", "docs/usage-guide.md"])
def test_update_validates_both_documents_before_writing_either(tmp_path, broken_name):
    (tmp_path / "docs").mkdir()
    names = (Path("README.md"), Path("docs/usage-guide.md"))
    for name in names:
        (tmp_path / name).write_text("<!-- Snippet:help -->\n```bash\nold\n```\n")
    (tmp_path / broken_name).write_text("```bash\ncu analyze documents --pattern '*.pdf'\n```\n")
    original = {name: (tmp_path / name).read_bytes() for name in names}

    errors = _synchronize(tmp_path, {name: {"help": _snippet("help")} for name in names}, update=True)

    assert any("no Snippet ID" in error for error in errors)
    assert all((tmp_path / name).read_bytes() == original[name] for name in names)


@pytest.mark.parametrize("mode", ["check", "update"])
@pytest.mark.parametrize("source_failure", [False, True], ids=["document-drift", "source-failure"])
def test_main_exit_code_and_document_writes_are_consistent(tmp_path, monkeypatch, capsys, mode, source_failure):
    (tmp_path / "docs").mkdir()
    names = (Path("README.md"), Path("docs/usage-guide.md"))
    for name in names:
        (tmp_path / name).write_bytes(b"# Manual heading\r\n<!-- Snippet:help -->\r\n```bash\r\nold\r\n```\r\n")
    original = {name: (tmp_path / name).read_bytes() for name in names}

    def collect_snippets(product_root):
        assert product_root == tmp_path
        if source_failure:
            raise ValueError("documentation tests failed: intentional failure")
        return {name: {"help": _snippet("help")} for name in names}

    monkeypatch.setitem(_MODULE.main.__globals__, "__file__", str(tmp_path / "scripts" / "update-snippet.py"))
    monkeypatch.setitem(_MODULE.main.__globals__, "collect_snippets", collect_snippets)

    exit_code = _MODULE.main([mode])

    succeeded = mode == "update" and not source_failure
    assert exit_code == (0 if succeeded else 1)
    captured = capsys.readouterr()
    assert bool(captured.err) != succeeded and "Traceback" not in captured.err
    if succeeded:
        assert "synchronized 2 tested code block(s)" in captured.out
    for name in names:
        expected = original[name].replace(b"old\r\n", b"cu --help\r\n") if succeeded else original[name]
        assert (tmp_path / name).read_bytes() == expected


def _documentation_suite(tmp_path, source_text):
    docs = tmp_path / "docs"
    docs.mkdir()
    shutil.copyfile(_TEST_ROOT / "docs" / "conftest.py", docs / "conftest.py")
    source = docs / "test_readme.py"
    source.write_text(source_text, encoding="utf-8")
    return source


def _run_documentation_suite(source, output, *options):
    return subprocess.run(
        [
            sys.executable, "-m", "pytest", "--strict-markers", "--tb=short", "-p", "no:cacheprovider",
            "-c", str(_TEST_ROOT.parent / "pyproject.toml"), "--rootdir", str(source.parents[1]),
            *options, str(source),
        ],
        cwd=source.parents[1],
        env=dict(
            os.environ, CU_TEST_REC_MODE="playback", PYTEST_ADDOPTS="",
            **{_MODULE.OUTPUT_ENVIRONMENT: str(output)},
        ),
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )


def test_documentation_tests_publish_only_calls_inside_regions(tmp_path):
    source = _documentation_suite(
        tmp_path,
        "from support.snippets import record_external, record_output, run_command as _run\n"
        "def test_commands():\n"
        "    _run('cu profile list')\n"
        "    # region Snippet:cli_setup\n"
        "    # region Snippet:version_step\n"
        "    version = _run('cu --version')\n"
        "    # endregion\n"
        "    assert version.exit_code == 0\n"
        "    help_text = _run('# List commands.\\ncu --help')\n"
        "    # endregion\n"
        "    assert 'Usage:' in help_text.output\n"
        "    _run('cu profile show')\n"
        "def test_output():\n"
        "    # region Snippet:json_output\n"
        "    record_output('{}\\n', language='json')\n"
        "    # endregion\n"
        "def test_external():\n"
        "    # region Snippet:login\n"
        "    record_external('az login', reason='Interactive sign-in')\n"
        "    # endregion\n",
    )
    output = tmp_path / "snippets.json"

    result = _run_documentation_suite(source, output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "test_readme.py": {
            "version_step": {"language": "bash", "content": "cu --version"},
            "cli_setup": {"language": "bash", "content": "cu --version\n# List commands.\ncu --help"},
            "json_output": {"language": "json", "content": "{}"},
            "login": {"language": "bash", "content": "az login"},
        }
    }


def test_documentation_tests_block_network_fail_skips_and_publish_only_passing_tests(tmp_path):
    source = _documentation_suite(
        tmp_path,
        "import socket\n"
        "import pytest\n"
        "from support.snippets import run_command\n"
        "def test_command():\n"
        "    # region Snippet:cli_help\n"
        "    run_command('cu --help')\n"
        "    # endregion\n"
        "@pytest.mark.parametrize('operation', ['connect', 'connect_ex'])\n"
        "def test_network(operation):\n"
        "    with socket.socket() as connection:\n"
        "        getattr(connection, operation)(('127.0.0.1', 9))\n"
        "def test_call_skip():\n"
        "    pytest.skip('recording unavailable')\n"
        "@pytest.fixture\n"
        "def missing_recording():\n"
        "    pytest.skip('missing recording')\n"
        "def test_setup_skip(missing_recording):\n"
        "    pass\n"
        "def test_failed_assertion():\n"
        "    # region Snippet:failed_probe\n"
        "    run_command('cu --version')\n"
        "    # endregion\n"
        "    assert False, 'post-command validation failed'\n"
        "def test_repeated_call():\n"
        "    # region Snippet:repeated_probe\n"
        "    for _ in range(2):\n"
        "        run_command('cu --version')\n"
        "    # endregion\n",
    )
    output = tmp_path / "snippets.json"
    report = tmp_path / "results.xml"

    result = _run_documentation_suite(source, output, "--junitxml", str(report))

    assert result.returncode == 1, result.stdout + result.stderr
    cases = {case.attrib["name"]: case for case in ElementTree.parse(report).iter("testcase")}
    for operation in ("connect", "connect_ex"):
        failure = cases[f"test_network[{operation}]"].find("failure")
        assert failure is not None and "must not open network connections" in failure.attrib["message"]
    failure = cases["test_call_skip"].find("failure")
    assert failure is not None and "cannot skip" in failure.attrib["message"]
    error = cases["test_setup_skip"].find("error")
    assert error is not None and "cannot skip" in error.attrib["message"]
    failure = cases["test_repeated_call"].find("failure")
    assert failure is not None and "runs line" in failure.attrib["message"]
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "test_readme.py": {"cli_help": {"language": "bash", "content": "cu --help"}},
    }


def test_collection_requires_every_region_to_publish(tmp_path, monkeypatch):
    tests = tmp_path / "packages" / "standalone" / "tests"
    (tests / "docs").mkdir(parents=True)
    for document in _MODULE.DOCUMENTS.values():
        (tmp_path / document).write_text(
            "def test_help():\n    # region Snippet:help\n    run_command('cu --help')\n    # endregion\n",
            encoding="utf-8",
        )
    monkeypatch.setitem(
        _MODULE.collect_snippets.__globals__, "execute_documentation_tests",
        lambda product_root, sources: {"test_readme.py": {"help": {"language": "bash", "content": "cu --help"}}},
    )

    with pytest.raises(ValueError, match="test_usage_guide.py:2: Snippet region 'help' published nothing"):
        _MODULE.collect_snippets(tmp_path)
