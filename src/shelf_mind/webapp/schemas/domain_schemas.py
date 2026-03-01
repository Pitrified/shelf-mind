"""API schemas (DTOs) for the domain endpoints."""

from datetime import datetime
import uuid

from pydantic import BaseModel
from pydantic import Field

# -- Location schemas --


class LocationCreate(BaseModel):
    """Request DTO for creating a Location.

    Attributes:
        name: Location name.
        parent_id: Optional parent UUID.
    """

    name: str = Field(min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None


class LocationUpdate(BaseModel):
    """Request DTO for updating a Location.

    Attributes:
        name: New name (for rename).
        parent_id: New parent (for move). Use sentinel to distinguish from None.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    move: bool = Field(
        default=False,
        description="Set True to move location to new parent_id",
    )


class LocationResponse(BaseModel):
    """Response DTO for a Location.

    Attributes:
        id: UUID.
        name: Location name.
        parent_id: Parent UUID.
        path: Materialized path.
        created_at: Creation timestamp.
    """

    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    path: str
    created_at: datetime


class LocationTreeResponse(BaseModel):
    """Response DTO for a Location with children count.

    Attributes:
        id: UUID.
        name: Location name.
        path: Materialized path.
        children_count: Number of direct children.
    """

    id: uuid.UUID
    name: str
    path: str
    children_count: int = 0


# -- Thing schemas --


class ThingCreate(BaseModel):
    """Request DTO for creating a Thing.

    Attributes:
        name: Thing name (1-120 chars).
        description: Optional description.
        location_id: Optional Location to place at.
    """

    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    location_id: uuid.UUID | None = None


class ThingUpdate(BaseModel):
    """Request DTO for updating a Thing.

    Attributes:
        name: New name.
        description: New description.
        regenerate_metadata: Re-run enrichment.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    regenerate_metadata: bool = False


class ThingResponse(BaseModel):
    """Response DTO for a Thing.

    Attributes:
        id: UUID.
        name: Thing name.
        description: Description.
        metadata_json: Raw metadata JSON.
        location_path: Current location path.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id: uuid.UUID
    name: str
    description: str
    metadata_json: str
    location_path: str | None = None
    created_at: datetime
    updated_at: datetime


class ThingListResponse(BaseModel):
    """Paginated list of Things.

    Attributes:
        items: List of ThingResponse.
        total: Total count.
        offset: Current offset.
        limit: Page size.
    """

    items: list[ThingResponse]
    total: int
    offset: int
    limit: int


# -- Placement schemas --


class PlacementCreate(BaseModel):
    """Request DTO for placing a Thing.

    The thing_id comes from the URL path parameter.

    Attributes:
        location_id: UUID of the Location.
    """

    location_id: uuid.UUID


class PlacementResponse(BaseModel):
    """Response DTO for a Placement.

    Attributes:
        id: UUID.
        thing_id: UUID of the Thing.
        location_id: UUID of the Location.
        placed_at: Placement timestamp.
        active: Whether this is current.
    """

    id: uuid.UUID
    thing_id: uuid.UUID
    location_id: uuid.UUID
    placed_at: datetime
    active: bool


# -- Search schemas --


class SearchRequest(BaseModel):
    """Request DTO for text search.

    Attributes:
        q: Query string.
        location_filter: Optional path prefix filter.
        category_filter: Optional category exact match filter.
        material_filter: Optional material keyword filter.
        tags_filter: Optional tags that must all be present.
        limit: Max results.
    """

    q: str = Field(min_length=1, max_length=500)
    location_filter: str | None = None
    category_filter: str | None = None
    material_filter: str | None = None
    tags_filter: list[str] | None = None
    limit: int = Field(default=10, ge=1, le=100)


class SearchResultResponse(BaseModel):
    """Response DTO for a single search result.

    Attributes:
        thing_id: UUID.
        name: Thing name.
        description: Description.
        category: Metadata category.
        tags: Metadata tags.
        location_path: Current location path.
        score: Confidence score.
    """

    thing_id: uuid.UUID
    name: str
    description: str = ""
    category: str = ""
    tags: list[str] = []
    location_path: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    """Response DTO for search results.

    Attributes:
        results: List of search results.
        total: Number of results.
        query: Original query.
    """

    results: list[SearchResultResponse]
    total: int
    query: str


# -- Batch operation schemas --


class BatchThingCreate(BaseModel):
    """Request DTO for batch thing creation.

    Attributes:
        items: List of ThingCreate items (1-50).
    """

    items: list[ThingCreate] = Field(min_length=1, max_length=50)


class BatchLocationCreate(BaseModel):
    """Request DTO for batch location creation.

    Attributes:
        items: List of LocationCreate items (1-50).
    """

    items: list[LocationCreate] = Field(min_length=1, max_length=50)


class BatchDeleteRequest(BaseModel):
    """Request DTO for batch deletion.

    Attributes:
        ids: List of UUIDs to delete (1-50).
    """

    ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class BatchResultResponse(BaseModel):
    """Response DTO for batch operations.

    Attributes:
        succeeded: Number of items that succeeded.
        failed: Number of items that failed.
        errors: List of error messages for failed items.
    """

    succeeded: int
    failed: int
    errors: list[str] = []
