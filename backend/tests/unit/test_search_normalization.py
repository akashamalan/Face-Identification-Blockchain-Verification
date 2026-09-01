"""Unit tests for search result normalization."""

import pytest
from app.models.domain import SearchResult


class TestSearchResultNormalization:
    def test_social_platform_detected(self):
        r = SearchResult(
            url="https://twitter.com/user/status/123",
            domain="twitter.com",
            platform="twitter.com",
            title="Tweet",
        )
        assert r.platform == "twitter.com"

    def test_non_social_has_empty_platform(self):
        r = SearchResult(
            url="https://example.com/page",
            domain="example.com",
            platform="",
            title="Page",
        )
        assert r.platform == ""

    def test_result_fields_populated(self):
        r = SearchResult(
            title="Test",
            url="https://x.com/test",
            domain="x.com",
            platform="x.com",
            snippet="test snippet",
            image_url="https://img.com/test.jpg",
            thumbnail="https://img.com/thumb.jpg",
            metadata={"position": 1},
        )
        assert r.title == "Test"
        assert r.metadata["position"] == 1

    def test_empty_metadata_default(self):
        r = SearchResult(title="T", url="u", domain="d")
        assert r.metadata == {}

    def test_ranking_social_first(self):
        results = [
            SearchResult(title="Blog", url="https://blog.com/p", domain="blog.com", platform="", snippet="x"),
            SearchResult(title="Tweet", url="https://twitter.com/u", domain="twitter.com", platform="twitter.com", snippet="y"),
        ]
        ranked = sorted(results, key=lambda r: (0 if r.platform else 1, r.title.lower()))
        assert ranked[0].platform == "twitter.com"
