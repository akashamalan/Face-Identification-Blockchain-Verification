"""In-memory blockchain simulation for testing.

Implements the same interface as EthereumProvider but stores records in a dict.
"""

from __future__ import annotations

import hashlib
import time

from app.core.exceptions import RecordNotFoundError
from app.core.logging import get_logger
from app.models.domain import BlockchainRecord
from app.providers.blockchain.base import BlockchainProvider

log = get_logger(__name__)


def _norm(value: str) -> str:
    """Bare lowercase hex, matching EthereumProvider's normalisation."""
    return value.removeprefix("0x").removeprefix("0X").lower()


class LocalBlockchainProvider(BlockchainProvider):
    """In-memory blockchain substitute for integration tests."""

    def __init__(self):
        self._records: dict[str, BlockchainRecord] = {}
        self._tx_counter = 0

    async def health_check(self) -> str:
        return "connected"

    async def register_fingerprint(self, fingerprint_hex: str, source_url: str) -> BlockchainRecord:
        self._tx_counter += 1
        ts = int(time.time())

        record_id = hashlib.sha256(
            f"{fingerprint_hex}:{ts}:{self._tx_counter}".encode()
        ).hexdigest()

        fake_tx = f"0x{'0' * 56}{self._tx_counter:08x}"

        record = BlockchainRecord(
            network="local",
            record_id=record_id,
            transaction_hash=fake_tx,
            block_number=self._tx_counter,
            fingerprint=fingerprint_hex.lower(),
            source_url=source_url,
            timestamp=ts,
            submitter="0x0000000000000000000000000000000000000000",
            explorer_url="",
            submission_time_ms=1.0,
        )
        # Store a copy so a caller mutating the returned record cannot alter the
        # stored one. A real chain returns a snapshot, not a live handle, and
        # verification is only meaningful if read-back is independent of the caller.
        self._records[record_id] = record.model_copy(deep=True)
        log.info("Local blockchain: registered record %s", record_id[:16])
        return record

    async def get_record(self, record_id: str) -> BlockchainRecord:
        record = self._records.get(_norm(record_id))
        if not record:
            raise RecordNotFoundError(record_id)
        return record.model_copy(deep=True)

    async def verify_fingerprint(self, record_id: str, fingerprint_hex: str) -> bool:
        record = self._records.get(_norm(record_id))
        if not record:
            raise RecordNotFoundError(record_id)
        return record.fingerprint == _norm(fingerprint_hex)

    def get_last_record_id(self) -> str | None:
        """Helper for tests — return the ID of the most recently registered record."""
        if self._records:
            return list(self._records.keys())[-1]
        return None
