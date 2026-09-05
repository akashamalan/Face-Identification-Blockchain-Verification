"""Deterministic SHA-256 hashing with canonical JSON serialisation."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def canonicalise(data: dict[str, Any]) -> str:
    """Return a canonical JSON string for the given dict."""
    cleaned = _deep_clean(data)
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    """Return the SHA-256 hex digest of the input."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def fingerprint_dict(data: dict[str, Any]) -> str:
    """Canonicalise a dict and return its SHA-256 hex digest."""
    canonical = canonicalise(data)
    return sha256_hex(canonical)


def canonicalise_obj(obj: Any) -> str:
    """Canonical JSON for any JSON-serialisable structure, including lists."""
    return json.dumps(
        _deep_clean(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def fingerprint_obj(obj: Any) -> str:
    """Canonicalise any structure (dict or list) and return its SHA-256 hex digest."""
    return sha256_hex(canonicalise_obj(obj))


def _deep_clean(obj: Any) -> Any:
    """Recursively normalise values for deterministic serialisation."""
    if isinstance(obj, dict):
        return {k: _deep_clean(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_deep_clean(item) for item in obj]
    if isinstance(obj, str):
        return _normalise_string(obj)
    return obj


def _normalise_string(s: str) -> str:
    """Strip and collapse internal whitespace."""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s
