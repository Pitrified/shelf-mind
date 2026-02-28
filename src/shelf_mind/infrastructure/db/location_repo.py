"""SQL implementation of LocationRepository."""

import uuid

from sqlmodel import Session
from sqlmodel import select

from shelf_mind.domain.entities.location import Location
from shelf_mind.domain.entities.placement import Placement
from shelf_mind.domain.repositories.location_repository import LocationRepository


class SqlLocationRepository(LocationRepository):
    """SQLModel-backed Location repository.

    Args:
        session: Active SQLModel session.
    """

    def __init__(self, session: Session) -> None:
        """Initialize with the given session.

        Args:
            session: Active SQLModel session.
        """
        self._session = session

    def create(self, location: Location) -> Location:
        """Persist a new Location.

        Args:
            location: Location entity to create.

        Returns:
            Created Location with generated id and path.
        """
        self._session.add(location)
        self._session.commit()
        self._session.refresh(location)
        return location

    def get_by_id(self, location_id: uuid.UUID) -> Location | None:
        """Retrieve a Location by its id.

        Args:
            location_id: UUID of the location.

        Returns:
            Location if found, None otherwise.
        """
        return self._session.get(Location, location_id)

    def get_by_path(self, path: str) -> Location | None:
        """Retrieve a Location by its materialized path.

        Args:
            path: Materialized path string.

        Returns:
            Location if found, None otherwise.
        """
        stmt = select(Location).where(Location.path == path)
        return self._session.exec(stmt).first()

    def get_children(self, parent_id: uuid.UUID | None) -> list[Location]:
        """List direct children of a parent location.

        Args:
            parent_id: UUID of the parent, or None for root-level.

        Returns:
            List of child Locations.
        """
        stmt = select(Location).where(Location.parent_id == parent_id)
        return list(self._session.exec(stmt).all())

    def get_descendants(self, path_prefix: str) -> list[Location]:
        """List all descendants under a path prefix.

        Args:
            path_prefix: Materialized path prefix to match.

        Returns:
            All locations whose path starts with prefix.
        """
        stmt = select(Location).where(Location.path.startswith(path_prefix))  # type: ignore[union-attr]
        return list(self._session.exec(stmt).all())

    def list_all(self) -> list[Location]:
        """List all locations.

        Returns:
            All Location records.
        """
        stmt = select(Location).order_by(Location.path)  # type: ignore[arg-type]
        return list(self._session.exec(stmt).all())

    def update(self, location: Location) -> Location:
        """Update an existing Location.

        Args:
            location: Location with updated fields.

        Returns:
            Updated Location.
        """
        self._session.add(location)
        self._session.commit()
        self._session.refresh(location)
        return location

    def update_paths(self, old_prefix: str, new_prefix: str) -> int:
        """Bulk-update materialized paths when a location is renamed or moved.

        Args:
            old_prefix: Previous path prefix.
            new_prefix: New path prefix.

        Returns:
            Number of rows affected.
        """
        descendants = self.get_descendants(old_prefix)
        count = 0
        for loc in descendants:
            loc.path = new_prefix + loc.path[len(old_prefix) :]
            self._session.add(loc)
            count += 1
        self._session.commit()
        return count

    def delete(self, location_id: uuid.UUID) -> bool:
        """Delete a Location by id.

        Args:
            location_id: UUID of the location to delete.

        Returns:
            True if deleted, False if not found.
        """
        location = self.get_by_id(location_id)
        if location is None:
            return False
        self._session.delete(location)
        self._session.commit()
        return True

    def has_children(self, location_id: uuid.UUID) -> bool:
        """Check whether a location has child locations.

        Args:
            location_id: UUID to check.

        Returns:
            True if children exist.
        """
        stmt = select(Location.id).where(Location.parent_id == location_id).limit(1)
        return self._session.exec(stmt).first() is not None

    def has_placements(self, location_id: uuid.UUID) -> bool:
        """Check whether any Things are placed at this location.

        Args:
            location_id: UUID to check.

        Returns:
            True if placements exist.
        """
        stmt = (
            select(Placement.id)
            .where(Placement.location_id == location_id, Placement.active.is_(True))  # type: ignore[union-attr]
            .limit(1)
        )
        return self._session.exec(stmt).first() is not None

    def sibling_name_exists(
        self,
        name: str,
        parent_id: uuid.UUID | None,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check for duplicate sibling names under the same parent.

        Args:
            name: Name to check.
            parent_id: Parent location id.
            exclude_id: Location id to exclude (for rename checks).

        Returns:
            True if a sibling with that name already exists.
        """
        stmt = select(Location.id).where(
            Location.name == name,
            Location.parent_id == parent_id,
        )
        if exclude_id is not None:
            stmt = stmt.where(Location.id != exclude_id)
        return self._session.exec(stmt).first() is not None
