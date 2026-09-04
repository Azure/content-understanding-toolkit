"""Unit tests for the Click-free analyzer service in :mod:`cu_cli.core.analyzers`."""

from __future__ import annotations

import pytest

from cu_cli.core.analyzers import analyzer_kind
from cu_cli_core.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ServiceError,
    UsageError,
)

pytestmark = pytest.mark.unit


class _A:
    def __init__(self, analyzer_id):
        self.analyzer_id = analyzer_id


@pytest.mark.parametrize(
    "analyzer_id, expected",
    [
        ("prebuilt-layout", "prebuilt"),
        ("prebuilt-invoice", "prebuilt"),
        ("my_custom_v1", "custom"),
        ("invoice_suggested_v1", "custom"),
        ("", "custom"),
        ("prebuilt", "custom"),  # no trailing hyphen => not a prebuilt id
    ],
)
def test_analyzer_kind_classifies_by_prefix(analyzer_id, expected):
    assert analyzer_kind(_A(analyzer_id)) == expected


def test_analyzer_kind_handles_missing_id():
    class _NoId:
        pass

    assert analyzer_kind(_NoId()) == "custom"


def test_create_analyzer_conflict_hints_to_delete_first():
    # Regression: a duplicate create (409) must tell the user to delete first, since
    # Content Understanding has no in-place replace.
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import create_analyzer

    conflict = HttpResponseError()
    conflict.status_code = 409

    class _ConflictClient:
        def begin_create_analyzer(self, aid, body):
            raise conflict

    with pytest.raises(ConflictError) as ei:
        create_analyzer(_ConflictClient(), "dup_v1", {"analyzerId": "dup_v1"})
    assert "already exists" in ei.value.message
    assert ei.value.hint is not None
    assert "Delete the existing analyzer" in ei.value.hint


def test_create_analyzer_non_conflict_error_is_not_swallowed():
    # A non-409 failure must propagate unchanged so friendly_errors can surface
    # the real service detail (only the 409 gets the delete-first hint).
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import create_analyzer

    boom = HttpResponseError()
    boom.status_code = 500

    class _BoomClient:
        def begin_create_analyzer(self, aid, body):
            raise boom

    with pytest.raises(HttpResponseError):
        create_analyzer(_BoomClient(), "x_v1", {"analyzerId": "x_v1"})


# --- copy_analyzer ------------------------------------------------------------


class _OKPoller:
    """Fake LRO poller: returns a canned result immediately."""

    def __init__(self, analyzer_id: str, status: str = "Succeeded"):
        self._result = _A(analyzer_id)
        self._result.status = status

    def result(self):
        return self._result


def _raise_missing(analyzer_id: str) -> None:
    from azure.core.exceptions import ResourceNotFoundError

    raise ResourceNotFoundError(message=f"no analyzer: {analyzer_id}")


def test_copy_analyzer_happy_path_returns_result():
    """copy_analyzer confirms source, invokes begin_copy_analyzer, and returns the poller result."""
    from cu_cli.core.analyzers import copy_analyzer

    seen: dict = {}
    progress_events: list[str] = []

    class _OKClient:
        def get_analyzer(self, aid):
            seen.setdefault("get", []).append(aid)
            if aid == "invoice_v1":
                return _A(aid)  # source exists
            _raise_missing(aid)  # target absent

        def begin_copy_analyzer(self, *, analyzer_id, source_analyzer_id, **_):
            seen["copy_from"] = source_analyzer_id
            seen["copy_to"] = analyzer_id
            return _OKPoller(analyzer_id, "Succeeded")

    result = copy_analyzer(
        _OKClient(),
        "invoice_v1",
        "invoice_v2",
        progress=progress_events.append,
    )
    assert result.analyzer_id == "invoice_v2"
    assert seen == {
        "get": ["invoice_v1", "invoice_v2"],
        "copy_from": "invoice_v1",
        "copy_to": "invoice_v2",
    }
    assert progress_events == [
        "checking source analyzer 'invoice_v1'",
        "checking destination analyzer 'invoice_v2'",
        "copying 'invoice_v1' -> 'invoice_v2'; this may take several minutes",
    ]


