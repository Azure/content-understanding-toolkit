"""Unit tests for `cu doctor` — helpers and command flows (no network)."""

from __future__ import annotations

from click.testing import CliRunner

from cu_cli.cli import main
from cu_cli.commands.doctor import _is_defaults_not_set, _missing_requirements



import pytest

pytestmark = pytest.mark.unit

def _run(*args):
    return CliRunner().invoke(main, list(args))


# --- helper: _is_defaults_not_set ------------------------------------------


def test_is_defaults_not_set_true_for_matching_message():
    from azure.core.exceptions import HttpResponseError

    assert _is_defaults_not_set(HttpResponseError(message="DefaultsNotSet: ...")) is True
    assert _is_defaults_not_set(
        HttpResponseError(message="Defaults have not yet been set")
    ) is True


def test_is_defaults_not_set_false_for_other_errors():
    from azure.core.exceptions import HttpResponseError

    assert _is_defaults_not_set(ValueError("nope")) is False
    assert _is_defaults_not_set(HttpResponseError(message="Something else")) is False


# --- helper: _missing_requirements -----------------------------------------


def test_missing_requirements_empty_reports_all():
    missing = _missing_requirements({})
    assert any("text-embedding-3-large" in m for m in missing)
    assert any("large language model" in m for m in missing)
    assert any("prebuilt analyzer mapping" in m for m in missing)


def test_missing_requirements_satisfied_direct_models():
    mapped = {
        "text-embedding-3-large": "emb",
        "gpt-5.2": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    }
    assert _missing_requirements(mapped) == []


def test_missing_requirements_completion_via_prebuilt_alias():
    mapped = {
        "text-embedding-3-large": "emb",
        "prebuilt-analyzer-completion": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    }
    assert _missing_requirements(mapped) == []


def test_missing_requirements_accepts_live_embedding_family_and_alias():
    direct = {
        "text-embedding-3-small": "emb",
        "gpt-5.2": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    }
    assert _missing_requirements(direct) == []

    alias = {
        "prebuilt-analyzer-embedding": "emb",
        "prebuilt-analyzer-completion": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    }
    assert _missing_requirements(alias) == []


def test_missing_requirements_accepts_live_completion_family():
    mapped = {
        "text-embedding-3-large": "emb",
        "gpt-5.5": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    }
    assert _missing_requirements(mapped) == []


# --- command flows (mocked client) -----------------------------------------


class _FakeDefaults:
    def __init__(self, mapping):
        self.model_deployments = mapping


class _FakeClient:
    def __init__(self, mapping=None, raise_exc=None):
        self._mapping = mapping or {}
        self._raise = raise_exc
        self.updated = None

    def get_defaults(self):
        if self._raise is not None:
            raise self._raise
        return _FakeDefaults(self._mapping)

    def update_defaults(self, *, model_deployments):
        self.updated = model_deployments


def _set_endpoint():
    res = _run("profile", "set", "endpoint",
               "https://x.services.ai.azure.com/")
    assert res.exit_code == 0, res.output


def test_doctor_all_checks_pass(monkeypatch):
    _set_endpoint()
    fake = _FakeClient({
        "text-embedding-3-large": "emb",
        "gpt-5.2": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    })
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *a, **k: fake)
    res = _run("doctor")
    assert res.exit_code == 0, res.output
    assert "Configuration check complete. CU CLI is ready." in res.output
    assert "Checking Content Understanding defaults" in res.output
    assert "get_defaults()" not in res.output


def test_doctor_missing_mappings_still_exits_zero(monkeypatch):
    _set_endpoint()
    fake = _FakeClient({"gpt-5.2": "cmp"})  # no embedding / mini
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *a, **k: fake)
    res = _run("doctor")
    assert res.exit_code == 0, res.output
    output = " ".join(res.output.split())
    assert "Setup needed for analyzers that use generative AI" in output
    assert "--models recommended" in output
    assert "choose your own models in the text-based wizard" in output
    assert "Replace both model names" in output
    assert "with the models and deployments you selected" in output
    assert "cu profile sync-defaults" in output


def test_doctor_service_unreachable_exits_nonzero(monkeypatch):
    _set_endpoint()
    fake = _FakeClient(raise_exc=RuntimeError("boom"))
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *a, **k: fake)
    res = _run("doctor")
    assert res.exit_code != 0
    assert "Could not connect to the service" in res.output


def test_doctor_non_https_login_endpoint_is_actionable_and_not_redacted():
    res = _run(
        "doctor",
        "--endpoint",
        "http://not-https.example.invalid",
        "--auth-mode",
        "login",
    )

    assert res.exit_code == 1
    assert "authentication mode 'login' requires an HTTPS endpoint" in res.output
    assert "update the endpoint to use https://" in res.output
    assert "******" not in res.output


def test_doctor_defaults_not_set_hint(monkeypatch):
    from azure.core.exceptions import HttpResponseError

    _set_endpoint()
    fake = _FakeClient(raise_exc=HttpResponseError(message="DefaultsNotSet"))
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *a, **k: fake)
    res = _run("doctor")
    assert res.exit_code == 0, res.output
    assert "Content Understanding defaults are not configured" in res.output
    assert res.output.index("--models recommended") < res.output.index("cu defaults set")


def test_doctor_fix_defaults_calls_update(monkeypatch):
    _set_endpoint()
    assert _run(
        "profile", "set", "model_deployments.gpt-5.2", "dep-gpt"
    ).exit_code == 0
    assert _run(
        "profile", "set", "model_deployments.text-embedding-3-large", "dep-emb"
    ).exit_code == 0
    fake = _FakeClient({})
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *a, **k: fake)
    res = _run("doctor", "--fix-defaults")
    assert res.exit_code == 0, res.output
    assert "Content Understanding defaults updated" in res.output
    assert fake.updated is not None
    assert fake.updated.get("gpt-5.2") == "dep-gpt"
    assert fake.updated.get("text-embedding-3-large") == "dep-emb"


def test_doctor_explains_missing_default_analyzer(monkeypatch):
    _set_endpoint()
    fake = _FakeClient({
        "text-embedding-3-large": "emb",
        "gpt-5.2": "cmp",
        "prebuilt-analyzer-completion-mini": "mini",
    })
    monkeypatch.setattr("cu_cli.commands.doctor.build_client", lambda *a, **k: fake)

    res = _run("doctor")

    assert res.exit_code == 0, res.output
    assert "Default analyzer: not configured" in res.output
    assert "`cu analyze` requires --analyzer" in res.output
