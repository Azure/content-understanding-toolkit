"""Doctor checks (Click-free): model-requirement analysis.

The ``cu doctor`` command is an interactive diagnostic whose output is printed
progressively; the reusable, testable pieces are the pure requirement analysis
here plus :func:`cu_cli.core.defaults.is_defaults_not_set`.
"""

from __future__ import annotations

from cu_cli_core.defaults import PREBUILT_COMPLETION_KEY, PREBUILT_COMPLETION_MINI_KEY
from .defaults import is_defaults_not_set  # re-exported for callers

__all__ = ["missing_requirements", "is_defaults_not_set"]


def missing_requirements(mapped: dict) -> list[str]:
    """Model requirements not satisfied by *mapped* (model-name -> deployment).

    CU needs the embedding model plus ANY one supported completion model,
    so a single completion model suffices.
    """
    missing: list[str] = []
    has_embedding = bool(mapped.get("prebuilt-analyzer-embedding")) or any(
        name.startswith("text-embedding-") for name in mapped
    )
    if not has_embedding:
        missing.append("an embeddings model (for example text-embedding-3-large)")
    has_completion = bool(mapped.get(PREBUILT_COMPLETION_KEY)) or any(
        not name.startswith(("prebuilt-analyzer-", "text-embedding-"))
        for name in mapped
    )
    if not has_completion:
        missing.append("a supported large language model (LLM) deployment")
    if not mapped.get(PREBUILT_COMPLETION_MINI_KEY):
        missing.append(
            "Content Understanding's prebuilt analyzer mapping for the selected LLM "
            "(created when defaults are configured)"
        )
    return missing
