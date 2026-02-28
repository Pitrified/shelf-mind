"""Dependency injection container for the ShelfMind domain layer.

Manages singleton instances of infrastructure components and provides
factory methods for application services scoped to a database session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg
from qdrant_client import QdrantClient

from shelf_mind.application.services.location_service import LocationService
from shelf_mind.application.services.placement_service import PlacementService
from shelf_mind.application.services.search_ranker import SearchRanker
from shelf_mind.application.services.search_service import SearchService
from shelf_mind.application.services.thing_service import ThingService
from shelf_mind.config.shelf_mind_config import ShelfMindConfig
from shelf_mind.infrastructure.db.database import create_db_engine
from shelf_mind.infrastructure.db.database import init_db
from shelf_mind.infrastructure.db.location_repo import SqlLocationRepository
from shelf_mind.infrastructure.db.placement_repo import SqlPlacementRepository
from shelf_mind.infrastructure.db.thing_repo import SqlThingRepository
from shelf_mind.infrastructure.embeddings.text_embedding import (
    SentenceTransformerEmbedder,
)
from shelf_mind.infrastructure.embeddings.text_embedding import TextEmbeddingProvider
from shelf_mind.infrastructure.metadata.metadata_enricher import MetadataEnricher
from shelf_mind.infrastructure.metadata.metadata_enricher import (
    RuleBasedMetadataEnricher,
)
from shelf_mind.infrastructure.vector.qdrant_repository import QdrantVectorRepository
from shelf_mind.infrastructure.vision.vision_strategy import NoOpVisionStrategy
from shelf_mind.infrastructure.vision.vision_strategy import VisionStrategy

if TYPE_CHECKING:
    from sqlmodel import Session


class Container:
    """Dependency injection container.

    Holds singleton infrastructure instances and creates
    session-scoped services on demand.

    Args:
        config: ShelfMindConfig instance.
    """

    def __init__(self, config: ShelfMindConfig | None = None) -> None:
        """Initialize the container.

        Args:
            config: ShelfMindConfig instance, or None for defaults.
        """
        self._config = config or ShelfMindConfig()
        self._qdrant_client: QdrantClient | None = None
        self._vector_repo: QdrantVectorRepository | None = None
        self._embedder: TextEmbeddingProvider | None = None
        self._enricher: MetadataEnricher | None = None
        self._vision: VisionStrategy | None = None
        self._ranker: SearchRanker | None = None
        self._initialized = False

    @property
    def config(self) -> ShelfMindConfig:
        """Return the domain configuration."""
        return self._config

    def initialize(self) -> None:
        """Initialize infrastructure - database engine, tables, and vector collection.

        Call once at application startup.
        """
        if self._initialized:
            return

        lg.info("Initializing ShelfMind container...")

        # Database
        create_db_engine(self._config.database_url)
        init_db()

        # Vector store
        self._qdrant_client = QdrantClient(url=self._config.qdrant_url)
        self._vector_repo = QdrantVectorRepository(
            client=self._qdrant_client,
            collection_name=self._config.qdrant_collection,
            text_vector_dim=self._config.text_vector_dim,
            image_vector_dim=self._config.image_vector_dim,
        )
        self._vector_repo.ensure_collection()

        # Embedding provider (lazy load on first use)
        self._embedder = SentenceTransformerEmbedder(
            model_name=self._config.text_model_name,
        )

        # Metadata enricher
        self._enricher = RuleBasedMetadataEnricher()

        # Vision (no-op for Phase 1)
        self._vision = NoOpVisionStrategy(
            vector_dim=self._config.image_vector_dim,
        )

        # Search ranker
        self._ranker = SearchRanker(
            alpha=self._config.rank_alpha,
            beta=self._config.rank_beta,
            gamma=self._config.rank_gamma,
        )

        self._initialized = True
        lg.info("ShelfMind container initialized")

    def get_vector_repo(self) -> QdrantVectorRepository:
        """Return the singleton VectorRepository.

        Returns:
            QdrantVectorRepository instance.

        Raises:
            RuntimeError: If container not initialized.
        """
        if self._vector_repo is None:
            msg = "Container not initialized - call initialize() first"
            raise RuntimeError(msg)
        return self._vector_repo

    def get_embedder(self) -> TextEmbeddingProvider:
        """Return the singleton TextEmbeddingProvider.

        Returns:
            TextEmbeddingProvider instance.

        Raises:
            RuntimeError: If container not initialized.
        """
        if self._embedder is None:
            msg = "Container not initialized - call initialize() first"
            raise RuntimeError(msg)
        return self._embedder

    def get_enricher(self) -> MetadataEnricher:
        """Return the singleton MetadataEnricher.

        Returns:
            MetadataEnricher instance.

        Raises:
            RuntimeError: If container not initialized.
        """
        if self._enricher is None:
            msg = "Container not initialized - call initialize() first"
            raise RuntimeError(msg)
        return self._enricher

    def get_vision(self) -> VisionStrategy:
        """Return the singleton VisionStrategy.

        Returns:
            VisionStrategy instance.

        Raises:
            RuntimeError: If container not initialized.
        """
        if self._vision is None:
            msg = "Container not initialized - call initialize() first"
            raise RuntimeError(msg)
        return self._vision

    def get_ranker(self) -> SearchRanker:
        """Return the singleton SearchRanker.

        Returns:
            SearchRanker instance.

        Raises:
            RuntimeError: If container not initialized.
        """
        if self._ranker is None:
            msg = "Container not initialized - call initialize() first"
            raise RuntimeError(msg)
        return self._ranker

    # -- Session-scoped service factories --

    def location_service(self, session: Session) -> LocationService:
        """Create a LocationService scoped to the given session.

        Args:
            session: Active SQLModel session.

        Returns:
            LocationService instance.
        """
        repo = SqlLocationRepository(session)
        placement_repo = SqlPlacementRepository(session)
        return LocationService(repo, placement_repo=placement_repo)

    def thing_service(self, session: Session) -> ThingService:
        """Create a ThingService scoped to the given session.

        Args:
            session: Active SQLModel session.

        Returns:
            ThingService instance.
        """
        repo = SqlThingRepository(session)
        return ThingService(
            repo=repo,
            vector_repo=self.get_vector_repo(),
            embedder=self.get_embedder(),
            enricher=self.get_enricher(),
        )

    def placement_service(self, session: Session) -> PlacementService:
        """Create a PlacementService scoped to the given session.

        Args:
            session: Active SQLModel session.

        Returns:
            PlacementService instance.
        """
        return PlacementService(
            placement_repo=SqlPlacementRepository(session),
            thing_repo=SqlThingRepository(session),
            location_repo=SqlLocationRepository(session),
        )

    def search_service(self) -> SearchService:
        """Create a SearchService (session-independent).

        Returns:
            SearchService instance.
        """
        return SearchService(
            vector_repo=self.get_vector_repo(),
            embedder=self.get_embedder(),
            ranker=self.get_ranker(),
            vision=self.get_vision(),
        )
