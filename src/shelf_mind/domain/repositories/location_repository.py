"""Abstract repository for Location persistence."""

from abc import ABC
from abc import abstractmethod
import uuid

from shelf_mind.domain.entities.location import Location


class LocationRepository(ABC):
    """Interface for Location CRUD and hierarchy operations."""

    @abstractmethod
    def create(self, location: Location) -> Location:
        """Persist a new Location.

        Args:
            location: Location entity to create.

        Returns:
            Created Location with generated id and path.
        """

    @abstractmethod
    def get_by_id(self, location_id: uuid.UUID) -> Location | None:
        """Retrieve a Location by its id.

        Args:
            location_id: UUID of the location.

        Returns:
            Location if found, None otherwise.
        """

    @abstractmethod
    def get_by_path(self, path: str) -> Location | None:
        """Retrieve a Location by its materialized path.

        Args:
            path: Materialized path string.

        Returns:
            Location if found, None otherwise.
        """

    @abstractmethod
    def get_children(self, parent_id: uuid.UUID | None) -> list[Location]:
        """List direct children of a parent location.

        Args:
            parent_id: UUID of the parent, or None for root-level.

        Returns:
            List of child Locations.
        """

    @abstractmethod
    def get_descendants(self, path_prefix: str) -> list[Location]:
        """List all descendants under a path prefix.

        Args:
            path_prefix: Materialized path prefix to match.

        Returns:
            All locations whose path starts with prefix.
        """

    @abstractmethod
    def list_all(self) -> list[Location]:
        """List all locations.

        Returns:
            All Location records.
        """

    @abstractmethod
    def update(self, location: Location) -> Location:
        """Update an existing Location.

        Args:
            location: Location with updated fields.

        Returns:
            Updated Location.
        """

    @abstractmethod
    def update_paths(self, old_prefix: str, new_prefix: str) -> int:
        """Bulk-update materialized paths when a location is renamed or moved.

        Args:
            old_prefix: Previous path prefix.
            new_prefix: New path prefix.

        Returns:
            Number of rows affected.
        """

    @abstractmethod
    def delete(self, location_id: uuid.UUID) -> bool:
        """Delete a Location by id.

        Args:
            location_id: UUID of the location to delete.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    def has_children(self, location_id: uuid.UUID) -> bool:
        """Check whether a location has child locations.

        Args:
            location_id: UUID to check.

        Returns:
            True if children exist.
        """

    @abstractmethod
    def has_placements(self, location_id: uuid.UUID) -> bool:
        """Check whether any Things are placed at this location.

        Args:
            location_id: UUID to check.

        Returns:
            True if placements exist.
        """

    @abstractmethod
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
