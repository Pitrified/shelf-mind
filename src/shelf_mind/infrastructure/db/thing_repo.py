"""SQL implementation of ThingRepository."""

import uuid

from sqlmodel import Session
from sqlmodel import func
from sqlmodel import select

from shelf_mind.domain.entities.thing import Thing
from shelf_mind.domain.repositories.thing_repository import ThingRepository


class SqlThingRepository(ThingRepository):
    """SQLModel-backed Thing repository.

    Args:
        session: Active SQLModel session.
    """

    def __init__(self, session: Session) -> None:
        """Initialize with the given session.

        Args:
            session: Active SQLModel session.
        """
        self._session = session

    def create(self, thing: Thing) -> Thing:
        """Persist a new Thing.

        Args:
            thing: Thing entity to create.

        Returns:
            Created Thing with generated id.
        """
        self._session.add(thing)
        self._session.commit()
        self._session.refresh(thing)
        return thing

    def get_by_id(self, thing_id: uuid.UUID) -> Thing | None:
        """Retrieve a Thing by its id.

        Args:
            thing_id: UUID of the thing.

        Returns:
            Thing if found, None otherwise.
        """
        return self._session.get(Thing, thing_id)

    def get_by_name(self, name: str) -> Thing | None:
        """Retrieve a Thing by exact name match.

        Args:
            name: Thing name.

        Returns:
            Thing if found, None otherwise.
        """
        stmt = select(Thing).where(Thing.name == name)
        return self._session.exec(stmt).first()

    def list_all(self, offset: int = 0, limit: int = 50) -> list[Thing]:
        """List things with pagination.

        Args:
            offset: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            List of Thing records.
        """
        stmt = select(Thing).offset(offset).limit(limit).order_by(Thing.name)  # type: ignore[arg-type]
        return list(self._session.exec(stmt).all())

    def count(self) -> int:
        """Count total Things.

        Returns:
            Total number of Thing records.
        """
        stmt = select(func.count()).select_from(Thing)
        result = self._session.exec(stmt).one()
        return int(result)

    def update(self, thing: Thing) -> Thing:
        """Update an existing Thing.

        Args:
            thing: Thing with updated fields.

        Returns:
            Updated Thing.
        """
        self._session.add(thing)
        self._session.commit()
        self._session.refresh(thing)
        return thing

    def delete(self, thing_id: uuid.UUID) -> bool:
        """Delete a Thing by id.

        Args:
            thing_id: UUID of the thing to delete.

        Returns:
            True if deleted, False if not found.
        """
        thing = self.get_by_id(thing_id)
        if thing is None:
            return False
        self._session.delete(thing)
        self._session.commit()
        return True

    def search_by_name(self, query: str, limit: int = 10) -> list[Thing]:
        """Search Things by name substring.

        Args:
            query: Search string.
            limit: Max results.

        Returns:
            Matching Thing records.
        """
        stmt = (
            select(Thing)
            .where(Thing.name.contains(query))  # type: ignore[union-attr]
            .limit(limit)
            .order_by(Thing.name)  # type: ignore[arg-type]
        )
        return list(self._session.exec(stmt).all())
