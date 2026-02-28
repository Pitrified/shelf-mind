"""Tests for Placement entity."""

import uuid

from shelf_mind.domain.entities.placement import Placement


class TestPlacement:
    """Tests for the Placement entity."""

    def test_create_placement_defaults(self) -> None:
        """Placement should default to active."""
        tid = uuid.uuid4()
        lid = uuid.uuid4()
        p = Placement(thing_id=tid, location_id=lid)
        assert p.active is True
        assert p.thing_id == tid
        assert p.location_id == lid

    def test_placement_has_uuid(self) -> None:
        """Placement id should be a valid UUID."""
        p = Placement(thing_id=uuid.uuid4(), location_id=uuid.uuid4())
        assert isinstance(p.id, uuid.UUID)

    def test_placement_timestamp(self) -> None:
        """Placement should have placed_at."""
        p = Placement(thing_id=uuid.uuid4(), location_id=uuid.uuid4())
        assert p.placed_at is not None

    def test_placement_inactive(self) -> None:
        """Placement can be created as inactive."""
        p = Placement(thing_id=uuid.uuid4(), location_id=uuid.uuid4(), active=False)
        assert p.active is False
