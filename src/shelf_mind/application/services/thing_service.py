"""Thing management service with metadata enrichment and vector indexing."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
import json
from typing import TYPE_CHECKING
import uuid

from loguru import logger as lg

from shelf_mind.application.errors import ThingNotFoundError
from shelf_mind.domain.entities.thing import Thing
from shelf_mind.domain.schemas.metadata_schema import MetadataSchema

if TYPE_CHECKING:
    import uuid

    from shelf_mind.domain.repositories.placement_repository import PlacementRepository
    from shelf_mind.domain.repositories.thing_repository import ThingRepository
    from shelf_mind.domain.repositories.vector_repository import VectorRepository
    from shelf_mind.infrastructure.embeddings.text_embedding import (
        TextEmbeddingProvider,
    )
    from shelf_mind.infrastructure.metadata.metadata_enricher import MetadataEnricher


class ThingService:
    """Application service for Thing CRUD with metadata and vector indexing.

    Args:
        repo: ThingRepository implementation.
        vector_repo: VectorRepository for embedding storage.
        embedder: TextEmbeddingProvider for generating vectors.
        enricher: MetadataEnricher for extracting structured metadata.
        placement_repo: PlacementRepository for cascade deletion.
    """

    def __init__(
        self,
        repo: ThingRepository,
        vector_repo: VectorRepository,
        embedder: TextEmbeddingProvider,
        enricher: MetadataEnricher,
        placement_repo: PlacementRepository | None = None,
    ) -> None:
        """Initialize with repository and infrastructure dependencies.

        Args:
            repo: ThingRepository implementation.
            vector_repo: VectorRepository for embedding storage.
            embedder: TextEmbeddingProvider for generating vectors.
            enricher: MetadataEnricher for extracting structured metadata.
            placement_repo: PlacementRepository for cascade deletion.
        """
        self._repo = repo
        self._vector_repo = vector_repo
        self._embedder = embedder
        self._enricher = enricher
        self._placement_repo = placement_repo

    def create_thing(
        self,
        name: str,
        description: str = "",
        location_path: str | None = None,
    ) -> Thing:
        """Register a new Thing with metadata enrichment and vector indexing.

        Steps:
        1. Deterministic metadata extraction.
        2. Metadata schema validation.
        3. Persist Thing in SQL.
        4. Generate text embedding.
        5. Store vector in Qdrant.

        Args:
            name: Thing name (1-120 chars, required).
            description: Optional description.
            location_path: Current location path for payload indexing.

        Returns:
            Created Thing.
        """
        # 1. Enrich metadata
        metadata = self._enricher.enrich(name, description or None)
        metadata_json = metadata.model_dump_json()

        # 2. Persist
        thing = Thing(
            name=name,
            description=description,
            metadata_json=metadata_json,
        )
        thing = self._repo.create(thing)

        # 3. Generate and store text embedding
        embed_text = self._build_embed_text(name, description, metadata.tags)
        self._index_text_vector(thing, embed_text, metadata, location_path)

        lg.info(f"Created thing: '{name}' ({thing.id})")
        return thing

    def get_thing(self, thing_id: uuid.UUID) -> Thing:
        """Get a Thing by id.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            The Thing.

        Raises:
            ThingNotFoundError: If not found.
        """
        thing = self._repo.get_by_id(thing_id)
        if thing is None:
            msg = f"Thing {thing_id} not found"
            raise ThingNotFoundError(msg)
        return thing

    def list_things(self, offset: int = 0, limit: int = 50) -> list[Thing]:
        """List Things with pagination.

        Args:
            offset: Skip count.
            limit: Max results.

        Returns:
            List of Things.
        """
        return self._repo.list_all(offset=offset, limit=limit)

    def count_things(self) -> int:
        """Count total Things.

        Returns:
            Total count.
        """
        return self._repo.count()

    def update_thing(
        self,
        thing_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        *,
        regenerate_metadata: bool = False,
        location_path: str | None = None,
    ) -> Thing:
        """Update a Thing, optionally regenerating metadata and re-indexing.

        Args:
            thing_id: UUID of the Thing.
            name: New name (or None to keep existing).
            description: New description (or None to keep existing).
            regenerate_metadata: Whether to re-run metadata enrichment.
            location_path: Current location path for payload indexing.

        Returns:
            Updated Thing.

        Raises:
            ThingNotFoundError: If not found.
        """
        thing = self.get_thing(thing_id)

        if name is not None:
            thing.name = name
        if description is not None:
            thing.description = description

        if regenerate_metadata:
            metadata = self._enricher.enrich(thing.name, thing.description or None)
            thing.metadata_json = metadata.model_dump_json()

        thing.updated_at = datetime.now(tz=UTC)
        thing = self._repo.update(thing)

        # Re-index vectors
        metadata_dict = json.loads(thing.metadata_json)
        embed_text = self._build_embed_text(
            thing.name,
            thing.description,
            metadata_dict.get("tags", []),
        )
        metadata = MetadataSchema.model_validate(metadata_dict)
        self._index_text_vector(thing, embed_text, metadata, location_path)

        lg.info(f"Updated thing: '{thing.name}' ({thing.id})")
        return thing

    def delete_thing(self, thing_id: uuid.UUID) -> bool:
        """Delete a Thing and its vectors.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            True if deleted.

        Raises:
            ThingNotFoundError: If not found.
        """
        self.get_thing(thing_id)  # ensure exists
        self._vector_repo.delete_vectors(thing_id)
        if self._placement_repo is not None:
            self._placement_repo.delete_by_thing(thing_id)
        deleted = self._repo.delete(thing_id)
        lg.info(f"Deleted thing: {thing_id}")
        return deleted

    def index_image(
        self,
        thing_id: uuid.UUID,
        image_vector: list[float],
    ) -> None:
        """Store an image embedding for an existing Thing.

        Args:
            thing_id: UUID of the Thing (must exist).
            image_vector: Pre-computed image embedding.

        Raises:
            ThingNotFoundError: If thing not found.
        """
        thing = self.get_thing(thing_id)
        payload = {
            "name": thing.name,
            "description": thing.description,
        }
        self._vector_repo.upsert_image_vector(thing_id, image_vector, payload)
        lg.info(f"Indexed image vector for thing: {thing.name} ({thing_id})")

    def _index_text_vector(
        self,
        thing: Thing,
        embed_text: str,
        metadata,  # noqa: ANN001
        location_path: str | None,
    ) -> None:
        """Generate text embedding and upsert into vector store.

        Args:
            thing: Thing entity.
            embed_text: Text to embed.
            metadata: MetadataSchema instance.
            location_path: Current location path for filtering.
        """
        vector = self._embedder.embed(embed_text)
        payload = {
            "name": thing.name,
            "description": thing.description,
            "category": metadata.category,
            "tags": metadata.tags,
            "location_path": location_path or "",
        }
        self._vector_repo.upsert_text_vector(thing.id, vector, payload)

    @staticmethod
    def _build_embed_text(
        name: str,
        description: str,
        tags: list[str],
    ) -> str:
        """Build a rich text string for embedding.

        Args:
            name: Thing name.
            description: Thing description.
            tags: Metadata tags.

        Returns:
            Combined text for embedding.
        """
        parts = [name]
        if description:
            parts.append(description)
        if tags:
            parts.append(" ".join(tags))
        return " ".join(parts)
