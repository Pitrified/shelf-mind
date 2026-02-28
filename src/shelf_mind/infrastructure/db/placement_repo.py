"""SQL implementation of PlacementRepository."""

import uuid

from sqlmodel import Session
from sqlmodel import func
from sqlmodel import select

from shelf_mind.domain.entities.placement import Placement
from shelf_mind.domain.repositories.placement_repository import PlacementRepository


class SqlPlacementRepository(PlacementRepository):
    """SQLModel-backed Placement repository.

    Args:
        session: Active SQLModel session.
    """

    def __init__(self, session: Session) -> None:
        """Initialize with the given session.

        Args:
            session: Active SQLModel session.
        """
        self._session = session

    def create(self, placement: Placement) -> Placement:
        """Persist a new Placement.

        Args:
            placement: Placement entity to create.

        Returns:
            Created Placement with generated id.
        """
        self._session.add(placement)
        self._session.commit()
        self._session.refresh(placement)
        return placement

    def get_active_for_thing(self, thing_id: uuid.UUID) -> Placement | None:
        """Get the current active placement for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            Active Placement if exists, None otherwise.
        """
        stmt = select(Placement).where(
            Placement.thing_id == thing_id,
            Placement.active.is_(True),  # type: ignore[union-attr]
        )
        return self._session.exec(stmt).first()

    def get_history_for_thing(self, thing_id: uuid.UUID) -> list[Placement]:
        """Get all placements (including inactive) for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            All Placement records ordered by placed_at desc.
        """
        stmt = (
            select(Placement)
            .where(Placement.thing_id == thing_id)
            .order_by(Placement.placed_at.desc())  # type: ignore[union-attr]
        )
        return list(self._session.exec(stmt).all())

    def deactivate_for_thing(self, thing_id: uuid.UUID) -> int:
        """Deactivate all placements for a Thing.

        Args:
            thing_id: UUID of the Thing.

        Returns:
            Number of placements deactivated.
        """
        stmt = select(Placement).where(
            Placement.thing_id == thing_id,
            Placement.active.is_(True),  # type: ignore[union-attr]
        )
        results = list(self._session.exec(stmt).all())
        for p in results:
            p.active = False
            self._session.add(p)
        self._session.commit()
        return len(results)

    def get_things_at_location(self, location_id: uuid.UUID) -> list[Placement]:
        """Get all active placements at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Active Placement records at this location.
        """
        stmt = select(Placement).where(
            Placement.location_id == location_id,
            Placement.active.is_(True),  # type: ignore[union-attr]
        )
        return list(self._session.exec(stmt).all())

    def count_at_location(self, location_id: uuid.UUID) -> int:
        """Count active placements at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Number of active placements.
        """
        stmt = (
            select(func.count())
            .select_from(Placement)
            .where(
                Placement.location_id == location_id,
                Placement.active.is_(True),  # type: ignore[union-attr]
            )
        )
        result = self._session.exec(stmt).one()
        return int(result)

    def delete(self, placement_id: uuid.UUID) -> bool:
        """Delete a Placement by id.

        Args:
            placement_id: UUID of the Placement to delete.

        Returns:
            True if deleted, False if not found.
        """
        placement = self._session.get(Placement, placement_id)
        if placement is None:
            return False
        self._session.delete(placement)
        self._session.commit()
        return True

    def delete_by_location(self, location_id: uuid.UUID) -> int:
        """Delete all placements at a location.

        Args:
            location_id: UUID of the Location.

        Returns:
            Number of placements deleted.
        """
        stmt = select(Placement).where(Placement.location_id == location_id)
        placements = list(self._session.exec(stmt).all())
        for p in placements:
            self._session.delete(p)
        self._session.commit()
        return len(placements)
