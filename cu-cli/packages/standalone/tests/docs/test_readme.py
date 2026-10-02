# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Tested source for the code blocks in cu-cli/README.md, in document order."""

from __future__ import annotations

import copy
from importlib.metadata import entry_points, version
import json
from pathlib import Path
import shutil

import yaml

from cu_cli.profile import ProfileStore
from support.fake_analyzers import LocalAnalyzers
from support.recording import PLACEHOLDER_ENDPOINT, cassette_path, use_cassette
from support.snippets import record_external, run_command as _run


def _analyzer_ids(cassette: str) -> list[str]:
    recording = yaml.safe_load(cassette_path(cassette).read_text(encoding="utf-8"))
    body = json.loads(recording["interactions"][0]["response"]["body"]["string"])
    return [analyzer["analyzerId"] for analyzer in body["value"]]


def test_install_and_list_commands():
    # region Snippet:cli_installation
    # region Snippet:cli_install
    record_external(
        "python -m pip install cu-cli",
        reason="Installs the published distribution; release CI verifies the built wheels.",
    )
    # endregion
    # region Snippet:cli_version
    result = _run("cu --version")
    # endregion
    assert version("cu-cli") in result.output
    # region Snippet:cli_help
    result = _run("""
        # List top-level command groups and global options.
        cu --help
    """)
    # endregion
    assert all(group in result.output for group in ("analyze", "profile", "doctor"))
    # endregion


def test_macos_executable_name():
    # region Snippet:cu_cli_help
    result = _run("cu-cli --help")
    # endregion
    assert "Usage:" in result.output
    scripts = {entry.name: entry.value for entry in entry_points(group="console_scripts")}
    assert scripts["cu-cli"] == scripts["cu"]


def test_configure_login_authentication(azure_login):
    # region Snippet:configure_login
    # region Snippet:login_endpoint
    _run("""
        # Save the endpoint on the active profile.
        cu profile set endpoint https://<resource-name>.services.ai.azure.com/
    """, placeholder_values={"resource-name": "sanitized"})
    # endregion
    assert ProfileStore.load().get("endpoint") == PLACEHOLDER_ENDPOINT
    # region Snippet:profile_login
    _run("""
        # Login authentication is the default; this command selects it explicitly.
        cu profile set auth_mode login
    """)
    # endregion
    assert ProfileStore.load().get("auth_mode") == "login"
    # region Snippet:azure_login
    record_external("""
        # Sign in for the default login authentication mode.
        az login
    """, reason="Interactive sign-in; the azure_login fixture provides the signed-in identity.")
    # endregion
    with use_cassette("doctor"):
        # region Snippet:login_doctor
        result = _run("""
            # Check the active profile.
            cu doctor
        """)
        # endregion
    assert "Authentication: Microsoft Entra ID" in result.output
    assert "Connected to the Microsoft Foundry resource." in result.output
    # endregion


def test_configure_key_authentication():
    # region Snippet:configure_key
    # region Snippet:key_endpoint
    _run("""
        # Save the endpoint on the active profile.
        cu profile set endpoint https://<resource-name>.services.ai.azure.com/
    """, placeholder_values={"resource-name": "sanitized"})
    # endregion
    assert ProfileStore.load().get("endpoint") == PLACEHOLDER_ENDPOINT
    # region Snippet:profile_key
    _run("""
        # Save a resource key on the active profile and select key authentication.
        cu profile set api_key <key>
    """, placeholder_values={"key": "playback-dummy-key"})
    # endregion
    assert ProfileStore.load().get("auth_mode") == "key"
    with use_cassette("doctor"):
        # region Snippet:key_doctor
        result = _run("""
            # Check the active profile.
            cu doctor
        """)
        # endregion
    assert "Authentication: resource key" in result.output
    assert "Connected to the Microsoft Foundry resource." in result.output
    # endregion


