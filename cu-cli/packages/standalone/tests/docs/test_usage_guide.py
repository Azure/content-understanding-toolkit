# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tested source for the code blocks in cu-cli/docs/usage-guide.md, in document order."""

from __future__ import annotations

import copy
from importlib.metadata import version
import json
from pathlib import Path
import re
from types import SimpleNamespace

from click import unstyle
import pytest
import yaml

from cu_cli.commands.infra import AzureAccount
from cu_cli.profile import Profile, ProfileStore
from support.fake_analyzers import LocalAnalyzers
from support.recording import PLACEHOLDER_ENDPOINT, cassette_path, mode, use_cassette
from support.snippets import record_external, record_output, run_command as _run

_ACCOUNT = AzureAccount(subscription_id="sub-id", subscription_name="Development", tenant_id="tenant-id")
_WARNING_FREE_SCHEMA = {
    "analyzerId": "invoice_v1",
    "baseAnalyzerId": "prebuilt-document",
    "models": {"completion": "gpt-5.2"},
    "fieldSchema": {
        "fields": {
            "InvoiceNumber": {
                "type": "string",
                "method": "extract",
                "description": "Invoice number printed on the document.",
            }
        }
    },
}


def _read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class _Defaults:
    def __init__(self, model_deployments):
        self.model_deployments = dict(model_deployments)

    def as_dict(self):
        return {"modelDeployments": dict(self.model_deployments)}


class _DefaultsService:
    """Applies defaults updates with the service's merge-patch semantics."""

    def __init__(self, existing):
        self._existing = dict(existing)
        self.updated = None

    def get_defaults(self):
        return _Defaults(self._existing)

    def update_defaults(self, *, model_deployments):
        self.updated = dict(model_deployments)
        for model, deployment in model_deployments.items():
            if deployment is None:
                self._existing.pop(model, None)
            else:
                self._existing[model] = deployment
        return _Defaults(self._existing)


@pytest.fixture
def resolved_endpoints(monkeypatch, azure_login):
    from cu_cli.client import resolve
    from cu_cli.commands import analyzer as analyzer_commands

    endpoints = []
    build_client = analyzer_commands.build_client

    def record_endpoint(profile, **overrides):
        endpoints.append(resolve(profile, **overrides).endpoint)
        return build_client(profile, **overrides)

    monkeypatch.setattr(analyzer_commands, "build_client", record_endpoint)
    return endpoints


@pytest.fixture
def analyzer_copies(monkeypatch):
    """Resolve profile endpoints to ARM metadata offline and capture the copy operation."""
    from cu_cli.commands import analyzer as analyzer_commands
    from cu_cli.core import azure_resources
    from cu_cli_core.command_spec import ANALYZER_COPY

    def resolve_resource(selector, *, subscription_id=None, resource_group=None, **_options):
        account = selector.split("://")[-1].split(".", 1)[0]
        subscription = subscription_id or "active-subscription"
        group = resource_group or "test-rg"
        return azure_resources.ResolvedResource(
            arm_id=f"/subscriptions/{subscription}/resourceGroups/{group}/providers/"
            f"Microsoft.CognitiveServices/accounts/{account}",
            region="eastus",
            endpoint=selector,
            subscription_id=subscription,
            resource_group=group,
            account_name=account,
        )

    copies = []
    resolve_identifier = analyzer_commands.resolve_identifier

    def resolve_operation(identifier):
        if identifier == ANALYZER_COPY.operation:
            return lambda *args, **options: copies.append((args, options))
        return resolve_identifier(identifier)

    monkeypatch.setattr(azure_resources, "resolve_resource", resolve_resource)
    monkeypatch.setattr(analyzer_commands, "resolve_identifier", resolve_operation)
    return copies


def test_named_profiles_and_resolution_precedence(resolved_endpoints, monkeypatch):
    monkeypatch.setattr("cu_cli.commands._options.console._width", 500)
    # region Snippet:profile_setup
    # region Snippet:profile_create_dev
    _run("""
        # Create an empty dev profile.
        cu profile create dev
    """)
    # endregion
    assert ProfileStore.load().has_name("dev")
    # region Snippet:profile_dev_endpoint
    _run("""
        # Save the dev resource endpoint without changing the active profile.
        cu profile set endpoint https://<dev-resource>.services.ai.azure.com/ --name dev
    """, placeholder_values={"dev-resource": "dev"})
    # endregion
    assert ProfileStore.load().get("endpoint", name="dev") == "https://dev.services.ai.azure.com/"
    # region Snippet:profile_create_prod
    _run("""
        # Create an empty prod profile.
        cu profile create prod
    """)
    # endregion
    assert ProfileStore.load().has_name("prod")
    # region Snippet:profile_prod_endpoint
    _run("""
        # Save a distinct resource endpoint on prod.
        cu profile set endpoint https://<prod-resource>.services.ai.azure.com/ --name prod
    """, placeholder_values={"prod-resource": "prod"})
    # endregion
    assert ProfileStore.load().get("endpoint", name="prod") == "https://prod.services.ai.azure.com/"
    # region Snippet:profile_activate_dev
    _run("""
        # Make dev the profile used when --profile is omitted.
        cu profile set-active dev
    """)
    # endregion
    assert ProfileStore.load().get_active_name() == "dev"
    # endregion
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_active
        result = _run("""
            # Use all effective settings from the active dev profile.
            # --info prints resolved, non-secret runtime settings to stderr before the request.
            # It is not a dry run; the analyzer list request still runs.
            cu analyzer list --info
        """)
        # endregion
    assert resolved_endpoints[-1] == "https://dev.services.ai.azure.com/"
    assert "endpoint:" not in result.stdout and "prebuilt-layout" in result.output
    context = "\n".join(result.stderr.splitlines()[:5])
    context = context.replace(str(Profile.load().path), "~/.azure/config")
    assert "settings: ~/.azure/config" in context
    context = context.replace(
        "https://dev.services.ai.azure.com/", "https://<dev-resource>.services.ai.azure.com/",
    )
    # region Snippet:runtime_info
    record_output(context)
    # endregion
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_prod
        _run("""
            # Use prod for this command only; dev remains active.
            cu analyzer list --profile prod
        """)
        # endregion
    assert resolved_endpoints[-1] == "https://prod.services.ai.azure.com/"
    assert ProfileStore.load().get_active_name() == "dev"
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_env
        _run(r"""
            # Use prod's remaining settings, but this endpoint wins for this invocation.
            CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
              cu analyzer list --profile prod --info
        """, placeholder_values={"temporary-resource": "temporary"})
        # endregion
    assert resolved_endpoints[-1] == "https://temporary.services.ai.azure.com/"
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_explicit
        _run(r"""
            # The explicit option wins over both CU_ENDPOINT and the selected profile.
            CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
              cu analyzer list \
                --profile prod \
                --endpoint https://<one-time-resource>.services.ai.azure.com/ \
                --info
        """, placeholder_values={"one-time-resource": "one-time", "temporary-resource": "temporary"})
        # endregion
    assert resolved_endpoints[-1] == "https://one-time.services.ai.azure.com/"
    assert ProfileStore.load().get_active_name() == "dev"


