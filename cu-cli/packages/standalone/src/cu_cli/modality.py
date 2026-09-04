"""Service-aligned file extensions used for safe discovery."""

from __future__ import annotations

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
