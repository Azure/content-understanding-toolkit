"""Shared profile operations with frontend-injected storage and discovered models."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..contracts import (
    ProfileCopyRequest,
    ProfileCreateRequest,
    ProfileDeleteRequest,
    ProfileGetRequest,
    ProfileListRequest,
    ProfileRenameRequest,
    ProfileSetActiveRequest,
    ProfileSetRequest,
    ProfileShowRequest,
    ProfileSyncModelsRequest,
    ProfileUnsetRequest,
)
from ..errors import NotFoundError
from ..profiles import Profile, ProfileStore, validate_profile_name


def show_profile(
    request: ProfileShowRequest,
    *,
    path: Path | None = None,
    include_environment: bool = True,
) -> Profile:
    loader = Profile.load if include_environment else Profile.load_saved
    return loader(profile_name=request.name, path=path)


def list_profiles(
    request: ProfileListRequest,
    *,
    path: Path | None = None,
) -> tuple[str, tuple[str, ...]]:
    del request
    store = ProfileStore.load(path)
    return store.get_active_name(), tuple(store.list_names())


def get_profile_value(
    request: ProfileGetRequest,
    *,
    path: Path | None = None,
) -> str | None:
    return ProfileStore.load(path).get(request.key, name=request.name)


def set_profile_value(
    request: ProfileSetRequest,
    *,
    path: Path | None = None,
) -> Path:
    store = ProfileStore.load(path)
    store.set(request.key, request.value, name=request.name)
    return store.save()


def unset_profile_value(
    request: ProfileUnsetRequest,
    *,
    path: Path | None = None,
) -> Path:
    store = ProfileStore.load(path)
    if not store.unset(request.key, name=request.name):
        target = request.name or store.get_active_name()
        raise NotFoundError(
            f"'{request.key}' is not saved in profile '{target}'.",
            hint="`cu profile show` includes inherited defaults and environment overrides; "
            "only explicitly saved values can be unset.",
        )
    return store.save()


def create_profile(
    request: ProfileCreateRequest,
    *,
    path: Path | None = None,
) -> Path:
    store = ProfileStore.load(path)
    store.create_name(request.name)
    return store.save()


def delete_profile(
    request: ProfileDeleteRequest,
    *,
    path: Path | None = None,
) -> Path:
    store = ProfileStore.load(path)
    store.delete_name(request.name)
    return store.save()


def copy_profile(
    request: ProfileCopyRequest,
    *,
    path: Path | None = None,
) -> tuple[Path, str]:
    store = ProfileStore.load(path)
    source = (
        store.get_active_name()
        if request.source is None
        else validate_profile_name(request.source)
    )
    store.copy_name(source, request.destination)
    return store.save(), source


def rename_profile(
    request: ProfileRenameRequest,
    *,
    path: Path | None = None,
) -> Path:
    store = ProfileStore.load(path)
    store.rename_name(request.source, request.destination)
    return store.save()


def set_active_profile(
    request: ProfileSetActiveRequest,
    *,
    path: Path | None = None,
) -> Path:
    store = ProfileStore.load(path)
    store.set_active_name(request.name)
    return store.save()


def sync_profile_models(
    request: ProfileSyncModelsRequest,
    model_deployments: Mapping[str, str],
    *,
    path: Path | None = None,
) -> tuple[Path, str]:
    store = ProfileStore.load(path)
    target = store.get_active_name() if request.name is None else request.name
    store.replace_model_deployments(model_deployments, name=target)
    return store.save(), target
