# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""In-memory custom analyzers for documentation examples that have no analyzer recordings."""

from __future__ import annotations

from types import SimpleNamespace


class LocalAnalyzers:
    """Keeps custom analyzers in memory and forwards other calls to *service*."""

    def __init__(self, service, created: dict[str, dict]):
        self._service = service
        self._created = created

    def __getattr__(self, name):
        return getattr(self._service, name)

    def begin_create_analyzer(self, name, definition):
        self._created[name] = definition
        return SimpleNamespace(result=lambda: self.get_analyzer(name))

    def get_analyzer(self, name):
        definition = {"analyzerId": name, **self._created[name]}
        return SimpleNamespace(analyzer_id=name, as_dict=lambda: definition)

    def delete_analyzer(self, name):
        del self._created[name]
