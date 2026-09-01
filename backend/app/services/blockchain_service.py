"""Blockchain service — business logic for fingerprint registration and retrieval."""

from __future__ import annotations

import time

from app.core.logging import get_logger
from app.models.domain import BlockchainRecord
from app.providers.blockchain.base import BlockchainProvider

log = get_logger(__name__)


class BlockchainService:
    def __init__(self, provider: BlockchainProvider):
        self._provider = provider

    async def register(self, fingerprint_hex: str, source_url: str) -> BlockchainRecord:
        log.info("Registering fingerprint on blockchain…")
        t0 = time.perf_counter()
        record = await self._provider.register_fingerprint(fingerprint_hex, source_url)
        elapsed = (time.perf_counter() - t0) * 1000
        record.submission_time_ms = round(elapsed, 1)
        log.info(
            "Blockchain registration complete: tx=%s block=%d time=%.0fms",
            record.transaction_hash[:16],
            record.block_number,
            elapsed,
        )
        return record

    async def get_record(self, record_id: str) -> BlockchainRecord:
        return await self._provider.get_record(record_id)

    async def verify(self, record_id: str, fingerprint_hex: str) -> bool:
        return await self._provider.verify_fingerprint(record_id, fingerprint_hex)
