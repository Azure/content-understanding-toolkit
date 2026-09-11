# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Framework-neutral Content Understanding doctor contracts and orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from .defaults import (
    PREBUILT_COMPLETION_KEY,
    PREBUILT_COMPLETION_MINI_KEY,
    PREBUILT_EMBEDDING_KEY,
    extract_model_deployments,
    is_defaults_not_set,
    with_prebuilt_default_mappings,
)
from .errors import UsageError, ValidationError
from .service_options import SUPPORTED_API_VERSIONS, is_supported_api_version


class DoctorProfile(Protocol):
    """Profile fields needed to resolve a doctor request."""

    @property
    def endpoint(self) -> str | None: ...

    @property
    def api_version(self) -> str: ...

    @property
    def auth_mode(self) -> str: ...

    @property
    def api_key(self) -> str | None: ...

    @property
    def default_analyzer(self) -> str | None: ...

    @property
    def model_deployments(self) -> Mapping[str, str]: ...

    @property
    def profile_name(self) -> str: ...


@dataclass(frozen=True)
class DoctorRequest:
    """Resolved doctor inputs. Credentials are intentionally absent from results."""

    endpoint: str
    api_version: str
    authentication: str
    profile: str
    default_analyzer: str | None
    profile_model_deployments: Mapping[str, str] = field(default_factory=dict)
    api_key: str | None = field(default=None, repr=False, compare=False)
    fix_defaults: bool = False


@dataclass(frozen=True)
class DoctorFailure:
    """A failed required readiness check."""

    check: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"check": self.check, "message": self.message}


@dataclass(frozen=True)
class DoctorResult:
    """Complete, secret-free doctor assessment shared by all frontends."""

    endpoint: str
    api_version: str
    authentication: str
    profile: str
    default_analyzer: str | None
    model_deployments: Mapping[str, str]
    missing_requirements: tuple[str, ...]
    failures: tuple[DoctorFailure, ...] = ()
    defaults_configured: bool = True
    defaults_updated: bool = False

    @property
    def ready(self) -> bool:
        return not self.failures and not self.missing_requirements

    @property
    def required_checks_passed(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical frontend-neutral structured representation."""

        return {
            "ready": self.ready,
            "endpoint": self.endpoint,
            "apiVersion": self.api_version,
            "authentication": self.authentication,
            "profile": self.profile,
            "defaultAnalyzer": self.default_analyzer,
            "modelDeployments": dict(self.model_deployments),
            "missingRequirements": list(self.missing_requirements),
            "failures": [failure.to_dict() for failure in self.failures],
        }


def resolve_doctor_request(
    profile: DoctorProfile,
    *,
    endpoint: str | None = None,
    api_version: str | None = None,
    auth_mode: str | None = None,
    api_key: str | None = None,
    fix_defaults: bool = False,
) -> DoctorRequest:
    """Resolve explicit doctor options over one already-loaded profile."""

    resolved_endpoint = endpoint or profile.endpoint
    if not resolved_endpoint:
        raise UsageError(
            "No Content Understanding endpoint is configured.",
            hint="pass --endpoint or configure an endpoint in the selected CU CLI profile.",
        )
    resolved_version = api_version or profile.api_version
    if not is_supported_api_version(resolved_version):
        raise ValidationError(
            f"API version {resolved_version} is not supported by this CLI build.",
            hint=f"supported versions: {', '.join(SUPPORTED_API_VERSIONS)}, or any YYYY-MM-DD-preview version.",
        )
    resolved_auth = auth_mode or ("key" if api_key else profile.auth_mode)
    if resolved_auth not in {"login", "key", "entra"}:
        raise ValidationError("auth mode must be 'login' or 'key'.")
    resolved_key = api_key or profile.api_key
    if resolved_auth == "key" and not resolved_key:
        raise UsageError(
            "--auth-mode key requires an API key.",
            hint="pass --api-key or configure api_key in the selected CU CLI profile.",
        )
    authentication = "resource key" if resolved_auth == "key" else "Microsoft Entra ID"
    return DoctorRequest(
        endpoint=resolved_endpoint,
        api_version=resolved_version,
        authentication=authentication,
        profile=profile.profile_name,
        default_analyzer=profile.default_analyzer,
        profile_model_deployments=dict(profile.model_deployments),
        api_key=resolved_key if resolved_auth == "key" else None,
        fix_defaults=fix_defaults,
    )


def missing_requirements(mapped: Mapping[str, str]) -> tuple[str, ...]:
    """Return generative-model requirements not satisfied by a defaults mapping."""

    missing: list[str] = []
    has_embedding = bool(mapped.get(PREBUILT_EMBEDDING_KEY)) or any(
        name.startswith("text-embedding-") for name in mapped
    )
    if not has_embedding:
        missing.append("an embeddings model (for example text-embedding-3-large)")
    has_completion = bool(mapped.get(PREBUILT_COMPLETION_KEY)) or any(
        not name.startswith(("prebuilt-analyzer-", "text-embedding-")) for name in mapped
    )
    if not has_completion:
        missing.append("a supported large language model (LLM) deployment")
    if not mapped.get(PREBUILT_COMPLETION_MINI_KEY):
        missing.append("Content Understanding's prebuilt analyzer mapping for the selected LLM")
    return tuple(missing)


def _safe_failure_message(exc: Exception, secret: str | None) -> str:
    message = str(exc)
    if secret:
        message = message.replace(secret, "***redacted***")
    return message


def assess_doctor(
    request: DoctorRequest,
    client_factory: Callable[[DoctorRequest], Any],
) -> DoctorResult:
    """Read one defaults snapshot, optionally update it once, and assess readiness."""

    mappings: dict[str, str] = {}
    defaults_configured = True
    try:
        client = client_factory(request)
        try:
            mappings = extract_model_deployments(client.get_defaults())
        except Exception as exc:  # service SDK exception types belong to adapters
            if not is_defaults_not_set(exc):
                raise
            defaults_configured = False

        updated = False
        if request.fix_defaults:
            merged = {**mappings, **request.profile_model_deployments}
            merged = with_prebuilt_default_mappings(merged)
            if not merged:
                raise UsageError(
                    "cannot set defaults: no model deployment mapping is configured",
                    hint="set model mappings in the selected profile, then rerun doctor --fix-defaults.",
                )
            client.update_defaults(model_deployments=merged)
            mappings = merged
            defaults_configured = True
            updated = True
        return DoctorResult(
            endpoint=request.endpoint,
            api_version=request.api_version,
            authentication=request.authentication,
            profile=request.profile,
            default_analyzer=request.default_analyzer,
            model_deployments=mappings,
            missing_requirements=missing_requirements(mappings),
            defaults_configured=defaults_configured,
            defaults_updated=updated,
        )
    except UsageError:
        raise
    except Exception as exc:
        failure = DoctorFailure(
            check="connectivity",
            message=_safe_failure_message(exc, request.api_key),
        )
        return DoctorResult(
            endpoint=request.endpoint,
            api_version=request.api_version,
            authentication=request.authentication,
            profile=request.profile,
            default_analyzer=request.default_analyzer,
            model_deployments={},
            missing_requirements=(),
            failures=(failure,),
            defaults_configured=False,
        )