#!/usr/bin/env pwsh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Post-provision hook: prints a summary and optionally wires the `cu` CLI
# to the freshly provisioned Foundry endpoint.
#
# Live model setup is controlled by CU_MODEL_SELECTION. CU CLI profile setup is
# automatic unless CU_DISABLE_AUTO_PROFILE_SETUP=true.

$ErrorActionPreference = 'Stop'

$envLines = azd env get-values

function Get-AzdValue {
  param([string] $Name)
  $line = $envLines | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
  if (-not $line) { return '' }
  if ($line -match "^$Name=`"?(.*?)`"?$") { return $Matches[1] }
  return ''
}

$endpoint = Get-AzdValue 'FOUNDRY_ENDPOINT'
$project  = Get-AzdValue 'FOUNDRY_PROJECT_NAME'
$account  = Get-AzdValue 'FOUNDRY_RESOURCE_NAME'
$rg       = Get-AzdValue 'AZURE_RESOURCE_GROUP'
$subscriptionId = Get-AzdValue 'AZURE_SUBSCRIPTION_ID'
$existingEndpoint = Get-AzdValue 'FOUNDRY_EXISTING_ENDPOINT'
$apiVersion = Get-AzdValue 'CU_API_VERSION'
$modelSelection = Get-AzdValue 'CU_MODEL_SELECTION'
$modelSetupComplete = Get-AzdValue 'CU_MODEL_SETUP_COMPLETE'
$assignRoles = Get-AzdValue 'AZD_ASSIGN_ROLES'
$profileSetupForce = Get-AzdValue 'CU_PROFILE_SETUP_FORCE'

# Detect the right cu CLI command (macOS ships a built-in `cu` UUCP tool)
$cuCmd = $null
if (Get-Command cu-cli -ErrorAction SilentlyContinue) { $cuCmd = 'cu-cli' }
elseif (Get-Command cu -ErrorAction SilentlyContinue)       { $cuCmd = 'cu' }

Write-Host ""
if ($existingEndpoint) {
  Write-Host "================================================================" -ForegroundColor Cyan
  Write-Host " Existing Microsoft Foundry resource configured" -ForegroundColor Cyan
  Write-Host "================================================================" -ForegroundColor Cyan
  Write-Host "  Resource group : $rg"
  Write-Host "  Account        : $account"
  Write-Host "  Endpoint       : $endpoint"
} else {
  Write-Host "================================================================" -ForegroundColor Cyan
  Write-Host " Microsoft Foundry resource provisioned" -ForegroundColor Cyan
  Write-Host "================================================================" -ForegroundColor Cyan
  Write-Host "  Resource group : $rg"
  Write-Host "  Account        : $account"
  Write-Host "  Project        : $project"
  Write-Host "  Endpoint       : $endpoint"
}
Write-Host ""

$modelSetupFailed = $false
if ($modelSetupComplete -ne 'true') {
  if ($modelSelection -eq 'none') {
    Set-Content -Path 'infra/models.json' -Value "[]`n" -NoNewline
    Write-Host "No model deployments selected." -ForegroundColor Green
    Write-Host "Available without a large language model (LLM) or embeddings model: prebuilt-digitalParse, prebuilt-read, prebuilt-layout"
  } else {
    if (-not $cuCmd) {
      Write-Host "Could not set up optional model deployments because cu CLI is not on PATH." -ForegroundColor Yellow
      $modelSetupFailed = $true
    } else {
      $modelAuthArgs = @()
      $previousApiKey = $env:CU_API_KEY
      $previousAuthMode = $env:CU_AUTH_MODE
      try {
      if ($assignRoles -eq 'false') {
        $azForModelSetup = Get-Command az -ErrorAction SilentlyContinue
        if (-not $azForModelSetup) {
          Write-Host "Could not set up optional model deployments because Azure CLI is not on PATH." -ForegroundColor Yellow
          $modelSetupFailed = $true
        } else {
          $key = (& az cognitiveservices account keys list `
            -g $rg -n $account --subscription $subscriptionId --query key1 -o tsv 2>$null)
        }
        if (-not $modelSetupFailed -and -not $key) {
          Write-Host "Could not obtain a Microsoft Foundry resource key for optional model setup." -ForegroundColor Yellow
          $modelSetupFailed = $true
        } elseif ($key) {
          $env:CU_API_KEY = $key
          $env:CU_AUTH_MODE = 'key'
        }
      } else {
        $modelAuthArgs = @('--auth-mode', 'login')
      }
      if (-not $modelSetupFailed) {
        & $cuCmd _infra-models `
          --resource-group $rg `
          --account $account `
          --subscription $subscriptionId `
          --selection $(if ($modelSelection) { $modelSelection } else { 'prompt' }) `
          --out 'infra/models.json' `
          --deploy `
          --endpoint $endpoint `
          --api-version $(if ($apiVersion) { $apiVersion } else { '2025-11-01' }) `
          @modelAuthArgs
        if ($LASTEXITCODE -ne 0) {
          $modelSetupFailed = $true
        }
      }
      } finally {
        $env:CU_API_KEY = $previousApiKey
        $env:CU_AUTH_MODE = $previousAuthMode
      }
    }
  }
  if (-not $modelSetupFailed) {
    & azd env set CU_MODEL_SETUP_COMPLETE true *> $null
  }
}

if ($env:CU_DISABLE_AUTO_PROFILE_SETUP -eq 'true' -or $env:CU_AUTOCONFIG -eq 'false') {
  Write-Host "Automatic CU CLI profile setup disabled." -ForegroundColor Yellow
  Write-Host "To configure manually: cu-cli profile set endpoint $endpoint --name default" -ForegroundColor Yellow
  return
}

if (-not $cuCmd) {
  Write-Host "cu CLI not found on PATH. To configure manually:" -ForegroundColor Yellow
  Write-Host "  cu-cli profile set endpoint $endpoint --name default" -ForegroundColor Yellow
  return
}

& $cuCmd profile _has-values --name default *> $null
$profileStatus = $LASTEXITCODE
if ($profileStatus -eq 0 -and $profileSetupForce -ne 'true') {
  Write-Host "Default CU CLI profile already has saved values; preserving it." -ForegroundColor Yellow
  Write-Host "Current default CU CLI profile:"
  & $cuCmd profile show --name default
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not display the preserved default CU CLI profile." -ForegroundColor Yellow
  }
  Write-Host "To replace its values, rerun cu infra generate with --force, then run azd up." -ForegroundColor Yellow
  return
} elseif ($profileStatus -ne 0 -and $profileStatus -ne 3) {
  Write-Host "Could not inspect the default CU CLI profile; refusing to overwrite it." -ForegroundColor Yellow
  Write-Host "Run: $cuCmd profile show --name default" -ForegroundColor Yellow
  exit 1
}

$setupIncomplete = $false
$authReady = $true
$endpointReady = $false
if ($assignRoles -eq 'false') {
  $az = Get-Command az -ErrorAction SilentlyContinue
  if (-not $az) {
    Write-Host ""
    Write-Host "Roles were skipped and 'az' CLI is not on PATH." -ForegroundColor Yellow
    Write-Host "To enable key-based auth from cu, install az and run:" -ForegroundColor Yellow
    Write-Host "  az login" -ForegroundColor Yellow
    Write-Host "  cu profile set api_key (az cognitiveservices account keys list -g $rg -n $account --subscription $subscriptionId --query key1 -o tsv) --name default" -ForegroundColor Yellow
    $authReady = $false
    $setupIncomplete = $true
  } else {
    & az account show --subscription $subscriptionId --only-show-errors *> $null
    if ($LASTEXITCODE -ne 0) {
      Write-Host ""
      Write-Host "Roles were skipped and 'az' isn't logged in (azd auth login is separate from az login)." -ForegroundColor Yellow
      Write-Host "To enable key-based auth from cu, run:" -ForegroundColor Yellow
      Write-Host "  az login" -ForegroundColor Yellow
      Write-Host "  cu profile set api_key (az cognitiveservices account keys list -g $rg -n $account --subscription $subscriptionId --query key1 -o tsv) --name default" -ForegroundColor Yellow
      $authReady = $false
      $setupIncomplete = $true
    } else {
      Write-Host "Roles were skipped; fetching account key for cu..." -ForegroundColor Green
      $key = (& az cognitiveservices account keys list -g $rg -n $account --subscription $subscriptionId --query key1 -o tsv 2>$null)
      if ($LASTEXITCODE -eq 0 -and $key) {
        & $cuCmd profile set api_key $key --name default
        if ($LASTEXITCODE -eq 0) {
          Write-Host "API key written to the default CU CLI profile." -ForegroundColor Green
        } else {
          Write-Host "Could not configure key authentication." -ForegroundColor Yellow
          $authReady = $false
          $setupIncomplete = $true
        }
      } else {
        Write-Host "Could not configure key authentication." -ForegroundColor Yellow
        Write-Host "Try: az cognitiveservices account keys list -g $rg -n $account --subscription $subscriptionId" -ForegroundColor Yellow
        $authReady = $false
        $setupIncomplete = $true
      }
    }
  }
} else {
  Write-Host "Configuring cu CLI to use Entra authentication..." -ForegroundColor Green
  & $cuCmd profile set auth_mode login --name default
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not configure Entra authentication." -ForegroundColor Yellow
    $authReady = $false
    $setupIncomplete = $true
  }
}

