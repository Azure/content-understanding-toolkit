# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Shared CU profile storage and resolution over Azure CLI configuration."""

from __future__ import annotations

import configparser
from contextlib import contextmanager
import copy
from dataclasses import dataclass, field
import hashlib
from io import StringIO
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Iterator, Mapping

from .errors import ConflictError, LocalIOError, NotFoundError, ValidationError
from .service_options import DEFAULT_API_VERSION

AZURE_CONFIG_DIR_ENV = "AZURE_CONFIG_DIR"
CU_SECTION = "cu"
DEFAULT_PROFILE_NAME = "default"
ACTIVE_PROFILE_KEY = "active_profile"
PROFILE_MARKER = "_created"
RESERVED_PROFILE_NAMES = frozenset({DEFAULT_PROFILE_NAME, "model_deployments"})
KNOWN_PROFILE_KEYS = {
    "endpoint",
    "auth_mode",
    "api_key",
    "api_version",
    "default_analyzer",
}
MODEL_DEPLOYMENTS_PREFIX = "model_deployments."
MODEL_ENV_OVERRIDES: Mapping[str, str] = {
    "gpt-5.2": "GPT_5_2_DEPLOYMENT",
    "gpt-4.1": "GPT_4_1_DEPLOYMENT",
    "text-embedding-3-large": "TEXT_EMBEDDING_3_LARGE_DEPLOYMENT",
}
PROFILE_NAME_HINT = (
    "use 1-64 ASCII letters or numbers, with hyphens (-) or underscores (_) "
    "only between characters; for example 'dev', 'West_US2', or 'test-01'. "
    "'default' and 'model_deployments' are reserved."
)
_PROFILE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,62}[A-Za-z0-9])?$"
)
_MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
_SECTION_PATTERN = re.compile(
    r"^[ \t]*\[(?P<name>[^\]\r\n]+)\][ \t]*(?:[;#].*)?(?:\r?\n|$)",
    re.MULTILINE,
)


class _CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def azure_config_path() -> Path:
    """Return the active Azure CLI configuration file path."""

    configured = os.getenv(AZURE_CONFIG_DIR_ENV)
    config_dir = Path(configured).expanduser() if configured else Path.home() / ".azure"
    return config_dir / "config"


def normalize_profile_name(name: str) -> str:
    """Validate a mutable named profile without changing its case."""

    if (
        _PROFILE_NAME_PATTERN.fullmatch(name) is None
        or name.casefold() in RESERVED_PROFILE_NAMES
    ):
        raise ValidationError(f"invalid profile name '{name}'.", hint=PROFILE_NAME_HINT)
    return name


def validate_profile_name(name: str) -> str:
    if name == DEFAULT_PROFILE_NAME:
        return name
    return normalize_profile_name(name)


def is_valid_profile_name(name: str, *, allow_default: bool = True) -> bool:
    if _PROFILE_NAME_PATTERN.fullmatch(name) is None:
        return False
    folded = name.casefold()
    if folded == DEFAULT_PROFILE_NAME:
        return allow_default and name == DEFAULT_PROFILE_NAME
    return folded not in RESERVED_PROFILE_NAMES


def validate_profile_key(key: str) -> str:
    if key.startswith(MODEL_DEPLOYMENTS_PREFIX):
        model = key.removeprefix(MODEL_DEPLOYMENTS_PREFIX)
        if _MODEL_NAME_PATTERN.fullmatch(model) is not None:
            return key
        raise ValidationError(
            f"invalid model deployment key '{key}'.",
            hint=(
                "use model_deployments.<model> with letters, numbers, dots, "
                "hyphens, or underscores; for example model_deployments.gpt-5.2."
            ),
        )
    if key not in KNOWN_PROFILE_KEYS:
        known = ", ".join(sorted(KNOWN_PROFILE_KEYS))
        raise ValidationError(
            f"unknown profile key '{key}'.",
            hint=f"known keys: {known}, or model_deployments.<model>.",
        )
    return key


