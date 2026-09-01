"""Face detection and encoding endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File

from app.api.dependencies import get_face_service
from app.core.config import get_settings
from app.core.security import validate_upload
from app.models.responses import ApiResponse
from app.services.face_service import FaceService

router = APIRouter(prefix="/face", tags=["face"])


@router.post("/detect", response_model=ApiResponse)
async def detect_face(
    file: UploadFile = File(..., description="Image file (JPG, PNG, WEBP)"),
):
    """Detect faces in the uploaded image."""
    settings = get_settings()
    image_bytes = await validate_upload(file, settings)

    svc = get_face_service()
    face_data = svc.detect(image_bytes, allow_multiple=True)

    return ApiResponse(success=True, data=face_data.model_dump())


@router.post("/encode", response_model=ApiResponse)
async def encode_face(
    file: UploadFile = File(..., description="Image with exactly one face"),
):
    """Detect one face and generate its embedding. The raw embedding is NOT returned."""
    settings = get_settings()
    image_bytes = await validate_upload(file, settings)

    svc = get_face_service()
    face_data, _embedding = svc.detect_and_encode(image_bytes)

    return ApiResponse(success=True, data=face_data.model_dump())
