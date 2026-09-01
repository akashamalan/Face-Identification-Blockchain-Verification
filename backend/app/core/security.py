"""Security utilities: CORS, upload validation, rate limiting."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import InvalidImageError

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


async def validate_upload(file: UploadFile, settings: Settings) -> bytes:
    """Validate uploaded file type, size, and read bytes."""
    if not file.filename:
        raise InvalidImageError("No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidImageError(
            f"Unsupported file type '{ext}'. Allowed: {settings.ALLOWED_IMAGE_EXTENSIONS}"
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise InvalidImageError(
            f"Unsupported MIME type '{file.content_type}'."
        )

    content = await file.read()
    if len(content) == 0:
        raise InvalidImageError("Uploaded file is empty.")

    if len(content) > settings.max_upload_bytes:
        raise InvalidImageError(
            f"File size exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )

    # Basic magic-byte validation
    if not _valid_magic_bytes(content):
        raise InvalidImageError("File content does not match a supported image format.")

    return content


def _valid_magic_bytes(data: bytes) -> bool:
    """Check file magic bytes for JPEG, PNG, WEBP."""
    if data[:2] == b"\xff\xd8":
        return True  # JPEG
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True  # PNG
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True  # WEBP
    return False


def ensure_temp_dir(settings: Settings) -> Path:
    """Create temp upload directory if it doesn't exist."""
    p = Path(settings.TEMP_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p
