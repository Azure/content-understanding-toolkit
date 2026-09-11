#!/usr/bin/env pwsh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Product policy lives in cu-cli-core. This launcher selects an installed frontend.
$ErrorActionPreference = 'Stop'

if (Get-Command cu-cli -ErrorAction SilentlyContinue) {
  & cu-cli _infra-postprovision-v1
  exit $LASTEXITCODE
}

if (Get-Command az -ErrorAction SilentlyContinue) {
  & az cu infra _postprovision-v1
  exit $LASTEXITCODE
}

$cuCommand = Get-Command cu -ErrorAction SilentlyContinue
if ($cuCommand -and $cuCommand.Source -ne '/usr/bin/cu') {
  & $cuCommand.Source _infra-postprovision-v1
  exit $LASTEXITCODE
}

Write-Error 'Postprovision requires either the standalone cu CLI or the az cu extension.'
exit 1
