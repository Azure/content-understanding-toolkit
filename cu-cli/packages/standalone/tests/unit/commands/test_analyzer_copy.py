# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""CLI-level unit tests for ``cu analyzer copy`` — no network calls.

Focus areas:

* Positional and named object selector equivalence.
* Mixed object/resource-selector rejection before service calls.
* Same-ID guard before any service call.
* Every effective endpoint resolves in the explicit or active Azure CLI
  subscription before analyzer service calls.
* Resource-group overrides still require direct resource selectors.

Service-side orchestration is covered by ``test_analyzers.py::test_copy_*``
which drive :func:`cu_cli.core.analyzers.copy_analyzer` directly against fake
clients. These CLI tests exercise the Click layer end-to-end via ``CliRunner``.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cu_cli.cli import main
from cu_cli_core.command_spec import ANALYZER_COPY

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _resolve_patched_copy_operation(monkeypatch):
    """Route the registered operation through this module's patchable test seam."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    resolve_identifier = analyzer_cmd.resolve_identifier

    def resolve(identifier):
        if identifier == ANALYZER_COPY.operation:
            return analyzers_core.copy_analyzer
        return resolve_identifier(identifier)

    monkeypatch.setattr(analyzer_cmd, "resolve_identifier", resolve)


@pytest.fixture(autouse=True)
def _resolve_profile_backed_resources(monkeypatch):
    """Keep command tests network-free now that every copy resolves ARM metadata."""
    from cu_cli.core import azure_resources

    def resolve(selector, *, subscription_id=None, resource_group=None, **_):
        account_name = selector.split("://")[-1].split(".", 1)[0]
        subscription = subscription_id or "active-subscription"
        group = resource_group or "test-rg"
        return azure_resources.ResolvedResource(
            arm_id=f"/subscriptions/{subscription}/resourceGroups/{group}/providers/"
                   f"Microsoft.CognitiveServices/accounts/{account_name}",
            region="eastus",
            endpoint=selector,
            subscription_id=subscription,
            resource_group=group,
            account_name=account_name,
        )

    monkeypatch.setattr(azure_resources, "resolve_resource", resolve)


def _invoke(*args) -> object:
    return CliRunner().invoke(main, list(args))


# --- Same-ID guard ----------------------------------------------------------


def test_copy_rejects_identical_source_and_destination_same_resource():
    result = _invoke("analyzer", "copy", "my_v1", "my_v1")
    assert result.exit_code != 0
    assert "identical" in result.output
    assert "_v2" in result.output


def test_copy_allows_identical_ids_when_destination_is_different_resource(monkeypatch):
    """Identical analyzer IDs are legal when copying *across* resources
    (dev -> prod versioning uses the same schema name on both sides)."""
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    src = azure_resources.ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
        region="eastus",
        endpoint="https://src.services.ai.azure.com/",
        subscription_id="S",
        resource_group="rg",
        account_name="src",
    )
    tgt = azure_resources.ResolvedResource(
        arm_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt",
        region="westus",
        endpoint="https://tgt.services.ai.azure.com/",
        subscription_id="T",
        resource_group="rg",
        account_name="tgt",
    )
    monkeypatch.setattr(
        azure_resources,
        "resolve_resource",
        lambda selector, **_: src if "src" in selector else tgt,
    )
    monkeypatch.setattr(analyzer_cmd, "_client_from_resource", lambda resolved, **_: object())
    monkeypatch.setattr(
        analyzers_core,
        "get_copy_source_analyzer",
        lambda *a, **kw: SimpleNamespace(config=SimpleNamespace(content_categories={})),
    )
    calls: list[tuple] = []
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: calls.append((a, kw)))

    result = _invoke(
        "analyzer", "copy", "invoice_v1", "invoice_v1",
        "--source-resource", "src",
        "--destination-resource", "tgt",
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 1


def test_copy_rejects_identical_ids_when_source_selector_defaults_destination(monkeypatch):
    """A source-only selector still resolves to a same-resource copy."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    resource = azure_resources.ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
        region="eastus",
        endpoint="https://src.services.ai.azure.com/",
        subscription_id="S",
        resource_group="rg",
        account_name="src",
    )
    monkeypatch.setattr(azure_resources, "resolve_resource", lambda *a, **kw: resource)
    monkeypatch.setattr(analyzer_cmd, "_client_from_resource", lambda *a, **kw: object())
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: pytest.fail("copy must not run for a same-resource no-op"),
    )

    result = _invoke(
        "analyzer", "copy", "same", "same", "--source-resource", "src"
    )
    assert result.exit_code != 0
    assert "identical" in result.output


