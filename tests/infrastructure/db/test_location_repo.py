"""Tests for SqlLocationRepository."""

import uuid

from sqlmodel import Session

from shelf_mind.domain.entities.location import Location
from shelf_mind.domain.entities.placement import Placement
from shelf_mind.domain.entities.thing import Thing
from shelf_mind.infrastructure.db.location_repo import SqlLocationRepository


class TestSqlLocationRepository:
    """Tests for the SQL LocationRepository implementation."""

    def test_create_and_get(self, db_session: Session) -> None:
        """Should create and retrieve a location."""
        repo = SqlLocationRepository(db_session)
        loc = Location(name="Kitchen", path="/Kitchen")
        created = repo.create(loc)

        assert created.id is not None
        assert created.name == "Kitchen"

        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.name == "Kitchen"

    def test_get_by_path(self, db_session: Session) -> None:
        """Should retrieve by materialized path."""
        repo = SqlLocationRepository(db_session)
        loc = Location(name="Kitchen", path="/Kitchen")
        repo.create(loc)

        fetched = repo.get_by_path("/Kitchen")
        assert fetched is not None
        assert fetched.name == "Kitchen"

    def test_get_by_path_not_found(self, db_session: Session) -> None:
        """Should return None for missing path."""
        repo = SqlLocationRepository(db_session)
        assert repo.get_by_path("/nonexistent") is None

    def test_get_children(self, db_session: Session) -> None:
        """Should list direct children."""
        repo = SqlLocationRepository(db_session)
        parent = Location(name="Home", path="/Home")
        repo.create(parent)

        child1 = Location(name="Kitchen", parent_id=parent.id, path="/Home/Kitchen")
        child2 = Location(name="Bedroom", parent_id=parent.id, path="/Home/Bedroom")
        repo.create(child1)
        repo.create(child2)

        children = repo.get_children(parent.id)
        assert len(children) == 2
        names = {c.name for c in children}
        assert names == {"Kitchen", "Bedroom"}

    def test_get_children_root_level(self, db_session: Session) -> None:
        """Should list root-level locations."""
        repo = SqlLocationRepository(db_session)
        repo.create(Location(name="Home", path="/Home"))
        repo.create(Location(name="Office", path="/Office"))

        roots = repo.get_children(None)
        assert len(roots) == 2

    def test_get_descendants(self, db_session: Session) -> None:
        """Should list all descendants by path prefix."""
        repo = SqlLocationRepository(db_session)
        repo.create(Location(name="Home", path="/Home"))
        repo.create(Location(name="Kitchen", path="/Home/Kitchen"))
        repo.create(Location(name="Drawer", path="/Home/Kitchen/Drawer"))
        repo.create(Location(name="Office", path="/Office"))

        descendants = repo.get_descendants("/Home")
        assert len(descendants) == 3
        paths = {d.path for d in descendants}
        assert "/Home" in paths
        assert "/Home/Kitchen" in paths
        assert "/Home/Kitchen/Drawer" in paths
        assert "/Office" not in paths

    def test_list_all(self, db_session: Session) -> None:
        """Should list all locations ordered by path."""
        repo = SqlLocationRepository(db_session)
        repo.create(Location(name="Zebra", path="/Zebra"))
        repo.create(Location(name="Alpha", path="/Alpha"))

        all_locs = repo.list_all()
        assert len(all_locs) == 2
        assert all_locs[0].name == "Alpha"

    def test_update(self, db_session: Session) -> None:
        """Should update a location."""
        repo = SqlLocationRepository(db_session)
        loc = Location(name="Kitchen", path="/Kitchen")
        repo.create(loc)

        loc.name = "Big Kitchen"
        updated = repo.update(loc)
        assert updated.name == "Big Kitchen"

    def test_update_paths(self, db_session: Session) -> None:
        """Should bulk-update paths."""
        repo = SqlLocationRepository(db_session)
        repo.create(Location(name="Kitchen", path="/Kitchen"))
        repo.create(Location(name="Drawer", path="/Kitchen/Drawer"))

        count = repo.update_paths("/Kitchen", "/Home/Kitchen")
        assert count == 2

        fetched = repo.get_by_path("/Home/Kitchen")
        assert fetched is not None
        fetched2 = repo.get_by_path("/Home/Kitchen/Drawer")
        assert fetched2 is not None

    def test_delete(self, db_session: Session) -> None:
        """Should delete a location."""
        repo = SqlLocationRepository(db_session)
        loc = Location(name="Temp", path="/Temp")
        repo.create(loc)

        assert repo.delete(loc.id) is True
        assert repo.get_by_id(loc.id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False for missing location."""
        repo = SqlLocationRepository(db_session)
        assert repo.delete(uuid.uuid4()) is False

    def test_has_children(self, db_session: Session) -> None:
        """Should detect if location has children."""
        repo = SqlLocationRepository(db_session)
        parent = Location(name="Home", path="/Home")
        repo.create(parent)

        assert repo.has_children(parent.id) is False

        child = Location(name="Room", parent_id=parent.id, path="/Home/Room")
        repo.create(child)

        assert repo.has_children(parent.id) is True

    def test_has_placements(self, db_session: Session) -> None:
        """Should detect if location has active placements."""
        repo = SqlLocationRepository(db_session)
        loc = Location(name="Kitchen", path="/Kitchen")
        repo.create(loc)

        assert repo.has_placements(loc.id) is False

        thing = Thing(name="Spoon")
        db_session.add(thing)
        db_session.commit()

        placement = Placement(thing_id=thing.id, location_id=loc.id, active=True)
        db_session.add(placement)
        db_session.commit()

        assert repo.has_placements(loc.id) is True

    def test_sibling_name_exists(self, db_session: Session) -> None:
        """Should detect duplicate sibling names."""
        repo = SqlLocationRepository(db_session)
        parent = Location(name="Home", path="/Home")
        repo.create(parent)

        child = Location(name="Kitchen", parent_id=parent.id, path="/Home/Kitchen")
        repo.create(child)

        assert repo.sibling_name_exists("Kitchen", parent.id) is True
        assert repo.sibling_name_exists("Bedroom", parent.id) is False

    def test_sibling_name_exists_with_exclude(self, db_session: Session) -> None:
        """Should exclude specified id from sibling check."""
        repo = SqlLocationRepository(db_session)
        parent = Location(name="Home", path="/Home")
        repo.create(parent)

        child = Location(name="Kitchen", parent_id=parent.id, path="/Home/Kitchen")
        repo.create(child)

        # Excluding the child itself should return False
        assert repo.sibling_name_exists("Kitchen", parent.id, child.id) is False
