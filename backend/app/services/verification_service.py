"""Verification service — recomputes the fingerprint and compares it against the"""

from __future__ import annotations

import time

from app.core.logging import get_logger
from app.models.domain import VerificationResult
from app.services.fingerprint_service import FingerprintService
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
        record_id: str = "",
    ) -> VerificationResult:
        """Recompute the fingerprint from canonical data and compare with the"""
        t0 = time.perf_counter()

        local_fp = fingerprint_dict(canonical_data)
        on_chain = (on_chain_fingerprint or "").removeprefix("0x").lower()
        match = bool(on_chain) and local_fp == on_chain

        elapsed = (time.perf_counter() - t0) * 1000

        status = "VERIFIED" if match else "TAMPERED"
        log.info(
            "Verification result: %s (record=%s local=%s… on_chain=%s…)",
            status,
            record_id[:16] or "-",
            local_fp[:16],
            on_chain[:16] or "-",
        )

        return VerificationResult(
            verified=match,
            status=status,
            local_fingerprint=local_fp,
            on_chain_fingerprint=on_chain,
            record_id=record_id,
            transaction_hash=transaction_hash,
            verification_time_ms=round(elapsed, 2),
        )
