"""Temporary file cleanup utilities."""

from __future__ import annotations

import os
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)


def cleanup_temp_file(path: str | Path) -> None:
    """Safely delete a temporary file."""
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
            log.debug("Cleaned up temp file: %s", p.name)
    except OSError as exc:
        log.warning("Failed to clean up temp file %s: %s", path, exc)
