#!/usr/bin/env sh
# Post-provision hook: prints a summary and optionally wires the `cu` CLI
# to the freshly provisioned Foundry endpoint.
#
# Live model setup is controlled by CU_MODEL_SELECTION. CU CLI profile setup is
# automatic unless CU_DISABLE_AUTO_PROFILE_SETUP=true.

set -e

values=$(azd env get-values)
endpoint=$(printf '%s\n' "$values" | sed -n 's/^FOUNDRY_ENDPOINT="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
project=$(printf '%s\n'  "$values" | sed -n 's/^FOUNDRY_PROJECT_NAME="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
account=$(printf '%s\n'  "$values" | sed -n 's/^FOUNDRY_RESOURCE_NAME="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
rg=$(printf '%s\n'       "$values" | sed -n 's/^AZURE_RESOURCE_GROUP="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
subscription_id=$(printf '%s\n' "$values" | sed -n 's/^AZURE_SUBSCRIPTION_ID="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
existing_endpoint=$(printf '%s\n' "$values" | sed -n 's/^FOUNDRY_EXISTING_ENDPOINT="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
api_version=$(printf '%s\n' "$values" | sed -n 's/^CU_API_VERSION="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
model_selection=$(printf '%s\n' "$values" | sed -n 's/^CU_MODEL_SELECTION="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
model_setup_complete=$(printf '%s\n' "$values" | sed -n 's/^CU_MODEL_SETUP_COMPLETE="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
assign_roles=$(printf '%s\n' "$values" | sed -n 's/^AZD_ASSIGN_ROLES="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')
profile_setup_force=$(printf '%s\n' "$values" | sed -n 's/^CU_PROFILE_SETUP_FORCE="\{0,1\}\([^"]*\)"\{0,1\}/\1/p')

# Detect the right cu CLI command (macOS ships a built-in `cu` UUCP tool)
if command -v cu-cli >/dev/null 2>&1; then
  CU_CMD="cu-cli"
elif command -v cu >/dev/null 2>&1; then
  CU_CMD="cu"
else
  CU_CMD=""
fi

if [ -n "$existing_endpoint" ]; then
  cat <<EOF

================================================================
 Existing Microsoft Foundry resource configured
================================================================
  Resource group : $rg
  Account        : $account
  Endpoint       : $endpoint

EOF
else
  cat <<EOF

================================================================
 Microsoft Foundry resource provisioned
================================================================
  Resource group : $rg
  Account        : $account
  Project        : $project
  Endpoint       : $endpoint

EOF
fi

model_setup_failed=false
if [ "$model_setup_complete" != "true" ]; then
  if [ "$model_selection" = "none" ]; then
    printf '[]\n' > infra/models.json
    echo "No model deployments selected."
    echo "Available without a large language model (LLM) or embeddings model: prebuilt-digitalParse, prebuilt-read, prebuilt-layout"
  else
    if [ -z "$CU_CMD" ]; then
      echo "Could not set up optional model deployments because cu CLI is not on PATH."
      model_setup_failed=true
    elif [ "$assign_roles" = "false" ]; then
      key=$(az cognitiveservices account keys list \
        -g "$rg" -n "$account" --subscription "$subscription_id" \
        --query key1 -o tsv 2>/dev/null || true)
      if [ -z "$key" ]; then
        echo "Could not obtain a Microsoft Foundry resource key for optional model setup."
        model_setup_failed=true
      elif ! CU_API_KEY="$key" CU_AUTH_MODE=key "$CU_CMD" _infra-models \
          --resource-group "$rg" \
          --account "$account" \
          --subscription "$subscription_id" \
          --selection "${model_selection:-prompt}" \
          --out infra/models.json \
          --deploy \
          --endpoint "$endpoint" \
          --api-version "${api_version:-2025-11-01}"; then
        model_setup_failed=true
      fi
    elif ! "$CU_CMD" _infra-models \
        --resource-group "$rg" \
        --account "$account" \
        --subscription "$subscription_id" \
        --selection "${model_selection:-prompt}" \
        --out infra/models.json \
        --deploy \
        --endpoint "$endpoint" \
        --api-version "${api_version:-2025-11-01}" \
        --auth-mode login; then
      model_setup_failed=true
    fi
  fi
  if [ "$model_setup_failed" = "false" ]; then
    azd env set CU_MODEL_SETUP_COMPLETE true >/dev/null
  fi
fi

if [ "${CU_DISABLE_AUTO_PROFILE_SETUP:-}" = "true" ] || [ "${CU_AUTOCONFIG:-}" = "false" ]; then
  echo "Automatic CU CLI profile setup disabled."
  echo "To configure manually: cu-cli profile set endpoint $endpoint --name default"
  exit 0
fi

if [ -z "$CU_CMD" ]; then
  echo "cu CLI not found on PATH. Install it to auto-configure:"
  echo "  pip install -e <path-to-cu-cli>"
  echo "Then run: cu-cli profile set endpoint $endpoint --name default"
  exit 0
fi

profile_status=0
"$CU_CMD" profile _has-values --name default >/dev/null 2>&1 || profile_status=$?
if [ "$profile_status" -eq 0 ] && [ "$profile_setup_force" != "true" ]; then
  echo "Default CU CLI profile already has saved values; preserving it."
  echo "Current default CU CLI profile:"
  if ! "$CU_CMD" profile show --name default; then
    echo "Could not display the preserved default CU CLI profile."
  fi
  echo "To replace its values, rerun cu provision with --force, then run azd up."
  exit 0
elif [ "$profile_status" -ne 0 ] && [ "$profile_status" -ne 3 ]; then
  echo "Could not inspect the default CU CLI profile; refusing to overwrite it."
  echo "Run: $CU_CMD profile show --name default"
  exit 1
fi

setup_incomplete=false
auth_ready=true
endpoint_ready=false
if [ "$assign_roles" = "false" ]; then
  if ! command -v az >/dev/null 2>&1; then
    echo
    echo "Roles were skipped and 'az' CLI is not on PATH."
    echo "To enable key-based auth from cu, install az and run:"
    echo "  az login"
    echo "  cu profile set api_key \$(az cognitiveservices account keys list -g $rg -n $account --subscription $subscription_id --query key1 -o tsv) --name default"
    auth_ready=false
    setup_incomplete=true
  elif ! az account show --subscription "$subscription_id" --only-show-errors >/dev/null 2>&1; then
    echo
    echo "Roles were skipped and 'az' isn't logged in (azd auth login is separate from az login)."
    echo "To enable key-based auth from cu, run:"
    echo "  az login"
    echo "  cu profile set api_key \$(az cognitiveservices account keys list -g $rg -n $account --subscription $subscription_id --query key1 -o tsv) --name default"
    auth_ready=false
    setup_incomplete=true
  else
    echo "Roles were skipped; fetching account key for cu..."
    key=$(az cognitiveservices account keys list -g "$rg" -n "$account" --subscription "$subscription_id" --query key1 -o tsv 2>/dev/null || true)
    if [ -n "$key" ] && $CU_CMD profile set api_key "$key" --name default; then
      echo "API key written to the default CU CLI profile."
    else
      echo "Could not configure key authentication."
      echo "Try: az cognitiveservices account keys list -g $rg -n $account --subscription $subscription_id"
      auth_ready=false
      setup_incomplete=true
    fi
  fi
else
  echo "Configuring cu CLI to use Entra authentication..."
  if ! $CU_CMD profile set auth_mode login --name default; then
    echo "Could not configure Entra authentication."
    auth_ready=false
    setup_incomplete=true
  fi
fi

echo "Configuring cu CLI endpoint..."
if $CU_CMD profile set endpoint "$endpoint" --name default; then
  endpoint_ready=true
else
  echo "Could not configure the cu CLI endpoint."
  setup_incomplete=true
fi

echo "Configuring prebuilt-layout as the default analyzer..."
if ! $CU_CMD profile set default_analyzer prebuilt-layout --name default; then
  echo "Could not configure the default analyzer."
  setup_incomplete=true
fi

maybe_set_defaults=false
defaults_initialized=false
defaults_failed=false
dep_completion=""
dep_mini=""
dep_embedding=""
completion_ready=false
embedding_ready=false
if command -v az >/dev/null 2>&1 && az account show --subscription "$subscription_id" --only-show-errors >/dev/null 2>&1; then
  # Discover all deployed models and configure mappings dynamically.
  # Use a POSIX here-doc (not a bash `<<<` here-string) so this runs under
  # /bin/sh (dash), and so the loop stays in the current shell and the flag
  # variables set below persist. `tab` is a literal tab for the TSV columns.
  tab=$(printf '\t')
  deployments=$(az cognitiveservices account deployment list \
    -g "$rg" -n "$account" --subscription "$subscription_id" \
    --query "[].{dep:name,model:properties.model.name,state:properties.provisioningState}" \
    -o tsv 2>/dev/null || true)
  while IFS="$tab" read -r dep_name model_name deployment_state; do
    [ -z "$dep_name" ] && continue
    $CU_CMD profile set "model_deployments.$model_name" "$dep_name" --name default
    maybe_set_defaults=true
    case "$model_name" in
      text-embedding-*)
        [ -z "$dep_embedding" ] && dep_embedding="$dep_name"
        [ "$deployment_state" = "Succeeded" ] && embedding_ready=true
        ;;
      *-mini)
        [ -z "$dep_mini" ] && dep_mini="$dep_name"
        [ -z "$dep_completion" ] && dep_completion="$dep_name"
        [ "$deployment_state" = "Succeeded" ] && completion_ready=true
        ;;
      *)
        [ -z "$dep_completion" ] && dep_completion="$dep_name"
        [ "$deployment_state" = "Succeeded" ] && completion_ready=true
        ;;
    esac
  done <<EOF
$deployments
EOF
fi

if [ "$maybe_set_defaults" = "true" ]; then
  completion_dep="$dep_completion"
  mini_dep="$dep_mini"
  [ -z "$mini_dep" ] && mini_dep="$completion_dep"
  if [ -n "$completion_dep" ]; then
    $CU_CMD profile set "model_deployments.prebuilt-analyzer-completion" "$completion_dep" --name default
    $CU_CMD profile set "model_deployments.prebuilt-analyzer-completion-mini" "$mini_dep" --name default
  fi
  if [ -n "$dep_embedding" ]; then
    $CU_CMD profile set "model_deployments.prebuilt-analyzer-embedding" "$dep_embedding" --name default
  fi
  echo "Initializing Foundry defaults from configured model deployments..."
  if $CU_CMD defaults set --from-profile --profile default >/dev/null 2>&1; then
    echo "Foundry defaults initialized."
    defaults_initialized=true
  else
    echo "Could not initialize Foundry defaults automatically."
    echo "Run: $CU_CMD defaults set --from-profile --profile default"
    defaults_failed=true
  fi
fi

llm_ready=false
if [ "$defaults_initialized" = "true" ] &&
   [ "$completion_ready" = "true" ] &&
   [ "$embedding_ready" = "true" ]; then
  llm_ready=true
  echo "Model readiness verified: LLM and embeddings model deployments succeeded and Content Understanding defaults are configured."
fi

echo
if [ "$setup_incomplete" = "true" ]; then
  echo "Azure provisioning completed, but cu auto-configuration is incomplete."
  echo "Run: $CU_CMD doctor"
  exit 1
fi
echo "Setup complete."
if [ "$endpoint_ready" = "true" ]; then
  echo "Default CU CLI profile configured:"
  if ! "$CU_CMD" profile show --name default; then
    echo "  Warning: profile setup succeeded, but its values could not be displayed."
  fi
  echo
  echo "  Verify setup with:"
  echo "    $CU_CMD doctor"
fi
if [ "$endpoint_ready" = "true" ] && [ "$auth_ready" = "true" ]; then
  echo "  Available without an LLM or embeddings model: prebuilt-digitalParse, prebuilt-read, prebuilt-layout"
  echo "  Content extraction sanity check:"
  echo "    $CU_CMD analyze <file> --analyzer prebuilt-layout"
fi
if [ "$model_setup_failed" = "true" ]; then
  echo "  Optional model setup failed; the Microsoft Foundry resource and CU CLI profile are still ready."
  echo "  Resolve the deployment issue, then rerun azd up before using generative AI"
  echo "  prebuilt analyzers such as prebuilt-invoice or custom analyzers."
elif [ "$llm_ready" = "true" ]; then
  echo "  Custom analyzer workflow:"
  echo "    $CU_CMD analyzer schema create --from-sample <file> --output-file schema.json"
  echo "    $CU_CMD analyzer create --name my-analyzer --schema schema.json"
  echo "    $CU_CMD analyze <file> --analyzer my-analyzer"
elif [ "$defaults_failed" = "true" ]; then
  echo "  Generative AI workflows are not ready because Content Understanding defaults configuration failed."
  echo "  Repair with: $CU_CMD defaults set --from-profile --profile default"
elif [ "$maybe_set_defaults" = "true" ]; then
  echo "  Generative AI workflows require succeeded LLM and embeddings model deployments."
else
  echo "  No optional models were configured; content extraction analyzers remain available."
fi
