"""Tests for PlacementService."""

from collections.abc import Generator
import uuid

import pytest
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine

from shelf_mind.application.errors import LocationNotFoundError
from shelf_mind.application.errors import ThingNotFoundError
from shelf_mind.application.services.placement_service import PlacementService
from shelf_mind.domain.entities.location import Location
from shelf_mind.domain.entities.thing import Thing
from shelf_mind.infrastructure.db.location_repo import SqlLocationRepository
from shelf_mind.infrastructure.db.placement_repo import SqlPlacementRepository
from shelf_mind.infrastructure.db.thing_repo import SqlThingRepository


@pytest.fixture
def db_session() -> Generator[Session]:
    """Create an in-memory SQLite session."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def placement_service(db_session: Session) -> PlacementService:
    """Build a PlacementService with in-memory repos.

    Args:
        db_session: Test database session.

    Returns:
        PlacementService instance.
    """
    return PlacementService(
        placement_repo=SqlPlacementRepository(db_session),
        thing_repo=SqlThingRepository(db_session),
        location_repo=SqlLocationRepository(db_session),
    )


def _seed_data(session: Session) -> tuple[Thing, Location, Location]:
    """Create test thing and locations.

    Args:
        session: Database session.

    Returns:
        Tuple of (thing, location1, location2).
    """
    thing = Thing(name="Test Thing")
    loc1 = Location(name="Kitchen", path="/Kitchen")
    loc2 = Location(name="Bedroom", path="/Bedroom")
    session.add(thing)
    session.add(loc1)
    session.add(loc2)
    session.commit()
    session.refresh(thing)
    session.refresh(loc1)
    session.refresh(loc2)
    return thing, loc1, loc2


class TestPlacementService:
    """Tests for the PlacementService."""

    def test_place_thing(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Should place a thing at a location."""
        thing, loc, _ = _seed_data(db_session)
        placement = placement_service.place_thing(thing.id, loc.id)
        assert placement.active is True
        assert placement.thing_id == thing.id
        assert placement.location_id == loc.id

    def test_place_thing_deactivates_old(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Moving should deactivate previous placement."""
        thing, loc1, loc2 = _seed_data(db_session)

        _p1 = placement_service.place_thing(thing.id, loc1.id)
        p2 = placement_service.place_thing(thing.id, loc2.id)

        # New placement is active
        assert p2.active is True

        # Old placement should be inactive
        current = placement_service.get_current_placement(thing.id)
        assert current is not None
        assert current.id == p2.id

    def test_place_thing_not_found(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Should raise for missing thing."""
        _, loc, _ = _seed_data(db_session)
        with pytest.raises(ThingNotFoundError):
            placement_service.place_thing(uuid.uuid4(), loc.id)

    def test_place_location_not_found(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Should raise for missing location."""
        thing, _, _ = _seed_data(db_session)
        with pytest.raises(LocationNotFoundError):
            placement_service.place_thing(thing.id, uuid.uuid4())

    def test_get_placement_history(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Should return full placement history."""
        thing, loc1, loc2 = _seed_data(db_session)
        placement_service.place_thing(thing.id, loc1.id)
        placement_service.place_thing(thing.id, loc2.id)

        history = placement_service.get_placement_history(thing.id)
        assert len(history) == 2

    def test_get_things_at_location(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Should list things at a location."""
        thing, loc, _ = _seed_data(db_session)
        placement_service.place_thing(thing.id, loc.id)

        placements = placement_service.get_things_at_location(loc.id)
        assert len(placements) == 1

    def test_remove_placement(
        self,
        placement_service: PlacementService,
        db_session: Session,
    ) -> None:
        """Should deactivate current placement."""
        thing, loc, _ = _seed_data(db_session)
        placement_service.place_thing(thing.id, loc.id)

        count = placement_service.remove_placement(thing.id)
        assert count == 1

        current = placement_service.get_current_placement(thing.id)
        assert current is None
