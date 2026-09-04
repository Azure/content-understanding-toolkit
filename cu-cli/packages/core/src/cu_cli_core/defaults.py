# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Client-injected CU service-default operations."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .errors import NotFoundError, ValidationError

PREFERRED_EMBEDDING_MODEL = "text-embedding-3-large"
COMPLETION_MODEL_PREFERENCE = ("gpt-5.2",)
PREBUILT_COMPLETION_KEY = "prebuilt-analyzer-completion"
PREBUILT_COMPLETION_MINI_KEY = "prebuilt-analyzer-completion-mini"
PREBUILT_EMBEDDING_KEY = "prebuilt-analyzer-embedding"


def with_prebuilt_default_mappings(
    model_deployments: Mapping[str, str],
) -> dict[str, str]:
    """Return model mappings enriched with the aliases required by prebuilt analyzers."""

    out = {str(key): str(value) for key, value in model_deployments.items()}
    model_names = list(out)

    def is_alias(name: str) -> bool:
        return name.startswith("prebuilt-analyzer-")

    completion_model = next(
        (model for model in COMPLETION_MODEL_PREFERENCE if model in out),
        None,
    )
    if completion_model is None:
        completion_model = next(
            (
                name
                for name in model_names
                if not is_alias(name)
                and not name.startswith("text-embedding-")
                and not name.endswith("-mini")
            ),
            None,
        )

    mini_model = next(
        (
            model
            for model in ("gpt-5.2-mini", "gpt-4.1-mini", "gpt-4o-mini")
            if model in out
        ),
        None,
    )
    if mini_model is None:
        mini_model = next(
            (name for name in model_names if not is_alias(name) and name.endswith("-mini")),
            None,
        )

    embedding_model = next(
        (
            name
            for name in (PREFERRED_EMBEDDING_MODEL, *sorted(model_names))
            if name in out and name.startswith("text-embedding-")
        ),
        None,
    )

    if completion_model is None and mini_model is not None:
        completion_model = mini_model
    if completion_model is not None:
        out[PREBUILT_COMPLETION_KEY] = out[completion_model]
        out[PREBUILT_COMPLETION_MINI_KEY] = (
            out[mini_model] if mini_model else out[completion_model]
        )
    if embedding_model is not None:
        out[PREBUILT_EMBEDDING_KEY] = out[embedding_model]
    return out


def is_defaults_not_set(exc: Exception) -> bool:
    """Return whether a service exception means defaults have not been configured."""

    message = getattr(exc, "message", None) or str(exc)
    return "DefaultsNotSet" in message or "Defaults have not yet been set" in message


def get_defaults(client: Any) -> Any:
    """Return service defaults from an injected client."""

    from azure.core.exceptions import HttpResponseError

    try:
        return client.get_defaults()
    except HttpResponseError as exc:
        if is_defaults_not_set(exc):
            raise NotFoundError(
                "defaults are not set yet on this resource.",
                hint="Configure model deployments, then run defaults set.",
            ) from exc
        raise


def extract_model_deployments(defaults_obj: Any) -> dict[str, str]:
    """Return a defaults object's model-deployment mapping as strings."""

    mapped = getattr(defaults_obj, "model_deployments", None) or {}
    return {str(key): str(value) for key, value in mapped.items()}


def parse_model_kv(values: Sequence[str]) -> dict[str, str]:
    """Parse repeatable ``MODEL=DEPLOYMENT`` values."""

    parsed: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValidationError(
                f"invalid --model mapping '{raw}'.",
                hint="use --model MODEL=DEPLOYMENT (repeatable).",
            )
        model, deployment = (part.strip() for part in raw.split("=", 1))
        if not model or not deployment:
            raise ValidationError(
                f"invalid --model mapping '{raw}'.",
                hint="use --model MODEL=DEPLOYMENT (repeatable).",
            )
        parsed[model] = deployment
    return parsed


def apply_defaults(
    client: Any,
    desired: Mapping[str, str],
    *,
    replace: bool,
) -> tuple[Any, dict[str, str]]:
    """Merge or replace service defaults and return the result and final mapping."""

    existing: dict[str, str] = {}
    if not replace:
        from azure.core.exceptions import HttpResponseError

        try:
            existing = extract_model_deployments(client.get_defaults())
        except HttpResponseError as exc:
            if not is_defaults_not_set(exc):
                raise
    merged = dict(desired) if replace else {**existing, **desired}
    merged = with_prebuilt_default_mappings(merged)
    return client.update_defaults(model_deployments=merged), merged
