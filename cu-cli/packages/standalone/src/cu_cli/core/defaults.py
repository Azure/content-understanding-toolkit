"""Compatibility imports for defaults operations now provided by cu-cli-core."""

from cu_cli_core.defaults import (
    apply_defaults,
    extract_model_deployments,
    is_defaults_not_set,
    parse_model_kv,
)

__all__ = [
    "apply_defaults",
    "extract_model_deployments",
    "is_defaults_not_set",
    "parse_model_kv",
]
