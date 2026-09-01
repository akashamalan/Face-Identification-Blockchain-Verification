"""Domain models used across the application."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FaceData(BaseModel):
    face_detected: bool = False
    face_count: int = 0
    embedding_generated: bool = False
    bbox: list[float] = Field(default_factory=list, description="Bounding box [x1,y1,x2,y2]")
    confidence: float = 0.0
    processing_time_ms: float = 0.0


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    domain: str = ""
    platform: str = ""
    snippet: str = ""
    image_url: str = ""
    thumbnail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    provider: str = ""
    results_found: int = 0
    results: list[SearchResult] = Field(default_factory=list)
    selected_result: SearchResult | None = None
    search_time_ms: float = 0.0


class CanonicalPostData(BaseModel):
    """Canonical representation of a discovered result for fingerprinting."""
    url: str
    title: str
    domain: str
    snippet: str
    image_url: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Fingerprint(BaseModel):
    algorithm: str = "SHA-256"
    value: str = ""
    canonical_data: dict[str, Any] = Field(default_factory=dict)


class BlockchainRecord(BaseModel):
    network: str = ""
    transaction_hash: str = ""
    block_number: int = 0
    fingerprint: str = ""
    source_url: str = ""
    timestamp: int = 0
    submitter: str = ""
    explorer_url: str = ""
    submission_time_ms: float = 0.0


class VerificationResult(BaseModel):
    verified: bool = False
    status: str = "PENDING"  # VERIFIED | TAMPERED | PENDING | ERROR
    local_fingerprint: str = ""
    on_chain_fingerprint: str = ""
    transaction_hash: str = ""
    verification_time_ms: float = 0.0


class PipelineResult(BaseModel):
    pipeline_id: str = ""
    status: str = "pending"  # success | error
    face: FaceData = Field(default_factory=FaceData)
    search: SearchResponse = Field(default_factory=SearchResponse)
    fingerprint: Fingerprint = Field(default_factory=Fingerprint)
    blockchain: BlockchainRecord = Field(default_factory=BlockchainRecord)
    verification: VerificationResult = Field(default_factory=VerificationResult)
    total_time_ms: float = 0.0
    error: str | None = None


class StageTimings(BaseModel):
    face_ms: float = 0.0
    search_ms: float = 0.0
    fingerprint_ms: float = 0.0
    blockchain_ms: float = 0.0
    verification_ms: float = 0.0
    total_ms: float = 0.0
