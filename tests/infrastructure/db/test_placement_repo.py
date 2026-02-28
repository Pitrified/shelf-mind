"""Tests for SqlPlacementRepository."""

import uuid

from sqlmodel import Session

from shelf_mind.domain.entities.location import Location
from shelf_mind.domain.entities.placement import Placement
from shelf_mind.domain.entities.thing import Thing
from shelf_mind.infrastructure.db.placement_repo import SqlPlacementRepository


def _make_thing_and_location(session: Session) -> tuple[Thing, Location]:
    """Create a test Thing and Location.

    Args:
        session: Database session.

    Returns:
        Tuple of (Thing, Location).
    """
    thing = Thing(name="Test Thing")
    session.add(thing)
    loc = Location(name="Test Loc", path="/Test")
    session.add(loc)
    session.commit()
    session.refresh(thing)
    session.refresh(loc)
    return thing, loc


class TestSqlPlacementRepository:
    """Tests for the SQL PlacementRepository implementation."""

    def test_create_and_get_active(self, db_session: Session) -> None:
        """Should create a placement and retrieve the active one."""
        thing, loc = _make_thing_and_location(db_session)
        repo = SqlPlacementRepository(db_session)

        placement = Placement(thing_id=thing.id, location_id=loc.id, active=True)
        created = repo.create(placement)

        assert created.active is True

        active = repo.get_active_for_thing(thing.id)
        assert active is not None
        assert active.id == created.id

    def test_no_active_placement(self, db_session: Session) -> None:
        """Should return None when no active placement exists."""
        repo = SqlPlacementRepository(db_session)
        assert repo.get_active_for_thing(uuid.uuid4()) is None

    def test_deactivate_for_thing(self, db_session: Session) -> None:
        """Should deactivate all placements for a thing."""
        thing, loc = _make_thing_and_location(db_session)
        repo = SqlPlacementRepository(db_session)

        repo.create(Placement(thing_id=thing.id, location_id=loc.id, active=True))
        count = repo.deactivate_for_thing(thing.id)
        assert count == 1

        active = repo.get_active_for_thing(thing.id)
        assert active is None

    def test_get_history(self, db_session: Session) -> None:
        """Should return all placements including inactive."""
        thing, loc = _make_thing_and_location(db_session)
        repo = SqlPlacementRepository(db_session)

        repo.create(Placement(thing_id=thing.id, location_id=loc.id, active=False))
        repo.create(Placement(thing_id=thing.id, location_id=loc.id, active=True))

        history = repo.get_history_for_thing(thing.id)
        assert len(history) == 2

    def test_get_things_at_location(self, db_session: Session) -> None:
        """Should list active placements at a location."""
        thing, loc = _make_thing_and_location(db_session)
        repo = SqlPlacementRepository(db_session)

        repo.create(Placement(thing_id=thing.id, location_id=loc.id, active=True))
        placements = repo.get_things_at_location(loc.id)
        assert len(placements) == 1

    def test_count_at_location(self, db_session: Session) -> None:
        """Should count active placements at a location."""
        thing, loc = _make_thing_and_location(db_session)
        repo = SqlPlacementRepository(db_session)

        assert repo.count_at_location(loc.id) == 0

        repo.create(Placement(thing_id=thing.id, location_id=loc.id, active=True))
        assert repo.count_at_location(loc.id) == 1

    def test_delete(self, db_session: Session) -> None:
        """Should delete a placement."""
        thing, loc = _make_thing_and_location(db_session)
        repo = SqlPlacementRepository(db_session)

        p = repo.create(Placement(thing_id=thing.id, location_id=loc.id))
        assert repo.delete(p.id) is True

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False for missing placement."""
        repo = SqlPlacementRepository(db_session)
        assert repo.delete(uuid.uuid4()) is False