def test_copy_rejects_identical_ids_when_named_profiles_resolve_same_endpoint(monkeypatch):
    """Different config names can still refer to the same effective resource."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_named_profile",
        lambda *a, **kw: (
            object(),
            "https://same.services.ai.azure.com/",
            "2025-11-01",
        ),
    )
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: pytest.fail("copy must not run for a same-resource no-op"),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "same",
        "same",
        "--source-profile",
        "dev",
        "--destination-profile",
        "prod",
    )
    assert result.exit_code != 0
    assert "identical" in result.output


# --- Mixed-selector rejection ----------------------------------------------


def test_copy_rejects_source_resource_and_config_together():
    result = _invoke(
        "analyzer", "copy", "src", "tgt",
        "--source-resource", "https://foo.services.ai.azure.com/",
        "--source-profile", "dev",
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower() or "mutual" in result.output.lower()
    assert "--source-resource" in result.output and "--source-profile" in result.output


def test_copy_rejects_destination_resource_and_config_together():
    result = _invoke(
        "analyzer", "copy", "src", "tgt",
        "--destination-resource", "https://foo.services.ai.azure.com/",
        "--destination-profile", "prod",
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower() or "mutual" in result.output.lower()
    assert "--destination-resource" in result.output
    assert "--destination-profile" in result.output


def test_copy_rejects_destination_subscription_without_destination_context():
    result = _invoke(
        "analyzer", "copy", "src", "tgt",
        "--destination-subscription", "aaaa-bbbb",
    )
    assert result.exit_code != 0
    assert "--destination-subscription requires --destination-resource" in result.output


def test_copy_rejects_destination_resource_group_without_resource():
    result = _invoke(
        "analyzer", "copy", "src", "tgt",
        "--destination-resource-group", "rg-prod",
    )
    assert result.exit_code != 0
    assert "--destination-resource-group requires --destination-resource" in result.output


def test_copy_symmetric_resource_selectors_pass_side_specific_scope(monkeypatch):
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    resource = azure_resources.ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/rg/providers/"
        "Microsoft.CognitiveServices/accounts/acct",
        region="eastus",
        endpoint="https://acct.services.ai.azure.com/",
        subscription_id="S",
        resource_group="rg",
        account_name="acct",
    )
    resolutions: list[tuple[str, str | None, str | None]] = []

    def _resolve(selector, *, subscription_id=None, resource_group=None, **_):
        resolutions.append((selector, subscription_id, resource_group))
        return resource

    client = object()
    monkeypatch.setattr(azure_resources, "resolve_resource", _resolve)
    monkeypatch.setattr(analyzer_cmd, "_client_from_resource", lambda *a, **kw: client)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: None)

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "dst",
        "--source-resource",
        "source-account",
        "--source-subscription",
        "source-sub",
        "--source-resource-group",
        "source-rg",
        "--destination-resource",
        "destination-account",
        "--destination-subscription",
        "destination-sub",
        "--destination-resource-group",
        "destination-rg",
    )

    assert result.exit_code == 0, result.output
    assert resolutions == [
        ("source-account", "source-sub", "source-rg"),
        ("destination-account", "destination-sub", "destination-rg"),
    ]


# --- Object selector forms --------------------------------------------------


def test_copy_named_object_selectors_match_positionals(monkeypatch):
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    sentinel = object()
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(analyzer_cmd, "_client", lambda *a, **kw: sentinel)
    monkeypatch.setattr(
        analyzer_cmd.Profile,
        "load",
        lambda **_: SimpleNamespace(
            profile_name="default",
            endpoint="https://active.services.ai.azure.com/",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda _client, source, destination, **_kwargs: calls.append(
            (source, destination)
        ),
    )

    positional = _invoke("analyzer", "copy", "src", "dst")
    named = _invoke(
        "analyzer", "copy", "--source", "src", "--destination", "dst"
    )

    assert positional.exit_code == 0, positional.output
    assert named.exit_code == 0, named.output
    assert calls == [("src", "dst"), ("src", "dst")]


def test_copy_rejects_mixed_positional_and_named_objects_before_service(monkeypatch):
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    monkeypatch.setattr(
        analyzer_cmd,
        "_client",
        lambda *a, **kw: pytest.fail("client creation must not run"),
    )
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: pytest.fail("copy must not run"),
    )
    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "dst",
        "--source",
        "src",
        "--destination",
        "dst",
    )
    assert result.exit_code != 0
    assert "cannot be combined" in result.output


# --- Argument validation happens before client creation ---------------------


@pytest.mark.parametrize(
    ("args", "missing_option"),
    [
        ((), "--source"),
        (("src",), "--destination"),
        (("--source", "src"), "--destination"),
        (("--destination", "dst"), "--source"),
    ],
)
def test_copy_requires_both_source_and_destination(args, missing_option):
    result = _invoke("analyzer", "copy", *args)
    assert result.exit_code != 0
    assert f"missing required argument: {missing_option}" in result.output


# --- Destination resource defaults to source --------------------------------


def test_copy_destination_resource_defaults_from_source(monkeypatch):
    """With no destination context, the destination side reuses the source client —
    proving the same-resource (``target_client=None``) path is taken.

    We patch :func:`cu_cli.commands.analyzer._client` to return a sentinel and
    :func:`cu_cli.core.analyzers.copy_analyzer` to capture what the CLI passes.
    """
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    class _Sentinel:
        """Only identity matters — copy_analyzer should be called with the same instance."""

    the_client = _Sentinel()
    calls: dict = {}

    def _fake_client(endpoint, api_key, api_version, entra, profile_name, show_runtime_context):
        return the_client

    def _fake_copy(client, source_analyzer_id, target_analyzer_id,
                   *, target_client=None, **kwargs):
        calls["client"] = client
        calls["target_client"] = target_client
        calls["source"] = source_analyzer_id
        calls["target"] = target_analyzer_id
        return None

    monkeypatch.setattr(analyzer_cmd, "_client", _fake_client)
    monkeypatch.setattr(
        analyzer_cmd.Profile,
        "load",
        lambda **_: SimpleNamespace(
            profile_name="default",
            endpoint="https://active.services.ai.azure.com/",
            api_version="2025-11-01",
        ),
    )
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _fake_copy)

    result = _invoke("analyzer", "copy", "src_v1", "tgt_v1")
    assert result.exit_code == 0, result.output
    # Same client identity → same-resource copy path.
    assert calls["client"] is the_client
    # No destination context means a same-resource SDK call.
    assert calls["target_client"] is None
    assert calls["source"] == "src_v1"
    assert calls["target"] == "tgt_v1"


# --- Dependency preflight gates the copy -----------------------------------


def test_copy_dep_preflight_prevents_copy_when_destination_missing_deps(monkeypatch):
    """When the source has a custom category ref that's missing on the destination,
    ``copy_analyzer`` must never be called — the CLI errors before any grant/copy.

    Sets up a fake cross-resource scenario:
    * Source: analyzer with ``content_categories[analyzer_id='my_dep_v1']``.
    * Target: 404 on ``get_analyzer('my_dep_v1')``.

    Uses direct resource selectors with stubbed ``resolve_resource`` so the CLI
    enters the cross-resource branch that runs the dep preflight.
    """
    from types import SimpleNamespace

    from azure.core.exceptions import ResourceNotFoundError

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    src_resource = azure_resources.ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src-acct",
        region="eastus",
        endpoint="https://src.services.ai.azure.com/",
        subscription_id="S", resource_group="rg", account_name="src-acct",
    )
    tgt_resource = azure_resources.ResolvedResource(
        arm_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt-acct",
        region="westus",
        endpoint="https://tgt.services.ai.azure.com/",
        subscription_id="T", resource_group="rg", account_name="tgt-acct",
    )

    def _fake_resolve(selector, *, subscription_id=None, resource_group=None, credential=None):
        if "src" in selector.lower():
            return src_resource
        return tgt_resource

    monkeypatch.setattr(analyzer_cmd, "resolve_resource", _fake_resolve, raising=False)
    monkeypatch.setattr(azure_resources, "resolve_resource", _fake_resolve)

    class _FakeSrcClient:
        def get_analyzer(self, aid):
            # Source has a custom classifier category referring to my_dep_v1.
            return SimpleNamespace(
                analyzer_id=aid,
                config=SimpleNamespace(content_categories={
                    "custom": SimpleNamespace(analyzer_id="my_dep_v1"),
                    "prebuilt": SimpleNamespace(
                        analyzer_id="prebuilt-invoice"
                    ),  # must be skipped
                }),
            )

    class _FakeTgtClient:
        def get_analyzer(self, aid):
            # Target has neither the parent nor the dep.
            raise ResourceNotFoundError(message=f"no {aid}")

    def _fake_client_from_resource(resolved, *, api_version):
        return _FakeSrcClient() if "src" in resolved.endpoint else _FakeTgtClient()

    monkeypatch.setattr(analyzer_cmd, "_client_from_resource", _fake_client_from_resource)

    dependency_commands: list[str] = []
    build_dependency_command = analyzer_cmd._dependency_copy_cli_command

    def _record_dependency_command(*args, **kwargs):
        command = build_dependency_command(*args, **kwargs)
        dependency_commands.append(command)
        return command

    monkeypatch.setattr(
        analyzer_cmd,
        "_dependency_copy_cli_command",
        _record_dependency_command,
    )

    # Guard: copy_analyzer must NOT be called after a failed preflight.
    copy_called = {"count": 0}

    def _copy_should_not_run(*args, **kwargs):
        copy_called["count"] += 1
        raise AssertionError("copy_analyzer must not be called after failed dep preflight")

    monkeypatch.setattr(analyzers_core, "copy_analyzer", _copy_should_not_run)

    result = _invoke(
        "analyzer", "copy", "src_classifier_v1", "tgt_classifier_v1",
        "--source-resource", "https://src.services.ai.azure.com/",
        "--source-subscription", "S",
        "--destination-resource", "https://tgt.services.ai.azure.com/",
        "--destination-subscription", "T",
        "--api-version", "2026-06-01-preview",
    )
    assert result.exit_code != 0
    # The missing custom dep is named in the error, and the actual copy never ran.
    assert "my_dep_v1" in result.output
    assert "missing on the" in result.output.lower()
    assert "destination resource" in result.output.lower()
    assert copy_called["count"] == 0
    # Prebuilt refs must not be recommended as needing to be copied.
    assert "prebuilt-invoice" not in result.output
    assert dependency_commands == [
        "cu analyzer copy --source my_dep_v1 --destination my_dep_v1 "
        "--source-resource /subscriptions/S/resourceGroups/rg/providers/"
        "Microsoft.CognitiveServices/accounts/src-acct "
        "--destination-resource /subscriptions/T/resourceGroups/rg/providers/"
        "Microsoft.CognitiveServices/accounts/tgt-acct "
        "--api-version 2026-06-01-preview"
    ]
    assert "--source-subscription" not in dependency_commands[0]
    assert "--destination-subscription" not in dependency_commands[0]
    assert "2026-06-01-preview" in result.output


def test_copy_dep_commands_preserve_named_profile_subscription_context(monkeypatch):
    """Generated config-backed retries retain scope and explicit API version."""
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    def _fake_named(profile_name, **_):
        return (
            object(),
            f"https://{profile_name}.services.ai.azure.com/",
            "2026-06-01-preview",
        )

    resources = {
        side: azure_resources.ResolvedResource(
            arm_id=f"/subscriptions/{side}/resourceGroups/rg/providers/"
                   f"Microsoft.CognitiveServices/accounts/{side}",
            region="eastus" if side == "dev" else "westus",
            endpoint=f"https://{side}.services.ai.azure.com/",
            subscription_id=side,
            resource_group="rg",
            account_name=side,
        )
        for side in ("dev", "prod")
    }

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    monkeypatch.setattr(
        azure_resources,
        "resolve_resource",
        lambda endpoint, **_: resources["dev" if "/dev." in endpoint else "prod"],
    )
    monkeypatch.setattr(
        analyzers_core,
        "get_copy_source_analyzer",
        lambda *a, **kw: SimpleNamespace(config=SimpleNamespace(content_categories={})),
    )
    monkeypatch.setattr(
        analyzers_core,
        "collect_custom_dependencies",
        lambda _: ["dependency_v1"],
    )
    monkeypatch.setattr(
        analyzers_core,
        "preflight_dependencies_on_target",
        lambda *a, **kw: ["dependency_v1"],
    )
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: pytest.fail("copy must not run with missing dependencies"),
    )
    dependency_commands: list[str] = []
    build_dependency_command = analyzer_cmd._dependency_copy_cli_command

    def _record_dependency_command(*args, **kwargs):
        command = build_dependency_command(*args, **kwargs)
        dependency_commands.append(command)
        return command

    monkeypatch.setattr(
        analyzer_cmd,
        "_dependency_copy_cli_command",
        _record_dependency_command,
    )

    result = _invoke(
        "analyzer",
        "copy",
        "router_v1",
        "router_v1",
        "--source-profile",
        "dev",
        "--source-subscription",
        "Development Subscription",
        "--destination-profile",
        "prod",
        "--destination-subscription",
        "Production Subscription",
        "--api-version",
        "2026-06-01-preview",
    )

    assert result.exit_code != 0
    assert dependency_commands == [
        "cu analyzer copy --source dependency_v1 --destination dependency_v1 "
        "--source-profile dev --source-subscription 'Development Subscription' "
        "--destination-profile prod "
        "--destination-subscription 'Production Subscription' "
        "--api-version 2026-06-01-preview"
    ]
    assert "--api-key" not in dependency_commands[0]
    assert "secret" not in dependency_commands[0]
    assert "Development Subscription" in result.output
    assert "Production Subscription" in result.output
    assert "2026-06-01-preview" in result.output


# --- ID validation before auth / service ------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "",                                     # empty
        "/tmp/schema.json",                     # user passed a file path
        "https://x.services.ai.azure.com/",     # user passed a URL
        "has space",                            # spaces
        "a" * 65,                               # over 64 chars
        "id!with*bad+chars",                    # invalid punctuation
    ],
)
def test_copy_rejects_invalid_source_id_before_any_service_call(monkeypatch, bad_id):
    """Invalid source IDs must fail with a CuCliError from the validation
    helper *before* the Profile loader, ``resolve_resource``, or
    ``copy_analyzer`` are ever touched. This verifies that source and destination
    analyzer IDs are validated before authentication or service calls.
    """
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    tripwires = {"resolve": 0, "named_profile": 0, "copy": 0}

    def _tripwire_resolve(*a, **kw):
        tripwires["resolve"] += 1
        raise AssertionError("resolve_resource must not be called for invalid IDs")

    def _tripwire_named(*a, **kw):
        tripwires["named_profile"] += 1
        raise AssertionError("_client_from_named_profile must not be called for invalid IDs")

    def _tripwire_copy(*a, **kw):
        tripwires["copy"] += 1
        raise AssertionError("copy_analyzer must not be called for invalid IDs")

    monkeypatch.setattr(azure_resources, "resolve_resource", _tripwire_resolve)
    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _tripwire_named)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _tripwire_copy)

    # Give the destination a valid ID so we specifically exercise source validation.
    result = _invoke("analyzer", "copy", bad_id, "valid_target_v1")
    assert result.exit_code != 0, result.output
    expected = (
        "source and destination analyzer names are required"
        if not bad_id
        else "source analyzer ID"
    )
    assert expected in result.output
    assert tripwires == {"resolve": 0, "named_profile": 0, "copy": 0}


def test_copy_rejects_invalid_destination_before_any_service_call(monkeypatch):
    """Same guarantee for the destination side."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    def _tripwire(*a, **kw):
        raise AssertionError("service layer must not be reached")

    monkeypatch.setattr(azure_resources, "resolve_resource", _tripwire)
    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _tripwire)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _tripwire)

    result = _invoke("analyzer", "copy", "valid_source_v1", "id with spaces")
    assert result.exit_code != 0, result.output
    assert "destination analyzer ID" in result.output


