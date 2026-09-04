from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.name == "nt",
        reason="hook command stubs use POSIX executables and are covered on Unix",
    ),
]

_HOOKS = (
    Path(__file__).parents[3]
    / "src"
    / "cu_cli"
    / "resources"
    / "azd_template"
    / "hooks"
)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _stub_environment(
    tmp_path: Path,
    *,
    assign_roles: bool,
    defaults_exit: int = 0,
    deployments: list[dict[str, str]] | None = None,
    failure_match: str = "",
    profile_has_values: bool = False,
    profile_setup_force: bool = False,
    disable_profile_setup: bool = False,
) -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    call_log = tmp_path / "calls.log"
    azd_values = "\n".join(
        [
            'FOUNDRY_ENDPOINT="https://example.services.ai.azure.com/"',
            'FOUNDRY_PROJECT_NAME="example-project"',
            'FOUNDRY_RESOURCE_NAME="example-account"',
            'AZURE_RESOURCE_GROUP="example-rg"',
            f'AZD_ASSIGN_ROLES="{str(assign_roles).lower()}"',
            f'CU_PROFILE_SETUP_FORCE="{str(profile_setup_force).lower()}"',
        ]
    )
    deployments = deployments if deployments is not None else [
        {"name": "gpt", "model": "gpt-5.2", "state": "Succeeded"},
        {
            "name": "embedding",
            "model": "text-embedding-3-large",
            "state": "Succeeded",
        },
    ]
    deployments_json = json.dumps(
        [
            {
                "name": deployment["name"],
                "properties": {
                    "model": {"name": deployment["model"]},
                    "provisioningState": deployment["state"],
                },
            }
            for deployment in deployments
        ]
    )
    deployments_tsv = "\n".join(
        f"{deployment['name']}\t{deployment['model']}\t{deployment['state']}"
        for deployment in deployments
    )
    _write_executable(
        bin_dir / "azd",
        f"""#!/bin/sh
printf '%s\n' "$*" >> "$CALL_LOG"
if [ "$*" = "env get-values" ]; then
  cat <<'EOF'
{azd_values}
EOF
fi
""",
    )
    _write_executable(
        bin_dir / "az",
        """#!/bin/sh
printf 'az %s\n' "$*" >> "$CALL_LOG"
case "$*" in
  "account show --only-show-errors")
    exit 0
    ;;
  *"account keys list"*)
    printf '%s\n' "fake-account-key"
    ;;
  *"account deployment list"*)
    case "$*" in
      *"-o json"*)
        printf '%s\n' "$AZ_DEPLOYMENTS_JSON"
        ;;
      *)
        printf '%s\n' "$AZ_DEPLOYMENTS_TSV"
        ;;
    esac
    ;;
esac
""",
    )
    _write_executable(
        bin_dir / "cu-cli",
        """#!/bin/sh
printf 'cu-cli %s\n' "$*" >> "$CALL_LOG"
case "$*" in
  "profile _has-values --name default")
    exit "$PROFILE_HAS_VALUES"
    ;;
  "profile show --name default")
    printf '%s\n' "CU CLI profile: default"
    printf '%s\n' "endpoint  https://example.services.ai.azure.com/"
    exit 0
    ;;
  *"$CU_FAILURE_MATCH"*)
    if [ -n "$CU_FAILURE_MATCH" ]; then
      exit 23
    fi
    ;;
esac
if [ "$*" = "defaults set --from-profile --profile default" ]; then
  exit "$DEFAULTS_EXIT"
fi
exit 0
""",
    )
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "CALL_LOG": str(call_log),
            "DEFAULTS_EXIT": str(defaults_exit),
            "CU_FAILURE_MATCH": failure_match,
            "PROFILE_HAS_VALUES": "0" if profile_has_values else "3",
            "AZ_DEPLOYMENTS_JSON": deployments_json,
            "AZ_DEPLOYMENTS_TSV": deployments_tsv,
        }
    )
    if disable_profile_setup:
        env["CU_DISABLE_AUTO_PROFILE_SETUP"] = "true"
    return env, call_log


