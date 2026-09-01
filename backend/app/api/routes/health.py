"""Health check and preflight endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import get_blockchain_provider, get_search_provider
from app.core.config import get_settings
from app.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    settings = get_settings()
    services: dict[str, str] = {}

    # Face engine — always available (loaded lazily)
    services["face_engine"] = "ready"

    # Search provider
    try:
        sp = get_search_provider()
        services["search_provider"] = await sp.health_check()
    except Exception:
        services["search_provider"] = "unconfigured"

    # Blockchain
    try:
        bp = get_blockchain_provider()
        services["blockchain"] = await bp.health_check()
    except Exception:
        services["blockchain"] = "disconnected"

    overall = "ok" if all(
        v in ("ready", "configured", "connected") for v in services.values()
    ) else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        services=services,
    )


@router.get("/preflight")
async def preflight():
    """Detailed preflight check — validates all required environment variables."""
    settings = get_settings()
    checks: dict[str, dict] = {}

    checks["search"] = {
        "provider": settings.SEARCH_PROVIDER,
        "configured": settings.search_configured,
        "message": "OK" if settings.search_configured else "Set SERPAPI_API_KEY in .env",
    }
    checks["blockchain"] = {
        "provider": settings.BLOCKCHAIN_PROVIDER,
        "configured": settings.blockchain_configured,
        "message": "OK" if settings.blockchain_configured else "Set BLOCKCHAIN_RPC_URL, BLOCKCHAIN_PRIVATE_KEY, CONTRACT_ADDRESS in .env",
    }

    all_ok = all(c["configured"] for c in checks.values())
    return {
        "ready": all_ok,
        "checks": checks,
    }
