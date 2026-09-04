# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Frontend-neutral CU error types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ErrorCategory(str, Enum):
    USAGE = "usage"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not-found"
    CONFLICT = "conflict"
    SERVICE = "service"
    LOCAL_IO = "local-io"


@dataclass(frozen=True)
class ServiceErrorDetail:
    code: str | None = None
    message: str | None = None
    target: str | None = None


class CuCoreError(Exception):
    """Structured failure translated by each command frontend."""

    category = ErrorCategory.SERVICE

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        status_code: int | None = None,
        details: tuple[ServiceErrorDetail, ...] = (),
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.status_code = status_code
        self.details = details
        self.context = dict(context or {})


class UsageError(CuCoreError):
    category = ErrorCategory.USAGE


class ValidationError(CuCoreError):
    category = ErrorCategory.VALIDATION


class AuthenticationError(CuCoreError):
    category = ErrorCategory.AUTHENTICATION


class NotFoundError(CuCoreError):
    category = ErrorCategory.NOT_FOUND


class ConflictError(CuCoreError):
    category = ErrorCategory.CONFLICT


class ServiceError(CuCoreError):
    category = ErrorCategory.SERVICE


class LocalIOError(CuCoreError):
    category = ErrorCategory.LOCAL_IO