def validate_profile_value(key: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"value for '{key}' must not be empty.")
    if "\n" in cleaned or "\r" in cleaned:
        raise ValidationError(f"value for '{key}' must be a single line.")
    if key == "auth_mode" and cleaned not in {"login", "key"}:
        raise ValidationError("auth_mode must be 'login' or 'key'.")
    return cleaned


def _read_config(path: Path) -> tuple[str, dict[str, str], str | None]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return "", {}, None
    except OSError as exc:
        raise LocalIOError(
            f"could not read Azure CLI configuration '{path}': {exc}.",
            hint="check the file permissions and try again.",
        ) from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(
            f"Azure CLI configuration '{path}' is not valid UTF-8.",
            hint="fix or move the file before changing CU profiles.",
        ) from exc

    parser = _CaseSensitiveConfigParser(interpolation=None, strict=True)
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        raise ValidationError(
            f"Azure CLI configuration '{path}' is not valid INI: {exc}.",
            hint="fix the configuration before changing CU profiles.",
        ) from exc
    values = dict(parser.items(CU_SECTION)) if parser.has_section(CU_SECTION) else {}
    return text, values, hashlib.sha256(raw).hexdigest()


@contextmanager
def _exclusive_config_lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(f"{path.name}.lock")
    with open(lock_path, "a+b") as lock_file:
        if sys.platform == "win32":
            import msvcrt

            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _render_cu_section(values: Mapping[str, str], newline: str) -> str:
    if not values:
        return ""
    parser = _CaseSensitiveConfigParser(interpolation=None)
    parser.add_section(CU_SECTION)
    for key in sorted(values):
        parser.set(CU_SECTION, key, values[key])
    stream = StringIO()
    parser.write(stream, space_around_delimiters=True)
    rendered = stream.getvalue()
    return rendered.replace("\n", newline)


def _replace_cu_section(original: str, values: Mapping[str, str]) -> str:
    newline = "\r\n" if "\r\n" in original else "\n"
    matches = list(_SECTION_PATTERN.finditer(original))
    cu_match_index = next(
        (
            index
            for index, match in enumerate(matches)
            if match.group("name").strip().casefold() == CU_SECTION
        ),
        None,
    )
    replacement = _render_cu_section(values, newline)
    if cu_match_index is None:
        if not replacement:
            return original
        separator = "" if not original else newline if original.endswith(("\n", "\r")) else newline * 2
        return f"{original}{separator}{replacement}"

    start = matches[cu_match_index].start()
    end = (
        matches[cu_match_index + 1].start()
        if cu_match_index + 1 < len(matches)
        else len(original)
    )
    suffix = original[end:]
    if replacement and suffix and not replacement.endswith(("\n", "\r")):
        replacement += newline
    return f"{original[:start]}{replacement}{suffix}"


def _profile_prefix(name: str) -> str:
    return f"{name}."


def _is_profile_setting(key: str) -> bool:
    return key in KNOWN_PROFILE_KEYS or key.startswith(MODEL_DEPLOYMENTS_PREFIX)


