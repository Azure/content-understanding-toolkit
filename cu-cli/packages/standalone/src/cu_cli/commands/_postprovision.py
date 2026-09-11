# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Standalone adapter for the versioned generated-project postprovision contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Sequence

import rich_click as click

from cu_cli_core.command_spec import INFRA_POSTPROVISION_V1
from cu_cli_core.defaults import apply_defaults
from cu_cli_core.postprovision import (
    DeploymentState,
    PostprovisionCapabilities,
    PostprovisionRequest,
    execute_postprovision,
)
from cu_cli_core.profiles import ProfileStore

from ..client import build_client
from ..profile import Profile
from ..output import console
from ._help import common_commands


def _run(command: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=capture, text=True)


def _azd_values() -> dict[str, str]:
    result = _run(["azd", "env", "get-values"])
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "azd env get-values failed").strip())
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition("=")
        if separator:
            values[name] = value.strip().strip('"')
    return values


def _true(value: str | None) -> bool:
    return str(value or "").casefold() == "true"


def _request_from_environment() -> PostprovisionRequest:
    values = _azd_values()
    return PostprovisionRequest(
        endpoint=values.get("FOUNDRY_ENDPOINT", ""),
        project_name=values.get("FOUNDRY_PROJECT_NAME", ""),
        account_name=values.get("FOUNDRY_RESOURCE_NAME", ""),
        resource_group=values.get("AZURE_RESOURCE_GROUP", ""),
        subscription_id=values.get("AZURE_SUBSCRIPTION_ID", ""),
        existing_endpoint=values.get("FOUNDRY_EXISTING_ENDPOINT", ""),
        api_version=values.get("CU_API_VERSION") or "2025-11-01",
        model_selection=values.get("CU_MODEL_SELECTION") or "prompt",
        model_setup_complete=_true(values.get("CU_MODEL_SETUP_COMPLETE")),
        assign_roles=_true(values.get("AZD_ASSIGN_ROLES")),
        force_profile_setup=_true(values.get("CU_PROFILE_SETUP_FORCE")),
        disable_profile_setup=(
            _true(os.getenv("CU_DISABLE_AUTO_PROFILE_SETUP"))
            or str(os.getenv("CU_AUTOCONFIG", "")).casefold() == "false"
        ),
    )


class _StandaloneCapabilities(PostprovisionCapabilities):
    def __init__(self) -> None:
        self._profile: Profile | None = None

    def setup_models(self, request: PostprovisionRequest) -> None:
        executable = shutil.which("cu-cli") or shutil.which("cu") or sys.argv[0]
        command = [
            executable,
            "_infra-models",
            "--resource-group",
            request.resource_group,
            "--account",
            request.account_name,
            "--subscription",
            request.subscription_id,
            "--selection",
            request.model_selection,
            "--out",
            os.fspath(Path("infra/models.json")),
            "--deploy",
            "--endpoint",
            request.endpoint,
            "--api-version",
            request.api_version,
        ]
        env = os.environ.copy()
        if request.assign_roles:
            command.extend(("--auth-mode", "login"))
        else:
            env["CU_API_KEY"] = self.get_account_key(request)
            env["CU_AUTH_MODE"] = "key"
        result = subprocess.run(command, check=False, env=env)
        if result.returncode != 0:
            raise RuntimeError("model command returned a nonzero exit code")

    def mark_model_setup_complete(self) -> None:
        result = _run(["azd", "env", "set", "CU_MODEL_SETUP_COMPLETE", "true"])
        if result.returncode != 0:
            raise RuntimeError((result.stderr or "could not save model setup state").strip())

    def profile_has_values(self, name: str) -> bool:
        return bool(ProfileStore.load().get_profile(name))

    def set_profile_value(self, name: str, key: str, value: str) -> None:
        store = ProfileStore.load()
        store.set(key, value, name=name)
        store.save()
        self._profile = None

    def get_account_key(self, request: PostprovisionRequest) -> str:
        az = shutil.which("az")
        if not az:
            raise RuntimeError("Azure CLI 'az' was not found")
        login = _run([az, "account", "show", "--subscription", request.subscription_id, "--only-show-errors"])
        if login.returncode != 0:
            raise RuntimeError("Azure CLI is not logged in for the generated subscription")
        result = _run(
            [
                az,
                "cognitiveservices",
                "account",
                "keys",
                "list",
                "-g",
                request.resource_group,
                "-n",
                request.account_name,
                "--subscription",
                request.subscription_id,
                "--query",
                "key1",
                "-o",
                "tsv",
            ]
        )
        key = result.stdout.strip()
        if result.returncode != 0 or not key:
            raise RuntimeError("could not obtain a Microsoft Foundry resource key")
        return key

    def list_deployments(self, request: PostprovisionRequest) -> Sequence[DeploymentState]:
        az = shutil.which("az")
        if not az:
            return ()
        result = _run(
            [
                az,
                "cognitiveservices",
                "account",
                "deployment",
                "list",
                "-g",
                request.resource_group,
                "-n",
                request.account_name,
                "--subscription",
                request.subscription_id,
                "-o",
                "json",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError("Azure CLI could not list model deployments")
        payload = json.loads(result.stdout or "[]")
        return tuple(
            DeploymentState(
                name=str(item.get("name") or ""),
                model_name=str(item.get("properties", {}).get("model", {}).get("name") or ""),
                succeeded=item.get("properties", {}).get("provisioningState") == "Succeeded",
            )
            for item in payload
            if item.get("name") and item.get("properties", {}).get("model", {}).get("name")
        )

    def configure_defaults(self, request: PostprovisionRequest, mappings: dict[str, str]) -> None:
        del request
        profile = Profile.load(profile_name="default")
        client: Any = build_client(profile)
        apply_defaults(client, mappings, replace=False)


@click.command(
    INFRA_POSTPROVISION_V1.path[0],
    hidden=True,
    epilog=common_commands(("cu doctor", "Verify postprovision setup.")),
)
def cmd_postprovision_v1() -> None:
    """Run the v1 generated-project postprovision state machine."""

    result = execute_postprovision(_request_from_environment(), _StandaloneCapabilities())
    for message in result.messages:
        console.print(message)
    if not result.succeeded:
        raise click.exceptions.Exit(1)
