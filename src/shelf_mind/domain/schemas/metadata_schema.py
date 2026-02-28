"""Metadata schema for Thing enrichment.

Defines the strict metadata structure extracted from a Thing's
name and description via the MetadataEnricher.
"""

from pydantic import BaseModel
from pydantic import field_validator


class MetadataSchema(BaseModel):
    """Strict metadata schema for a Thing.

    Attributes:
        category: Primary category (e.g. "electronics", "kitchenware").
        subtype: Optional sub-category.
        tags: Lowercase, deduplicated descriptive tags (max 30).
        material: Optional primary material.
        room_hint: Optional suggested room/area.
        usage_context: Contexts where the thing is typically used.
        custom: Arbitrary key-value metadata.
    """

    category: str
    subtype: str | None = None
    tags: list[str] = []
    material: str | None = None
    room_hint: str | None = None
    usage_context: list[str] = []
    custom: dict[str, str] = {}

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        """Lowercase and deduplicate tags, enforce max 30.

        Args:
            v: Raw tag list.

        Returns:
            Cleaned tag list.
        """
        seen: set[str] = set()
        result: list[str] = []
        for tag in v:
            lower = tag.lower().strip()
            if lower and lower not in seen:
                seen.add(lower)
                result.append(lower)
        if len(result) > 30:  # noqa: PLR2004
            msg = "Maximum 30 tags allowed"
            raise ValueError(msg)
        return result
