"""Abstract repository for vector storage and search."""

from abc import ABC
from abc import abstractmethod
import uuid

from shelf_mind.domain.schemas.search_schemas import SearchResult


class VectorRepository(ABC):
    """Interface for vector CRUD and similarity search."""

    @abstractmethod
    def upsert_text_vector(
        self,
        thing_id: uuid.UUID,
        vector: list[float],
        payload: dict,
    ) -> None:
        """Insert or update a text embedding vector.

        Args:
            thing_id: UUID of the Thing.
            vector: Text embedding vector.
            payload: Indexed payload fields (name, category, tags, etc.).
        """

    @abstractmethod
    def upsert_image_vector(
        self,
        thing_id: uuid.UUID,
        vector: list[float],
        payload: dict,
    ) -> None:
        """Insert or update an image embedding vector.

        Args:
            thing_id: UUID of the Thing.
            vector: Image embedding vector.
            payload: Indexed payload fields.
        """

    @abstractmethod
    def search_text(
        self,
        vector: list[float],
        limit: int = 10,
        location_filter: str | None = None,
        category_filter: str | None = None,
        material_filter: str | None = None,
        tags_filter: list[str] | None = None,
    ) -> list[SearchResult]:
        """Search by text vector similarity.

        Args:
            vector: Query embedding.
            limit: Max results.
            location_filter: Optional location_path prefix filter.
            category_filter: Optional category exact match.
            material_filter: Optional material keyword filter.
            tags_filter: Optional tags that must all be present.

        Returns:
            Ranked search results with scores.
        """

    @abstractmethod
    def search_image(
        self,
        vector: list[float],
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search by image vector similarity.

        Args:
            vector: Query image embedding.
            limit: Max results.

        Returns:
            Ranked search results with scores.
        """

    @abstractmethod
    def delete_vectors(self, thing_id: uuid.UUID) -> None:
        """Delete all vectors for a Thing.

        Args:
            thing_id: UUID of the Thing.
        """

    @abstractmethod
    def collection_exists(self) -> bool:
        """Check if the vector collection exists.

        Returns:
            True if collection is available.
        """

    @abstractmethod
    def ensure_collection(self) -> None:
        """Create the vector collection if it does not exist."""