def test_copy_analyzer_missing_source_gives_clear_error():
    """copy_analyzer raises a typed core error when the source doesn't exist."""
    from azure.core.exceptions import ResourceNotFoundError

    from cu_cli.core.analyzers import copy_analyzer

    class _MissingClient:
        def get_analyzer(self, aid):
            raise ResourceNotFoundError(message=f"no such analyzer: {aid}")

    with pytest.raises(NotFoundError) as ei:
        copy_analyzer(_MissingClient(), "invoice_v1", "invoice_v2")
    assert "source analyzer 'invoice_v1' was not found" in ei.value.message
    assert ei.value.hint is not None
    assert "cu analyzer list" in ei.value.hint


def test_copy_analyzer_409_hints_to_delete_destination_first():
    """copy_analyzer surfaces a 409 with a versioned-ID recommendation.

    Existing destinations must stop without mutation and recommend a new/versioned
    ID. The hint must recommend the versioned-ID path first, and mention the
    delete-then-retry fallback for users who really want to overwrite.
    """
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import copy_analyzer

    conflict = HttpResponseError()
    conflict.status_code = 409

    class _ConflictClient:
        def get_analyzer(self, aid):
            if aid == "invoice_v1":
                return _A(aid)
            _raise_missing(aid)

        def begin_copy_analyzer(self, **_):
            raise conflict

    with pytest.raises(ConflictError) as ei:
        copy_analyzer(_ConflictClient(), "invoice_v1", "invoice_v2")
    assert "destination analyzer 'invoice_v2' already exists" in ei.value.message
    assert ei.value.hint is not None
    # Recommend a versioned destination first so the old copy remains available.
    assert "versioned" in ei.value.hint.lower()
    assert "invoice_v2_v2" in ei.value.hint
    # Spec: also mention the delete fallback for users who want to overwrite.
    assert "cu analyzer delete invoice_v2" in ei.value.hint


def test_copy_analyzer_non_conflict_error_is_not_swallowed():
    """A non-409 failure from begin_copy_analyzer must propagate unchanged."""
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import copy_analyzer

    boom = HttpResponseError()
    boom.status_code = 500

    class _BoomClient:
        def get_analyzer(self, aid):
            if aid == "invoice_v1":
                return _A(aid)
            _raise_missing(aid)

        def begin_copy_analyzer(self, **_):
            raise boom

    with pytest.raises(HttpResponseError):
        copy_analyzer(_BoomClient(), "invoice_v1", "invoice_v2")


def test_copy_analyzer_failed_status_becomes_cli_error():
    """A completed poller in FAILED state is treated like create_analyzer does."""
    from cu_cli.core.analyzers import copy_analyzer

    class _FailingClient:
        def get_analyzer(self, aid):
            if aid == "invoice_v1":
                return _A(aid)
            _raise_missing(aid)

        def begin_copy_analyzer(self, *, analyzer_id, **_):
            return _OKPoller(analyzer_id, status="Failed")

    with pytest.raises(ServiceError) as ei:
        copy_analyzer(_FailingClient(), "invoice_v1", "invoice_v2")
    assert "was copied but its status is FAILED" in ei.value.message
    assert ei.value.hint is not None
    assert "cu analyzer show invoice_v2" in ei.value.hint


# --- copy_analyzer cross-resource --------------------------------------------