@dataclass
class ProfileStore:
    """Read and atomically update CU profiles in Azure CLI configuration."""

    path: Path
    values: dict[str, str] = field(default_factory=dict)
    _source_text: str = field(default="", repr=False)
    _source_digest: str | None = field(default=None, repr=False)

    @classmethod
    def load(cls, path: Path | None = None) -> "ProfileStore":
        resolved_path = path or azure_config_path()
        text, values, digest = _read_config(resolved_path)
        store = cls(
            path=resolved_path,
            values=values,
            _source_text=text,
            _source_digest=digest,
        )
        store._validate()
        return store

    def _validate(self) -> None:
        active = self.values.get(ACTIVE_PROFILE_KEY)
        if active is not None:
            validate_profile_name(active)
        for key in self.values:
            if key == ACTIVE_PROFILE_KEY:
                continue
            if _is_profile_setting(key):
                validate_profile_key(key)
                continue
            name, separator, setting = key.partition(".")
            if not separator:
                continue
            validate_profile_name(name)
            if setting != PROFILE_MARKER:
                validate_profile_key(setting)

    def list_names(self) -> list[str]:
        names = {DEFAULT_PROFILE_NAME}
        for key in self.values:
            name, separator, setting = key.partition(".")
            if separator and (
                setting == PROFILE_MARKER or _is_profile_setting(setting)
            ):
                names.add(name)
        return sorted(names)

    def has_name(self, name: str) -> bool:
        if name == DEFAULT_PROFILE_NAME:
            return True
        prefix = _profile_prefix(name)
        return any(key.startswith(prefix) for key in self.values)

    def get_active_name(self) -> str:
        active = self.values.get(ACTIVE_PROFILE_KEY, DEFAULT_PROFILE_NAME)
        if not self.has_name(active):
            raise NotFoundError(
                f"active CU CLI profile '{active}' was not found.",
                hint="run `cu profile set-active default` or select another listed profile.",
            )
        return active

    def set_active_name(self, name: str) -> None:
        target = validate_profile_name(name)
        if not self.has_name(target):
            raise NotFoundError(
                f"profile '{target}' was not found.",
                hint="run `cu profile list` to see available profiles.",
            )
        if target == DEFAULT_PROFILE_NAME:
            self.values.pop(ACTIVE_PROFILE_KEY, None)
        else:
            self.values[ACTIVE_PROFILE_KEY] = target

    def _base_profile(self) -> dict[str, str]:
        return {
            key: value
            for key, value in self.values.items()
            if _is_profile_setting(key)
        }

    def get_explicit_profile(self, name: str) -> dict[str, str]:
        target = validate_profile_name(name)
        prefix = _profile_prefix(target)
        return {
            key.removeprefix(prefix): value
            for key, value in self.values.items()
            if key.startswith(prefix)
            and key.removeprefix(prefix) != PROFILE_MARKER
        }

    def get_profile(self, name: str | None = None) -> dict[str, object]:
        target = self.get_active_name() if name is None else validate_profile_name(name)
        if not self.has_name(target):
            raise NotFoundError(
                f"profile '{target}' was not found.",
                hint="run `cu profile list` to see available profiles.",
            )
        flat = {**self._base_profile(), **self.get_explicit_profile(target)}
        models = {
            key.removeprefix(MODEL_DEPLOYMENTS_PREFIX): value
            for key, value in flat.items()
            if key.startswith(MODEL_DEPLOYMENTS_PREFIX)
        }
        profile: dict[str, object] = {
            key: value for key, value in flat.items() if key in KNOWN_PROFILE_KEYS
        }
        if models:
            profile["model_deployments"] = models
        return profile

    def create_name(self, name: str) -> None:
        target = normalize_profile_name(name)
        if self.has_name(target):
            raise ConflictError(f"profile '{target}' already exists.")
        self.values[f"{target}.{PROFILE_MARKER}"] = "true"

    def get(self, key: str, *, name: str | None = None) -> str | None:
        setting = validate_profile_key(key)
        target = self.get_active_name() if name is None else validate_profile_name(name)
        if not self.has_name(target):
            raise NotFoundError(f"profile '{target}' was not found.")
        return self.values.get(f"{target}.{setting}") or self.values.get(setting)

    def set(self, key: str, value: str, *, name: str | None = None) -> None:
        setting = validate_profile_key(key)
        cleaned = validate_profile_value(setting, value)
        target = self.get_active_name() if name is None else validate_profile_name(name)
        if not self.has_name(target):
            raise NotFoundError(
                f"profile '{target}' was not found.",
                hint=f"create it with `cu profile create {target}` first.",
            )
        self.values[f"{target}.{setting}"] = cleaned
        if setting == "api_key":
            self.values[f"{target}.auth_mode"] = "key"

    def unset(self, key: str, *, name: str | None = None) -> bool:
        setting = validate_profile_key(key)
        target = self.get_active_name() if name is None else validate_profile_name(name)
        if not self.has_name(target):
            raise NotFoundError(f"profile '{target}' was not found.")
        removed = self.values.pop(f"{target}.{setting}", None) is not None
        if setting == "api_key":
            self.values[f"{target}.auth_mode"] = "login"
        return removed

    def replace_model_deployments(
        self,
        model_deployments: Mapping[str, str],
        *,
        name: str | None = None,
    ) -> None:
        target = self.get_active_name() if name is None else validate_profile_name(name)
        prefix = f"{target}.{MODEL_DEPLOYMENTS_PREFIX}"
        for key in tuple(self.values):
            if key.startswith(prefix):
                del self.values[key]
        for model, deployment in model_deployments.items():
            self.set(
                f"{MODEL_DEPLOYMENTS_PREFIX}{model}",
                str(deployment),
                name=target,
            )

    def has_explicit_model_deployments(self, name: str | None = None) -> bool:
        target = self.get_active_name() if name is None else validate_profile_name(name)
        prefix = f"{target}.{MODEL_DEPLOYMENTS_PREFIX}"
        return any(key.startswith(prefix) for key in self.values)

    def copy_name(self, source: str, destination: str) -> None:
        source_name = validate_profile_name(source)
        destination_name = normalize_profile_name(destination)
        if not self.has_name(source_name):
            raise NotFoundError(f"profile '{source_name}' was not found.")
        if self.has_name(destination_name):
            raise ConflictError(f"profile '{destination_name}' already exists.")
        self.create_name(destination_name)
        for key, value in self.get_explicit_profile(source_name).items():
            self.values[f"{destination_name}.{key}"] = copy.deepcopy(value)

    def rename_name(self, source: str, destination: str) -> None:
        source_name = normalize_profile_name(source)
        destination_name = normalize_profile_name(destination)
        if not self.has_name(source_name):
            raise NotFoundError(f"profile '{source_name}' was not found.")
        if self.has_name(destination_name):
            raise ConflictError(f"profile '{destination_name}' already exists.")
        source_prefix = _profile_prefix(source_name)
        moved = {
            f"{destination_name}.{key.removeprefix(source_prefix)}": value
            for key, value in self.values.items()
            if key.startswith(source_prefix)
        }
        for key in tuple(self.values):
            if key.startswith(source_prefix):
                del self.values[key]
        self.values.update(moved)
        if self.values.get(ACTIVE_PROFILE_KEY) == source_name:
            self.values[ACTIVE_PROFILE_KEY] = destination_name

    def delete_name(self, name: str) -> None:
        target = normalize_profile_name(name)
        if not self.has_name(target):
            raise NotFoundError(f"profile '{target}' was not found.")
        if self.get_active_name() == target:
            raise ConflictError(
                f"cannot delete active CU CLI profile '{target}'.",
                hint="activate another profile before deleting it.",
            )
        prefix = _profile_prefix(target)
        for key in tuple(self.values):
            if key.startswith(prefix):
                del self.values[key]

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_config_lock(self.path):
            try:
                current_raw = self.path.read_bytes()
            except FileNotFoundError:
                current_digest = None
            except OSError as exc:
                raise LocalIOError(
                    f"could not verify Azure CLI configuration '{self.path}': {exc}."
                ) from exc
            else:
                current_digest = hashlib.sha256(current_raw).hexdigest()
            if current_digest != self._source_digest:
                raise ConflictError(
                    f"Azure CLI configuration '{self.path}' changed after it was loaded.",
                    hint="reload the profile and retry the command.",
                )

            updated = _replace_cu_section(self._source_text, self.values)
            encoded = updated.encode("utf-8")
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                dir=self.path.parent,
            )
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_name, self.path)
                self.path.chmod(0o600)
            except Exception:
                Path(temporary_name).unlink(missing_ok=True)
                raise
        self._source_text = updated
        self._source_digest = hashlib.sha256(encoded).hexdigest()
        return self.path


