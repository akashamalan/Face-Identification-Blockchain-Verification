"""Image validation helpers."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import InvalidImageError


def validate_extension(filename: str, settings: Settings) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidImageError(f"Unsupported extension '{ext}'.")
    return ext
