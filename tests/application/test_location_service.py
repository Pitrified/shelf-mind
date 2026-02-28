"""Tests for LocationService."""

from collections.abc import Generator
import uuid

import pytest
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine

from shelf_mind.application.errors import DuplicateSiblingNameError
from shelf_mind.application.errors import LocationHasChildrenError
from shelf_mind.application.errors import LocationHasThingsError
from shelf_mind.application.errors import LocationNotFoundError
from shelf_mind.application.services.location_service import LocationService
from shelf_mind.domain.entities.placement import Placement
from shelf_mind.domain.entities.thing import Thing
from shelf_mind.infrastructure.db.location_repo import SqlLocationRepository
from shelf_mind.infrastructure.db.placement_repo import SqlPlacementRepository


@pytest.fixture
def db_session() -> Generator[Session]:
    """Create an in-memory SQLite session."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def location_service(db_session: Session) -> LocationService:
    """Build a LocationService with an in-memory repo.

    Args:
        db_session: Test database session.

    Returns:
        LocationService instance.
    """
    repo = SqlLocationRepository(db_session)
    placement_repo = SqlPlacementRepository(db_session)
    return LocationService(repo, placement_repo=placement_repo)


class TestLocationService:
    """Tests for the LocationService."""

    def test_create_root_location(self, location_service: LocationService) -> None:
        """Should create a root-level location."""
        loc = location_service.create_location("Home")
        assert loc.path == "/Home"
        assert loc.parent_id is None

    def test_create_nested_location(self, location_service: LocationService) -> None:
        """Should create a nested location with correct path."""
        home = location_service.create_location("Home")
        kitchen = location_service.create_location("Kitchen", parent_id=home.id)
        assert kitchen.path == "/Home/Kitchen"
        assert kitchen.parent_id == home.id

    def test_create_deeply_nested(self, location_service: LocationService) -> None:
        """Should support deep nesting."""
        home = location_service.create_location("Home")
        kitchen = location_service.create_location("Kitchen", parent_id=home.id)
        drawer = location_service.create_location("Drawer", parent_id=kitchen.id)
        assert drawer.path == "/Home/Kitchen/Drawer"

    def test_create_duplicate_sibling_fails(
        self,
        location_service: LocationService,
    ) -> None:
        """Should reject duplicate sibling names."""
        location_service.create_location("Kitchen")
        with pytest.raises(DuplicateSiblingNameError):
            location_service.create_location("Kitchen")

    def test_create_with_missing_parent_fails(
        self,
        location_service: LocationService,
    ) -> None:
        """Should fail if parent does not exist."""
        with pytest.raises(LocationNotFoundError):
            location_service.create_location("Room", parent_id=uuid.uuid4())

    def test_get_location(self, location_service: LocationService) -> None:
        """Should retrieve a location by id."""
        loc = location_service.create_location("Office")
        fetched = location_service.get_location(loc.id)
        assert fetched.name == "Office"

    def test_get_location_not_found(self, location_service: LocationService) -> None:
        """Should raise for missing location."""
        with pytest.raises(LocationNotFoundError):
            location_service.get_location(uuid.uuid4())

    def test_get_location_by_path(self, location_service: LocationService) -> None:
        """Should retrieve by path."""
        location_service.create_location("Garage")
        fetched = location_service.get_location_by_path("/Garage")
        assert fetched.name == "Garage"

    def test_list_locations(self, location_service: LocationService) -> None:
        """Should list all locations."""
        location_service.create_location("A")
        location_service.create_location("B")
        all_locs = location_service.list_locations()
        assert len(all_locs) == 2

    def test_get_children(self, location_service: LocationService) -> None:
        """Should list children."""
        parent = location_service.create_location("Home")
        location_service.create_location("Kitchen", parent_id=parent.id)
        location_service.create_location("Bedroom", parent_id=parent.id)

        children = location_service.get_children(parent.id)
        assert len(children) == 2

    def test_rename_location(self, location_service: LocationService) -> None:
        """Should rename and update path."""
        loc = location_service.create_location("Kitchn")
        renamed = location_service.rename_location(loc.id, "Kitchen")
        assert renamed.name == "Kitchen"
        assert renamed.path == "/Kitchen"

    def test_rename_updates_children_paths(
        self,
        location_service: LocationService,
    ) -> None:
        """Renaming parent should cascade to children paths."""
        home = location_service.create_location("Home")
        kitchen = location_service.create_location("Kitchen", parent_id=home.id)
        location_service.create_location("Drawer", parent_id=kitchen.id)

        location_service.rename_location(kitchen.id, "BigKitchen")

        # Verify all descendant paths updated
        fetched = location_service.get_location_by_path("/Home/BigKitchen")
        assert fetched is not None

    def test_rename_duplicate_fails(self, location_service: LocationService) -> None:
        """Should reject rename to existing sibling name."""
        location_service.create_location("Kitchen")
        bedroom = location_service.create_location("Bedroom")

        with pytest.raises(DuplicateSiblingNameError):
            location_service.rename_location(bedroom.id, "Kitchen")

    def test_move_location(self, location_service: LocationService) -> None:
        """Should move location to new parent."""
        home = location_service.create_location("Home")
        office = location_service.create_location("Office")
        desk = location_service.create_location("Desk", parent_id=office.id)

        moved = location_service.move_location(desk.id, home.id)
        assert moved.path == "/Home/Desk"
        assert moved.parent_id == home.id

    def test_delete_location(self, location_service: LocationService) -> None:
        """Should delete a leaf location."""
        loc = location_service.create_location("Temp")
        assert location_service.delete_location(loc.id) is True

    def test_delete_with_children_fails(
        self,
        location_service: LocationService,
    ) -> None:
        """Should prevent deletion of location with children."""
        parent = location_service.create_location("Home")
        location_service.create_location("Kitchen", parent_id=parent.id)

        with pytest.raises(LocationHasChildrenError):
            location_service.delete_location(parent.id)

    def test_delete_with_placements_fails(
        self,
        location_service: LocationService,
        db_session: Session,
    ) -> None:
        """Should prevent deletion of location with active placements."""
        loc = location_service.create_location("Kitchen")

        thing = Thing(name="Spoon")
        db_session.add(thing)
        db_session.commit()
        placement = Placement(thing_id=thing.id, location_id=loc.id, active=True)
        db_session.add(placement)
        db_session.commit()

        with pytest.raises(LocationHasThingsError):
            location_service.delete_location(loc.id)

    def test_delete_with_placements_force(
        self,
        location_service: LocationService,
        db_session: Session,
    ) -> None:
        """Should allow forced deletion with placements."""
        loc = location_service.create_location("Kitchen")

        thing = Thing(name="Spoon")
        db_session.add(thing)
        db_session.commit()
        placement = Placement(thing_id=thing.id, location_id=loc.id, active=True)
        db_session.add(placement)
        db_session.commit()

        assert location_service.delete_location(loc.id, force=True) is True
