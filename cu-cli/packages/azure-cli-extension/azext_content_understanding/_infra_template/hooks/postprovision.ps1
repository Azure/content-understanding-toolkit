#!/usr/bin/env pwsh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Azure CLI extension post-provision hook.
$ErrorActionPreference = 'Stop'
$envLines = azd env get-values
function Get-AzdValue {
  param([string] $Name)
  $line = $envLines | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
  if ($line -and $line -match "^$Name=`"?(.*?)`"?$") { return $Matches[1] }
  return ''
}

$endpoint = Get-AzdValue 'FOUNDRY_ENDPOINT'
$project = Get-AzdValue 'FOUNDRY_PROJECT_NAME'
$account = Get-AzdValue 'FOUNDRY_RESOURCE_NAME'
$rg = Get-AzdValue 'AZURE_RESOURCE_GROUP'
$subscriptionId = Get-AzdValue 'AZURE_SUBSCRIPTION_ID'
$existingEndpoint = Get-AzdValue 'FOUNDRY_EXISTING_ENDPOINT'
$apiVersion = Get-AzdValue 'CU_API_VERSION'
$modelSelection = Get-AzdValue 'CU_MODEL_SELECTION'
$assignRoles = Get-AzdValue 'AZD_ASSIGN_ROLES'
$profileSetupForce = Get-AzdValue 'CU_PROFILE_SETUP_FORCE'

Write-Host ''
Write-Host '================================================================' -ForegroundColor Cyan
Write-Host " Microsoft Foundry resource $(if ($existingEndpoint) { 'configured' } else { 'provisioned' })" -ForegroundColor Cyan
Write-Host '================================================================' -ForegroundColor Cyan
Write-Host "  Resource group : $rg"
Write-Host "  Account        : $account"
Write-Host "  Project        : $project"
Write-Host "  Endpoint       : $endpoint"
Write-Host ''

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
  throw 'Azure CLI with the content-understanding extension is required for post-provision setup.'
}
& az cu -h *> $null
if ($LASTEXITCODE -ne 0) {
  throw 'Install the content-understanding Azure CLI extension, then rerun azd up.'
}

$modelArgs = @(
  'cu', 'infra', '_models',
  '--resource-group', $rg, '--account', $account, '--subscription', $subscriptionId,
  '--selection', $(if ($modelSelection) { $modelSelection } else { 'recommended' }),
  '--out', 'infra/models.json', '--deploy', '--endpoint', $endpoint,
  '--api-version', $(if ($apiVersion) { $apiVersion } else { '2025-11-01' }),
  '--query', 'models[].name', '--output', 'tsv'
)
if ($assignRoles -eq 'false') { $modelArgs += '--use-key' }
$modelNames = @(& az @modelArgs)
if ($LASTEXITCODE -ne 0) { throw 'Optional model setup failed; rerun azd up after resolving the reported issue.' }
& azd env set CU_MODEL_SETUP_COMPLETE true *> $null

$savedEndpoint = & az cu profile show --name default --query endpoint --output tsv 2>$null
if (-not $savedEndpoint -or $profileSetupForce -eq 'true') {
  & az cu profile set --key endpoint --value $endpoint --name default *> $null
  & az cu profile set --key default_analyzer --value prebuilt-layout --name default *> $null
  foreach ($modelName in $modelNames) {
    & az cu profile set --key "model_deployments.$modelName" --value $modelName --name default *> $null
  }
  Write-Host "Configured the default az cu profile for $endpoint" -ForegroundColor Green
} else {
  Write-Host 'The default az cu profile already has an endpoint; preserving it.' -ForegroundColor Yellow
}
Write-Host 'Setup complete. Verify with: az cu doctor' -ForegroundColor Green