"""Tests for Location entity."""

import uuid

from shelf_mind.domain.entities.location import Location


class TestLocation:
    """Tests for the Location entity."""

    def test_create_location_defaults(self) -> None:
        """Location should have sensible defaults."""
        loc = Location(name="Kitchen")
        assert loc.name == "Kitchen"
        assert loc.parent_id is None
        assert loc.path == "/"
        assert loc.id is not None

    def test_build_path_root_level(self) -> None:
        """Root-level path should be /name."""
        loc = Location(name="Kitchen")
        assert loc.build_path("") == "/Kitchen"
        assert loc.build_path("/") == "/Kitchen"

    def test_build_path_nested(self) -> None:
        """Nested path should be parent_path/name."""
        loc = Location(name="Drawer")
        assert loc.build_path("/Kitchen") == "/Kitchen/Drawer"

    def test_build_path_deep_nesting(self) -> None:
        """Deeply nested path should chain correctly."""
        loc = Location(name="Utensils")
        result = loc.build_path("/Home/Kitchen/Drawer")
        assert result == "/Home/Kitchen/Drawer/Utensils"

    def test_location_has_uuid(self) -> None:
        """Location id should be a valid UUID."""
        loc = Location(name="Living Room")
        assert isinstance(loc.id, uuid.UUID)

    def test_location_created_at(self) -> None:
        """Location should have a created_at timestamp."""
        loc = Location(name="Office")
        assert loc.created_at is not None
