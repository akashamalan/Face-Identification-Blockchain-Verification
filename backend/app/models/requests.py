"""Request models for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    record_id: str = Field(..., description="Blockchain record ID (fingerprint hex)")
    post_data: dict = Field(..., description="Post data to verify against on-chain record")


class BlockchainRegisterRequest(BaseModel):
    fingerprint: str = Field(..., description="SHA-256 hex fingerprint")
    source_url: str = Field(..., description="Source URL of the discovered content")
