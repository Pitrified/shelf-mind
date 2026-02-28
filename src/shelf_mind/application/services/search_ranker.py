"""Search ranker - scoring and ranking of search results."""

from shelf_mind.domain.schemas.search_schemas import SearchResult


class SearchRanker:
    """Ranks search results using a weighted scoring formula.

    score = alpha * vector_score + beta * metadata_overlap + gamma * location_bonus

    Args:
        alpha: Weight for vector similarity.
        beta: Weight for metadata (tag) overlap.
        gamma: Weight for location match bonus.
    """

    def __init__(
        self,
        alpha: float = 0.7,
        beta: float = 0.2,
        gamma: float = 0.1,
    ) -> None:
        """Initialize with scoring weights.

        Args:
            alpha: Weight for vector similarity.
            beta: Weight for metadata (tag) overlap.
            gamma: Weight for location match bonus.
        """
        self._alpha = alpha
        self._beta = beta
        self._gamma = gamma

    def rank(
        self,
        results: list[SearchResult],
        query_tags: list[str] | None = None,
        location_path: str | None = None,
    ) -> list[SearchResult]:
        """Re-rank results applying the full scoring formula.

        Args:
            results: Raw search results with vector scores.
            query_tags: Tags from the search query for metadata overlap.
            location_path: Query location path for location bonus.

        Returns:
            Re-ranked results sorted by combined score descending.
        """
        query_tag_set = set(query_tags) if query_tags else set()

        scored: list[SearchResult] = []
        for result in results:
            vector_score = result.score
            meta_overlap = self._jaccard_similarity(
                set(result.tags),
                query_tag_set,
            )
            loc_bonus = self._location_bonus(result.location_path, location_path)

            combined = (
                self._alpha * vector_score
                + self._beta * meta_overlap
                + self._gamma * loc_bonus
            )

            scored.append(
                SearchResult(
                    thing_id=result.thing_id,
                    name=result.name,
                    description=result.description,
                    category=result.category,
                    tags=result.tags,
                    location_path=result.location_path,
                    score=combined,
                ),
            )

        return sorted(scored, key=lambda r: r.score, reverse=True)

    @staticmethod
    def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
        """Compute Jaccard similarity between two sets.

        Args:
            set_a: First set.
            set_b: Second set.

        Returns:
            Jaccard index (0-1).
        """
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    @staticmethod
    def _location_bonus(
        result_path: str | None,
        query_path: str | None,
    ) -> float:
        """Calculate location bonus.

        +0.1 if direct match, +0.05 if ancestor match.

        Args:
            result_path: Result's location path.
            query_path: Query's location filter.

        Returns:
            Location bonus value.
        """
        if not result_path or not query_path:
            return 0.0
        if result_path == query_path:
            return 0.1
        if result_path.startswith(query_path):
            return 0.05
        return 0.0