def test_profile_commands():
    for name in ("dev", "prod"):
        _run(f"cu profile create {name}")
        _run(f"cu profile set endpoint https://{name}.services.ai.azure.com/ --name {name}")
    _run("cu profile set-active dev")
    # region Snippet:profile_workflow
    # region Snippet:profile_show
    result = _run("""
        # Show all effective values for the active profile.
        cu profile show
    """)
    # endregion
    assert "CU CLI profile: dev (active)" in result.output
    # region Snippet:profile_get_endpoint
    result = _run("""
        # Print only the effective endpoint from the active profile.
        cu profile get endpoint
    """)
    # endregion
    assert result.stdout.strip() == "https://dev.services.ai.azure.com/"
    # region Snippet:profile_list
    result = _run("""
        # List saved profiles and identify the active profile.
        cu profile list
    """)
    # endregion
    assert "dev" in result.stdout and "prod" in result.stdout
    # region Snippet:profile_show_prod
    result = _run("""
        # Show prod without changing the active profile.
        cu profile show --name prod
    """)
    # endregion
    assert "https://prod.services.ai.azure.com/" in result.output
    assert ProfileStore.load().get_active_name() == "dev"
    # endregion
    # region Snippet:profile_preview
    _run("""
        # Save a preview API version on dev without changing the active profile.
        cu profile set api_version 2026-06-01-preview --name dev
    """)
    # endregion
    assert ProfileStore.load().get("api_version", name="dev") == "2026-06-01-preview"
    # region Snippet:profile_copy_cleanup
    # region Snippet:profile_copy
    _run("""
        # Create test as an independent copy of dev.
        cu profile copy dev test
    """)
    # endregion
    assert ProfileStore.load().get("endpoint", name="test") == "https://dev.services.ai.azure.com/"
    # region Snippet:profile_rename
    _run("""
        # Rename test and its saved values to staging.
        cu profile rename test staging
    """)
    # endregion
    assert not ProfileStore.load().has_name("test")
    assert ProfileStore.load().get("endpoint", name="staging") == "https://dev.services.ai.azure.com/"
    # region Snippet:profile_delete
    _run("""
        # Delete the inactive staging profile; this does not delete an Azure resource.
        cu profile delete staging --yes
    """)
    # endregion
    assert not ProfileStore.load().has_name("staging")
    # endregion


def test_inspect_live_deployments(monkeypatch):
    _run("cu profile set endpoint https://dev.services.ai.azure.com/")
    inspected = []
    monkeypatch.setattr(
        "cu_cli.commands.profile_cmd._live_foundry_deployments",
        lambda profile: inspected.append(profile.endpoint) or {"deployment=completion": "gpt-5.2"},
    )
    settings = Profile.load().path
    saved = settings.read_bytes()
    # region Snippet:profile_deployments
    result = _run("cu profile show --deployments --time")
    # endregion
    assert inspected == ["https://dev.services.ai.azure.com/"]
    assert "gpt-5.2" in result.stdout and "Total command time:" in result.stderr
    assert settings.read_bytes() == saved


def test_authentication_settings():
    # region Snippet:login_authentication
    # region Snippet:azure_login
    record_external("""
        # Sign in for the default login authentication mode.
        az login
    """, reason="Interactive Azure sign-in is never run by tests.")
    # endregion
    # region Snippet:profile_login
    _run("""
        # Login authentication is the default; this command selects it explicitly.
        cu profile set auth_mode login
    """)
    # endregion
    assert ProfileStore.load().get("auth_mode") == "login"
    # endregion
    # region Snippet:profile_key
    _run("""
        # Save a resource key on the active profile and select key authentication.
        cu profile set api_key <key>
    """, placeholder_values={"key": "offline-test-key"})
    # endregion
    assert ProfileStore.load().get("api_key") == "offline-test-key"
    assert ProfileStore.load().get("auth_mode") == "key"
    # region Snippet:profile_unset_key
    _run("""
        # Remove the saved key and return this profile to login authentication.
        cu profile unset api_key
    """)
    # endregion
    assert ProfileStore.load().get("api_key") is None
    assert ProfileStore.load().get("auth_mode") == "login"


def test_inspect_environment_overrides(monkeypatch):
    monkeypatch.setenv("CU_ENDPOINT", "https://temporary.services.ai.azure.com/")
    monkeypatch.setenv("CU_API_KEY", "offline-test-key")
    # region Snippet:environment_inspection
    # region Snippet:env_list
    result = _run("""
        # List set, recognized environment overrides in a table.
        cu env-var list
    """)
    # endregion
    assert "CU_ENDPOINT" in result.output and "offline-test-key" not in result.output
    # region Snippet:env_json
    result = _run("""
        # Emit the same set of overrides as machine-readable JSON.
        cu env-var list --json
    """)
    # endregion
    assert any(item["name"] == "CU_ENDPOINT" for item in json.loads(result.stdout))
    assert "offline-test-key" not in result.stdout
    # endregion