def test_copy_accepts_realistic_analyzer_ids(monkeypatch):
    """Realistic IDs must pass validation: prebuilt-invoice, my_analyzer_v1,
    check.us, digits123. Regression guard for the regex being too strict.

    Routes through ``--source-profile`` so we hit the stubbed named-profile path
    (avoids depending on any on-disk CU profile for a pure ID-validation test).
    """
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_named_profile",
        lambda *a, **kw: (
            object(),
            "https://x.services.ai.azure.com/",
            "2025-11-01",
        ),
    )
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: None)

    for src, tgt in [
        ("prebuilt-invoice", "my_invoice_v1"),
        ("my_analyzer_v1", "my_analyzer_v2"),
        ("check.us", "check.eu"),
        ("digits123", "digits456"),
        (".hidden", "_private"),
    ]:
        result = _invoke(
            "analyzer", "copy", src, tgt,
            "--source-profile", "stub",
            "--destination-profile", "stub",
        )
        assert result.exit_code == 0, f"{src!r} -> {tgt!r} failed: {result.output}"


def test_copy_accepts_leading_hyphen_id_after_click_separator(monkeypatch):
    """The REST pattern permits leading ``-``; Click accepts it after ``--``."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_named_profile",
        lambda *a, **kw: (
            object(),
            "https://x.services.ai.azure.com/",
            "2025-11-01",
        ),
    )
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: None)

    result = _invoke(
        "analyzer",
        "copy",
        "--source-profile",
        "stub",
        "--destination-profile",
        "stub",
        "--",
        "-source",
        "-destination",
    )
    assert result.exit_code == 0, result.output


# --- --endpoint conflicts with direct resource selectors --------------------


def test_copy_rejects_endpoint_combined_with_source_resource(monkeypatch):
    """``--endpoint`` composes with the active/named-profile path only. Combining
    it with ``--source-resource`` is ambiguous because discovery resolves the endpoint,
    so an inline override would silently disagree with the ARM-ID / region we
    use for grant + copy.
    """
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    def _tripwire(*a, **kw):
        raise AssertionError("must fail before Azure resolution")

    monkeypatch.setattr(azure_resources, "resolve_resource", _tripwire)
    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _tripwire)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _tripwire)

    result = _invoke(
        "analyzer", "copy", "src_v1", "tgt_v1",
        "--source-resource", "https://acct.services.ai.azure.com/",
        "--endpoint", "https://different.services.ai.azure.com/",
    )
    assert result.exit_code != 0, result.output
    assert "--endpoint cannot be combined with --source-resource" in result.output


def test_copy_rejects_endpoint_combined_with_destination_resource(monkeypatch):
    """Symmetric guard for the destination."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    def _tripwire(*a, **kw):
        raise AssertionError("must fail before Azure resolution")

    monkeypatch.setattr(azure_resources, "resolve_resource", _tripwire)
    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _tripwire)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _tripwire)

    result = _invoke(
        "analyzer", "copy", "src_v1", "tgt_v1",
        "--destination-resource", "https://acct.services.ai.azure.com/",
        "--endpoint", "https://different.services.ai.azure.com/",
    )
    assert result.exit_code != 0, result.output
    assert "--destination-resource" in result.output