def test_frontends_share_profile_settings(sample_invoice):
    _run("cu profile set api_key playback-dummy-key")
    # region Snippet:shared_frontend_profile
    # region Snippet:standalone_endpoint
    _run("""
        # Save the endpoint with the standalone frontend.
        cu profile set endpoint https://<resource-name>.services.ai.azure.com/
    """, placeholder_values={"resource-name": "sanitized"})
    # endregion
    assert ProfileStore.load().get("endpoint") == PLACEHOLDER_ENDPOINT
    with use_cassette("analyzer_list"):
        # region Snippet:az_analyzer_list
        analyzers = _run("""
            # Use the same default profile with the Azure CLI extension.
            az cu analyzer list --output table
        """)
        # endregion
    listed = sorted(analyzer["analyzerId"] for analyzer in analyzers)
    assert listed == sorted(_analyzer_ids("analyzer_list"))
    # region Snippet:az_default_analyzer
    _run("""
        # Change the default analyzer with the Azure CLI extension.
        az cu profile set --key default_analyzer --value prebuilt-layout
    """)
    # endregion
    assert ProfileStore.load().get("default_analyzer") == "prebuilt-layout"
    with use_cassette("analyze_single"):
        # region Snippet:standalone_analyze
        result = _run("""
            # Use that setting with the standalone frontend.
            cu analyze sample_invoice.pdf --json
        """)
        # endregion
    assert json.loads(result.stdout)["result"]["analyzerId"] == "prebuilt-layout"
    # endregion


def test_inline_analysis_with_preview_api(cloud_profile, sample_invoice):
    with use_cassette("analyze_inline_preview"):
        # region Snippet:analyze_inline
        result = _run(r"""
            cu analyze --inline --api-version 2026-06-01-preview sample_invoice.pdf --analyzer prebuilt-layout \
              --json
        """)
        # endregion
    content = json.loads(result.stdout)["result"]["contents"][0]
    assert content["kind"] == "document" and content["markdown"]


def test_list_prebuilt_analyzers(cloud_profile):
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_prebuilt
        result = _run("cu analyzer list --kind prebuilt")
        # endregion
    prebuilt = [name for name in _analyzer_ids("analyzer_list") if name.startswith("prebuilt-")]
    assert f"{len(prebuilt)} analyzer(s)" in result.output
    assert "prebuilt-layout" in result.output


def test_analyze_with_prebuilt_layout(cloud_profile, sample_invoice):
    # region Snippet:analyze_layout_options
    with use_cassette("analyze_single"):
        # region Snippet:analyze_layout
        result = _run("""
            # Generate Markdown from the analyzer result with the CU SDK's to_llm_input().
            # This is a billed service call; Markdown is written to standard output.
            cu analyze sample_invoice.pdf --analyzer prebuilt-layout
        """)
        # endregion
    assert result.stdout.startswith("---") and "<!-- InputPageNumber:" in result.stdout
    with use_cassette("analyze_single"):
        # region Snippet:analyze_layout_short
        short = _run("""
            # `-a` is the short form of `--analyzer`.
            cu analyze sample_invoice.pdf -a prebuilt-layout
        """)
        # endregion
    assert short.stdout == result.stdout
    # endregion


def test_analyze_remote_url_keeps_sas_private(cloud_profile, monkeypatch):
    recording = yaml.safe_load(cassette_path("analyze_public_video_url").read_text(encoding="utf-8"))
    response = json.loads(recording["interactions"][-1]["response"]["body"]["string"])
    sent = []

    def analyze_remote(_client, job):
        sent.append(job.input_url)
        return job, copy.deepcopy(response if job.output_format == "json" else response["result"])

    monkeypatch.setattr("cu_cli.commands.analyze._run_one", analyze_remote)
    # region Snippet:analyze_url
    result = _run("""
        cu analyze --url "https://storage.example.net/container/video.mp4?sv=<version>&sp=r&sig=<signature>" -a prebuilt-videoSearch
    """, placeholder_values={"version": "2026-01-01", "signature": "example"})
    # endregion
    assert sent == [
        "https://storage.example.net/container/video.mp4?sv=2026-01-01&sp=r&sig=example",
    ]
    assert "# Video:" in result.stdout and "\nWEBVTT\n" in result.stdout
    assert "sig=example" not in result.output


def test_analyze_invoice_fields(cloud_profile, sample_invoice):
    with use_cassette("analyze_prebuilt_invoice_json"):
        # region Snippet:analyze_invoice
        result = _run("cu analyze sample_invoice.pdf -a prebuilt-invoice --json")
        # endregion
    payload = json.loads(result.stdout)
    assert payload["result"]["analyzerId"] == "prebuilt-invoice"
    assert "AmountDue" in payload["result"]["contents"][0]["fields"]


def test_analyze_matching_files_in_directory(cloud_profile, sample_invoice):
    source = Path("my_document_dir")
    source.mkdir()
    shutil.move(sample_invoice, source / "invoice-01.pdf")
    (source / "notes.txt").write_text("not matched by the PDF pattern", encoding="utf-8")
    with use_cassette("analyze_batch"):
        # region Snippet:analyze_pattern
        _run("""
            # Analyze only matching files directly inside my_document_dir.
            cu analyze --source my_document_dir --pattern "*.pdf" -a prebuilt-layout --output-dir results
        """)
        # endregion
    assert [path.as_posix() for path in Path("results").rglob("*.result.*")] == [
        "results/invoice-01.pdf.result.md",
    ]