def test_temporary_endpoint_override(resolved_endpoints):
    _run("cu profile set endpoint https://saved.services.ai.azure.com/")
    with use_cassette("analyzer_list"):
        # region Snippet:env_override_bash
        result = _run(r"""
            # Temporarily override only the endpoint; other values still resolve normally.
            # Use the active profile's other settings and print the effective runtime context.
            # Preserve the previous environment after the command.
            CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
              cu analyzer list --info
        """, placeholder_values={"temporary-resource": "temporary"})
        # endregion
    assert resolved_endpoints[-1] == "https://temporary.services.ai.azure.com/"
    assert "https://temporary.services.ai.azure.com/" in result.stderr
    with use_cassette("analyzer_list"):
        # region Snippet:env_override_powershell
        result = _run("""
            # Temporarily override only the endpoint; other values still resolve normally.
            # Use the active profile's other settings and print the effective runtime context.
            # Preserve the previous environment after the command.
            $previous_CU_ENDPOINT = $env:CU_ENDPOINT
            $env:CU_ENDPOINT = "https://<temporary-resource>.services.ai.azure.com/"
            try {
              cu analyzer list --info
            } finally {
              $env:CU_ENDPOINT = $previous_CU_ENDPOINT
            }
        """, language="powershell", placeholder_values={"temporary-resource": "temporary"})
        # endregion
    assert resolved_endpoints[-1] == "https://temporary.services.ai.azure.com/"
    assert ProfileStore.load().get("endpoint") == "https://saved.services.ai.azure.com/"


def test_import_remote_defaults_into_profiles(monkeypatch):
    _run("cu profile set endpoint https://default.services.ai.azure.com/")
    _run("cu profile create dev")
    _run("cu profile set endpoint https://dev.services.ai.azure.com/ --name dev")
    monkeypatch.setenv("CU_ENDPOINT", "https://environment.services.ai.azure.com/")
    remote = _Defaults({"gpt-5.2": "gpt-prod", "text-embedding-3-large": "embedding-prod"})
    requests = []

    def build_client(profile, **overrides):
        requests.append((profile.endpoint, overrides.get("api_key_override")))
        return SimpleNamespace(get_defaults=lambda: remote)

    monkeypatch.setattr("cu_cli.commands.profile_cmd.build_client", build_client)
    # region Snippet:profile_sync
    _run("""
        # Import remote defaults into the active CU CLI profile.
        cu profile sync-defaults
    """)
    # endregion
    assert requests[-1] == ("https://default.services.ai.azure.com/", None)
    assert ProfileStore.load().get("model_deployments.gpt-5.2") == "gpt-prod"
    # region Snippet:profile_sync_named
    _run("""
        # Import remote defaults into dev without changing the active profile.
        cu profile sync-defaults --name dev
    """)
    # endregion
    assert requests[-1] == ("https://dev.services.ai.azure.com/", None)
    assert ProfileStore.load().get("model_deployments.gpt-5.2", name="dev") == "gpt-prod"
    assert ProfileStore.load().get_active_name() == "default"
    # region Snippet:profile_sync_auth
    result = _run(
        "cu profile sync-defaults --name dev --auth-mode key --api-key <key> --time",
        placeholder_values={"key": "offline-test-key"},
    )
    # endregion
    assert requests[-1] == ("https://dev.services.ai.azure.com/", "offline-test-key")
    assert "Total command time:" in result.stderr and "offline-test-key" not in result.output


def test_save_model_deployment_mappings():
    # region Snippet:configure_model_mappings
    # region Snippet:profile_completion_model
    _run("""
        # Replace my-gpt-52-deployment with the completion deployment name on your resource.
        cu profile set model_deployments.gpt-5.2 my-gpt-52-deployment
    """)
    # endregion
    assert ProfileStore.load().get("model_deployments.gpt-5.2") == "my-gpt-52-deployment"
    # region Snippet:profile_embedding_model
    _run("""
        # Replace my-embedding-deployment with your embeddings deployment name.
        cu profile set model_deployments.text-embedding-3-large my-embedding-deployment
    """)
    # endregion
    assert ProfileStore.load().get("model_deployments.text-embedding-3-large") == "my-embedding-deployment"
    # endregion


def test_generate_infrastructure(monkeypatch):
    wizards: list[dict] = []
    subscriptions: list[str | None] = []
    monkeypatch.setattr(
        "cu_cli.commands.infra._check_az_subscription",
        lambda subscription=None: subscriptions.append(subscription) or _ACCOUNT,
    )
    monkeypatch.setattr(
        "cu_cli.commands.infra.run_wizard",
        lambda target, **options: wizards.append({"target": target, **options}),
    )
    # region Snippet:infra_generate
    result = _run("cu infra generate")
    # endregion
    assert wizards[-1]["target"] == Path("provision").resolve()
    assert wizards[-1]["interactive"] is False and wizards[-1]["models"] is None
    assert wizards[-1]["subscription_id"] == "sub-id" and "cu infra generate" in result.output
    # region Snippet:infra_custom
    _run(r"""
        cu infra generate --output-dir infra --environment dev-01 --location westus3 --subscription Development \
          --api-version 2026-06-01-preview \
          --models "gpt-5.2, text-embedding-3-large" \
          --foundry-prefix contoso-cu \
          --assign-roles false \
          --force
    """)
    # endregion
    assert subscriptions[-1] == "Development"
    assert wizards[-1]["target"] == Path("infra").resolve()
    assert wizards[-1]["env"] == "dev-01" and wizards[-1]["location"] == "westus3"
    assert wizards[-1]["models"] == ["gpt-5.2", "text-embedding-3-large"]
    assert wizards[-1]["foundry_account_prefix"] == "contoso-cu"
    assert wizards[-1]["assign_roles"] is False and wizards[-1]["force"] is True


def test_analyze_local_file(cloud_profile, sample_invoice):
    with use_cassette("analyze_single"):
        # region Snippet:analyze_layout
        result = _run("""
            # Generate Markdown from the analyzer result with the CU SDK's to_llm_input().
            # This is a billed service call; Markdown is written to standard output.
            cu analyze sample_invoice.pdf --analyzer prebuilt-layout
        """)
        # endregion
    assert result.stdout.startswith("---")
    assert "mimeType:" in result.stdout and "<!-- InputPageNumber:" in result.stdout


