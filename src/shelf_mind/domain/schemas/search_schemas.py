"""Search-related domain schemas."""

import uuid

from pydantic import BaseModel
from pydantic import Field


class SearchQuery(BaseModel):
    """Incoming text search request.

    Attributes:
        q: Query string.
        location_filter: Optional location path prefix filter.
        limit: Max results to return.
    """

    q: str = Field(min_length=1)
    location_filter: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    """A single search result with confidence score.

    Attributes:
        thing_id: UUID of the matched Thing.
        name: Thing name.
        description: Thing description.
        category: Metadata category.
        tags: Metadata tags.
        location_path: Current location path (if placed).
        score: Combined confidence score (0-1).
    """

    thing_id: uuid.UUID
    name: str
    description: str = ""
    category: str = ""
    tags: list[str] = []
    location_path: str | None = None
    score: float = 0.0


class VisionSearchQuery(BaseModel):
    """Incoming vision search request.

    Attributes:
        limit: Max results to return.
    """

    limit: int = Field(default=10, ge=1, le=100)