def test_copy_rejects_api_key_combined_with_direct_selector(monkeypatch):
    """Direct resource flows always use Entra; one key cannot auth two sides."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    def _tripwire(*a, **kw):
        raise AssertionError("must fail before Azure resolution or client creation")

    monkeypatch.setattr(azure_resources, "resolve_resource", _tripwire)
    monkeypatch.setattr(analyzer_cmd, "_client_from_resource", _tripwire)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _tripwire)

    result = _invoke(
        "analyzer",
        "copy",
        "src_v1",
        "tgt_v1",
        "--source-resource",
        "https://acct.services.ai.azure.com/",
        "--api-key",
        "secret-that-must-not-be-used",
    )
    assert result.exit_code != 0, result.output
    assert "--api-key cannot be combined with --source-resource" in result.output
    assert "secret-that-must-not-be-used" not in result.output


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--endpoint", "https://override.example/"),
        ("--api-key", "one-account-key"),
    ],
)
def test_copy_rejects_shared_override_with_explicit_destination_profile(
    monkeypatch,
    option,
    value,
):
    """One account-scoped override cannot safely represent two named sides."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    def _tripwire(*a, **kw):
        raise AssertionError("must fail before named profiles or service calls")

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _tripwire)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _tripwire)

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--destination-profile",
        "prod",
        option,
        value,
    )
    assert result.exit_code != 0, result.output
    assert option in result.output
    assert "--destination-profile" in result.output
    if option == "--api-key":
        assert value not in result.output