def test_analyze_with_profile_default(cloud_profile, sample_invoice):
    # region Snippet:analyze_with_profile_default
    # region Snippet:profile_default_analyzer
    _run("""
        # Save the default analyzer on the active profile.
        cu profile set default_analyzer prebuilt-layout
    """)
    # endregion
    assert ProfileStore.load().get("default_analyzer") == "prebuilt-layout"
    with use_cassette("analyze_single"):
        # region Snippet:analyze_default
        result = _run("""
            # Analyze one file using the saved default analyzer.
            cu analyze sample_invoice.pdf --json
        """)
        # endregion
    assert json.loads(result.stdout)["result"]["analyzerId"] == "prebuilt-layout"
    # endregion


def test_output_formats(cloud_profile, sample_invoice):
    with use_cassette("analyze_single"):
        # region Snippet:analyze_json
        result = _run("""
            # Print the complete structured result as JSON to the terminal.
            cu analyze sample_invoice.pdf --analyzer prebuilt-layout --json
        """)
        # endregion
    assert json.loads(result.stdout)["result"]["contents"][0]["markdown"]
    with use_cassette("analyze_single"):
        # region Snippet:analyze_markdown_file
        _run("""
            # Save Markdown instead of printing it; parent directories are created.
            cu analyze sample_invoice.pdf --analyzer prebuilt-layout --output-file results/invoice.md
        """)
        # endregion
    assert "<!-- InputPageNumber:" in Path("results/invoice.md").read_text(encoding="utf-8")
    with use_cassette("analyze_single"):
        # region Snippet:analyze_json_file
        _run("""
            # Save structured JSON instead of printing it.
            cu analyze sample_invoice.pdf --analyzer prebuilt-layout --json --output-file results/invoice.json
        """)
        # endregion
    assert _read_json("results/invoice.json")["result"]["analyzerId"] == "prebuilt-layout"


def test_analyze_public_video_url(cloud_profile):
    with use_cassette("analyze_public_video_url"):
        # region Snippet:analyze_video_url
        result = _run(r"""
            cu analyze --url https://github.com/Azure-Samples/azure-ai-content-understanding-assets/raw/refs/heads/main/videos/sdk_samples/FlightSimulator.mp4 \
              --analyzer prebuilt-videoSearch \
              --json
        """)
        # endregion
    contents = json.loads(result.stdout)["result"]["contents"]
    assert contents and all(content["kind"] == "audioVisual" for content in contents)
    assert any(content["endTimeMs"] > content["startTimeMs"] for content in contents)


def test_analyze_sas_url_and_preview_remote_inputs(cloud_profile, monkeypatch):
    recording = yaml.safe_load(cassette_path("analyze_public_video_url").read_text(encoding="utf-8"))
    response = json.loads(recording["interactions"][-1]["response"]["body"]["string"])
    sent = []

    def analyze_remote(_client, job):
        sent.append(job.input_url)
        return job, copy.deepcopy(response if job.output_format == "json" else response["result"])

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", analyze_remote)
    sas_token = "sv=2026-01-01&sp=r&sig=a%2Bb%2Fc%3D"
    # region Snippet:analyze_sas_url
    result = _run(r"""
        cu analyze --url "https://<storage-account>.blob.core.windows.net/<container>/<blob>?<sas-token>" \
          --analyzer prebuilt-videoSearch \
          --json
    """, placeholder_values={
        "storage-account": "cuclitest", "container": "samples", "blob": "video.mp4",
        "sas-token": sas_token,
    })
    # endregion
    assert sent == [f"https://cuclitest.blob.core.windows.net/samples/video.mp4?{sas_token}"]
    assert "a%2Bb%2Fc%3D" not in result.output
    # region Snippet:analyze_urls_preview
    result = _run(r"""
        cu analyze --url https://github.com/Azure-Samples/azure-ai-content-understanding-assets/raw/refs/heads/main/document/invoice.pdf \
          --url https://github.com/Azure-Samples/azure-ai-content-understanding-assets/raw/refs/heads/main/document/receipt.png \
          --output-dir results \
          --analyzer prebuilt-layout \
          --dry-run
    """)
    # endregion
    assert len(sent) == 1 and not Path("results").exists()
    assert "2 remote size(s) unavailable" in unstyle(result.output)


def test_select_multiple_local_inputs(copy_invoice, monkeypatch):
    from cu_cli_core import input_planning

    for name in (
        "invoice one.pdf", "invoice two.pdf", "unselected.pdf", "my_incoming_dir/first.pdf",
        "my_archive_dir/second.pdf", "my_incoming_dir/nested/excluded.pdf",
    ):
        copy_invoice(name)
    Path("my_incoming_dir/excluded.txt").write_text("not a PDF", encoding="utf-8")
    selections = []
    plan_inputs = input_planning.plan_inputs

    def capture_selection(**options):
        plan = plan_inputs(**options)
        selections.append({item.path for item in plan.inputs})
        return plan

    monkeypatch.setattr(input_planning, "plan_inputs", capture_selection)
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("previews must not create a service client"),
    )
    # region Snippet:analyze_files_preview
    result = _run(r"""
        cu analyze --file "invoice one.pdf" --file "invoice two.pdf" --analyzer prebuilt-layout \
          --output-dir selected-results \
          --json \
          --dry-run
    """)
    # endregion
    assert selections[-1] == {Path("invoice one.pdf").resolve(), Path("invoice two.pdf").resolve()}
    assert "Selected: 2 input(s)" in result.output and not Path("selected-results").exists()
    # region Snippet:analyze_sources_preview
    result = _run(r"""
        cu analyze --source my_incoming_dir --source my_archive_dir --pattern "*.pdf" --analyzer prebuilt-layout \
          --output-dir combined-results \
          --dry-run
    """)
    # endregion
    assert selections[-1] == {
        Path("my_incoming_dir/first.pdf").resolve(), Path("my_archive_dir/second.pdf").resolve(),
    }
    assert "Selected: 2 input(s)" in result.output and not Path("combined-results").exists()