Write-Host "Configuring cu CLI endpoint..." -ForegroundColor Green
& $cuCmd profile set endpoint $endpoint --name default
if ($LASTEXITCODE -eq 0) {
  $endpointReady = $true
} else {
  Write-Host "Could not configure the cu CLI endpoint." -ForegroundColor Yellow
  $setupIncomplete = $true
}

Write-Host "Configuring prebuilt-layout as the default analyzer..." -ForegroundColor Green
& $cuCmd profile set default_analyzer prebuilt-layout --name default
if ($LASTEXITCODE -ne 0) {
  Write-Host "Could not configure the default analyzer." -ForegroundColor Yellow
  $setupIncomplete = $true
}

$maybeSetDefaults = $false
$defaultsInitialized = $false
$defaultsFailed = $false
$depCompletion = $null
$depMini = $null
$depEmbedding = $null
$completionReady = $false
$embeddingReady = $false
$azForDefaults = Get-Command az -ErrorAction SilentlyContinue
if ($azForDefaults) {
  & az account show --subscription $subscriptionId --only-show-errors *> $null
  if ($LASTEXITCODE -eq 0) {
    $deploymentsJson = & az cognitiveservices account deployment list -g $rg -n $account --subscription $subscriptionId -o json 2>$null
    if ($deploymentsJson) {
      $deployments = $deploymentsJson | ConvertFrom-Json
      foreach ($dep in $deployments) {
        $modelName = $dep.properties.model.name
        if ($modelName) {
          & $cuCmd profile set "model_deployments.$modelName" $dep.name --name default
          $maybeSetDefaults = $true
          if ($modelName -like 'text-embedding-*') {
            if (-not $depEmbedding) { $depEmbedding = $dep.name }
            if ($dep.properties.provisioningState -eq 'Succeeded') { $embeddingReady = $true }
          } elseif ($modelName -like '*-mini') {
            if (-not $depMini) { $depMini = $dep.name }
            if (-not $depCompletion) { $depCompletion = $dep.name }
            if ($dep.properties.provisioningState -eq 'Succeeded') { $completionReady = $true }
          } else {
            if (-not $depCompletion) { $depCompletion = $dep.name }
            if ($dep.properties.provisioningState -eq 'Succeeded') { $completionReady = $true }
          }
        }
      }
    }
  }
}

