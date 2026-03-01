"""Qdrant implementation of VectorRepository."""

import uuid

from loguru import logger as lg
from qdrant_client import QdrantClient
from qdrant_client import models

from shelf_mind.domain.repositories.vector_repository import VectorRepository
from shelf_mind.domain.schemas.search_schemas import SearchResult


class QdrantVectorRepository(VectorRepository):
    """Qdrant-backed vector storage and similarity search.

    Uses named vectors to store both text and image embeddings in a
    single collection.

    Args:
        client: Qdrant client instance.
        collection_name: Collection name.
        text_vector_dim: Dimensionality of text vectors.
        image_vector_dim: Dimensionality of image vectors.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "things",
        text_vector_dim: int = 384,
        image_vector_dim: int = 512,
    ) -> None:
        """Initialize with Qdrant client and collection parameters.

        Args:
            client: Qdrant client instance.
            collection_name: Collection name.
            text_vector_dim: Dimensionality of text vectors.
            image_vector_dim: Dimensionality of image vectors.
        """
        self._client = client
        self._collection = collection_name
        self._text_dim = text_vector_dim
        self._image_dim = image_vector_dim

    def ensure_collection(self) -> None:
        """Create the vector collection if it does not exist."""
        if self.collection_exists():
            lg.debug(f"Collection '{self._collection}' already exists")
            return

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                "text_vector": models.VectorParams(
                    size=self._text_dim,
                    distance=models.Distance.COSINE,
                ),
                "image_vector": models.VectorParams(
                    size=self._image_dim,
                    distance=models.Distance.COSINE,
                ),
            },
        )

        # Create payload indexes for filtering
        for field_name in ("thing_id", "name", "category", "location_path"):
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="tags",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

        lg.info(f"Created Qdrant collection '{self._collection}'")

    def collection_exists(self) -> bool:
        """Check if the vector collection exists.

        Returns:
            True if collection is available.
        """
        collections = self._client.get_collections().collections
        return any(c.name == self._collection for c in collections)

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
            payload: Indexed payload fields.
        """
        point_id = str(thing_id)
        payload["thing_id"] = point_id

        self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector={"text_vector": vector},
                    payload=payload,
                ),
            ],
        )
        lg.debug(f"Upserted text vector for thing {point_id}")

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
        point_id = str(thing_id)
        payload["thing_id"] = point_id

        self._client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector={"image_vector": vector},
                    payload=payload,
                ),
            ],
        )
        lg.debug(f"Upserted image vector for thing {point_id}")

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
        conditions: list[models.Condition] = []

        if location_filter:
            conditions.append(
                models.FieldCondition(
                    key="location_path",
                    match=models.MatchText(text=location_filter),
                ),
            )

        if category_filter:
            conditions.append(
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category_filter),
                ),
            )

        if material_filter:
            conditions.append(
                models.FieldCondition(
                    key="description",
                    match=models.MatchText(text=material_filter),
                ),
            )

        if tags_filter:
            conditions.extend(
                models.FieldCondition(
                    key="tags",
                    match=models.MatchValue(value=tag),
                )
                for tag in tags_filter
            )

        query_filter = models.Filter(must=conditions) if conditions else None

        results = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            using="text_vector",
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )

        return [self._to_search_result(hit) for hit in results.points]

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
        results = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            using="image_vector",
            limit=limit,
            with_payload=True,
        )

        return [self._to_search_result(hit) for hit in results.points]

    def delete_vectors(self, thing_id: uuid.UUID) -> None:
        """Delete all vectors for a Thing.

        Args:
            thing_id: UUID of the Thing.
        """
        point_id = str(thing_id)
        self._client.delete(
            collection_name=self._collection,
            points_selector=models.PointIdsList(points=[point_id]),
        )
        lg.debug(f"Deleted vectors for thing {point_id}")

    @staticmethod
    def _to_search_result(hit) -> SearchResult:  # noqa: ANN001
        """Convert a Qdrant ScoredPoint to a SearchResult.

        Args:
            hit: Qdrant ScoredPoint.

        Returns:
            SearchResult domain object.
        """
        payload = hit.payload or {}
        return SearchResult(
            thing_id=uuid.UUID(payload.get("thing_id", str(uuid.uuid4()))),
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            category=payload.get("category", ""),
            tags=payload.get("tags", []),
            location_path=payload.get("location_path"),
            score=hit.score if hit.score is not None else 0.0,
        )