def test_analyze_matching_files(cloud_profile, copy_invoice):
    copy_invoice("my_document_dir/sample_invoice.pdf")
    Path("my_document_dir/notes.txt").write_text("not matched by the PDF pattern", encoding="utf-8")
    with use_cassette("analyze_batch"):
        # region Snippet:analyze_pattern
        _run("""
            # Analyze only matching files directly inside my_document_dir.
            cu analyze --source my_document_dir --pattern "*.pdf" -a prebuilt-layout --output-dir results
        """)
        # endregion
    assert list(Path("results").rglob("*.result.*")) == [Path("results/sample_invoice.pdf.result.md")]


def test_analyze_directory_recursively(cloud_profile, copy_invoice):
    sample = copy_invoice("my_document_dir/nested/sample_invoice.pdf")
    Path("my_document_dir/notes.txt").write_text("not matched by the PDF pattern", encoding="utf-8")
    with use_cassette("analyze_batch"):
        # region Snippet:analyze_recursive
        _run(r"""
            # Quote the pattern so CU CLI, rather than the shell, applies it.
            cu analyze --source my_document_dir --pattern "*.pdf" --recursive --analyzer prebuilt-layout \
              --output-dir recursive-results
        """)
        # endregion
    output = Path("recursive-results/nested/sample_invoice.pdf.result.md")
    assert list(Path("recursive-results").rglob("*.result.*")) == [output]
    # region Snippet:output_mapping
    record_output(f"{sample.as_posix()}\n  -> {output.as_posix()}")
    # endregion


def test_analyze_directory_argument(cloud_profile, copy_invoice):
    copy_invoice("my_document_dir/sample_invoice.pdf")
    with use_cassette("analyze_batch"):
        # region Snippet:analyze_directory
        _run("cu analyze my_document_dir --analyzer prebuilt-layout --output-dir out")
        # endregion
    assert list(Path("out").rglob("*.result.*")) == [Path("out/sample_invoice.pdf.result.md")]


def test_preview_batch_without_service_calls(copy_invoice, monkeypatch):
    copy_invoice("my_document_dir/sample_invoice.pdf")
    Path("my_document_dir/.DS_Store").write_text("metadata", encoding="utf-8")
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: pytest.fail("dry runs must not create a service client"),
    )
    # region Snippet:analyze_dry_run
    result = _run(r"""
        # Preview the discovered files and output mappings without service calls.
        cu analyze --source my_document_dir --analyzer prebuilt-layout --output-dir results \
          --report-file report.json \
          --dry-run
    """)
    # endregion
    assert "Skipped during discovery: 1" in result.output
    assert ".DS_Store:hiddenfileskipped" in "".join(result.output.split())
    assert not Path("results").exists() and not Path("report.json").exists()


def test_existing_output_policies(cloud_profile, sample_invoice):
    _run("cu profile set default_analyzer prebuilt-layout")
    with use_cassette("analyze_single"):
        _run("cu analyze sample_invoice.pdf --json --output-file result.json")
    output = Path("result.json")
    content, modified = output.read_bytes(), output.stat().st_mtime_ns
    with use_cassette("analyze_single") as cassette:
        # region Snippet:analyze_skip
        _run("cu analyze sample_invoice.pdf --json --output-file result.json --on-existing skip")
        # endregion
    assert mode() != "playback" or cassette.play_count == 0
    assert output.read_bytes() == content and output.stat().st_mtime_ns == modified
    with use_cassette("analyze_single") as cassette:
        # region Snippet:analyze_reanalyze
        _run("cu analyze sample_invoice.pdf --json --output-file result.json --on-existing reanalyze")
        # endregion
    assert mode() != "playback" or cassette.play_count > 0
    assert _read_json("result.json")["result"]["analyzerId"] == "prebuilt-layout"


def test_recursive_batch_report(cloud_profile, copy_invoice):
    copy_invoice("my_document_dir/nested/sample_invoice.pdf")
    Path("my_document_dir/notes.txt").write_text("not matched by the PDF pattern", encoding="utf-8")
    with use_cassette("analyze_batch"):
        # region Snippet:analyze_recursive_report
        _run(r"""
            # Analyze recursively, save one Markdown result per input, and record all statuses in JSON.
            # Process up to eight batch jobs concurrently instead of the default four.
            cu analyze --source my_document_dir --pattern "*.pdf" --recursive --analyzer prebuilt-layout \
              --output-dir batch-results \
              --report-file run-report.json \
              --yes \
              --concurrency 8
        """)
        # endregion
    output = Path("batch-results/nested/sample_invoice.pdf.result.md")
    assert list(Path("batch-results").rglob("*.result.*")) == [output]
    counts = _read_json("run-report.json")["counts"]
    assert counts["succeeded"] == 1 and counts["failed"] == 0


def test_track_elapsed_time(cloud_profile, sample_invoice):
    with use_cassette("analyze_single"):
        # region Snippet:analyze_llm_input
        result = _run("""
            # Print service-call and total elapsed time for the analysis.
            cu analyze sample_invoice.pdf --analyzer prebuilt-layout --llm-input --time
        """)
        # endregion
    assert "<!-- InputPageNumber:" in result.stdout
    timings = [line for line in result.stderr.splitlines() if "time:" in line]
    assert len(timings) == 2
    # region Snippet:analysis_timing
    record_output(re.sub(r"\d+\.\d+s", "<seconds>s", "\n".join(timings)))
    # endregion


def test_inspect_service_usage(cloud_profile, sample_invoice):
    with use_cassette("analyze_single"):
        # region Snippet:analyze_usage
        result = _run("cu analyze sample_invoice.pdf --analyzer prebuilt-layout --json --usage --time")
        # endregion
    usage = result.stderr.split("Usage:", 1)[1]
    reported, _end = json.JSONDecoder().raw_decode(usage[usage.index("{"):])
    assert reported and reported == json.loads(result.stdout)["usage"]
    assert len([line for line in result.stderr.splitlines() if "time:" in line]) == 2


