"""Standardised API response wrappers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: ErrorDetail | None = None


class HealthService(BaseModel):
    status: str  # "ready", "configured", "unconfigured", "connected", "disconnected"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = ""
    services: dict[str, str] = Field(default_factory=dict)
