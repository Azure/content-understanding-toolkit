# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from azure.ai.contentunderstanding.models import AnalysisResult, DocumentContent
from click.testing import CliRunner
import pytest

from cu_cli.cli import main
from cu_cli_core.command_spec import ANALYZER_COPY
from tests.support.doc_snippets import (
    ExecutionMode,
    SNIPPET_EXECUTION_MODES,
    load_doc_snippets,
    parse_cu_commands,
    parse_shell_commands,
)


pytestmark = pytest.mark.unit

_PRODUCT_ROOT = Path(__file__).resolve().parents[4]
_SNIPPETS = load_doc_snippets(
    _PRODUCT_ROOT / "README.md",
    _PRODUCT_ROOT / "docs" / "usage-guide.md",
)
_OFFLINE_SNIPPET_IDS = sorted(
    identifier
    for identifier, mode in SNIPPET_EXECUTION_MODES.items()
    if mode is ExecutionMode.OFFLINE
)
_FAKE_ANALYZE_SNIPPET_IDS = [
    "cu_cli_analyze_batch_with_report",
    "cu_cli_analyze_concurrency_and_timing",
    "cu_cli_analyze_directory",
    "cu_cli_analyze_directory_pattern",
    "cu_cli_analyze_directory_recursive",
    "cu_cli_analyze_inline_preview",
    "cu_cli_analyze_output_formats",
    "cu_cli_analyze_public_url",
    "cu_cli_analyze_remote_url",
    "cu_cli_analyze_sas_url",
]
_FAKE_DEFAULTS_SNIPPET_IDS = [
    "cu_cli_configure_and_apply_defaults",
    "cu_cli_manage_defaults",
    "cu_cli_run_diagnostics",
]
_MIXED_SHELL_SNIPPET_IDS = [
    "cu_cli_azure_login",
    "cu_cli_configure_login_profile",
    "cu_cli_install",
    "cu_cli_profile_resolution_precedence",
    "cu_cli_temporarily_override_endpoint",
    "cu_cli_use_multiple_profiles",
]
_FAKE_ANALYZER_SNIPPET_IDS = [
    "cu_cli_create_and_test_analyzer",
    "cu_cli_create_and_test_custom_analyzer",
    "cu_cli_create_schema_from_sample",
    "cu_cli_manage_analyzers",
]
_FAKE_COPY_SNIPPET_IDS = [
    "cu_cli_copy_analyzer_with_profiles",
    "cu_cli_copy_analyzer_with_resources",
]
_PLAYBACK_SNIPPET_IDS = {
    identifier
    for identifier, mode in SNIPPET_EXECUTION_MODES.items()
    if mode is ExecutionMode.PLAYBACK
}


def test_every_bash_snippet_has_an_execution_consumer():
    consumed = set(_OFFLINE_SNIPPET_IDS)
    consumed.update(_FAKE_ANALYZE_SNIPPET_IDS)
    consumed.update(_FAKE_DEFAULTS_SNIPPET_IDS)
    consumed.update(_MIXED_SHELL_SNIPPET_IDS)
    consumed.update(_FAKE_ANALYZER_SNIPPET_IDS)
    consumed.update(_FAKE_COPY_SNIPPET_IDS)
    consumed.add("cu_cli_sync_profile_defaults")
    consumed.update(_PLAYBACK_SNIPPET_IDS)
    bash_snippets = {
        identifier
        for identifier, snippet in _SNIPPETS.items()
        if snippet.language == "bash"
    }

    assert consumed == bash_snippets


def _prepare_offline_state(
    runner: CliRunner, work_dir: Path, snippet_id: str
) -> None:
    if snippet_id in {
        "cu_cli_analyze_multiple_urls_dry_run",
        "cu_cli_preview_batch",
    }:
        documents = work_dir / "documents"
        documents.mkdir()
        (documents / "invoice.pdf").write_bytes(b"%PDF-1.4\n")

    if snippet_id == "cu_cli_unset_key_authentication":
        result = runner.invoke(main, ["profile", "set", "api_key", "test-api-key"])
        assert result.exit_code == 0, result.output

    if snippet_id == "cu_cli_validate_schema":
        result = runner.invoke(
            main,
            ["analyzer", "schema", "create", "--output-file", "schema.json"],
        )
        assert result.exit_code == 0, result.output


