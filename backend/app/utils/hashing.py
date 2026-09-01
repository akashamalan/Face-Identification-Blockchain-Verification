"""Deterministic SHA-256 hashing with canonical JSON serialisation.

Canonicalization algorithm (documented in README):
1. Input dict is recursively processed.
2. Keys are sorted alphabetically at every nesting level.
3. String values are stripped of leading/trailing whitespace.
4. The dict is serialised to JSON with:
   - sort_keys=True
   - separators=(',', ':')   (no extra spaces)
   - ensure_ascii=False       (UTF-8)
5. The resulting JSON string is encoded to UTF-8 bytes.
6. SHA-256 is computed over those bytes.
7. The digest is returned as a lowercase hex string.

No timestamps, random values, or non-deterministic content is included in
the hash input.
"""

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
