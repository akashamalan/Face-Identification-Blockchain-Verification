"""Blockchain endpoints — register, retrieve, verify."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import get_blockchain_service, get_fingerprint_service, get_verification_service
from app.models.requests import BlockchainRegisterRequest, VerifyRequest
from app.models.responses import ApiResponse
from app.utils.hashing import fingerprint_dict

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


@router.post("/register", response_model=ApiResponse)
async def register_fingerprint(req: BlockchainRegisterRequest):
    """Register a fingerprint on the blockchain."""
    svc = get_blockchain_service()
    record = await svc.register(req.fingerprint, req.source_url)
    return ApiResponse(success=True, data=record.model_dump())


@router.get("/record/{record_id}", response_model=ApiResponse)
async def get_record(record_id: str):
    """Retrieve a blockchain record by ID."""
    svc = get_blockchain_service()
    record = await svc.get_record(record_id)
    return ApiResponse(success=True, data=record.model_dump())


@router.post("/verify", response_model=ApiResponse)
async def verify_fingerprint(req: VerifyRequest):
    """Verify post data against a blockchain record."""
    verification_svc = get_verification_service()
    blockchain_svc = get_blockchain_service()

    # Recompute fingerprint from provided data
    local_fp = fingerprint_dict(req.post_data)

    # Get on-chain fingerprint
    on_chain_verified = await blockchain_svc.verify(req.record_id, local_fp)

    result = verification_svc.verify(
        canonical_data=req.post_data,
        on_chain_fingerprint=local_fp if on_chain_verified else "MISMATCH",
        transaction_hash=req.record_id,
    )

    return ApiResponse(success=True, data=result.model_dump())
