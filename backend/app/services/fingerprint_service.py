"""Fingerprint service — creates canonical representation and SHA-256 hash."""

from __future__ import annotations

from app.core.logging import get_logger
from app.models.domain import CanonicalPostData, Fingerprint, MatchingResult, SearchResult
from app.utils.hashing import fingerprint_dict, sha256_hex

log = get_logger(__name__)


class FingerprintService:
    def create_fingerprint(
        self,
        result: SearchResult,
        input_image_bytes: bytes | None = None,
        matching: MatchingResult | None = None,
    ) -> Fingerprint:
        """Convert a SearchResult into a canonical representation and hash it.

        The hash covers more than the search metadata:
          * input_image_sha256   — the uploaded image bytes
          * matched_image_sha256 — the candidate image bytes that actually matched
          * audit_bundle_sha256  — the ordered evaluation of EVERY candidate

        Without the first two, the on-chain record said nothing about the images
        themselves — either side could be swapped while the fingerprint still verified.
        Without the third, the record proved a result was registered but not that it
        was chosen honestly from the candidate set.
        """
        canonical = CanonicalPostData(
            url=result.url,
            title=result.title,
            domain=result.domain,
            snippet=result.snippet,
            image_url=result.image_url,
            metadata=result.metadata,
            input_image_sha256=sha256_hex(input_image_bytes) if input_image_bytes else "",
            matched_image_sha256=matching.matched_image_sha256 if matching else "",
            audit_bundle_sha256=matching.audit_bundle_sha256 if matching else "",
            match_similarity=matching.best_similarity if matching else None,
            match_threshold=matching.threshold if matching else None,
        )

        data_dict = canonical.model_dump()
        fp_value = fingerprint_dict(data_dict)

        log.info(
            "Fingerprint generated: %s… (input_img=%s… matched_img=%s… bundle=%s…)",
            fp_value[:16],
            canonical.input_image_sha256[:8] or "-",
            canonical.matched_image_sha256[:8] or "-",
            canonical.audit_bundle_sha256[:8] or "-",
        )

        return Fingerprint(
            algorithm="SHA-256",
            value=fp_value,
            canonical_data=data_dict,
        )
