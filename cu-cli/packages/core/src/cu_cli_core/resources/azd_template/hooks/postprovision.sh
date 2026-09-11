#!/usr/bin/env sh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Product policy lives in cu-cli-core. This launcher selects an installed frontend.
set -e

if command -v cu-cli >/dev/null 2>&1; then
  exec cu-cli _infra-postprovision-v1
elif command -v cu >/dev/null 2>&1; then
  exec cu _infra-postprovision-v1
elif command -v az >/dev/null 2>&1; then
  exec az cu infra _postprovision-v1
fi

echo "Postprovision requires either the standalone cu CLI or the az cu extension." >&2
exit 1