def test_show_defaults(cloud_profile):
    with use_cassette("defaults_get"):
        # region Snippet:defaults_show
        result = _run("""
            # Show the Content Understanding defaults configured on the resource.
            cu defaults show
        """)
        # endregion
    assert json.loads(result.stdout)["modelDeployments"]


def test_create_custom_analyzer(cloud_profile, sample_invoice, monkeypatch):
    from cu_cli.commands import analyzer as analyzer_commands

    created: dict[str, dict] = {}
    analyzed: list[str] = []
    service_client = analyzer_commands._client

    def analyze(_client, job):
        analyzed.append(job.analyzer_id)
        return job, {"analyzerId": job.analyzer_id, "contents": []}

    monkeypatch.setattr(
        analyzer_commands, "_client",
        lambda *args, **kwargs: LocalAnalyzers(service_client(*args, **kwargs), created),
    )
    monkeypatch.setattr(
        "cu_cli.commands.analyze.build_client",
        lambda *_args, **_kwargs: LocalAnalyzers(None, created),
    )
    monkeypatch.setattr("cu_cli.commands.analyze._run_one", analyze)
    # region Snippet:custom_analyzer_workflow
    with use_cassette("schema_suggest"):
        # region Snippet:schema_from_sample
        _run("""
            # Generate a schema from a representative document.
            cu analyzer schema create --name invoice_v1 --from-sample sample_invoice.pdf --output-file schema.json
        """)
        # endregion
    schema = json.loads(Path("schema.json").read_text(encoding="utf-8"))
    assert schema["analyzerId"] == "invoice_v1" and schema["fieldSchema"]["fields"]
    # region Snippet:analyzer_create
    _run("""
        # Review and update the generated schema for your extraction requirements,
        # then create the analyzer.
        cu analyzer create --name invoice_v1 --schema schema.json
    """)
    # endregion
    assert created["invoice_v1"]["fieldSchema"] == schema["fieldSchema"]
    # region Snippet:analyzer_test_single
    result = _run("""
        # Run the analyzer against the sample and summarize whether fields were returned
        # and any confidence values supplied by the service. This is not an accuracy
        # benchmark and does not compare the result with labeled ground truth.
        cu analyzer test invoice_v1 sample_invoice.pdf
    """)
    # endregion
    assert "1 ok / 0 failed / 1 total" in result.output
    # region Snippet:analyze_custom
    result = _run("cu analyze sample_invoice.pdf -a invoice_v1 --json")
    # endregion
    assert json.loads(result.stdout)["analyzerId"] == "invoice_v1"
    assert analyzed == ["invoice_v1", "invoice_v1"]
    # endregion


def test_command_help():
    # region Snippet:setup_help
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
    # region Snippet:infra_help
    result = _run("cu infra generate --help")
    # endregion
    assert "--models" in result.output
    # endregion


def test_multiple_profiles(azure_login, monkeypatch):
    from cu_cli.commands import analyzer as analyzer_commands

    selected = []
    build_client = analyzer_commands.build_client

    def record_profile(profile, **options):
        selected.append(profile.profile_name)
        return build_client(profile, **options)

    monkeypatch.setattr(analyzer_commands, "build_client", record_profile)
    # region Snippet:multiple_profiles
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
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_active
        result = _run("""
            # Use all effective settings from the active dev profile.
            # --info prints resolved, non-secret runtime settings to stderr before the request.
            # It is not a dry run; the analyzer list request still runs.
            cu analyzer list --info
        """)
        # endregion
    assert "endpoint: https://dev.services.ai.azure.com/" in result.stderr
    assert "endpoint:" not in result.stdout and "prebuilt-layout" in result.output
    with use_cassette("analyzer_list"):
        # region Snippet:analyzer_list_prod
        _run("""
            # Use prod for this command only; dev remains active.
            cu analyzer list --profile prod
        """)
        # endregion
    assert selected == ["dev", "prod"]
    assert ProfileStore.load().get_active_name() == "dev"
    with use_cassette("doctor"):
        # region Snippet:doctor_named
        result = _run("""
            # Check prod without changing the active profile.
            cu doctor --profile prod
        """)
        # endregion
    assert "Microsoft Foundry resource: https://prod.services.ai.azure.com/" in result.output
    assert ProfileStore.load().get_active_name() == "dev"
    # endregion