def _replace_placeholders(args: list[str]) -> list[str]:
    replacements = {
        "<key>": "test-api-key",
        "https://<resource-name>.services.ai.azure.com/": (
            "https://example.services.ai.azure.com/"
        ),
    }
    return [replacements.get(arg, arg) for arg in args]


def _replace_documentation_placeholders(args: list[str]) -> list[str]:
    replacements = {
        "<dev-resource>": "dev",
        "<one-time-resource>": "one-time",
        "<prod-resource>": "prod",
        "<resource-name>": "example",
        "<temporary-resource>": "temporary",
    }
    replaced = []
    for arg in args:
        for placeholder, value in replacements.items():
            arg = arg.replace(placeholder, value)
        replaced.append(arg)
    return replaced


@pytest.mark.parametrize("snippet_id", _OFFLINE_SNIPPET_IDS)
def test_offline_documented_snippet_executes(
    snippet_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    _prepare_offline_state(runner, tmp_path, snippet_id)

    for args in parse_cu_commands(_SNIPPETS[snippet_id]):
        result = runner.invoke(main, _replace_placeholders(args))

        assert result.exit_code == 0, (
            f"Snippet:{snippet_id} failed for {' '.join(args)}\n{result.output}"
        )


@pytest.mark.parametrize("snippet_id", _FAKE_ANALYZE_SNIPPET_IDS)
def test_fake_documented_analyze_snippet_executes(
    snippet_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "invoice.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "document.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "invoice.pdf").write_bytes(b"%PDF-1.4\n")

    def fake_result(_client, job):
        return job, AnalysisResult(
            contents=[DocumentContent(markdown="# result\n")]
        )

    monkeypatch.setattr(
        "cu_cli.commands.analyze.Profile.load",
        lambda **_kwargs: SimpleNamespace(
            default_analyzer="prebuilt-layout",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", fake_result)
    monkeypatch.setattr("cu_cli.commands.analyze._run_one_inline", fake_result)

    for args in parse_cu_commands(_SNIPPETS[snippet_id]):
        result = CliRunner().invoke(main, _replace_placeholders(args))

        assert result.exit_code == 0, (
            f"Snippet:{snippet_id} failed for {' '.join(args)}\n{result.output}"
        )


@pytest.mark.parametrize("snippet_id", _FAKE_DEFAULTS_SNIPPET_IDS)
def test_fake_documented_defaults_snippet_executes(
    snippet_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class FakeDefaults:
        def __init__(self, mappings: dict[str, str]):
            self.model_deployments = mappings

        def as_dict(self):
            return {"modelDeployments": self.model_deployments}

    class FakeDefaultsClient:
        def __init__(self):
            self.mappings = {
                "gpt-5.2": "fake-gpt",
                "text-embedding-3-large": "fake-embedding",
                "prebuilt-analyzer-completion-mini": "fake-gpt-mini",
            }

        def get_defaults(self):
            return FakeDefaults(self.mappings)

        def update_defaults(self, *, model_deployments):
            self.mappings = dict(model_deployments)
            return FakeDefaults(self.mappings)

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    for args in (
        ["profile", "set", "endpoint", "https://example.services.ai.azure.com/"],
        ["profile", "create", "prod"],
        [
            "profile",
            "set",
            "endpoint",
            "https://prod.services.ai.azure.com/",
            "--name",
            "prod",
        ],
        ["profile", "set", "model_deployments.gpt-5.2", "fake-gpt"],
        [
            "profile",
            "set",
            "model_deployments.text-embedding-3-large",
            "fake-embedding",
        ],
    ):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output

    fake = FakeDefaultsClient()
    monkeypatch.setattr(
        "cu_cli.commands.defaults.build_client", lambda *_args, **_kwargs: fake
    )
    monkeypatch.setattr(
        "cu_cli.commands.doctor.build_client", lambda *_args, **_kwargs: fake
    )

    for args in parse_cu_commands(_SNIPPETS[snippet_id]):
        result = runner.invoke(main, args)

        assert result.exit_code == 0, (
            f"Snippet:{snippet_id} failed for {' '.join(args)}\n{result.output}"
        )


def test_documented_sync_defaults_snippet_executes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class FakeClient:
        def get_defaults(self):
            return SimpleNamespace(
                model_deployments={
                    "gpt-5.2": "fake-gpt",
                    "text-embedding-3-large": "fake-embedding",
                }
            )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "cu_cli.commands.profile_cmd.build_client",
        lambda *_args, **_kwargs: FakeClient(),
    )
    runner = CliRunner()
    for args in (
        ["profile", "set", "endpoint", "https://example.services.ai.azure.com/"],
        ["profile", "create", "prod"],
        [
            "profile",
            "set",
            "endpoint",
            "https://prod.services.ai.azure.com/",
            "--name",
            "prod",
        ],
    ):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output

    for args in parse_cu_commands(_SNIPPETS["cu_cli_sync_profile_defaults"]):
        result = runner.invoke(main, args)

        assert result.exit_code == 0, (
            "Snippet:cu_cli_sync_profile_defaults failed for "
            f"{' '.join(args)}\n{result.output}"
        )


@pytest.mark.parametrize("snippet_id", _MIXED_SHELL_SNIPPET_IDS)
def test_mixed_shell_documented_snippet_executes_safe_commands(
    snippet_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class FakeAnalyzer:
        def as_dict(self):
            return {"analyzerId": "prebuilt-layout"}

    class FakeDefaults:
        model_deployments = {
            "gpt-5.2": "fake-gpt",
            "text-embedding-3-large": "fake-embedding",
            "prebuilt-analyzer-completion-mini": "fake-gpt-mini",
        }

    class FakeClient:
        def list_analyzers(self):
            return [FakeAnalyzer()]

        def get_defaults(self):
            return FakeDefaults()

    monkeypatch.chdir(tmp_path)
    fake = FakeClient()
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.build_client", lambda *_args, **_kwargs: fake
    )
    monkeypatch.setattr(
        "cu_cli.commands.doctor.build_client", lambda *_args, **_kwargs: fake
    )
    runner = CliRunner()
    if snippet_id == "cu_cli_temporarily_override_endpoint":
        result = runner.invoke(main, ["profile", "create", "dev"])
        assert result.exit_code == 0, result.output

    for raw_args in parse_shell_commands(_SNIPPETS[snippet_id]):
        args = _replace_documentation_placeholders(raw_args)
        if args[:4] == ["python", "-m", "pip", "install"]:
            assert args == ["python", "-m", "pip", "install", "cu-cli"]
            continue
        if args == ["az", "login"]:
            continue
        if args[0] == "export":
            name, value = args[1].split("=", 1)
            monkeypatch.setenv(name, value)
            continue
        if args[0] == "unset":
            monkeypatch.delenv(args[1], raising=False)
            continue

        env_assignment = None
        if args[0].startswith("CU_ENDPOINT="):
            env_assignment = args.pop(0).split("=", 1)[1]
        assert args[0] in {"cu", "cu-cli"}, (
            f"Snippet:{snippet_id} has an unapproved external command: {' '.join(args)}"
        )
        if env_assignment is not None:
            monkeypatch.setenv("CU_ENDPOINT", env_assignment)

        result = runner.invoke(main, args[1:])

        assert result.exit_code == 0, (
            f"Snippet:{snippet_id} failed for {' '.join(args)}\n{result.output}"
        )


@pytest.mark.parametrize("snippet_id", _FAKE_ANALYZER_SNIPPET_IDS)
def test_fake_documented_analyzer_snippet_executes(
    snippet_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    class FakeAnalyzer:
        analyzer_id = "invoice_v1"
        base_analyzer_id = "prebuilt-document"
        status = "ready"
        created_at = None
        last_modified_at = None
        description = "fake analyzer"

        def as_dict(self):
            return {"analyzerId": self.analyzer_id, "status": self.status}

    class FakePoller:
        def result(self):
            return FakeAnalyzer()

    class FakeClient:
        def list_analyzers(self):
            return [FakeAnalyzer()]

        def get_analyzer(self, _analyzer_id):
            return FakeAnalyzer()

        def begin_create_analyzer(self, _analyzer_id, _body):
            return FakePoller()

        def delete_analyzer(self, _analyzer_id):
            return None

    monkeypatch.chdir(tmp_path)
    (tmp_path / "invoice.pdf").write_bytes(b"%PDF-1.4\n")
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "invoice.pdf").write_bytes(b"%PDF-1.4\n")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["profile", "set", "endpoint", "https://example.services.ai.azure.com/"],
    )
    assert result.exit_code == 0, result.output

    fake = FakeClient()
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.build_client", lambda *_args, **_kwargs: fake
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client", lambda *_args, **_kwargs: fake
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyzer.suggest_schema_payload_from_sample",
        lambda **_kwargs: {
            "analyzerId": "invoice_v1",
            "baseAnalyzerId": "prebuilt-document",
            "fieldSchema": {"fields": {}},
        },
    )

    def fake_result(_client, job):
        return job, AnalysisResult(
            contents=[DocumentContent(markdown="# result\n")]
        )

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", fake_result)

    if snippet_id == "cu_cli_create_and_test_analyzer":
        result = runner.invoke(
            main, ["analyzer", "schema", "create", "--output-file", "schema.json"]
        )
        assert result.exit_code == 0, result.output

    for args in parse_cu_commands(_SNIPPETS[snippet_id]):
        result = runner.invoke(main, args, input="y\n")

        assert result.exit_code == 0, (
            f"Snippet:{snippet_id} failed for {' '.join(args)}\n{result.output}"
        )


@pytest.mark.parametrize("snippet_id", _FAKE_COPY_SNIPPET_IDS)
def test_fake_documented_copy_snippet_executes(
    snippet_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    endpoints = {
        "dev": "https://dev.services.ai.azure.com/",
        "prod": "https://prod.services.ai.azure.com/",
    }
    for profile_name, endpoint in endpoints.items():
        result = runner.invoke(main, ["profile", "create", profile_name])
        assert result.exit_code == 0, result.output
        result = runner.invoke(
            main,
            ["profile", "set", "endpoint", endpoint, "--name", profile_name],
        )
        assert result.exit_code == 0, result.output

    def fake_resource(selector, **_kwargs):
        name = "prod" if "prod" in selector else "dev"
        return azure_resources.ResolvedResource(
            arm_id=(
                "/subscriptions/fake/resourceGroups/rg/providers/"
                f"Microsoft.CognitiveServices/accounts/{name}"
            ),
            region="eastus",
            endpoint=endpoints[name],
            subscription_id="fake",
            resource_group="rg",
            account_name=name,
        )

    clients = {"dev": object(), "prod": object()}
    monkeypatch.setattr(azure_resources, "resolve_resource", fake_resource)
    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_resource",
        lambda resource, **_kwargs: clients[resource.account_name],
    )
    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_named_profile",
        lambda profile_name, **_kwargs: (
            clients[profile_name],
            endpoints[profile_name],
            "2025-11-01",
        ),
    )
    monkeypatch.setattr(
        analyzers_core,
        "get_copy_source_analyzer",
        lambda *_args, **_kwargs: SimpleNamespace(
            analyzer_id="invoice_v1", base_analyzer_id="prebuilt-document"
        ),
    )
    monkeypatch.setattr(
        analyzers_core, "collect_custom_dependencies", lambda _analyzer: []
    )
    copy_calls = []
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *args, **kwargs: copy_calls.append((args, kwargs)),
    )
    registered_resolver = analyzer_cmd.resolve_identifier

    def resolve_operation(identifier):
        if identifier == ANALYZER_COPY.operation:
            return analyzers_core.copy_analyzer
        return registered_resolver(identifier)

    monkeypatch.setattr(analyzer_cmd, "resolve_identifier", resolve_operation)

    commands = parse_cu_commands(_SNIPPETS[snippet_id])
    if snippet_id == "cu_cli_copy_analyzer_with_resources":
        replacements = iter(("dev-resource", "prod-resource"))
        commands = [[
            next(replacements)
            if token == "<endpoint-resource-name-or-arm-id>"
            else token
            for token in command
        ] for command in commands]

    for args in commands:
        result = runner.invoke(main, args)
        assert result.exit_code == 0, (
            f"Snippet:{snippet_id} failed for {' '.join(args)}\n{result.output}"
        )

    assert len(copy_calls) == 1
    assert copy_calls[0][1]["target_client"] is clients["prod"]