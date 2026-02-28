"""Tests for Thing entity."""

import uuid

from shelf_mind.domain.entities.thing import Thing


class TestThing:
    """Tests for the Thing entity."""

    def test_create_thing_defaults(self) -> None:
        """Thing should have sensible defaults."""
        thing = Thing(name="Phone Charger")
        assert thing.name == "Phone Charger"
        assert thing.description == ""
        assert thing.metadata_json == "{}"

    def test_thing_has_uuid(self) -> None:
        """Thing id should be a valid UUID."""
        thing = Thing(name="Laptop")
        assert isinstance(thing.id, uuid.UUID)

    def test_thing_timestamps(self) -> None:
        """Thing should have created_at and updated_at."""
        thing = Thing(name="Mouse")
        assert thing.created_at is not None
        assert thing.updated_at is not None

    def test_thing_with_description(self) -> None:
        """Thing should accept a description."""
        thing = Thing(name="Keyboard", description="Mechanical RGB keyboard")
        assert thing.description == "Mechanical RGB keyboard"

    def test_thing_with_metadata(self) -> None:
        """Thing should accept metadata JSON string."""
        thing = Thing(name="Pen", metadata_json='{"category": "stationery"}')
        assert "stationery" in thing.metadata_json