# --- Direct resource copy must never touch on-disk profile storage ----------


def test_copy_source_resource_never_writes_profiles(monkeypatch):
    """``--source-resource`` resolves the source directly from Azure. Even if the copy
    succeeds, ``ProfileStore.save`` must not fire — the CLI must not create,
    rename, or mutate profiles in the Azure CLI config as a side effect
    of a copy.

    Guards against a regression where a future ``_resolve_side`` path might
    persist the freshly-discovered endpoint into the active profile.
    """
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources
    from cu_cli.profile import ProfileStore

    save_calls: list[object] = []

    def _record_save(self, *a, **kw):
        save_calls.append(getattr(self, "path", "<unknown>"))
        return getattr(self, "path", None)

    monkeypatch.setattr(ProfileStore, "save", _record_save)

    resolved = azure_resources.ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/rg/providers/"
               "Microsoft.CognitiveServices/accounts/acct",
        region="eastus",
        endpoint="https://acct.services.ai.azure.com/",
        subscription_id="S",
        resource_group="rg",
        account_name="acct",
    )
    monkeypatch.setattr(azure_resources, "resolve_resource",
                        lambda *a, **kw: resolved)
    monkeypatch.setattr(analyzer_cmd, "_client_from_resource",
                        lambda resolved, *, api_version: object())
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: None)

    result = _invoke(
        "analyzer", "copy", "src_v1", "tgt_v1",
        "--source-resource", "https://acct.services.ai.azure.com/",
    )
    assert result.exit_code == 0, result.output
    assert save_calls == [], (
        f"ProfileStore.save must not be invoked on the direct resource path; "
        f"got {save_calls}"
    )


