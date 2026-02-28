"""Tests for SearchRanker."""

import uuid

import pytest

from shelf_mind.application.services.search_ranker import SearchRanker
from shelf_mind.domain.schemas.search_schemas import SearchResult


def _make_result(
    name: str = "item",
    score: float = 0.5,
    tags: list[str] | None = None,
    location_path: str | None = None,
) -> SearchResult:
    """Create a SearchResult for testing.

    Args:
        name: Thing name.
        score: Vector similarity score.
        tags: Metadata tags.
        location_path: Location path.

    Returns:
        A SearchResult instance.
    """
    return SearchResult(
        thing_id=uuid.uuid4(),
        name=name,
        score=score,
        tags=tags or [],
        location_path=location_path,
    )


class TestSearchRanker:
    """Tests for the SearchRanker."""

    def test_rank_preserves_order_without_bonuses(self) -> None:
        """Without metadata or location, ranking should follow vector score."""
        ranker = SearchRanker(alpha=1.0, beta=0.0, gamma=0.0)
        results = [
            _make_result("low", score=0.3),
            _make_result("high", score=0.9),
            _make_result("mid", score=0.6),
        ]

        ranked = ranker.rank(results)
        assert ranked[0].name == "high"
        assert ranked[1].name == "mid"
        assert ranked[2].name == "low"

    def test_rank_with_tag_overlap(self) -> None:
        """Metadata overlap should boost matching results."""
        ranker = SearchRanker(alpha=0.5, beta=0.5, gamma=0.0)
        results = [
            _make_result("no_tags", score=0.8, tags=[]),
            _make_result("tagged", score=0.5, tags=["phone", "charger"]),
        ]

        ranked = ranker.rank(results, query_tags=["phone", "charger"])
        # Tagged result should be boosted significantly
        assert ranked[0].name == "tagged"

    def test_rank_with_location_bonus(self) -> None:
        """Location match should add bonus."""
        ranker = SearchRanker(alpha=0.5, beta=0.0, gamma=0.5)
        results = [
            _make_result("far", score=0.7, location_path="/Office"),
            _make_result("near", score=0.6, location_path="/Home/Kitchen"),
        ]

        _ranked = ranker.rank(results, location_path="/Home/Kitchen")
        # near: 0.5*0.6 + 0.5*0.1 = 0.35, far: 0.5*0.7 + 0 = 0.35 => tied
        # Increase gap so bonus wins clearly
        results2 = [
            _make_result("far", score=0.7, location_path="/Office"),
            _make_result("near", score=0.65, location_path="/Home/Kitchen"),
        ]
        ranked2 = ranker.rank(results2, location_path="/Home/Kitchen")
        # near: 0.5*0.65 + 0.5*0.1 = 0.375, far: 0.5*0.7 = 0.35
        assert ranked2[0].name == "near"

    def test_rank_location_ancestor_bonus(self) -> None:
        """Ancestor match should get smaller bonus than direct match."""
        ranker = SearchRanker(alpha=0.0, beta=0.0, gamma=1.0)
        results = [
            _make_result("direct", score=0.0, location_path="/Home"),
            _make_result("ancestor", score=0.0, location_path="/Home/Kitchen"),
        ]

        ranked = ranker.rank(results, location_path="/Home")
        # Direct match (+0.1) should beat ancestor match (+0.05)
        assert ranked[0].name == "direct"
        assert ranked[0].score == pytest.approx(0.1)
        assert ranked[1].score == pytest.approx(0.05)

    def test_jaccard_similarity(self) -> None:
        """Jaccard similarity should compute correctly."""
        ranker = SearchRanker()
        assert ranker._jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0
        assert ranker._jaccard_similarity({"a", "b"}, {"a", "c"}) == pytest.approx(
            1 / 3,
        )
        assert ranker._jaccard_similarity(set(), {"a"}) == 0.0

    def test_empty_results(self) -> None:
        """Should handle empty result list."""
        ranker = SearchRanker()
        ranked = ranker.rank([])
        assert ranked == []
