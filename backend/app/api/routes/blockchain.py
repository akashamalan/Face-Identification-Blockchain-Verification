"""Blockchain endpoints — register, retrieve, verify."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import get_blockchain_service, get_verification_service
from app.models.requests import BlockchainRegisterRequest, VerifyRequest
from app.models.responses import ApiResponse

router = APIRouter(prefix="/blockchain", tags=["blockchain"])


@router.post("/register", response_model=ApiResponse)
async def register_fingerprint(req: BlockchainRegisterRequest):
    """Register a fingerprint on the blockchain."""
    svc = get_blockchain_service()
    record = await svc.register(req.fingerprint, req.source_url)
    return ApiResponse(success=True, data=record.model_dump())


@router.get("/record/{record_id}", response_model=ApiResponse)
async def get_record(record_id: str):
    """Retrieve a blockchain record by its on-chain record id."""
    svc = get_blockchain_service()
    record = await svc.get_record(record_id)
    return ApiResponse(success=True, data=record.model_dump())


@router.post("/verify", response_model=ApiResponse)
async def verify_fingerprint(req: VerifyRequest):
    """Re-verify post data against an on-chain record.

    Reads the record back from the chain by `record_id`, recomputes the SHA-256
    fingerprint from the supplied `post_data`, and compares the two. Supplying
    post_data that differs in any way from what was registered yields TAMPERED.

    The previous implementation computed the fingerprint locally and then reported
    that same local value as the "on-chain" fingerprint, so the response could
    never disagree with itself. It also passed a fingerprint where the contract
    expects a recordId (keccak256 of fingerprint+sender+timestamp), which reverts.
    """
    blockchain_svc = get_blockchain_service()
    verification_svc = get_verification_service()

    # Genuine read-back: the comparison value comes from the chain, not from us.
    on_chain_record = await blockchain_svc.get_record(req.record_id)

    result = verification_svc.verify(
        canonical_data=req.post_data,
        on_chain_fingerprint=on_chain_record.fingerprint,
        transaction_hash=on_chain_record.transaction_hash,
        record_id=req.record_id,
    )

    return ApiResponse(
        success=True,
        data={
            **result.model_dump(),
            "on_chain_record": on_chain_record.model_dump(),
        },
    )