@dataclass
class Profile:
    """Effective CU settings after built-in, saved-profile, and environment precedence."""

    endpoint: str | None = None
    auth_mode: str = "login"
    api_key: str | None = None
    api_version: str = DEFAULT_API_VERSION
    default_analyzer: str | None = None
    model_deployments: dict[str, str] = field(default_factory=dict)
    profile_name: str = DEFAULT_PROFILE_NAME
    path: Path = field(default_factory=azure_config_path)

    @classmethod
    def load_saved(
        cls,
        *,
        profile_name: str | None = None,
        path: Path | None = None,
    ) -> "Profile":
        store = ProfileStore.load(path)
        selected = store.get_active_name() if profile_name is None else validate_profile_name(profile_name)
        profile = cls(profile_name=selected, path=store.path)
        profile._overlay(store.get_profile(selected), source=f"profile '{selected}'")
        return profile

    @classmethod
    def load(
        cls,
        *,
        profile_name: str | None = None,
        path: Path | None = None,
    ) -> "Profile":
        profile = cls.load_saved(profile_name=profile_name, path=path)
        profile._apply_environment()
        return profile

    def _apply_environment(self) -> None:
        endpoint = os.getenv("CU_ENDPOINT") or os.getenv("CONTENTUNDERSTANDING_ENDPOINT")
        if endpoint:
            self.endpoint = endpoint
        auth_mode = os.getenv("CU_AUTH_MODE")
        if auth_mode:
            self.auth_mode = validate_profile_value("auth_mode", auth_mode)
        api_key = os.getenv("CU_API_KEY") or os.getenv("CONTENTUNDERSTANDING_KEY")
        if api_key:
            self.api_key = api_key
            self.auth_mode = "key"
        api_version = os.getenv("CU_API_VERSION")
        if api_version:
            self.api_version = api_version
        for model, environment_name in MODEL_ENV_OVERRIDES.items():
            deployment = os.getenv(environment_name)
            if deployment:
                self.model_deployments[model] = deployment

    @staticmethod
    def _optional_string(
        values: Mapping[str, object],
        key: str,
        *,
        source: str,
    ) -> str | None:
        value = values.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                f"{source} has an invalid '{key}' value; expected a non-empty string."
            )
        return value

    def _overlay(self, values: Mapping[str, object], *, source: str) -> None:
        endpoint = self._optional_string(values, "endpoint", source=source)
        if endpoint is not None:
            self.endpoint = endpoint
        auth_mode = self._optional_string(values, "auth_mode", source=source)
        if auth_mode is not None:
            self.auth_mode = validate_profile_value("auth_mode", auth_mode)
        api_key = self._optional_string(values, "api_key", source=source)
        if api_key is not None:
            self.api_key = api_key
            if auth_mode is None:
                self.auth_mode = "key"
        api_version = self._optional_string(values, "api_version", source=source)
        if api_version is not None:
            self.api_version = api_version
        default_analyzer = self._optional_string(values, "default_analyzer", source=source)
        if default_analyzer is not None:
            self.default_analyzer = default_analyzer
        models = values.get("model_deployments")
        if models is not None:
            if not isinstance(models, Mapping):
                raise ValidationError(
                    f"{source} has invalid model_deployments; expected a mapping."
                )
            self.model_deployments.update(
                {str(key): str(value) for key, value in models.items()}
            )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile_name,
            "endpoint": self.endpoint,
            "auth_mode": self.auth_mode,
            "api_key": "***redacted***" if self.api_key else None,
            "api_version": self.api_version,
            "default_analyzer": self.default_analyzer,
            "model_deployments": dict(self.model_deployments),
        }
