"""Abstract repository for Placement persistence."""

from abc import ABC
from abc import abstractmethod
import uuid

from shelf_mind.domain.entities.placement import Placement


class PlacementRepository(ABC):
    """Interface for Placement CRUD operations."""

    @abstractmethod
    def create(self, placement: Placement) -> Placement:
        """Persist a new Placement.

        Args:
            placement: Placement entity to create.

        Returns:
            Created Placement with generated id.
        """

    @abstractmethod
    def get_active_for_thing(self, thing_id: uuid.UUID) -> Placement | None:
        """Get the current active placement for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            Active Placement if exists, None otherwise.
        """

    @abstractmethod
    def get_history_for_thing(self, thing_id: uuid.UUID) -> list[Placement]:
        """Get all placements (including inactive) for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            All Placement records ordered by placed_at desc.
        """

    @abstractmethod
    def deactivate_for_thing(self, thing_id: uuid.UUID) -> int:
        """Deactivate all placements for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            Number of placements deactivated.
        """

    @abstractmethod
    def get_things_at_location(self, location_id: uuid.UUID) -> list[Placement]:
        """Get all active placements at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Active Placement records at this location.
        """

    @abstractmethod
    def count_at_location(self, location_id: uuid.UUID) -> int:
        """Count active placements at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Number of active placements.
        """

    @abstractmethod
    def delete(self, placement_id: uuid.UUID) -> bool:
        """Delete a Placement by id.

        Args:
            placement_id: UUID of the Placement to delete.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    def delete_by_location(self, location_id: uuid.UUID) -> int:
        """Delete all placements at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Number of placements deleted.
        """
