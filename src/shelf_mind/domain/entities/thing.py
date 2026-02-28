"""Thing entity - a household object registered in the system."""

from datetime import datetime
import uuid

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class Thing(SQLModel, table=True):
    """A household object tracked by ShelfMind.

    Attributes:
        id: Primary key UUID.
        name: Human-readable name (1-120 chars, required).
        description: Optional free-text description.
        metadata_json: Enriched metadata stored as JSON string.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last update.
        placements: Placement records for this thing.
    """

    __tablename__ = "thing"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, max_length=120, min_length=1)
    description: str = Field(default="")
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    placements: list["Placement"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="thing",
    )
