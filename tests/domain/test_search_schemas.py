"""Tests for search-related schemas."""

import uuid

from shelf_mind.domain.schemas.search_schemas import SearchQuery
from shelf_mind.domain.schemas.search_schemas import SearchResult


class TestSearchQuery:
    """Tests for SearchQuery schema."""

    def test_defaults(self) -> None:
        """Should have default limit of 10."""
        q = SearchQuery(q="phone charger")
        assert q.q == "phone charger"
        assert q.limit == 10
        assert q.location_filter is None

    def test_with_filter(self) -> None:
        """Should accept location filter."""
        q = SearchQuery(q="keys", location_filter="/home/kitchen", limit=5)
        assert q.location_filter == "/home/kitchen"
        assert q.limit == 5


class TestSearchResult:
    """Tests for SearchResult schema."""

    def test_basic_result(self) -> None:
        """Should construct a search result."""
        result = SearchResult(
            thing_id=uuid.uuid4(),
            name="USB Cable",
            score=0.85,
        )
        assert result.name == "USB Cable"
        assert result.score == 0.85
        assert result.tags == []
