"""Placement management service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

from shelf_mind.application.errors import LocationNotFoundError
from shelf_mind.application.errors import ThingNotFoundError
from shelf_mind.domain.entities.placement import Placement

if TYPE_CHECKING:
    import uuid

    from shelf_mind.domain.repositories.location_repository import LocationRepository
    from shelf_mind.domain.repositories.placement_repository import PlacementRepository
    from shelf_mind.domain.repositories.thing_repository import ThingRepository


class PlacementService:
    """Application service for managing Thing-Location placements.

    Only one placement per Thing is active at a time.
    Moving a Thing creates a new Placement and deactivates the old one.

    Args:
        placement_repo: PlacementRepository implementation.
        thing_repo: ThingRepository for validation.
        location_repo: LocationRepository for validation.
    """

    def __init__(
        self,
        placement_repo: PlacementRepository,
        thing_repo: ThingRepository,
        location_repo: LocationRepository,
    ) -> None:
        """Initialize with repository dependencies.

        Args:
            placement_repo: PlacementRepository implementation.
            thing_repo: ThingRepository for validation.
            location_repo: LocationRepository for validation.
        """
        self._placement_repo = placement_repo
        self._thing_repo = thing_repo
        self._location_repo = location_repo

    def place_thing(
        self,
        thing_id: uuid.UUID,
        location_id: uuid.UUID,
    ) -> Placement:
        """Place a Thing at a Location (or move it).

        Deactivates any prior active placement, then creates a new one.

        Args:
            thing_id: UUID of the Thing.
            location_id: UUID of the Location.

        Returns:
            New active Placement.

        Raises:
            ThingNotFoundError: If Thing not found.
            LocationNotFoundError: If Location not found.
        """
        thing = self._thing_repo.get_by_id(thing_id)
        if thing is None:
            msg = f"Thing {thing_id} not found"
            raise ThingNotFoundError(msg)

        location = self._location_repo.get_by_id(location_id)
        if location is None:
            msg = f"Location {location_id} not found"
            raise LocationNotFoundError(msg)

        # Deactivate current placement
        self._placement_repo.deactivate_for_thing(thing_id)

        # Create new active placement
        placement = Placement(
            thing_id=thing_id,
            location_id=location_id,
            active=True,
        )
        created = self._placement_repo.create(placement)
        lg.info(
            f"Placed thing '{thing.name}' at '{location.path}' "
            f"(placement {created.id})",
        )
        return created

    def get_current_placement(self, thing_id: uuid.UUID) -> Placement | None:
        """Get the current active placement for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            Active Placement or None.
        """
        return self._placement_repo.get_active_for_thing(thing_id)

    def get_placement_history(self, thing_id: uuid.UUID) -> list[Placement]:
        """Get all placements for a Thing (historical).

        Args:
            thing_id: UUID of the Thing.

        Returns:
            All Placements ordered by placed_at desc.
        """
        return self._placement_repo.get_history_for_thing(thing_id)

    def get_things_at_location(self, location_id: uuid.UUID) -> list[Placement]:
        """List all things currently placed at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Active Placements at this location.
        """
        return self._placement_repo.get_things_at_location(location_id)

    def remove_placement(self, thing_id: uuid.UUID) -> int:
        """Remove (deactivate) the current placement.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            Number of placements deactivated.
        """
        count = self._placement_repo.deactivate_for_thing(thing_id)
        lg.info(f"Removed placement for thing {thing_id} ({count} deactivated)")
        return count
