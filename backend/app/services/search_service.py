"""Search service — orchestrates search providers and result ranking."""

from __future__ import annotations

import time

from app.core.config import Settings
from app.core.exceptions import NoSearchResultsError, SearchProviderError
from app.core.logging import get_logger
from app.models.domain import SearchResponse, SearchResult
from app.providers.search.base import SearchProvider

log = get_logger(__name__)


class SearchService:
    def __init__(self, provider: SearchProvider):
        self._provider = provider

    async def reverse_image_search(
        self,
        image_bytes: bytes,
        filename: str = "image.jpg",
    ) -> SearchResponse:
        """Perform reverse-image search and return ranked results."""
        t0 = time.perf_counter()

        try:
            results = await self._provider.search_by_image(image_bytes, filename=filename)
        except (SearchProviderError, Exception) as exc:
            log.error("Search failed: %s", exc)
            raise

        elapsed = (time.perf_counter() - t0) * 1000
        log.info("Search completed: %d results in %.0fms", len(results), elapsed)

        if not results:
            raise NoSearchResultsError()

        ranked = self._rank_results(results)
        selected = ranked[0] if ranked else None

        return SearchResponse(
            provider=type(self._provider).__name__,
            results_found=len(ranked),
            results=ranked,
            selected_result=selected,
            search_time_ms=round(elapsed, 1),
        )

    def _rank_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Sort results: Google Lens visual match position first, prioritizing social platforms."""

        def score(r: SearchResult) -> tuple[int, int, int, str]:
            # position is assigned 1, 2, 3... by SerpAPI/Google Lens based on visual similarity
            pos = int(r.metadata.get("position", 999))
            social = 0 if r.platform else 1
            has_snippet = 0 if r.snippet else 1
            return (social, pos, has_snippet, r.title.lower())

        return sorted(results, key=score)
