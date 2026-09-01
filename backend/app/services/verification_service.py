"""Verification service — recomputes fingerprint and compares against blockchain."""

from __future__ import annotations

import time

from app.core.logging import get_logger
from app.models.domain import VerificationResult
from app.services.fingerprint_service import FingerprintService
from app.models.domain import SearchResult
from app.utils.hashing import fingerprint_dict

log = get_logger(__name__)


class VerificationService:
    def __init__(self, fingerprint_service: FingerprintService):
        self._fp_service = fingerprint_service

    def verify(
        self,
        canonical_data: dict,
        on_chain_fingerprint: str,
        transaction_hash: str = "",
    ) -> VerificationResult:
        """Recompute fingerprint from canonical data and compare with on-chain value."""
        t0 = time.perf_counter()

        local_fp = fingerprint_dict(canonical_data)
        match = local_fp == on_chain_fingerprint

        elapsed = (time.perf_counter() - t0) * 1000

        status = "VERIFIED" if match else "TAMPERED"
        log.info(
            "Verification result: %s (local=%s… on_chain=%s…)",
            status,
            local_fp[:16],
            on_chain_fingerprint[:16],
        )

        return VerificationResult(
            verified=match,
            status=status,
            local_fingerprint=local_fp,
            on_chain_fingerprint=on_chain_fingerprint,
            transaction_hash=transaction_hash,
            verification_time_ms=round(elapsed, 2),
        )
