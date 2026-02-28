"""Tests for MetadataSchema."""

import pytest

from shelf_mind.domain.schemas.metadata_schema import MetadataSchema


class TestMetadataSchema:
    """Tests for MetadataSchema validation."""

    def test_basic_creation(self) -> None:
        """Schema should accept valid minimal input."""
        schema = MetadataSchema(category="electronics")
        assert schema.category == "electronics"
        assert schema.tags == []
        assert schema.subtype is None

    def test_tags_lowercased(self) -> None:
        """Tags should be lowercased."""
        schema = MetadataSchema(category="tools", tags=["Hammer", "WRENCH", "drill"])
        assert schema.tags == ["hammer", "wrench", "drill"]

    def test_tags_deduplicated(self) -> None:
        """Duplicate tags should be removed."""
        schema = MetadataSchema(category="tools", tags=["hammer", "Hammer", "HAMMER"])
        assert schema.tags == ["hammer"]

    def test_tags_max_30(self) -> None:
        """More than 30 tags should raise ValidationError."""
        tags = [f"tag{i}" for i in range(31)]
        with pytest.raises(ValueError, match="Maximum 30 tags"):
            MetadataSchema(category="general", tags=tags)

    def test_tags_exactly_30(self) -> None:
        """Exactly 30 tags should be accepted."""
        tags = [f"tag{i}" for i in range(30)]
        schema = MetadataSchema(category="general", tags=tags)
        assert len(schema.tags) == 30

    def test_full_schema(self) -> None:
        """Schema should accept all fields."""
        schema = MetadataSchema(
            category="electronics",
            subtype="charger",
            tags=["usb", "type-c"],
            material="plastic",
            room_hint="office",
            usage_context=["work", "charging"],
            custom={"brand": "anker"},
        )
        assert schema.subtype == "charger"
        assert schema.material == "plastic"
        assert schema.room_hint == "office"
        assert "work" in schema.usage_context
        assert schema.custom["brand"] == "anker"

    def test_tags_whitespace_stripped(self) -> None:
        """Tags should have whitespace stripped."""
        schema = MetadataSchema(category="general", tags=["  hello  ", " world "])
        assert schema.tags == ["hello", "world"]

    def test_empty_tags_filtered(self) -> None:
        """Empty string tags should be filtered out."""
        schema = MetadataSchema(category="general", tags=["valid", "", "  "])
        assert schema.tags == ["valid"]
