#!/usr/bin/env pwsh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Product policy lives in cu-cli-core. This launcher selects an installed frontend.
$ErrorActionPreference = 'Stop'

if (Get-Command cu-cli -ErrorAction SilentlyContinue) {
  & cu-cli _infra-postprovision-v1
} elseif (Get-Command cu -ErrorAction SilentlyContinue) {
  & cu _infra-postprovision-v1
} elseif (Get-Command az -ErrorAction SilentlyContinue) {
  & az cu infra _postprovision-v1
} else {
  Write-Error 'Postprovision requires either the standalone cu CLI or the az cu extension.'
  exit 1
}
exit $LASTEXITCODE
