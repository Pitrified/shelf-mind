"""Location entity - hierarchical spatial model with materialized path."""

from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class Location(SQLModel, table=True):
    """A hierarchical location for organizing Things.

    Supports unlimited nesting via parent_id. The ``path`` field is a
    materialized path (e.g. ``/home/kitchen/drawer``) that is
    auto-maintained on create, rename, and move operations.

    Attributes:
        id: Primary key UUID.
        name: Human-readable name (unique among siblings).
        parent_id: FK to parent Location (None for root).
        path: Materialized path string, auto-generated.
        created_at: Timestamp of creation.
        children: Child Location objects.
        parent: Parent Location object.
        placements: Placements assigned to this location.
    """

    __tablename__ = "location"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, max_length=120)
    parent_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="location.id",
        index=True,
    )
    path: str = Field(default="/", index=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    children: list["Location"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all"},
    )
    parent: Optional["Location"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Location.id"},
    )
    placements: list["Placement"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="location",
    )

    def build_path(self, parent_path: str = "") -> str:
        """Build the materialized path from a parent path.

        Args:
            parent_path: The parent's materialized path.

        Returns:
            Computed path string.
        """
        if not parent_path or parent_path == "/":
            return f"/{self.name}"
        return f"{parent_path}/{self.name}"