def test_copy_analyzer_cross_resource_grants_then_copies_with_arm_and_region():
    """Cross-resource orchestrates grant on source + copy on target with the right ARM+region.

    Also asserts that ``allow_replace`` is never enabled, preserving the target.
    """
    from cu_cli.core.analyzers import copy_analyzer

    calls: list[dict] = []
    progress_events: list[str] = []

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

        def grant_copy_authorization(self, *, analyzer_id, target_azure_resource_id, target_region):
            calls.append(
                {
                    "op": "grant",
                    "analyzer_id": analyzer_id,
                    "target_arm": target_azure_resource_id,
                    "target_region": target_region,
                }
            )
            # Real SDK returns a CopyAuthorization; tests only need something non-None.
            return object()

    class _Tgt:
        def get_analyzer(self, aid):
            _raise_missing(aid)

        def begin_copy_analyzer(
            self,
            *,
            analyzer_id,
            source_analyzer_id,
            source_azure_resource_id=None,
            source_region=None,
            allow_replace=None,
        ):
            assert allow_replace in (None, False), "allow_replace must never be enabled"
            calls.append(
                {
                    "op": "copy",
                    "analyzer_id": analyzer_id,
                    "source_analyzer_id": source_analyzer_id,
                    "source_arm": source_azure_resource_id,
                    "source_region": source_region,
                    "allow_replace": allow_replace,
                }
            )
            return _OKPoller(analyzer_id, "Succeeded")

    result = copy_analyzer(
        _Src(),
        "invoice_dev",
        "invoice_prod",
        target_client=_Tgt(),
        source_azure_resource_id="/subscriptions/SRC/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src-acct",
        source_region="eastus",
        target_azure_resource_id="/subscriptions/TGT/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt-acct",
        target_region="westus",
        progress=progress_events.append,
    )
    assert result.analyzer_id == "invoice_prod"

    # Grant first, then copy, in that order.
    assert [c["op"] for c in calls] == ["grant", "copy"]

    # Grant sees the source analyzer + target ARM/region.
    g = calls[0]
    assert g["analyzer_id"] == "invoice_dev"
    assert g["target_arm"].endswith("/tgt-acct")
    assert g["target_region"] == "westus"

    # Copy sees the target analyzer + source ARM/region.
    c = calls[1]
    assert c["analyzer_id"] == "invoice_prod"
    assert c["source_analyzer_id"] == "invoice_dev"
    assert c["source_arm"].endswith("/src-acct")
    assert c["source_region"] == "eastus"
    assert c["allow_replace"] in (None, False)

    # Progress lines were emitted for both actions and contain the target ARM.
    assert any("granting temporary copy authorization" in e for e in progress_events)
    assert any("copying 'invoice_dev'" in e for e in progress_events)


def test_copy_analyzer_cross_resource_requires_all_arm_and_region_args():
    """Missing ARM/region on either side is a hard error before service calls."""
    from cu_cli.core.analyzers import copy_analyzer

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

    class _Tgt:
        def begin_copy_analyzer(self, **_):
            raise AssertionError("must not be called")

    with pytest.raises(UsageError) as ei:
        copy_analyzer(
            _Src(),
            "src",
            "tgt",
            target_client=_Tgt(),
            # Deliberately omit target_azure_resource_id / target_region.
            source_azure_resource_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
            source_region="eastus",
        )
    assert "requires source and destination Azure resource IDs and regions" in ei.value.message


def test_copy_analyzer_cross_resource_grant_auth_error_gives_source_hint():
    """A 401/403 on the grant step calls out the source resource specifically."""
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import copy_analyzer

    forbidden = HttpResponseError()
    forbidden.status_code = 403

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

        def grant_copy_authorization(self, **_):
            raise forbidden

    class _Tgt:
        def get_analyzer(self, aid):
            _raise_missing(aid)

        def begin_copy_analyzer(self, **_):
            raise AssertionError("must not be called after grant failure")

    with pytest.raises(AuthenticationError) as ei:
        copy_analyzer(
            _Src(),
            "src",
            "tgt",
            target_client=_Tgt(),
            source_azure_resource_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
            source_region="eastus",
            target_azure_resource_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt",
            target_region="westus",
        )
    assert "source" in ei.value.message.lower()
    assert "Cognitive Services User" in (ei.value.hint or "")


def test_copy_analyzer_cross_resource_destination_auth_error_gives_destination_hint():
    """A 401/403 on the copy step calls out the destination specifically."""
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import copy_analyzer

    forbidden = HttpResponseError()
    forbidden.status_code = 401

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

        def grant_copy_authorization(self, **_):
            return object()

    class _Tgt:
        def get_analyzer(self, aid):
            _raise_missing(aid)

        def begin_copy_analyzer(self, **_):
            raise forbidden

    with pytest.raises(AuthenticationError) as ei:
        copy_analyzer(
            _Src(),
            "src",
            "tgt",
            target_client=_Tgt(),
            source_azure_resource_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
            source_region="eastus",
            target_azure_resource_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt",
            target_region="westus",
        )
    assert "destination" in ei.value.message.lower()
    assert "Cognitive Services User" in (ei.value.hint or "")
    assert "re-run" in (ei.value.hint or "") or "fresh one" in (ei.value.hint or "")


