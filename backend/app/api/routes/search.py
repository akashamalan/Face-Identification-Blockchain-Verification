"""Search endpoint — standalone reverse-image search."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File

from app.api.dependencies import get_search_service
from app.core.config import get_settings
from app.core.security import validate_upload
from app.models.responses import ApiResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/reverse-image", response_model=ApiResponse)
async def reverse_image_search(
    file: UploadFile = File(..., description="Image file to search"),
):
    """Perform a genuine reverse-image search using the configured provider."""
    settings = get_settings()
    image_bytes = await validate_upload(file, settings)

    svc = get_search_service()
    response = await svc.reverse_image_search(
        image_bytes, filename=file.filename or "image.jpg"
    )

    return ApiResponse(success=True, data=response.model_dump())
