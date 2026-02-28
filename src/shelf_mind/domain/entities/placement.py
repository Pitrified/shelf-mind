"""Placement entity - links a Thing to a Location at a point in time."""

from datetime import datetime
import uuid

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class Placement(SQLModel, table=True):
    """Records where a Thing is (or was) placed.

    Only one placement per Thing should be marked as active at a time.
    Moving a Thing creates a new Placement and deactivates the old one.

    Attributes:
        id: Primary key UUID.
        thing_id: FK to the Thing.
        location_id: FK to the Location.
        placed_at: Timestamp when placed.
        active: Whether this is the current placement.
        thing: Related Thing object.
        location: Related Location object.
    """

    __tablename__ = "placement"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    thing_id: uuid.UUID = Field(foreign_key="thing.id", index=True)
    location_id: uuid.UUID = Field(foreign_key="location.id", index=True)
    placed_at: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True)

    # Relationships
    thing: "Thing" = Relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="placements",
    )
    location: "Location" = Relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="placements",
    )
