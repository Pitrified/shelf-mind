"""Search service - text and vision search with ranking."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

if TYPE_CHECKING:
    from shelf_mind.application.services.search_ranker import SearchRanker
    from shelf_mind.domain.repositories.vector_repository import VectorRepository
    from shelf_mind.domain.schemas.search_schemas import SearchResult
    from shelf_mind.infrastructure.embeddings.text_embedding import (
        TextEmbeddingProvider,
    )
    from shelf_mind.infrastructure.vision.vision_strategy import VisionStrategy


class SearchService:
    """Application service for text and vision search.

    Orchestrates embedding, vector search, and ranking.

    Args:
        vector_repo: VectorRepository for similarity search.
        embedder: TextEmbeddingProvider for query embedding.
        ranker: SearchRanker for re-ranking results.
        vision: VisionStrategy for image embedding (Phase 2).
    """

    def __init__(
        self,
        vector_repo: VectorRepository,
        embedder: TextEmbeddingProvider,
        ranker: SearchRanker,
        vision: VisionStrategy | None = None,
    ) -> None:
        """Initialize with infrastructure dependencies.

        Args:
            vector_repo: VectorRepository for similarity search.
            embedder: TextEmbeddingProvider for query embedding.
            ranker: SearchRanker for re-ranking results.
            vision: VisionStrategy for image embedding (Phase 2).
        """
        self._vector_repo = vector_repo
        self._embedder = embedder
        self._ranker = ranker
        self._vision = vision

    def search_text(
        self,
        query: str,
        location_filter: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Execute a text search pipeline.

        Pipeline:
        1. Embed query.
        2. Vector similarity search.
        3. Payload filter (location_path prefix).
        4. Ranking layer.
        5. Return DTO with confidence score.

        Args:
            query: Search query string.
            location_filter: Optional location path prefix filter.
            limit: Max results.

        Returns:
            Ranked SearchResult list.
        """
        lg.debug(f"Text search: q='{query}', location={location_filter}, limit={limit}")

        # 1. Embed query
        query_vector = self._embedder.embed(query)

        # 2-3. Vector search with optional location filter
        raw_results = self._vector_repo.search_text(
            vector=query_vector,
            limit=limit,
            location_filter=location_filter,
        )

        # 4. Re-rank
        query_tags = query.lower().split()
        ranked = self._ranker.rank(
            results=raw_results,
            query_tags=query_tags,
            location_path=location_filter,
        )

        lg.debug(f"Text search returned {len(ranked)} results")
        return ranked

    def search_image(
        self,
        image_bytes: bytes,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Execute a vision search pipeline.

        Pipeline:
        1. Preprocess image (resize, normalize).
        2. VisionStrategy.embed()
        3. Vector search against image_vector.
        4. Ranked result return.

        Args:
            image_bytes: Raw image bytes.
            limit: Max results.

        Returns:
            Ranked SearchResult list.
        """
        if self._vision is None:
            lg.warning("Vision search requested but no vision strategy configured")
            return []

        lg.debug(f"Vision search: {len(image_bytes)} bytes, limit={limit}")

        # 1. Preprocess
        processed = self._vision.preprocess(image_bytes)

        # 2. Embed
        vectors = self._vision.embed(processed)
        if not vectors:
            return []

        # Use first embedding (whole image)
        query_vector = vectors[0]

        # 3. Vector search
        raw_results = self._vector_repo.search_image(
            vector=query_vector,
            limit=limit,
        )

        # 4. Basic ranking (no re-rank for vision for now)
        return sorted(raw_results, key=lambda r: r.score, reverse=True)
