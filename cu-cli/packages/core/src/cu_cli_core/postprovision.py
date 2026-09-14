# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Framework-neutral postprovision state machine for generated azd projects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .defaults import with_prebuilt_default_mappings

NO_MODEL_ANALYZERS = (
    "prebuilt-digitalParse",
    "prebuilt-read",
    "prebuilt-layout",
)


@dataclass(frozen=True)
class PostprovisionRequest:
    """Resolved azd state consumed by the versioned postprovision contract."""

    endpoint: str
    resource_group: str
    account_name: str
    subscription_id: str
    project_name: str = ""
    existing_endpoint: str = ""
    api_version: str = "2025-11-01"
    model_selection: str = "prompt"
    model_setup_complete: bool = False
    assign_roles: bool = False
    force_profile_setup: bool = False
    disable_profile_setup: bool = False


@dataclass(frozen=True)
class DeploymentState:
    """A model deployment relevant to profile/default configuration."""

    name: str
    model_name: str
    succeeded: bool


@dataclass(frozen=True)
class PostprovisionResult:
    """Stable result returned by both command frontends."""

    succeeded: bool
    profile_configured: bool = False
    profile_preserved: bool = False
    profile_setup_disabled: bool = False
    model_setup: str = "skipped"
    defaults_configured: bool = False
    generative_ready: bool = False
    warnings: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()


class PostprovisionCapabilities(Protocol):
    """Host operations injected by standalone and Azure CLI adapters."""

    def setup_models(self, request: PostprovisionRequest) -> None: ...

    def mark_model_setup_complete(self) -> None: ...

    def profile_has_values(self, name: str) -> bool: ...

    def set_profile_value(self, name: str, key: str, value: str) -> None: ...

    def get_account_key(self, request: PostprovisionRequest) -> str: ...

    def list_deployments(self, request: PostprovisionRequest) -> Sequence[DeploymentState]: ...

    def configure_defaults(self, request: PostprovisionRequest, mappings: dict[str, str]) -> None: ...


def _warning(warnings: list[str], messages: list[str], text: str) -> None:
    warnings.append(text)
    messages.append(text)


def execute_postprovision(
    request: PostprovisionRequest,
    capabilities: PostprovisionCapabilities,
) -> PostprovisionResult:
    """Run ordered, retry-safe setup while preserving useful partial success."""

    warnings: list[str] = []
    messages: list[str] = []
    model_setup = "skipped" if request.model_setup_complete else "pending"

    if request.model_setup_complete:
        messages.append("Model setup already completed; skipping it.")
    elif request.model_selection.casefold() == "none":
        try:
            capabilities.setup_models(request)
            capabilities.mark_model_setup_complete()
            model_setup = "completed"
            messages.append("No model deployments selected.")
        except Exception:  # Optional capability; profile setup must continue.
            model_setup = "failed"
            _warning(warnings, messages, "Optional model setup failed.")
    else:
        try:
            capabilities.setup_models(request)
            capabilities.mark_model_setup_complete()
            model_setup = "completed"
        except Exception:  # Optional capability; profile setup must continue.
            model_setup = "failed"
            _warning(warnings, messages, "Optional model setup failed.")

    if request.disable_profile_setup:
        messages.append("Automatic CU CLI profile setup disabled.")
        return PostprovisionResult(
            succeeded=True,
            profile_setup_disabled=True,
            model_setup=model_setup,
            warnings=tuple(warnings),
            messages=tuple(messages),
        )

    try:
        populated = capabilities.profile_has_values("default")
    except Exception:
        _warning(
            warnings,
            messages,
            "Could not inspect the default CU CLI profile; refusing to overwrite it.",
        )
        return PostprovisionResult(
            succeeded=False,
            model_setup=model_setup,
            warnings=tuple(warnings),
            messages=tuple(messages),
        )

    if populated and not request.force_profile_setup:
        messages.append("Default CU CLI profile already has saved values; preserving it.")
        return PostprovisionResult(
            succeeded=True,
            profile_preserved=True,
            model_setup=model_setup,
            warnings=tuple(warnings),
            messages=tuple(messages),
        )

    required_failures: list[str] = []

    def required_write(key: str, value: str, failure: str) -> None:
        try:
            capabilities.set_profile_value("default", key, value)
        except Exception:
            required_failures.append(failure)

    # Authentication must be protected before endpoint/default writes. Key material
    # is passed directly to the profile capability and never enters the result.
    if request.assign_roles:
        required_write("auth_mode", "login", "Could not configure Entra authentication")
    else:
        try:
            key = capabilities.get_account_key(request)
            if not key:
                raise RuntimeError("the Microsoft Foundry resource returned no account key")
            required_write("api_key", key, "Could not configure key authentication")
        except Exception:
            required_failures.append("Could not configure key authentication")

    required_write("endpoint", request.endpoint, "Could not configure the cu CLI endpoint")
    required_write(
        "default_analyzer",
        "prebuilt-layout",
        "Could not configure the default analyzer",
    )

    mappings: dict[str, str] = {}
    completion_ready = False
    embedding_ready = False
    try:
        deployments = capabilities.list_deployments(request)
    except Exception:
        deployments = ()
        _warning(warnings, messages, "Could not inspect optional model deployments.")

    for deployment in deployments:
        mappings[deployment.model_name] = deployment.name
        try:
            capabilities.set_profile_value(
                "default", f"model_deployments.{deployment.model_name}", deployment.name
            )
        except Exception:
            _warning(
                warnings,
                messages,
                f"Could not save optional model mapping '{deployment.model_name}'.",
            )
        if deployment.succeeded and deployment.model_name.startswith("text-embedding-"):
            embedding_ready = True
        elif deployment.succeeded:
            completion_ready = True

    defaults_configured = False
    enriched = with_prebuilt_default_mappings(mappings)
    for model, deployment_name in enriched.items():
        if model in mappings:
            continue
        try:
            capabilities.set_profile_value(
                "default", f"model_deployments.{model}", deployment_name
            )
        except Exception:
            _warning(warnings, messages, f"Could not save optional model mapping '{model}'.")

    if mappings:
        try:
            capabilities.configure_defaults(request, enriched)
            defaults_configured = True
            messages.append("Foundry defaults initialized.")
        except Exception:
            _warning(
                warnings,
                messages,
                "Could not initialize Foundry defaults automatically.",
            )

    messages.append(
        "Available without an LLM or embeddings model: " + ", ".join(NO_MODEL_ANALYZERS)
    )
    generative_ready = defaults_configured and completion_ready and embedding_ready
    if generative_ready:
        messages.append(
            "Model readiness verified: LLM and embeddings model deployments succeeded "
            "and Content Understanding defaults are configured."
        )
    elif model_setup == "failed":
        messages.append(
            "The Microsoft Foundry resource and CU CLI profile remain usable; resolve the "
            "optional model issue and rerun azd up."
        )
    elif mappings and not defaults_configured:
        messages.append("Generative AI workflows are not ready because defaults configuration failed.")
    elif mappings:
        messages.append("Generative AI workflows require succeeded LLM and embeddings deployments.")
    else:
        messages.append("No optional models were configured; content extraction analyzers remain available.")

    messages.extend(required_failures)
    if required_failures:
        messages.append("Azure provisioning completed, but cu auto-configuration is incomplete.")
        messages.append("Run the frontend's doctor command for actionable diagnostics.")

    return PostprovisionResult(
        succeeded=not required_failures,
        profile_configured=not required_failures,
        model_setup=model_setup,
        defaults_configured=defaults_configured,
        generative_ready=generative_ready,
        warnings=tuple(warnings),
        messages=tuple(messages),
    )
