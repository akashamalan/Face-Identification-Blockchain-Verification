"""Abstract base class for blockchain providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.domain import BlockchainRecord


class BlockchainProvider(ABC):
    """Interface for blockchain registration and verification."""

    @abstractmethod
    async def register_fingerprint(
        self, fingerprint_hex: str, source_url: str
    ) -> BlockchainRecord:
        """Store a fingerprint on-chain and return the record."""
        ...

    @abstractmethod
    async def get_record(self, record_id: str) -> BlockchainRecord:
        """Retrieve a record by its on-chain ID."""
        ...

    @abstractmethod
    async def verify_fingerprint(self, record_id: str, fingerprint_hex: str) -> bool:
        """Check if a fingerprint matches the stored record."""
        ...

    @abstractmethod
    async def health_check(self) -> str:
        """Return 'connected' or 'disconnected'."""
        ...