def _run_hook(
    tmp_path: Path,
    shell: str,
    *,
    assign_roles: bool,
    defaults_exit: int = 0,
    deployments: list[dict[str, str]] | None = None,
    failure_match: str = "",
    profile_has_values: bool = False,
    profile_setup_force: bool = False,
    disable_profile_setup: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    env, call_log = _stub_environment(
        tmp_path,
        assign_roles=assign_roles,
        defaults_exit=defaults_exit,
        deployments=deployments,
        failure_match=failure_match,
        profile_has_values=profile_has_values,
        profile_setup_force=profile_setup_force,
        disable_profile_setup=disable_profile_setup,
    )
    hook_name = "postprovision.ps1" if "pwsh" in shell else "postprovision.sh"
    command = [shell, str(_HOOKS / hook_name)]
    result = subprocess.run(
        command,
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    calls = call_log.read_text(encoding="utf-8").splitlines()
    return result, calls


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_key_auth_precedes_endpoint_and_defaults(tmp_path, shell):
    result, calls = _run_hook(tmp_path, shell, assign_roles=False)

    assert result.returncode == 0, result.stdout + result.stderr
    key_index = calls.index("cu-cli profile set api_key fake-account-key --name default")
    endpoint_index = calls.index(
        "cu-cli profile set endpoint https://example.services.ai.azure.com/ --name default"
    )
    analyzer_index = calls.index(
        "cu-cli profile set default_analyzer prebuilt-layout --name default"
    )
    defaults_index = calls.index("cu-cli defaults set --from-profile --profile default")
    assert key_index < endpoint_index < analyzer_index < defaults_index
    assert calls.count("cu-cli defaults set --from-profile --profile default") == 1
    assert "Model readiness verified" in result.stdout
    assert "Custom analyzer workflow" in result.stdout


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_rbac_does_not_fetch_key(tmp_path, shell):
    result, calls = _run_hook(tmp_path, shell, assign_roles=True)

    assert result.returncode == 0, result.stdout + result.stderr
    auth_index = calls.index("cu-cli profile set auth_mode login --name default")
    endpoint_index = calls.index(
        "cu-cli profile set endpoint https://example.services.ai.azure.com/ --name default"
    )
    analyzer_index = calls.index(
        "cu-cli profile set default_analyzer prebuilt-layout --name default"
    )
    defaults_index = calls.index("cu-cli defaults set --from-profile --profile default")
    assert auth_index < endpoint_index < analyzer_index < defaults_index
    assert not any("account keys list" in call for call in calls)


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_defaults_failure_is_visible(tmp_path, shell):
    result, calls = _run_hook(
        tmp_path, shell, assign_roles=False, defaults_exit=17
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "Setup complete" in output
    assert "Generative AI workflows are not ready because Content Understanding defaults" in output
    assert "Repair with: cu-cli defaults set --from-profile --profile default" in output
    assert calls.count("cu-cli defaults set --from-profile --profile default") == 1
    assert "Content extraction sanity check" in output
    assert "Custom analyzer workflow" not in output
    assert not any(" analyze " in f" {call} " for call in calls)


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_no_models_keeps_model_free_workflows_available(
    tmp_path,
    shell,
):
    result, calls = _run_hook(
        tmp_path,
        shell,
        assign_roles=True,
        deployments=[],
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Content extraction sanity check" in output
    assert "No optional models were configured" in output
    assert "Custom analyzer workflow" not in output
    assert "cu-cli defaults set --from-profile --profile default" not in calls


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_model_failure_keeps_profile_and_model_free_guidance(
    tmp_path,
    shell,
):
    result, calls = _run_hook(
        tmp_path,
        shell,
        assign_roles=True,
        deployments=[],
        failure_match="_infra-models",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Optional model setup failed" in output
    assert "Default CU CLI profile configured" in output
    assert "CU CLI profile: default" in output
    assert "cu-cli profile show --name default" in calls
    assert "prebuilt-digitalParse, prebuilt-read, prebuilt-layout" in output
    assert "prebuilt-invoice or custom analyzers" in output
    assert any(call.startswith("cu-cli profile set endpoint ") for call in calls)
    assert "azd env set CU_MODEL_SETUP_COMPLETE true" not in calls


@pytest.mark.parametrize(
    ("models", "missing_capability"),
    [
        (
            [
                {
                    "name": "embedding",
                    "model": "text-embedding-3-large",
                    "state": "Succeeded",
                }
            ],
            "completion",
        ),
        (
            [{"name": "gpt", "model": "gpt-5.2", "state": "Succeeded"}],
            "embedding",
        ),
    ],
)
@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_partial_models_do_not_claim_llm_readiness(
    tmp_path,
    shell,
    models,
    missing_capability,
):
    result, calls = _run_hook(
        tmp_path,
        shell,
        assign_roles=True,
        deployments=models,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Content extraction sanity check" in output
    assert "require succeeded LLM and embeddings model deployments" in output
    assert "Custom analyzer workflow" not in output
    assert "Model readiness verified" not in output
    assert missing_capability not in " ".join(
        call for call in calls if "model_deployments." in call
    )


@pytest.mark.parametrize(
    ("failure_match", "expected_message"),
    [
        ("profile set api_key", "Could not configure key authentication"),
        ("profile set endpoint", "Could not configure the cu CLI endpoint"),
        ("profile set default_analyzer", "Could not configure the default analyzer"),
    ],
)
@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_profile_setup_failure_is_actionable(
    tmp_path,
    shell,
    failure_match,
    expected_message,
):
    result, _ = _run_hook(
        tmp_path,
        shell,
        assign_roles=False,
        failure_match=failure_match,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert expected_message in output
    assert "cu auto-configuration is incomplete" in output
    assert "Run: cu-cli doctor" in output


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_preserves_populated_default_profile(tmp_path, shell):
    result, calls = _run_hook(
        tmp_path,
        shell,
        assign_roles=True,
        profile_has_values=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "already has saved values; preserving it" in output
    assert "CU CLI profile: default" in output
    assert "rerun cu provision with --force" in output
    assert not any("profile set " in call for call in calls)


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_force_updates_populated_default_profile(tmp_path, shell):
    result, calls = _run_hook(
        tmp_path,
        shell,
        assign_roles=True,
        profile_has_values=True,
        profile_setup_force=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Default CU CLI profile configured" in output
    assert any("profile set endpoint " in call for call in calls)


@pytest.mark.parametrize(
    "shell",
    [
        "/bin/sh",
        pytest.param(
            shutil.which("pwsh") or "pwsh",
            marks=pytest.mark.skipif(
                shutil.which("pwsh") is None, reason="pwsh is unavailable"
            ),
        ),
    ],
)
def test_postprovision_profile_setup_can_be_disabled(tmp_path, shell):
    result, calls = _run_hook(
        tmp_path,
        shell,
        assign_roles=True,
        disable_profile_setup=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Automatic CU CLI profile setup disabled" in output
    assert not any("profile _has-values" in call for call in calls)
    assert not any("profile set " in call for call in calls)
