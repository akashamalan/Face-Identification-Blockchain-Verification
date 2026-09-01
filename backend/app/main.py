"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import PipelineBaseError
from app.core.logging import setup_logging, get_logger
from app.models.responses import ApiResponse, ErrorDetail

from app.api.routes import health, face, search, blockchain, pipeline

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging("DEBUG" if settings.DEBUG else "INFO")
    log.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENV)

    if not settings.search_configured:
        log.warning("Search provider is NOT configured. Set SERPAPI_API_KEY.")
    if not settings.blockchain_configured:
        log.warning("Blockchain is NOT configured. Set RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS.")

    yield

    log.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────────
    @app.exception_handler(PipelineBaseError)
    async def pipeline_error_handler(request: Request, exc: PipelineBaseError):
        return JSONResponse(
            status_code=400,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        log.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                ),
            ).model_dump(),
        )

    # ── Routes ───────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api")
    app.include_router(face.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(blockchain.router, prefix="/api")
    app.include_router(pipeline.router, prefix="/api")

    return app


app = create_app()
