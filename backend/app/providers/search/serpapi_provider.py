"""SerpAPI Google Lens reverse-image search provider."""

from __future__ import annotations

import os
import tempfile
from urllib.parse import urlparse

import httpx

from app.core.exceptions import (
    SearchProviderError,
    SearchTimeoutError,
    SearchNotConfiguredError,
)
from app.core.logging import get_logger
from app.models.domain import SearchResult
from app.providers.search.base import SearchProvider

log = get_logger(__name__)

SERPAPI_BASE_URL = "https://serpapi.com/search"

SOCIAL_PLATFORMS = {
    "twitter.com", "x.com", "instagram.com", "facebook.com", "linkedin.com",
    "tiktok.com", "youtube.com", "reddit.com", "pinterest.com", "tumblr.com",
    "flickr.com", "vk.com", "medium.com", "github.com",
}


class SerpApiSearchProvider(SearchProvider):
    def __init__(self, api_key: str, timeout: int = 30):
        self._api_key = api_key
        self._timeout = timeout

    async def health_check(self) -> str:
        return "configured" if self._api_key else "unconfigured"

    async def search_by_image(
        self,
        image_bytes: bytes,
        *,
        filename: str = "image.jpg",
    ) -> list[SearchResult]:
        if not self._api_key:
            raise SearchNotConfiguredError()

        # Write to a temp file that SerpAPI can receive as upload
        suffix = os.path.splitext(filename)[1] or ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            tmp.write(image_bytes)
            tmp.flush()
            tmp_path = tmp.name
            tmp.close()

            results = await self._do_search(tmp_path, filename)
            return results
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def _do_search(self, file_path: str, filename: str) -> list[SearchResult]:
        """Call SerpAPI 2-step Google Lens endpoint (upload to /image -> search /search.json)."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                # Step 1: Upload image file to SerpAPI to get image_id
                with open(file_path, "rb") as f:
                    file_content = f.read()

                upload_resp = await client.post(
                    "https://serpapi.com/image",
                    data={"api_key": self._api_key},
                    files={"image": (filename, file_content)},
                )

                if upload_resp.status_code == 401:
                    raise SearchProviderError("Invalid SerpAPI API key.")
                if upload_resp.status_code == 429:
                    raise SearchProviderError("SerpAPI rate limit exceeded.")
                if upload_resp.status_code != 200:
                    raise SearchProviderError(f"SerpAPI image upload failed with HTTP {upload_resp.status_code}")

                upload_data = upload_resp.json()
                image_id = upload_data.get("image_id") or upload_data.get("id")
                if not image_id:
                    raise SearchProviderError("SerpAPI did not return a valid image_id.")

                # Step 2: Query Google Lens search using image_id
                search_resp = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "engine": "google_lens",
                        "image_id": image_id,
                        "api_key": self._api_key,
                    },
                )

                if search_resp.status_code != 200:
                    raise SearchProviderError(f"SerpAPI search failed with HTTP {search_resp.status_code}")

                data = search_resp.json()
                return self._parse_results(data)

        except httpx.TimeoutException as exc:
            raise SearchTimeoutError(f"SerpAPI request timed out after {self._timeout}s") from exc
        except httpx.RequestError as exc:
            raise SearchProviderError(f"Network error contacting SerpAPI: {exc}") from exc

    def _parse_results(self, data: dict) -> list[SearchResult]:
        """Normalise SerpAPI response into SearchResult objects."""
        results: list[SearchResult] = []

        # Google Lens returns visual_matches and/or knowledge_graph
        for match in data.get("visual_matches", []):
            sr = self._normalise_match(match)
            if sr:
                results.append(sr)

        # Also check knowledge_graph for identity matches
        kg = data.get("knowledge_graph", [])
        if isinstance(kg, dict):
            kg = [kg]
        for item in kg:
            sr = self._normalise_kg(item)
            if sr:
                results.append(sr)

        # Sort: social media first, then by position
        results.sort(key=lambda r: (0 if r.platform else 1, r.title))
        log.info("SerpAPI returned %d normalised results", len(results))
        return results

    def _normalise_match(self, match: dict) -> SearchResult | None:
        url = match.get("link", "")
        if not url:
            return None

        domain = urlparse(url).netloc.lower().removeprefix("www.")
        platform = domain if domain in SOCIAL_PLATFORMS else ""

        return SearchResult(
            title=match.get("title", ""),
            url=url,
            domain=domain,
            platform=platform,
            snippet=match.get("snippet", match.get("source", "")),
            # NEVER fall back to `link` here. `link` is the PAGE url; using it as
            # image_url makes every candidate look like it has an image, so the
            # matcher downloads HTML, fails to decode it, and scores nothing.
            # Leave it empty and let the thumbnail be used instead.
            image_url=match.get("source_image") or match.get("image") or "",
            thumbnail=match.get("thumbnail", ""),
            metadata={
                k: v for k, v in match.items()
                if k in ("position", "source", "source_icon")
            },
        )

    def _normalise_kg(self, item: dict) -> SearchResult | None:
        title = item.get("title", "")
        link = item.get("link", item.get("search_link", ""))
        if not title and not link:
            return None

        domain = urlparse(link).netloc.lower().removeprefix("www.") if link else ""

        return SearchResult(
            title=title,
            url=link,
            domain=domain,
            platform=domain if domain in SOCIAL_PLATFORMS else "",
            snippet=item.get("subtitle", item.get("description", "")),
            image_url=item.get("image", ""),
            thumbnail=item.get("thumbnail", ""),
            metadata={"type": "knowledge_graph"},
        )
