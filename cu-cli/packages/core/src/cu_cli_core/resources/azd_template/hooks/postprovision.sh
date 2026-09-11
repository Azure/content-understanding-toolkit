#!/usr/bin/env sh
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# Product policy lives in cu-cli-core. This launcher selects an installed frontend.
set -e

if command -v cu-cli >/dev/null 2>&1; then
  exec cu-cli _infra-postprovision-v1
fi

if command -v az >/dev/null 2>&1; then
  exec az cu infra _postprovision-v1
fi

cu_path="$(command -v cu 2>/dev/null || true)"
if [ -n "$cu_path" ] && [ "$cu_path" != "/usr/bin/cu" ]; then
  exec "$cu_path" _infra-postprovision-v1
fi

echo "Postprovision requires either the standalone cu CLI or the az cu extension." >&2
exit 1
