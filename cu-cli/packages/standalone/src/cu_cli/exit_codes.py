# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Exit-code convention.

    0  success
    2  validation failure (so agents can branch deterministically)
    non-zero (1, 3, ...)  service / auth / config errors

Keeping these as named constants makes the contract explicit at every
``sys.exit`` / ``ClickException`` site.
"""

from __future__ import annotations

SUCCESS = 0
GENERIC_ERROR = 1
VALIDATION_FAILURE = 2

__all__ = ["SUCCESS", "GENERIC_ERROR", "VALIDATION_FAILURE"]