def test_client_from_resource_uses_standard_builder(monkeypatch):
    """Selector clients keep telemetry, polling, and auth behavior centralized."""
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd

    sentinel = object()
    calls: list[dict] = []

    monkeypatch.setattr(
        analyzer_cmd.Profile,
        "load",
        lambda **_: SimpleNamespace(api_version="2025-11-01"),
    )

    def _fake_build(cfg, **kwargs):
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(analyzer_cmd, "build_client", _fake_build)

    resolved = SimpleNamespace(endpoint="https://acct.services.ai.azure.com/")
    client = analyzer_cmd._client_from_resource(resolved, api_version=None)

    assert client is sentinel
    assert calls == [{
        "endpoint_override": "https://acct.services.ai.azure.com/",
        "api_version_override": "2025-11-01",
        "force_entra": True,
    }]


# --- Side-specific config routing -------------------------------------------


def test_copy_source_profile_routes_to_the_named_profile(monkeypatch):
    """Side-specific config selectors must pass their exact names
    exact names to ``_client_from_named_profile`` (not the active config, not
    a default fallback).

    Stubs both named-profile resolutions to return the same endpoint string so
    Azure discovery resolves both profiles to the same resource.
    """
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    named_calls: list[tuple[str, str | None, str | None]] = []

    def _fake_named(profile_name, *, endpoint, api_key, api_version, entra):
        named_calls.append((profile_name, endpoint, api_key))
        return (
            object(),
            "https://same-endpoint.services.ai.azure.com/",
            "2025-11-01",
        )

    copy_calls: list[tuple] = []

    def _fake_copy(*a, **kw):
        copy_calls.append((a, kw))

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", _fake_copy)

    result = _invoke(
        "analyzer", "copy", "src_v1", "tgt_v1",
        "--source-profile", "src-config",
        "--destination-profile", "tgt-config",
    )
    assert result.exit_code == 0, result.output
    assert ("src-config", None, None) in named_calls
    assert ("tgt-config", None, None) in named_calls
    # copy_analyzer fired exactly once (same-resource path)
    assert len(copy_calls) == 1
    assert callable(copy_calls[0][1]["progress"])
    assert "Resolving source and destination resources for analyzer copy" in result.output
    assert "Checking source and destination analyzers" in result.output