if ($maybeSetDefaults) {
  $completionDep = $depCompletion
  $miniDep = if ($depMini) { $depMini } else { $completionDep }
  if ($completionDep) {
    & $cuCmd profile set "model_deployments.prebuilt-analyzer-completion" $completionDep --name default
    & $cuCmd profile set "model_deployments.prebuilt-analyzer-completion-mini" $miniDep --name default
  }
  if ($depEmbedding) {
    & $cuCmd profile set "model_deployments.prebuilt-analyzer-embedding" $depEmbedding --name default
  }

  Write-Host "Initializing Foundry defaults from configured model deployments..." -ForegroundColor Green
  & $cuCmd defaults set --from-profile --profile default *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Foundry defaults initialized." -ForegroundColor Green
    $defaultsInitialized = $true
  } else {
    Write-Host "Could not initialize Foundry defaults automatically." -ForegroundColor Yellow
    Write-Host "Run: $cuCmd defaults set --from-profile --profile default" -ForegroundColor Yellow
    $defaultsFailed = $true
  }
}

$llmReady = $defaultsInitialized -and $completionReady -and $embeddingReady
if ($llmReady) {
  Write-Host "Model readiness verified: LLM and embeddings model deployments succeeded and Content Understanding defaults are configured." -ForegroundColor Green
}

