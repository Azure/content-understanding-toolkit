# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

from pathlib import Path

import pytest

from cu_cli_core.contracts import (
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
from cu_cli_core.operations.profiles import (
    copy_profile,
    create_profile,
    delete_profile,
    get_profile_value,
    list_profiles,
    rename_profile,
    set_active_profile,
    set_profile_value,
    show_profile,
    sync_profile_models,
    unset_profile_value,
)

pytestmark = pytest.mark.unit


def test_profile_operations_cover_full_lifecycle(tmp_path: Path):
    path = tmp_path / ".azure" / "config"

    set_profile_value(
        ProfileSetRequest(key="endpoint", value="https://default.example/"),
        path=path,
    )
    create_profile(ProfileCreateRequest(name="dev"), path=path)
    set_profile_value(
        ProfileSetRequest(
            key="endpoint",
            value="https://dev.example/",
            name="dev",
        ),
        path=path,
    )
    set_active_profile(ProfileSetActiveRequest(name="dev"), path=path)

    active, names = list_profiles(ProfileListRequest(), path=path)
    assert active == "dev"
    assert names == ("default", "dev")
    assert (
        get_profile_value(ProfileGetRequest(key="endpoint"), path=path)
        == "https://dev.example/"
    )
    assert show_profile(
        ProfileShowRequest(),
        path=path,
        include_environment=False,
    ).profile_name == "dev"

    sync_profile_models(
        ProfileSyncModelsRequest(),
        {"gpt-5.2": "gpt-prod"},
        path=path,
    )
    copy_profile(
        ProfileCopyRequest(source="dev", destination="test"),
        path=path,
    )
    rename_profile(
        ProfileRenameRequest(source="test", destination="prod"),
        path=path,
    )
    unset_profile_value(
        ProfileUnsetRequest(key="endpoint", name="prod"),
        path=path,
    )
    delete_profile(ProfileDeleteRequest(name="prod"), path=path)

    assert list_profiles(ProfileListRequest(), path=path)[1] == ("default", "dev")
