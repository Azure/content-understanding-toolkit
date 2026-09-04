"""Standalone access to the shared CU profile implementation."""

from cu_cli_core.profiles import (
    DEFAULT_PROFILE_NAME,
    KNOWN_PROFILE_KEYS,
    Profile,
    ProfileStore,
    azure_config_path,
    is_valid_profile_name,
    normalize_profile_name,
    validate_profile_key,
    validate_profile_name,
    validate_profile_value,
)

__all__ = [
    "DEFAULT_PROFILE_NAME",
    "KNOWN_PROFILE_KEYS",
    "Profile",
    "ProfileStore",
    "azure_config_path",
    "is_valid_profile_name",
    "normalize_profile_name",
    "validate_profile_key",
    "validate_profile_name",
    "validate_profile_value",
]
