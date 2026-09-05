"""Request models for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    record_id: str = Field(
        ...,
        description="On-chain record id returned by registration "
                    "(BlockchainRecord.record_id). NOT the fingerprint — the contract "
                    "derives recordId as keccak256(fingerprint, sender, block.timestamp).",
    )
    post_data: dict = Field(
        ...,
        description="Canonical post data to re-hash and compare against the on-chain record.",
    )


class BlockchainRegisterRequest(BaseModel):
    fingerprint: str = Field(..., description="SHA-256 hex fingerprint")
    source_url: str = Field(..., description="Source URL of the discovered content")
