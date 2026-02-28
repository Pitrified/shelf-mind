"""Location management service with hierarchy enforcement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

from shelf_mind.application.errors import DuplicateSiblingNameError
from shelf_mind.application.errors import LocationHasChildrenError
from shelf_mind.application.errors import LocationHasThingsError
from shelf_mind.application.errors import LocationNotFoundError
from shelf_mind.domain.entities.location import Location

if TYPE_CHECKING:
    import uuid

    from shelf_mind.domain.repositories.location_repository import LocationRepository
    from shelf_mind.domain.repositories.placement_repository import PlacementRepository


class LocationService:
    """Application service for Location CRUD with hierarchy rules.

    Args:
        repo: LocationRepository implementation.
        placement_repo: PlacementRepository implementation (for force-delete).
    """

    def __init__(
        self,
        repo: LocationRepository,
        placement_repo: PlacementRepository | None = None,
    ) -> None:
        """Initialize with repository dependencies.

        Args:
            repo: LocationRepository implementation.
            placement_repo: PlacementRepository for force-delete checks.
        """
        self._repo = repo
        self._placement_repo = placement_repo

    def create_location(
        self,
        name: str,
        parent_id: uuid.UUID | None = None,
    ) -> Location:
        """Create a new Location, auto-generating its materialized path.

        Args:
            name: Human-readable name.
            parent_id: UUID of parent Location (None for root-level).

        Returns:
            Created Location.

        Raises:
            LocationNotFoundError: If parent_id is given but not found.
            DuplicateSiblingNameError: If a sibling with the same name exists.
        """
        # Validate parent exists
        parent_path = ""
        if parent_id is not None:
            parent = self._repo.get_by_id(parent_id)
            if parent is None:
                msg = f"Parent location {parent_id} not found"
                raise LocationNotFoundError(msg)
            parent_path = parent.path

        # Enforce unique sibling names
        if self._repo.sibling_name_exists(name, parent_id):
            msg = f"Location '{name}' already exists under parent {parent_id}"
            raise DuplicateSiblingNameError(msg)

        location = Location(name=name, parent_id=parent_id)
        location.path = location.build_path(parent_path)

        created = self._repo.create(location)
        lg.info(f"Created location: {created.path} ({created.id})")
        return created

    def get_location(self, location_id: uuid.UUID) -> Location:
        """Get a Location by id.

        Args:
            location_id: UUID of the Location.

        Returns:
            The Location.

        Raises:
            LocationNotFoundError: If not found.
        """
        location = self._repo.get_by_id(location_id)
        if location is None:
            msg = f"Location {location_id} not found"
            raise LocationNotFoundError(msg)
        return location

    def get_location_by_path(self, path: str) -> Location:
        """Get a Location by its materialized path.

        Args:
            path: Materialized path.

        Returns:
            The Location.

        Raises:
            LocationNotFoundError: If not found.
        """
        location = self._repo.get_by_path(path)
        if location is None:
            msg = f"Location at path '{path}' not found"
            raise LocationNotFoundError(msg)
        return location

    def list_locations(self) -> list[Location]:
        """List all locations ordered by path.

        Returns:
            All Location records.
        """
        return self._repo.list_all()

    def get_children(self, parent_id: uuid.UUID | None = None) -> list[Location]:
        """List direct children of a location.

        Args:
            parent_id: Parent UUID, or None for root-level.

        Returns:
            Child Locations.
        """
        return self._repo.get_children(parent_id)

    def get_subtree(self, location_id: uuid.UUID) -> list[Location]:
        """Get all descendants of a location.

        Args:
            location_id: Root of the subtree.

        Returns:
            All descendant Locations.

        Raises:
            LocationNotFoundError: If location not found.
        """
        location = self.get_location(location_id)
        return self._repo.get_descendants(location.path)

    def rename_location(self, location_id: uuid.UUID, new_name: str) -> Location:
        """Rename a location, updating all descendant paths.

        Args:
            location_id: UUID of the Location.
            new_name: New name.

        Returns:
            Updated Location.

        Raises:
            LocationNotFoundError: If not found.
            DuplicateSiblingNameError: If new name conflicts with a sibling.
        """
        location = self.get_location(location_id)

        if self._repo.sibling_name_exists(new_name, location.parent_id, location_id):
            msg = (
                f"Location '{new_name}' already exists "
                f"under parent {location.parent_id}"
            )
            raise DuplicateSiblingNameError(msg)

        old_path = location.path
        location.name = new_name

        # Rebuild path
        parent_path = ""
        if location.parent_id is not None:
            parent = self._repo.get_by_id(location.parent_id)
            if parent:
                parent_path = parent.path
        new_path = location.build_path(parent_path)
        location.path = new_path

        # Update all descendant paths
        self._repo.update_paths(old_path, new_path)

        updated = self._repo.update(location)
        lg.info(f"Renamed location: {old_path} -> {updated.path}")
        return updated

    def move_location(
        self,
        location_id: uuid.UUID,
        new_parent_id: uuid.UUID | None,
    ) -> Location:
        """Move a location to a new parent, updating all descendant paths.

        Args:
            location_id: UUID of the Location to move.
            new_parent_id: UUID of new parent, or None for root.

        Returns:
            Updated Location.

        Raises:
            LocationNotFoundError: If location or new parent not found.
            DuplicateSiblingNameError: If name conflicts under new parent.
        """
        location = self.get_location(location_id)

        new_parent_path = ""
        if new_parent_id is not None:
            new_parent = self._repo.get_by_id(new_parent_id)
            if new_parent is None:
                msg = f"New parent location {new_parent_id} not found"
                raise LocationNotFoundError(msg)
            new_parent_path = new_parent.path

        if self._repo.sibling_name_exists(location.name, new_parent_id, location_id):
            msg = (
                f"Location '{location.name}' already exists under "
                f"parent {new_parent_id}"
            )
            raise DuplicateSiblingNameError(msg)

        old_path = location.path
        location.parent_id = new_parent_id
        new_path = location.build_path(new_parent_path)
        location.path = new_path

        self._repo.update_paths(old_path, new_path)

        updated = self._repo.update(location)
        lg.info(f"Moved location: {old_path} -> {updated.path}")
        return updated

    def delete_location(
        self,
        location_id: uuid.UUID,
        *,
        force: bool = False,
    ) -> bool:
        """Delete a location, enforcing hierarchy constraints.

        Args:
            location_id: UUID of the Location to delete.
            force: If True, allow deletion even if Things are placed here.

        Returns:
            True if deleted.

        Raises:
            LocationNotFoundError: If not found.
            LocationHasChildrenError: If children exist.
            LocationHasThingsError: If Things are placed here and force=False.
        """
        self.get_location(location_id)  # ensure exists

        if self._repo.has_children(location_id):
            msg = f"Location {location_id} has children - cannot delete"
            raise LocationHasChildrenError(msg)

        if not force and self._repo.has_placements(location_id):
            msg = f"Location {location_id} has Things placed - use force=True"
            raise LocationHasThingsError(msg)

        if force and self._placement_repo is not None:
            self._placement_repo.delete_by_location(location_id)

        deleted = self._repo.delete(location_id)
        lg.info(f"Deleted location: {location_id}")
        return deleted
