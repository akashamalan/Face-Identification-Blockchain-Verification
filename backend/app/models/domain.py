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
    engine: str = Field(
        default="",
        description="Engine that produced this result, e.g. 'insightface:buffalo_l'. "
                    "Never treat a result as a real embedding unless this is set.",
    )
    det_score: float = Field(
        default=0.0,
        description="Raw detector score from the face engine. `confidence` is an "
                    "alias retained for existing clients.",
    )


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    domain: str = ""
    platform: str = ""
    snippet: str = ""
    image_url: str = ""
    thumbnail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity: float | None = Field(
        default=None,
        description="Cosine similarity between the input face embedding and the best "
                    "face found in this candidate's image. None means the candidate was "
                    "never scored (no image, download failed, or no face detected).",
    )
    match_reason: str = Field(
        default="",
        description="Why this candidate was accepted, rejected, or skipped.",
    )


class SearchResponse(BaseModel):
    provider: str = ""
    results_found: int = 0
    results: list[SearchResult] = Field(default_factory=list)
    selected_result: SearchResult | None = None
    search_time_ms: float = 0.0


class CandidateEvidence(BaseModel):
    """One candidate's full evaluation record — the unit of the audit bundle.

    Every candidate the search returned gets one of these, in search-return order,
    whether it was scored or skipped. Hashing the whole ordered list is what makes
    the search auditable: a verifier can confirm the winner was chosen on similarity
    and that no candidate was quietly dropped or reordered.
    """
    position: int = Field(description="0-based index in the order the search returned")
    url: str = ""
    domain: str = ""
    image_source: str = Field(default="", description="'image_url' | 'thumbnail' | ''")
    image_sha256: str = Field(default="", description="SHA-256 of the downloaded bytes")
    image_bytes: int = 0
    faces_detected: int = 0
    matched_face_index: int | None = Field(
        default=None,
        description="WHICH face in the candidate image produced the score. Without "
                    "this a group photo is unreproducible — a verifier could not tell "
                    "which of N faces matched.",
    )
    matched_face_bbox: list[float] = Field(default_factory=list)
    matched_face_det_score: float | None = None
    similarity: float | None = None
    decision: str = Field(
        default="",
        description="'accepted' | 'rejected_below_threshold' | 'skipped'",
    )
    reason: str = ""


class MatchingResult(BaseModel):
    """Outcome of stage 3 — re-encoding candidates and scoring them."""
    status: str = Field(
        default="no_confident_match",
        description="'match' | 'no_confident_match'. no_confident_match is a valid "
                    "outcome, not a failure.",
    )
    threshold: float = 0.0
    candidates: list[CandidateEvidence] = Field(default_factory=list)
    selected_position: int | None = None
    best_similarity: float | None = None
    matched_image_sha256: str = ""
    audit_bundle_sha256: str = Field(
        default="",
        description="SHA-256 over the ordered candidates list. Anchored in the "
                    "fingerprint, so the on-chain record covers the whole search.",
    )
    candidates_total: int = 0
    candidates_scored: int = 0
    candidates_skipped: int = 0
    matching_time_ms: float = 0.0


class CanonicalPostData(BaseModel):
    """Canonical representation of a discovered result for fingerprinting.

    Includes the input and matched image digests and the audit-bundle digest, so the
    on-chain fingerprint covers the actual image bytes and the full candidate
    evaluation — not just the search metadata.
    """
    url: str
    title: str
    domain: str
    snippet: str
    image_url: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    input_image_sha256: str = ""
    matched_image_sha256: str = ""
    audit_bundle_sha256: str = ""
    match_similarity: float | None = None
    match_threshold: float | None = None


class Fingerprint(BaseModel):
    algorithm: str = "SHA-256"
    value: str = ""
    canonical_data: dict[str, Any] = Field(default_factory=dict)


class BlockchainRecord(BaseModel):
    network: str = ""
    record_id: str = Field(
        default="",
        description="On-chain record identifier, as bare lowercase hex (no 0x). "
                    "Required to read the record back; without it the record is "
                    "write-only and verification cannot be independent.",
    )
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
    on_chain_fingerprint: str = Field(
        default="",
        description="Fingerprint as READ BACK from the chain via getRecord — never "
                    "the value that was submitted.",
    )
    record_id: str = ""
    transaction_hash: str = ""
    verification_time_ms: float = 0.0


class PipelineResult(BaseModel):
    pipeline_id: str = ""
    status: str = "pending"  # success | error
    face: FaceData = Field(default_factory=FaceData)
    search: SearchResponse = Field(default_factory=SearchResponse)
    matching: MatchingResult = Field(default_factory=MatchingResult)
    fingerprint: Fingerprint = Field(default_factory=Fingerprint)
    blockchain: BlockchainRecord = Field(default_factory=BlockchainRecord)
    on_chain_record: BlockchainRecord = Field(
        default_factory=BlockchainRecord,
        description="The record as READ BACK from the chain by record_id. This is "
                    "the value verification compares against.",
    )
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
