"""Tests for SqlThingRepository."""

import uuid

from sqlmodel import Session

from shelf_mind.domain.entities.thing import Thing
from shelf_mind.infrastructure.db.thing_repo import SqlThingRepository


class TestSqlThingRepository:
    """Tests for the SQL ThingRepository implementation."""

    def test_create_and_get(self, db_session: Session) -> None:
        """Should create and retrieve a thing."""
        repo = SqlThingRepository(db_session)
        thing = Thing(name="Phone Charger", description="USB-C charger")
        created = repo.create(thing)

        assert created.id is not None
        assert created.name == "Phone Charger"

        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.description == "USB-C charger"

    def test_get_by_name(self, db_session: Session) -> None:
        """Should find thing by exact name."""
        repo = SqlThingRepository(db_session)
        repo.create(Thing(name="Laptop"))

        fetched = repo.get_by_name("Laptop")
        assert fetched is not None
        assert fetched.name == "Laptop"

    def test_get_by_name_not_found(self, db_session: Session) -> None:
        """Should return None for missing name."""
        repo = SqlThingRepository(db_session)
        assert repo.get_by_name("Nonexistent") is None

    def test_list_all_paginated(self, db_session: Session) -> None:
        """Should paginate results."""
        repo = SqlThingRepository(db_session)
        for i in range(5):
            repo.create(Thing(name=f"Item {i:02d}"))

        page1 = repo.list_all(offset=0, limit=2)
        assert len(page1) == 2

        page2 = repo.list_all(offset=2, limit=2)
        assert len(page2) == 2

        page3 = repo.list_all(offset=4, limit=2)
        assert len(page3) == 1

    def test_count(self, db_session: Session) -> None:
        """Should count all things."""
        repo = SqlThingRepository(db_session)
        assert repo.count() == 0

        repo.create(Thing(name="A"))
        repo.create(Thing(name="B"))
        assert repo.count() == 2

    def test_update(self, db_session: Session) -> None:
        """Should update a thing."""
        repo = SqlThingRepository(db_session)
        thing = Thing(name="Old Name")
        repo.create(thing)

        thing.name = "New Name"
        updated = repo.update(thing)
        assert updated.name == "New Name"

    def test_delete(self, db_session: Session) -> None:
        """Should delete a thing."""
        repo = SqlThingRepository(db_session)
        thing = Thing(name="Temp")
        repo.create(thing)

        assert repo.delete(thing.id) is True
        assert repo.get_by_id(thing.id) is None

    def test_delete_not_found(self, db_session: Session) -> None:
        """Should return False for missing thing."""
        repo = SqlThingRepository(db_session)
        assert repo.delete(uuid.uuid4()) is False

    def test_search_by_name(self, db_session: Session) -> None:
        """Should search by name substring."""
        repo = SqlThingRepository(db_session)
        repo.create(Thing(name="Phone Charger"))
        repo.create(Thing(name="Phone Case"))
        repo.create(Thing(name="Laptop"))

        results = repo.search_by_name("Phone")
        assert len(results) == 2

    def test_search_by_name_no_match(self, db_session: Session) -> None:
        """Should return empty for no matches."""
        repo = SqlThingRepository(db_session)
        repo.create(Thing(name="Laptop"))

        results = repo.search_by_name("Phone")
        assert len(results) == 0
