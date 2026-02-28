"""Abstract repository for Thing persistence."""

from abc import ABC
from abc import abstractmethod
import uuid

from shelf_mind.domain.entities.thing import Thing


class ThingRepository(ABC):
    """Interface for Thing CRUD operations."""

    @abstractmethod
    def create(self, thing: Thing) -> Thing:
        """Persist a new Thing.

        Args:
            thing: Thing entity to create.

        Returns:
            Created Thing with generated id.
        """

    @abstractmethod
    def get_by_id(self, thing_id: uuid.UUID) -> Thing | None:
        """Retrieve a Thing by its id.

        Args:
            thing_id: UUID of the thing.

        Returns:
            Thing if found, None otherwise.
        """

    @abstractmethod
    def get_by_name(self, name: str) -> Thing | None:
        """Retrieve a Thing by exact name match.

        Args:
            name: Thing name.

        Returns:
            Thing if found, None otherwise.
        """

    @abstractmethod
    def list_all(self, offset: int = 0, limit: int = 50) -> list[Thing]:
        """List things with pagination.

        Args:
            offset: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            List of Thing records.
        """

    @abstractmethod
    def count(self) -> int:
        """Count total Things.

        Returns:
            Total number of Thing records.
        """

    @abstractmethod
    def update(self, thing: Thing) -> Thing:
        """Update an existing Thing.

        Args:
            thing: Thing with updated fields.

        Returns:
            Updated Thing.
        """

    @abstractmethod
    def delete(self, thing_id: uuid.UUID) -> bool:
        """Delete a Thing by id.

        Args:
            thing_id: UUID of the thing to delete.

        Returns:
            True if deleted, False if not found.
        """

    @abstractmethod
    def search_by_name(self, query: str, limit: int = 10) -> list[Thing]:
        """Search Things by name substring.

        Args:
            query: Search string.
            limit: Max results.

        Returns:
            Matching Thing records.
        """