Write-Host ""
if ($setupIncomplete) {
  Write-Host "Azure provisioning completed, but cu auto-configuration is incomplete." -ForegroundColor Yellow
  Write-Host "Run: $cuCmd doctor" -ForegroundColor Yellow
  exit 1
}
Write-Host "Setup complete." -ForegroundColor Green
if ($endpointReady) {
  Write-Host "Default CU CLI profile configured:"
  & $cuCmd profile show --name default
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  Warning: profile setup succeeded, but its values could not be displayed." -ForegroundColor Yellow
  }
  Write-Host ""
  Write-Host "  Verify setup with:"
  Write-Host "    $cuCmd doctor" -ForegroundColor Cyan
}
if ($endpointReady -and $authReady) {
  Write-Host "  Available without an LLM or embeddings model: prebuilt-digitalParse, prebuilt-read, prebuilt-layout"
  Write-Host "  Content extraction sanity check:"
  Write-Host "    $cuCmd analyze <file> --analyzer prebuilt-layout" -ForegroundColor Cyan
}
if ($modelSetupFailed) {
  Write-Host "  Optional model setup failed; the Microsoft Foundry resource and CU CLI profile are still ready." -ForegroundColor Yellow
  Write-Host "  Resolve the deployment issue, then rerun azd up before using generative AI" -ForegroundColor Yellow
  Write-Host "  prebuilt analyzers such as prebuilt-invoice or custom analyzers." -ForegroundColor Yellow
} elseif ($llmReady) {
  Write-Host "  Custom analyzer workflow:"
  Write-Host "    $cuCmd analyzer schema create --from-sample <file> --output-file schema.json" -ForegroundColor Cyan
  Write-Host "    $cuCmd analyzer create --name my-analyzer --schema schema.json" -ForegroundColor Cyan
  Write-Host "    $cuCmd analyze <file> --analyzer my-analyzer" -ForegroundColor Cyan
} elseif ($defaultsFailed) {
  Write-Host "  Generative AI workflows are not ready because Content Understanding defaults configuration failed." -ForegroundColor Yellow
  Write-Host "  Repair with: $cuCmd defaults set --from-profile --profile default" -ForegroundColor Yellow
} elseif ($maybeSetDefaults) {
  Write-Host "  Generative AI workflows require succeeded LLM and embeddings model deployments." -ForegroundColor Yellow
} else {
  Write-Host "  No optional models were configured; content extraction analyzers remain available." -ForegroundColor DarkGray
}