def test_schema_templates():
    # region Snippet:schema_templates
    # region Snippet:schema_template
    _run("""
        # Default to a document field-extraction schema.
        cu analyzer schema create --output-file schema.json
    """)
    # endregion
    schema = _read_json("schema.json")
    assert schema["apiVersion"] == "2025-11-01" and "example_string_field" in schema["fieldSchema"]["fields"]
    # region Snippet:schema_image
    _run("""
        # Generate an image field-extraction schema instead of the document default.
        cu analyzer schema create --modality image --output-file image-schema.json
    """)
    # endregion
    assert _read_json("image-schema.json")["baseAnalyzerId"] == "prebuilt-image"
    # region Snippet:schema_classification
    _run("""
        # Generate a classification schema instead of a field-extraction schema.
        cu analyzer schema create --output-file classify.json --type classification
    """)
    # endregion
    categories = _read_json("classify.json")["config"]["contentCategories"]
    assert "invoice" in categories
    assert all(item.get("description") and "analyzerId" not in item for item in categories.values())
    # endregion


def test_schema_from_sample(cloud_profile, sample_invoice):
    with use_cassette("schema_suggest"):
        # region Snippet:schema_from_sample
        _run("""
            # Generate a schema from a representative document.
            cu analyzer schema create --name invoice_v1 --from-sample sample_invoice.pdf --output-file schema.json
        """)
        # endregion
    schema = _read_json("schema.json")
    assert schema["analyzerId"] == "invoice_v1" and schema["fieldSchema"]["fields"]


def test_schema_base_override():
    # region Snippet:schema_base
    _run("cu analyzer schema create --base prebuilt-document --name invoice_v1 --output-file schema.json")
    # endregion
    schema = _read_json("schema.json")
    assert schema["baseAnalyzerId"] == "prebuilt-document" and schema["analyzerId"] == "invoice_v1"


def test_schema_modalities():
    # region Snippet:schema_modalities
    # region Snippet:schema_document
    _run("cu analyzer schema create --modality document --output-file document-schema.json")
    # endregion
    assert _read_json("document-schema.json")["baseAnalyzerId"] == "prebuilt-document"
    # region Snippet:schema_audio
    _run("cu analyzer schema create --modality audio --output-file audio-schema.json")
    # endregion
    assert _read_json("audio-schema.json")["baseAnalyzerId"] == "prebuilt-audio"
    # region Snippet:schema_video
    _run("cu analyzer schema create --modality video --output-file video-schema.json")
    # endregion
    assert _read_json("video-schema.json")["baseAnalyzerId"] == "prebuilt-video"
    # endregion
    for modality in ("document", "audio", "video"):
        validation = _run(f"cu analyzer validate --schema {modality}-schema.json --spec")
        assert validation.exit_code == 0, validation.output


def test_validate_schemas(monkeypatch):
    created = _run("cu analyzer schema create --base prebuilt-document --name invoice_v1 --output-file schema.json")
    assert created.exit_code == 0, created.output
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client",
        lambda *_args, **_kwargs: pytest.fail("local validation must not create a service client"),
    )
    # region Snippet:schema_validation
    # region Snippet:schema_validate
    result = _run("""
        # Validate the local schema shape.
        cu analyzer validate schema.json
    """)
    # endregion
    assert "schema.json" in result.output
    # region Snippet:schema_validate_spec
    result = _run("""
        # Also validate rules from the selected Content Understanding API specification.
        cu analyzer validate --schema schema.json --spec --json
    """)
    # endregion
    assert json.loads(result.stdout)["ok"] is True
    # endregion
    Path("schema.json").write_text(json.dumps(_WARNING_FREE_SCHEMA), encoding="utf-8")
    # region Snippet:schema_validate_strict
    result = _run("cu analyzer validate schema.json --strict --spec --json")
    # endregion
    payload = json.loads(result.stdout)
    assert payload["ok"] is True and payload["strict"] is True
    assert payload["errors"] == [] and payload["warnings"] == []


def test_create_and_test_analyzer(sample_invoice, monkeypatch):
    schema = _run("cu analyzer schema create --base prebuilt-document --name invoice_v1 --output-file schema.json")
    assert schema.exit_code == 0, schema.output
    created: dict[str, dict] = {}
    tested: list[str] = []

    def analyze(_client, job):
        tested.append(job.analyzer_id)
        return job, {"analyzerId": job.analyzer_id, "contents": []}

    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client", lambda *_args, **_kwargs: LocalAnalyzers(None, created),
    )
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", analyze)
    # region Snippet:analyzer_evaluation
    # region Snippet:analyzer_create
    _run("""
        # Review and update the generated schema for your extraction requirements,
        # then create the analyzer.
        cu analyzer create --name invoice_v1 --schema schema.json
    """)
    # endregion
    assert created["invoice_v1"]["fieldSchema"] == _read_json("schema.json")["fieldSchema"]
    # region Snippet:analyzer_test_single
    result = _run("""
        # Run the analyzer against the sample and summarize whether fields were returned
        # and any confidence values supplied by the service. This is not an accuracy
        # benchmark and does not compare the result with labeled ground truth.
        cu analyzer test invoice_v1 sample_invoice.pdf
    """)
    # endregion
    assert "1 ok / 0 failed / 1 total" in result.output and tested == ["invoice_v1"]
    # endregion


def test_preview_and_run_analyzer_tests(copy_invoice, monkeypatch):
    from cu_cli_core import input_planning

    copy_invoice("my_sample_dir/sample_invoice.pdf")
    copy_invoice("my_sample_dir/nested/sample_invoice.pdf")
    tested, selections, clients = [], [], []
    plan_inputs = input_planning.plan_inputs

    def capture_selection(**options):
        plan = plan_inputs(**options)
        selections.append({item.path for item in plan.inputs})
        return plan

    def analyze(_client, job):
        tested.append(Path(job.input_ref).relative_to(Path.cwd()).as_posix())
        return job, SimpleNamespace(contents=[])

    monkeypatch.setattr(input_planning, "plan_inputs", capture_selection)
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client", lambda *_args, **_kwargs: clients.append(object()) or clients[-1],
    )
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", analyze)
    # region Snippet:analyzer_test_preview
    result = _run(r"""
        # Preview the matching samples without making service calls.
        cu analyzer test --name invoice_v1 --source my_sample_dir --pattern "*.pdf" --recursive \
          --dry-run
    """)
    # endregion
    assert "Found 2 inputs:" in result.output and "No service calls or files were written" in result.output
    assert tested == [] and clients == []
    # region Snippet:analyzer_test_batch
    _run(r"""
        # Test every matching sample in my_sample_dir, including nested PDFs,
        # and save one aggregate JSON report.
        cu analyzer test --name invoice_v1 --source my_sample_dir --pattern "*.pdf" --recursive \
          --concurrency 2 \
          --yes \
          --json \
          --output-file test-report.json
    """)
    # endregion
    assert set(tested) == {"my_sample_dir/sample_invoice.pdf", "my_sample_dir/nested/sample_invoice.pdf"}
    assert selections[-2] == selections[-1] and len(clients) == 1
    assert _read_json("test-report.json")["analyzerId"] == "invoice_v1"


