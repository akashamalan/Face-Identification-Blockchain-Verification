"""Pipeline endpoint — runs the full face → search → hash → blockchain → verify flow."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from app.api.dependencies import get_pipeline_service
from app.core.config import get_settings
from app.core.security import validate_upload
from app.models.responses import ApiResponse

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", response_model=ApiResponse)
async def run_pipeline(
    file: UploadFile = File(..., description="Image with a face to verify"),
):
    """Execute the complete verification pipeline.

    1. Validate image
    2. Detect face
    3. Reverse-image search
    4. Select best result
    5. Generate SHA-256 fingerprint
    6. Register on blockchain
    7. Verify fingerprint
    """
    settings = get_settings()
    image_bytes = await validate_upload(file, settings)

    svc = get_pipeline_service()
    result = await svc.run(image_bytes, filename=file.filename or "image.jpg")

    return ApiResponse(success=True, data=result.model_dump())