def test_get_copy_source_analyzer_auth_error_gives_source_hint():
    """Dependency preflight source lookup uses the same source-specific guidance."""
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import get_copy_source_analyzer

    forbidden = HttpResponseError(message="Forbidden")
    forbidden.status_code = 403

    class _ForbiddenSource:
        def get_analyzer(self, aid):
            raise forbidden

    with pytest.raises(AuthenticationError) as ei:
        get_copy_source_analyzer(_ForbiddenSource(), "src")
    assert "source analyzer lookup" in ei.value.message
    assert "source" in (ei.value.hint or "").lower()
    assert "Cognitive Services User" in (ei.value.hint or "")


def test_copy_analyzer_existing_destination_stops_before_grant():
    """Destination presence is checked before grant with scoped recovery."""
    from cu_cli.core.analyzers import copy_analyzer

    calls: list[str] = []

    class _Src:
        def get_analyzer(self, aid):
            calls.append("get-source")
            return _A(aid)

        def grant_copy_authorization(self, **_):
            calls.append("grant")
            raise AssertionError("grant must not run when target already exists")

    class _Tgt:
        def get_analyzer(self, aid):
            calls.append("get-target")
            return _A(aid)

    with pytest.raises(ConflictError) as ei:
        copy_analyzer(
            _Src(),
            "src",
            "tgt",
            target_client=_Tgt(),
            source_azure_resource_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
            source_region="eastus",
            target_azure_resource_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt",
            target_region="westus",
            target_cli_options="--endpoint https://tgt.example/ --auth-mode login",
        )
    assert calls == ["get-source", "get-target"]
    assert "already exists" in ei.value.message
    assert "cu analyzer delete tgt --endpoint https://tgt.example/ --auth-mode login" in (
        ei.value.hint or ""
    )


def test_copy_analyzer_cross_resource_409_race_uses_destination_scoped_hint():
    """A post-preflight 409 remains safe and never prints an unqualified delete."""
    from azure.core.exceptions import HttpResponseError

    from cu_cli.core.analyzers import copy_analyzer

    conflict = HttpResponseError(message="Conflict")
    conflict.status_code = 409

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

        def grant_copy_authorization(self, **_):
            return object()

    class _Tgt:
        def get_analyzer(self, aid):
            _raise_missing(aid)

        def begin_copy_analyzer(self, **_):
            raise conflict

    with pytest.raises(ConflictError) as ei:
        copy_analyzer(
            _Src(),
            "src",
            "tgt",
            target_client=_Tgt(),
            source_azure_resource_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
            source_region="eastus",
            target_azure_resource_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt",
            target_region="westus",
            target_cli_options="--profile prod",
        )
    assert "cu analyzer delete tgt --profile prod" in (ei.value.hint or "")


def test_copy_analyzer_cross_resource_failed_status_uses_destination_show_hint():
    """A failed destination LRO points ``show`` at its profile, not active/source."""
    from cu_cli.core.analyzers import copy_analyzer

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

        def grant_copy_authorization(self, **_):
            return object()

    class _Tgt:
        def get_analyzer(self, aid):
            _raise_missing(aid)

        def begin_copy_analyzer(self, *, analyzer_id, **_):
            return _OKPoller(analyzer_id, status="Failed")

    with pytest.raises(ServiceError) as ei:
        copy_analyzer(
            _Src(),
            "src",
            "tgt",
            target_client=_Tgt(),
            source_azure_resource_id="/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src",
            source_region="eastus",
            target_azure_resource_id="/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt",
            target_region="westus",
            target_cli_options="--profile prod",
        )
    assert "cu analyzer show tgt --profile prod" in (ei.value.hint or "")


# --- Dependency collection + preflight ---------------------------------------