def test_inspect_analyzers(cloud_profile, monkeypatch):
    from cu_cli.commands import analyzer as analyzer_commands

    definition = {"baseAnalyzerId": "prebuilt-document", "fieldSchema": {"fields": {}}}
    service_client = analyzer_commands._client
    monkeypatch.setattr(
        analyzer_commands, "_client",
        lambda *args, **kwargs: LocalAnalyzers(service_client(*args, **kwargs), {"invoice_v1": definition}),
    )
    # region Snippet:analyzer_management
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list
        result = _run("""
            # List analyzers available on the selected resource.
            cu analyzer list
        """)
        # endregion
    assert "Analyzers" in result.stderr and "analyzer(s)" in result.stderr
    # region Snippet:analyzer_show
    result = _run("""
        # Print one analyzer definition.
        cu analyzer show invoice_v1
    """)
    # endregion
    assert json.loads(result.stdout)["baseAnalyzerId"] == "prebuilt-document"
    # endregion
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_custom
        result = _run("cu analyzer list --json --kind custom --sort-by analyzerId")
        # endregion
    names = [item["analyzerId"] for item in json.loads(result.stdout)]
    assert names == sorted(names) and not any(name.startswith("prebuilt-") for name in names)


def test_copy_within_resource(cloud_profile, analyzer_copies, monkeypatch):
    from cu_cli.commands import analyzer as analyzer_commands

    client = object()
    monkeypatch.setattr(analyzer_commands, "_client", lambda *_args, **_kwargs: client)
    # region Snippet:analyzer_copy_same_resource
    _run("cu analyzer copy invoice_v1 invoice_v2")
    # endregion
    [(arguments, options)] = analyzer_copies
    assert arguments == (client, "invoice_v1", "invoice_v2")
    assert options["target_client"] is None and options["target_azure_resource_id"] is None


def test_copy_between_profiles(analyzer_copies, monkeypatch):
    from cu_cli.commands import analyzer as analyzer_commands
    from cu_cli.core import analyzers as analyzers_core

    for name in ("dev", "prod"):
        _run(f"cu profile create {name}")
        _run(f"cu profile set endpoint https://{name}.services.ai.azure.com/ --name {name}")
    endpoints = []
    monkeypatch.setattr(
        analyzer_commands, "build_client",
        lambda profile, **_options: endpoints.append(profile.endpoint) or object(),
    )
    monkeypatch.setattr(
        analyzers_core, "get_copy_source_analyzer",
        lambda *_args, **_kwargs: SimpleNamespace(config=SimpleNamespace(content_categories={})),
    )
    # region Snippet:analyzer_copy_profiles
    _run("""
        # Copy one analyzer between resources represented by saved CU CLI profiles.
        # The first positional ID is the existing analyzer on the dev resource.
        # The second positional ID is the analyzer to create on the prod resource.
        # --source-profile supplies the source endpoint and authentication.
        # --destination-profile supplies the destination endpoint and authentication.
        cu analyzer copy invoice_v1 invoice_v1 --source-profile dev --destination-profile prod
    """)
    # endregion
    [(_arguments, options)] = analyzer_copies
    assert options["target_azure_resource_id"].endswith("/accounts/prod")
    assert sorted(endpoints) == ["https://dev.services.ai.azure.com/", "https://prod.services.ai.azure.com/"]


def test_copy_between_discovered_resources(analyzer_copies, monkeypatch):
    from cu_cli.commands import analyzer as analyzer_commands
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    resources = {
        name: azure_resources.ResolvedResource(
            arm_id=f"/subscriptions/{subscription}/resourceGroups/rg/providers/"
            f"Microsoft.CognitiveServices/accounts/{name}",
            region=region,
            endpoint=f"https://{name}.services.ai.azure.com/",
            subscription_id=subscription,
            resource_group="rg",
            account_name=name,
        )
        for name, subscription, region in (("src", "S", "eastus"), ("tgt", "T", "westus"))
    }
    monkeypatch.setattr(azure_resources, "resolve_resource", lambda selector, **_: resources[selector])
    monkeypatch.setattr(analyzer_commands, "_client_from_resource", lambda resolved, **_: object())
    monkeypatch.setattr(
        analyzers_core, "get_copy_source_analyzer",
        lambda *_args, **_kwargs: SimpleNamespace(config=SimpleNamespace(content_categories={})),
    )
    # region Snippet:analyzer_copy_resources
    _run("""
        # Copy one analyzer using Azure resource discovery instead of saved profiles.
        # The first positional ID is the existing analyzer on the source resource.
        # The second positional ID is the analyzer to create on the destination resource.
        # --source-resource selects the source by name, endpoint, or ARM resource ID.
        # --destination-resource selects the destination using the same identifier forms.
        cu analyzer copy invoice_v1 invoice_v1 --source-resource <source-resource> --destination-resource <destination-resource>
    """, placeholder_values={"source-resource": "src", "destination-resource": "tgt"})
    # endregion
    [(_arguments, options)] = analyzer_copies
    assert options["source_azure_resource_id"] == resources["src"].arm_id
    assert options["target_azure_resource_id"] == resources["tgt"].arm_id


def test_delete_analyzer_after_confirmation(monkeypatch):
    created = {"invoice_v1": {"baseAnalyzerId": "prebuilt-document"}}
    monkeypatch.setattr(
        "cu_cli.commands.analyzer._client", lambda *_args, **_kwargs: LocalAnalyzers(None, created),
    )
    declined = _run("cu analyzer delete invoice_v1", input="n\n")
    assert declined.exit_code != 0 and "invoice_v1" in created
    # region Snippet:analyzer_delete
    result = _run("""
        # Delete a custom analyzer after confirmation.
        cu analyzer delete invoice_v1
    """, input="y\n")
    # endregion
    assert "Delete analyzer 'invoice_v1'?" in result.output and created == {}


