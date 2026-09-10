#!/usr/bin/env sh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Azure CLI extension post-provision hook.
set -e

values=$(azd env get-values)
azd_value() {
  printf '%s\n' "$values" | sed -n "s/^$1=\"\{0,1\}\([^\"]*\)\"\{0,1\}/\1/p"
}

endpoint=$(azd_value FOUNDRY_ENDPOINT)
project=$(azd_value FOUNDRY_PROJECT_NAME)
account=$(azd_value FOUNDRY_RESOURCE_NAME)
rg=$(azd_value AZURE_RESOURCE_GROUP)
subscription_id=$(azd_value AZURE_SUBSCRIPTION_ID)
existing_endpoint=$(azd_value FOUNDRY_EXISTING_ENDPOINT)
api_version=$(azd_value CU_API_VERSION)
model_selection=$(azd_value CU_MODEL_SELECTION)
assign_roles=$(azd_value AZD_ASSIGN_ROLES)
profile_setup_force=$(azd_value CU_PROFILE_SETUP_FORCE)

cat <<EOF

================================================================
 Microsoft Foundry resource $([ -n "$existing_endpoint" ] && printf 'configured' || printf 'provisioned')
================================================================
  Resource group : $rg
  Account        : $account
  Project        : $project
  Endpoint       : $endpoint

EOF

if ! command -v az >/dev/null 2>&1 || ! az cu -h >/dev/null 2>&1; then
  echo "Azure CLI with the content-understanding extension is required for post-provision setup."
  echo "The Azure resources were provisioned, but model and profile setup were skipped."
  exit 1
fi

model_names=""
key_arg=""
[ "$assign_roles" = "false" ] && key_arg="--use-key"
# The helper is idempotent and must run on retries so profile setup can recover.
# shellcheck disable=SC2086
if model_names=$(az cu _infra-models \
    --resource-group "$rg" --account "$account" --subscription "$subscription_id" \
    --selection "${model_selection:-recommended}" --out infra/models.json --deploy \
    --endpoint "$endpoint" --api-version "${api_version:-2025-11-01}" $key_arg \
    --query "models[].name" --output tsv); then
  azd env set CU_MODEL_SETUP_COMPLETE true >/dev/null
else
  echo "Optional model setup failed; rerun azd up after resolving the reported issue."
  exit 1
fi

saved_endpoint=$(az cu profile show --name default --query endpoint --output tsv 2>/dev/null || true)
if [ -z "$saved_endpoint" ] || [ "$profile_setup_force" = "true" ]; then
  az cu profile set --key endpoint --value "$endpoint" --name default >/dev/null
  az cu profile set --key default_analyzer --value prebuilt-layout --name default >/dev/null
  for model_name in $model_names; do
    az cu profile set --key "model_deployments.$model_name" --value "$model_name" --name default >/dev/null
  done
  echo "Configured the default az cu profile for $endpoint"
else
  echo "The default az cu profile already has an endpoint; preserving it."
fi

echo "Setup complete. Verify with: az cu doctor"