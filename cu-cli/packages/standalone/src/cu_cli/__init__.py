# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""CU CLI — Azure Content Understanding Command Line Interface.

A deterministic, no-LLM CLI over the Content Understanding SDK for authoring,
validating, and running custom analyzers. See
https://github.com/Azure/content-understanding-toolkit/tree/main/cu-cli.
"""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("cu-cli")

__all__ = ["__version__"]