def test_cross_resource_copy_rejects_mismatched_profile_api_versions_before_data_plane(
    monkeypatch,
):
    """Unsupported cross-version copies fail before any analyzer operation."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    versions = {
        "dev": "2025-11-01",
        "prod": "2026-06-01-preview",
    }

    def _fake_named(profile_name, *, api_version, **_):
        return (
            object(),
            f"https://{profile_name}.services.ai.azure.com/",
            api_version or versions[profile_name],
        )

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    monkeypatch.setattr(
        analyzers_core,
        "get_copy_source_analyzer",
        lambda *a, **kw: pytest.fail("source analyzer lookup must not run"),
    )
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: pytest.fail("copy and authorization must not run"),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--destination-profile",
        "prod",
    )

    assert result.exit_code != 0
    assert "API versions must match" in result.output
    assert "source=2025-11-01" in result.output
    assert "destination=2026-06-01-preview" in result.output
    assert "--api-version" in result.output


def test_global_api_version_aligns_cross_resource_profiles(monkeypatch):
    """A global API-version override applies consistently to both copy sides."""
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    requested_versions: list[str | None] = []

    def _fake_named(profile_name, *, api_version, **_):
        requested_versions.append(api_version)
        return (
            object(),
            f"https://{profile_name}.services.ai.azure.com/",
            api_version,
        )

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    monkeypatch.setattr(
        analyzers_core,
        "get_copy_source_analyzer",
        lambda *a, **kw: SimpleNamespace(config=SimpleNamespace(content_categories={})),
    )
    copy_calls: list[dict] = []
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: copy_calls.append(kw),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--destination-profile",
        "prod",
        "--api-version",
        "2026-06-01-preview",
        "--info",
    )

    assert result.exit_code == 0, result.output
    assert requested_versions == ["2026-06-01-preview", "2026-06-01-preview"]
    assert len(copy_calls) == 1
    assert result.output.count("api-version: 2026-06-01-preview") == 2


def test_same_resource_profiles_allow_different_configured_api_versions(monkeypatch):
    """Profile-version differences do not block an effective same-resource copy."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    versions = {
        "dev": "2025-11-01",
        "prod": "2026-06-01-preview",
    }

    def _fake_named(profile_name, **_):
        return (
            object(),
            f"https://{profile_name}.services.ai.azure.com/",
            versions[profile_name],
        )

    same_resource = azure_resources.ResolvedResource(
        arm_id="/subscriptions/S/resourceGroups/rg/providers/"
               "Microsoft.CognitiveServices/accounts/shared",
        region="eastus",
        endpoint="https://shared.services.ai.azure.com/",
        subscription_id="S",
        resource_group="rg",
        account_name="shared",
    )
    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    monkeypatch.setattr(azure_resources, "resolve_resource", lambda *a, **kw: same_resource)
    copy_calls: list[dict] = []
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: copy_calls.append(kw),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--destination-profile",
        "prod",
    )

    assert result.exit_code == 0, result.output
    assert len(copy_calls) == 1
    assert copy_calls[0]["target_client"] is None


def test_source_profile_allows_overrides_when_destination_defaults_to_source(monkeypatch):
    """Overrides remain valid when both IDs are copied on one named resource."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core

    calls: list[tuple[str, str | None, str | None]] = []

    def _fake_named(profile_name, *, endpoint, api_key, api_version, entra):
        calls.append((profile_name, endpoint, api_key))
        return object(), endpoint or "https://config.example/", "2025-11-01"

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: None)

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--endpoint",
        "https://override.example/",
        "--api-key",
        "test-key",
    )
    assert result.exit_code == 0, result.output
    assert calls == [("dev", "https://override.example/", "test-key")]


def test_copy_resolves_endpoint_override_in_explicit_source_subscription(monkeypatch):
    """Regression: a source subscription scopes profile-backed endpoint discovery."""
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    client = object()
    monkeypatch.setattr(analyzer_cmd, "_client", lambda *a, **kw: client)
    monkeypatch.setattr(
        analyzer_cmd.Profile,
        "load",
        lambda **_: SimpleNamespace(
            profile_name="default",
            endpoint="https://profile.services.ai.azure.com/",
            api_version="2025-11-01",
        ),
    )
    resolutions: list[tuple[str, str | None]] = []

    def resolve(selector, *, subscription_id=None, **_):
        resolutions.append((selector, subscription_id))
        return azure_resources.ResolvedResource(
            arm_id="/subscriptions/source-sub/resourceGroups/source-rg/providers/"
                   "Microsoft.CognitiveServices/accounts/source-account",
            region="eastus",
            endpoint=selector,
            subscription_id="source-sub",
            resource_group="source-rg",
            account_name="source-account",
        )

    monkeypatch.setattr(azure_resources, "resolve_resource", resolve)
    copy_calls: list[dict] = []
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: copy_calls.append(kw),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--endpoint",
        "https://override.services.ai.azure.com/",
        "--source-subscription",
        "source-sub",
    )

    assert result.exit_code == 0, result.output
    assert resolutions == [
        ("https://override.services.ai.azure.com/", "source-sub"),
    ]
    assert len(copy_calls) == 1
    assert copy_calls[0]["target_client"] is None


def test_copy_uses_active_subscription_for_unqualified_profile_endpoint(monkeypatch):
    """Omitting a side subscription delegates scope selection to the active az account."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_named_profile",
        lambda *a, **kw: (
            object(),
            "https://dev.services.ai.azure.com/",
            "2025-11-01",
        ),
    )
    resolutions: list[tuple[str, str | None]] = []

    def resolve(selector, *, subscription_id=None, **_):
        resolutions.append((selector, subscription_id))
        return azure_resources.ResolvedResource(
            arm_id="/subscriptions/active-sub/resourceGroups/dev-rg/providers/"
                   "Microsoft.CognitiveServices/accounts/dev",
            region="eastus",
            endpoint=selector,
            subscription_id="active-sub",
            resource_group="dev-rg",
            account_name="dev",
        )

    monkeypatch.setattr(azure_resources, "resolve_resource", resolve)
    monkeypatch.setattr(analyzers_core, "copy_analyzer", lambda *a, **kw: None)

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
    )

    assert result.exit_code == 0, result.output
    assert resolutions == [
        ("https://dev.services.ai.azure.com/", None),
    ]