def test_collect_custom_dependencies_walks_categories():
    """Walk the SDK's category-name -> definition mapping; skip prebuilt refs."""
    from cu_cli.core.analyzers import collect_custom_dependencies
    from types import SimpleNamespace

    src = SimpleNamespace(
        analyzer_id="my_classifier_v1",
        config=SimpleNamespace(
            content_categories={
                "invoice": SimpleNamespace(analyzer_id="my_invoice_v1"),
                "prebuilt": SimpleNamespace(analyzer_id="prebuilt-invoice"),  # skipped
                "receipt": SimpleNamespace(analyzer_id="my_receipt_v1"),
                "no-ref": SimpleNamespace(analyzer_id=None),  # skipped
                "invoice-duplicate": SimpleNamespace(analyzer_id="my_invoice_v1"),  # dedup
            }
        ),
    )
    assert collect_custom_dependencies(src) == ["my_invoice_v1", "my_receipt_v1"]


def test_collect_custom_dependencies_empty_when_no_categories():
    from cu_cli.core.analyzers import collect_custom_dependencies
    from types import SimpleNamespace

    src = SimpleNamespace(analyzer_id="plain", config=SimpleNamespace(content_categories=None))
    assert collect_custom_dependencies(src) == []


def test_preflight_dependencies_reports_missing_on_target():
    """Any 404 dependency is listed; existing ones are omitted."""
    from azure.core.exceptions import ResourceNotFoundError

    from cu_cli.core.analyzers import preflight_dependencies_on_target

    class _Target:
        _present = {"my_invoice_v1"}

        def get_analyzer(self, aid):
            if aid in self._present:
                return _A(aid)
            raise ResourceNotFoundError(message=f"no {aid}")

    missing = preflight_dependencies_on_target(_Target(), ["my_invoice_v1", "my_receipt_v1"])
    assert missing == ["my_receipt_v1"]


def test_preflight_dependencies_empty_input():
    from cu_cli.core.analyzers import preflight_dependencies_on_target

    class _Never:
        def get_analyzer(self, aid):  # pragma: no cover - not reached
            raise AssertionError("must not be called on empty deps")

    assert preflight_dependencies_on_target(_Never(), []) == []


def test_copy_analyzer_progress_never_leaks_authorization_material():
    """Cross-resource progress lines must not contain any CopyAuthorization payload.

    This is the "secret redaction" ADO test: the ``progress`` callable is the
    only user-visible surface for cross-resource actions, so it must stay
    scrubbed if the SDK model grows sensitive fields in a future version.
    """
    import datetime

    from azure.ai.contentunderstanding.models import CopyAuthorization

    from cu_cli.core.analyzers import copy_analyzer

    source_path = "/subscriptions/S/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/src"
    target_path = "/subscriptions/T/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/tgt"
    expiry = datetime.datetime(2026, 8, 25, 12, tzinfo=datetime.timezone.utc)
    copy_authorization = CopyAuthorization(
        source=source_path,
        target_azure_resource_id=target_path,
        expires_at=expiry,
    )

    class _Src:
        def get_analyzer(self, aid):
            return _A(aid)

        def grant_copy_authorization(self, **_):
            return copy_authorization

    class _Tgt:
        def get_analyzer(self, aid):
            _raise_missing(aid)

        def begin_copy_analyzer(self, *, analyzer_id, **_):
            return _OKPoller(analyzer_id, "Succeeded")

    messages: list[str] = []
    copy_analyzer(
        _Src(),
        "src_v1",
        "tgt_v1",
        target_client=_Tgt(),
        source_azure_resource_id=source_path,
        source_region="eastus",
        target_azure_resource_id=target_path,
        target_region="westus",
        progress=messages.append,
    )

    combined = "\n".join(messages)
    # The grant action names its intended target, but no returned-record-only
    # fields (source or expiration) are rendered or persisted.
    assert source_path not in combined
    assert expiry.isoformat() not in combined
    # Positive: the *action* labels are visible (transparency requirement from the spec).
    assert any("granting temporary copy authorization" in m for m in messages)
    assert any("copying 'src_v1' -> 'tgt_v1'" in m for m in messages)