def test_show_remote_defaults(cloud_profile):
    with use_cassette("defaults_get"):
        # region Snippet:defaults_show
        result = _run("""
            # Show the Content Understanding defaults configured on the resource.
            cu defaults show
        """)
        # endregion
    assert json.loads(result.stdout)["modelDeployments"]
    # region Snippet:defaults_json_output
    record_output(result.stdout, language="json")
    # endregion
    with use_cassette("defaults_get"):
        # region Snippet:defaults_table
        result = _run("""
            # Show the same remote mappings as a human-readable table.
            cu defaults show --table
        """)
        # endregion
    assert "Model" in result.stdout and "Deployment" in result.stdout


def test_update_remote_defaults(monkeypatch):
    remote = _DefaultsService({"unrelated": "keep"})
    monkeypatch.setattr("cu_cli.commands.defaults.build_client", lambda *_args, **_kwargs: remote)
    _run(f"cu profile set endpoint {PLACEHOLDER_ENDPOINT}")
    _run("cu profile set model_deployments.gpt-5.2 my-gpt-52-deployment")
    _run("cu profile set model_deployments.text-embedding-3-large my-embedding-deployment")
    # region Snippet:defaults_model
    _run("""
        # Replace custom-completion with a deployment name and set that remote mapping.
        cu defaults set --model gpt-5.2=custom-completion
    """)
    # endregion
    assert remote.updated["gpt-5.2"] == "custom-completion" and remote.updated["unrelated"] == "keep"
    # region Snippet:defaults_from_profile
    _run("""
        # Apply model mappings from the active CU CLI profile to the remote resource.
        cu defaults set --from-profile
    """)
    # endregion
    assert remote.updated["prebuilt-analyzer-completion"] == "my-gpt-52-deployment"
    assert remote.updated["unrelated"] == "keep"
    # region Snippet:defaults_replace
    result = _run(r"""
        cu defaults set --model gpt-5.2=custom-completion --model text-embedding-3-large=custom-embedding \
          --replace \
          --json
    """)
    # endregion
    assert remote.updated["unrelated"] is None
    mappings = json.loads(result.stdout)["modelDeployments"]
    assert "unrelated" not in mappings and mappings == remote.get_defaults().model_deployments


def test_check_readiness(cloud_profile):
    _run("cu profile create prod")
    _run("cu profile set endpoint https://prod.services.ai.azure.com/ --name prod")
    _run("cu profile set api_key playback-dummy-key --name prod")
    # region Snippet:diagnose_configuration
    with use_cassette("doctor"):
        # region Snippet:doctor
        result = _run("""
            # Check the active profile.
            cu doctor
        """)
        # endregion
    assert f"Microsoft Foundry resource: {PLACEHOLDER_ENDPOINT}" in result.output
    assert "Connected to the Microsoft Foundry resource." in result.output
    with use_cassette("doctor"):
        # region Snippet:doctor_named
        result = _run("""
            # Check prod without changing the active profile.
            cu doctor --profile prod
        """)
        # endregion
    assert "Microsoft Foundry resource: https://prod.services.ai.azure.com/" in result.output
    assert ProfileStore.load().get_active_name() == "default"
    # endregion


def test_apply_reviewed_mappings_as_defaults(monkeypatch):
    _run(f"cu profile set endpoint {PLACEHOLDER_ENDPOINT}")
    _run("cu profile set model_deployments.gpt-5.2 dep-gpt")
    _run("cu profile set model_deployments.text-embedding-3-large dep-emb")
    remote = _DefaultsService({})
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *_args, **_kwargs: remote)
    # region Snippet:doctor_fix_defaults
    result = _run("""
        # Apply reviewed local model mappings as remote Content Understanding defaults.
        cu doctor --fix-defaults
    """)
    # endregion
    assert "Content Understanding defaults updated" in result.output
    assert remote.updated["gpt-5.2"] == "dep-gpt"
    assert remote.updated["text-embedding-3-large"] == "dep-emb"


def test_help_overview():
    # region Snippet:cli_help_overview
    # region Snippet:cli_help
    result = _run("""
        # List top-level command groups and global options.
        cu --help
    """)
    # endregion
    assert "Usage:" in result.output
    # region Snippet:profile_help
    result = _run("""
        # Show how to save profile values, including supported keys and examples.
        cu profile --help
    """)
    # endregion
    assert "set-active" in result.output
    # region Snippet:copy_help
    result = _run("""
        # Show profile-based and Azure-discovery analyzer copy options.
        cu analyzer copy --help
    """)
    # endregion
    assert "--destination-profile" in result.output
    # endregion


def test_check_for_upgrade(monkeypatch):
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.fetch_latest_version_detailed", lambda **_: (version("cu-cli"), "ok"),
    )
    # region Snippet:upgrade_check
    result = _run("cu upgrade --check")
    # endregion
    assert "up to date" in result.output


def test_apply_upgrade(monkeypatch):
    class Provider:
        name = "private feed"
        release_notes_url = "https://example.test/releases"
        source_install_hint = "install privately"

        @staticmethod
        def pip_environment():
            return {"PIP_INDEX_URL": "https://credential@example.test/simple/"}

    installs = []
    monkeypatch.setattr("cu_cli.commands.upgrade.get_update_provider", lambda: Provider())
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.fetch_latest_version_detailed", lambda **_: ("9.9.9", "ok"),
    )
    monkeypatch.setattr(
        "cu_cli.commands.upgrade.subprocess.run",
        lambda args, *, env: installs.append((args, env)) or SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr("cu_cli.commands.upgrade.is_windows", lambda: False)
    # region Snippet:upgrade_apply
    result = _run("cu upgrade --yes")
    # endregion
    [(arguments, environment)] = installs
    assert arguments[-1] == "cu-cli==9.9.9"
    assert environment["PIP_INDEX_URL"].startswith("https://credential@")
    assert "private feed" in result.output