def test_copy_subscription_resolution_failure_precedes_analyzer_service(monkeypatch):
    """An explicit subscription never falls back or reaches the data plane."""
    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources
    from cu_cli.errors import CuCliError

    monkeypatch.setattr(
        analyzer_cmd,
        "_client_from_named_profile",
        lambda *a, **kw: (
            object(),
            "https://dev.services.ai.azure.com/",
            "2025-11-01",
        ),
    )
    resolutions: list[tuple[str, str | None]] = []

    def fail_resolution(selector, *, subscription_id=None, **_):
        resolutions.append((selector, subscription_id))
        raise CuCliError("subscription is not accessible")

    monkeypatch.setattr(azure_resources, "resolve_resource", fail_resolution)
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: pytest.fail("analyzer service must not be called"),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--source-subscription",
        "requested-sub",
    )

    assert result.exit_code != 0
    assert resolutions == [
        ("https://dev.services.ai.azure.com/", "requested-sub"),
    ]
    assert "requested-sub" in result.output
    assert "subscription is not accessible" in result.output


@pytest.mark.parametrize(
    ("subscription_args", "expected_subscriptions"),
    [
        ((), [None, None]),
        (
            (
                "--source-subscription",
                "dev-subscription",
                "--destination-subscription",
                "prod-subscription",
            ),
            ["dev-subscription", "prod-subscription"],
        ),
    ],
)
def test_copy_metadata_backfill_preserves_named_destination_recovery_context(
    monkeypatch,
    subscription_args,
    expected_subscriptions,
):
    """Key-auth config promotion must keep destination-qualified follow-up commands."""
    from types import SimpleNamespace

    from cu_cli.commands import analyzer as analyzer_cmd
    from cu_cli.core import analyzers as analyzers_core
    from cu_cli.core import azure_resources

    clients = {"dev": object(), "prod": object()}

    def _fake_named(profile_name, **_):
        return (
            clients[profile_name],
            f"https://{profile_name}.services.ai.azure.com/",
            "2025-11-01",
        )

    resources = {
        side: azure_resources.ResolvedResource(
            arm_id=f"/subscriptions/{side}/resourceGroups/rg/providers/"
                   f"Microsoft.CognitiveServices/accounts/{side}",
            region="eastus" if side == "dev" else "westus",
            endpoint=f"https://{side}.services.ai.azure.com/",
            subscription_id=side,
            resource_group="rg",
            account_name=side,
        )
        for side in ("dev", "prod")
    }

    monkeypatch.setattr(analyzer_cmd, "_client_from_named_profile", _fake_named)
    resolved_subscriptions: list[str | None] = []

    def _resolve_resource(endpoint, *, subscription_id=None, **_):
        resolved_subscriptions.append(subscription_id)
        return resources["dev" if "/dev." in endpoint else "prod"]

    monkeypatch.setattr(azure_resources, "resolve_resource", _resolve_resource)
    monkeypatch.setattr(
        analyzers_core,
        "get_copy_source_analyzer",
        lambda *a, **kw: SimpleNamespace(config=SimpleNamespace(content_categories={})),
    )
    copy_calls: list[dict] = []
    monkeypatch.setattr(
        analyzers_core,
        "copy_analyzer",
        lambda *a, **kw: copy_calls.append(kw),
    )

    result = _invoke(
        "analyzer",
        "copy",
        "src",
        "tgt",
        "--source-profile",
        "dev",
        "--destination-profile",
        "prod",
        *subscription_args,
    )
    assert result.exit_code == 0, result.output
    assert resolved_subscriptions == expected_subscriptions
    assert copy_calls[0]["target_cli_options"].startswith("--profile prod")
    assert "--entra" not in copy_calls[0]["target_cli_options"]
    assert "cu analyzer show tgt --profile prod" in result.output
