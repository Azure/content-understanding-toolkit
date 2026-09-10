# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Thin command entry points for the Content Understanding extension."""

from __future__ import annotations

from typing import Any, Callable

from cu_cli_core.serialization import to_plain_value

from . import _analysis, _analyzers, _defaults, _diagnostics, _infra, _infra_models as _infra_models_feature, _profiles
from ._errors import azure_cli_error


def _invoke(function: Callable[..., Any], cmd: Any, values: dict[str, Any]) -> Any:
    try:
        return to_plain_value(function(cmd, **values))
    except Exception as exc:  # Azure CLI owns final rendering and exit behavior.
        raise azure_cli_error(exc) from exc


def analyzer__list(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.list_analyzers, cmd, kwargs)


def analyzer__show(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.show_analyzer, cmd, kwargs)


def analyzer__create(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.create_analyzer, cmd, kwargs)


def analyzer__delete(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.delete_analyzer, cmd, kwargs)


def analyzer__validate(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.validate_analyzer, cmd, kwargs)


def analyzer__schema__create(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.create_analyzer_schema, cmd, kwargs)


def analyzer__test(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.test_analyzer, cmd, kwargs)


def analyzer__copy(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analyzers.copy_analyzer, cmd, kwargs)


def analyze(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_analysis.analyze, cmd, kwargs)


def defaults__show(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_defaults.show_defaults, cmd, kwargs)


def defaults__set(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_defaults.set_defaults, cmd, kwargs)


def profile__show(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.show_profile, cmd, kwargs)


def profile__list(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.list_profiles, cmd, kwargs)


def profile__get(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.get_profile, cmd, kwargs)


def profile__set(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.set_profile, cmd, kwargs)


def profile__unset(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.unset_profile, cmd, kwargs)


def profile__create(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.create_profile, cmd, kwargs)


def profile__delete(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.delete_profile, cmd, kwargs)


def profile__copy(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.copy_profile, cmd, kwargs)


def profile__rename(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.rename_profile, cmd, kwargs)


def profile__set_active(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.set_active_profile, cmd, kwargs)


def profile__sync_defaults(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_profiles.sync_profile_defaults, cmd, kwargs)


def doctor(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_diagnostics.doctor, cmd, kwargs)


def infra__generate(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_infra.generate_infrastructure, cmd, kwargs)


def _infra_models(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_infra_models_feature.setup_models, cmd, kwargs)


def env_var__list(cmd: Any, **kwargs: Any) -> Any:
    return _invoke(_diagnostics.list_environment_variables, cmd, kwargs)
