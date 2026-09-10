# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Service-aligned file extensions used for safe discovery."""

from __future__ import annotations

import os

# Keep this list aligned with:
# https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits
DOCUMENT_SAMPLE_EXTS = frozenset({
    ".pdf", ".tiff",
    ".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm", ".doc", ".xls", ".ppt",
    ".odt", ".ods", ".odp", ".epub",
    ".txt", ".html", ".md", ".rtf", ".xml", ".json", ".csv", ".tsv", ".kml", ".eml", ".msg",
})
IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".jpe", ".png", ".bmp", ".heif", ".heic"})
AUDIO_EXTS = frozenset({
    ".wav", ".mp3", ".mp4", ".opus", ".ogg", ".flac", ".wma", ".aac", ".webm", ".m4a",
})
VIDEO_EXTS = frozenset({".mp4", ".m4v", ".flv", ".wmv", ".asf", ".avi", ".mkv", ".mov"})

KNOWN_SERVICE_INPUT_EXTS = (
    DOCUMENT_SAMPLE_EXTS | IMAGE_EXTS | AUDIO_EXTS | VIDEO_EXTS
)


DEFAULT_ANALYZER_ENV = "CU_DEFAULT_ANALYZER"

# Zero-config defaults: the "*Search" prebuilts return layout markdown plus
# LLM descriptions of figures/segments, which is what an agent needs to
# understand a file it has never seen. Video wins for extensions shared with
# audio (.mp4/.webm).
DEFAULT_ANALYZERS = {
    "document": "prebuilt-documentSearch",
    "image": "prebuilt-imageSearch",
    "audio": "prebuilt-audioSearch",
    "video": "prebuilt-videoSearch",
}


def modality_of(path: "str | os.PathLike[str]") -> str:
    """Best-effort modality from the file extension (documents when unknown)."""
    ext = os.path.splitext(os.fspath(path))[1].lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in IMAGE_EXTS:
        return "image"
    return "document"


def default_analyzer_for(
    path: "str | os.PathLike[str]",
    *,
    explicit: "str | None" = None,
    profile_default: "str | None" = None,
) -> str:
    """Resolve the analyzer for one input.

    Precedence: ``--analyzer`` > ``CU_DEFAULT_ANALYZER`` > profile
    ``default_analyzer`` > modality default (see :data:`DEFAULT_ANALYZERS`).
    """
    env_default = os.environ.get(DEFAULT_ANALYZER_ENV, "").strip()
    return (
        explicit
        or env_default
        or profile_default
        or DEFAULT_ANALYZERS[modality_of(path)]
    )
