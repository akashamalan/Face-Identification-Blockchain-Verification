"""Abstract base class for search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.domain import SearchResult


class SearchProvider(ABC):
    """Interface for reverse-image / web search providers."""

    @abstractmethod
    async def search_by_image(self, image_bytes: bytes, *, filename: str = "image.jpg") -> list[SearchResult]:
        """Perform a reverse-image search and return normalised results."""
        ...

    @abstractmethod
    async def health_check(self) -> str:
        """Return 'configured' or 'unconfigured'."""
        ...
