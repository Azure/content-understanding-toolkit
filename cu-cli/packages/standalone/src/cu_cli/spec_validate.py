# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Compatibility exports for spec validation now owned by ``cu-cli-core``."""

from cu_cli_core.spec_validation import (
    spec_allowed_methods,
    spec_allowed_types,
    spec_available,
    validate_against_spec,
)

__all__ = [
    "spec_allowed_methods",
    "spec_allowed_types",
    "spec_available",
    "validate_against_spec",
]
