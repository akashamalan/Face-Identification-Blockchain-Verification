"""Fingerprint service — creates canonical representation and SHA-256 hash."""

from __future__ import annotations

from app.core.logging import get_logger
from app.models.domain import CanonicalPostData, Fingerprint, SearchResult
from app.utils.hashing import canonicalise, fingerprint_dict

log = get_logger(__name__)


class FingerprintService:
    def create_fingerprint(self, result: SearchResult) -> Fingerprint:
        """Convert a SearchResult into a canonical representation and hash it."""
        canonical = CanonicalPostData(
            url=result.url,
            title=result.title,
            domain=result.domain,
            snippet=result.snippet,
            image_url=result.image_url,
            metadata=result.metadata,
        )

        data_dict = canonical.model_dump()
        fp_value = fingerprint_dict(data_dict)

        log.info("Fingerprint generated: %s…", fp_value[:16])

        return Fingerprint(
            algorithm="SHA-256",
            value=fp_value,
            canonical_data=data_dict,
        )
