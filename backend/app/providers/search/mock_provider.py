"""Mock search provider — for automated testing ONLY."""

from __future__ import annotations

from app.models.domain import SearchResult
from app.providers.search.base import SearchProvider


class MockSearchProvider(SearchProvider):
    """Returns deterministic canned results for unit/integration tests."""

    async def health_check(self) -> str:
        return "configured"

    async def search_by_image(
        self,
        image_bytes: bytes,
        *,
        filename: str = "image.jpg",
    ) -> list[SearchResult]:
        return [
            SearchResult(
                title="Mock Public Profile — Test User",
                url="https://example.com/mock-profile",
                domain="example.com",
                platform="",
                snippet="This is a mock search result used for automated testing.",
                image_url="https://example.com/mock-image.jpg",
                thumbnail="https://example.com/mock-thumb.jpg",
                metadata={"source": "mock"},
            ),
            SearchResult(
                title="Mock Social Post",
                url="https://twitter.com/mockuser/status/12345",
                domain="twitter.com",
                platform="twitter.com",
                snippet="Mock tweet content for testing.",
                image_url="https://pbs.twimg.com/mock.jpg",
                thumbnail="",
                metadata={"source": "mock"},
            ),
        ]
