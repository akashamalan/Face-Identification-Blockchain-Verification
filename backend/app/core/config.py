"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Face Verification Pipeline"
    APP_VERSION: str = "1.0.0"
    ENV: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".webp"]
    TEMP_DIR: str = "tmp_uploads"

    SEARCH_PROVIDER: Literal["serpapi", "mock"] = "serpapi"
    SERPAPI_API_KEY: str = ""
    SEARCH_TIMEOUT_SECONDS: int = 30

    BLOCKCHAIN_PROVIDER: Literal["ethereum", "local"] = "ethereum"
    BLOCKCHAIN_RPC_URL: str = ""
    BLOCKCHAIN_PRIVATE_KEY: str = ""
    CONTRACT_ADDRESS: str = ""
    CHAIN_ID: int = 11155111  # Sepolia
    BLOCKCHAIN_TIMEOUT_SECONDS: int = 120

    FACE_DETECTION_MODEL: str = "buffalo_l"
    FACE_DETECTION_THRESHOLD: float = 0.5

    MATCH_THRESHOLD: float = 0.40
    MATCH_MAX_CANDIDATES: int = 60
    MATCH_CONCURRENCY: int = 4
    MATCH_DOWNLOAD_CONCURRENCY: int = 16
    MATCH_DOWNLOAD_TIMEOUT_SECONDS: int = 10
    MATCH_MAX_IMAGE_BYTES: int = 8 * 1024 * 1024

    @field_validator("MATCH_THRESHOLD")
    @classmethod
    def threshold_in_range(cls, v: float) -> float:
        if not -1.0 <= v <= 1.0:
            raise ValueError("MATCH_THRESHOLD is a cosine similarity; it must be in [-1, 1]")
        return v

    @field_validator("SEARCH_PROVIDER")
    @classmethod
    def block_mock_in_production(cls, v: str, info) -> str:
        env = info.data.get("ENV", "development")
        if v == "mock" and env == "production":
            raise ValueError("MockSearchProvider is not allowed in production")
        return v

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def search_configured(self) -> bool:
        if self.SEARCH_PROVIDER == "serpapi":
            return bool(self.SERPAPI_API_KEY)
        return True

    @property
    def blockchain_configured(self) -> bool:
        if self.BLOCKCHAIN_PROVIDER == "ethereum":
            return all([
                self.BLOCKCHAIN_RPC_URL,
                self.BLOCKCHAIN_PRIVATE_KEY,
                self.CONTRACT_ADDRESS,
            ])
        return True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
