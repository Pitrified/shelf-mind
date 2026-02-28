"""Tests for metadata enricher."""

from shelf_mind.infrastructure.metadata.metadata_enricher import (
    RuleBasedMetadataEnricher,
)


class TestRuleBasedMetadataEnricher:
    """Tests for the rule-based metadata enricher."""

    def test_electronics_category(self) -> None:
        """Should detect electronics category."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Phone Charger", "USB cable for charging phones")
        assert result.category == "electronics"

    def test_kitchenware_category(self) -> None:
        """Should detect kitchenware category."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Wooden Spoon")
        assert result.category == "kitchenware"

    def test_tools_category(self) -> None:
        """Should detect tools category."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Hammer")
        assert result.category == "tools"

    def test_general_fallback(self) -> None:
        """Should fall back to general for unknown items."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Mystery Object")
        assert result.category == "general"

    def test_material_detection(self) -> None:
        """Should detect material from keywords."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Wooden Spoon", "Made of bamboo")
        assert result.material == "wood"

    def test_no_material(self) -> None:
        """Should return None when no material keyword found."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Mystery Box")
        assert result.material is None

    def test_room_hint(self) -> None:
        """Should detect room hint."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Dish Soap", "For kitchen use")
        assert result.room_hint == "kitchen"

    def test_tags_generated(self) -> None:
        """Should generate tags from name and description."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Phone Charger", "Quick charging USB-C cable")
        assert len(result.tags) > 0
        assert "phone" in result.tags
        assert "charger" in result.tags

    def test_usage_context(self) -> None:
        """Should infer usage context from category and room."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Kitchen Knife")
        # Should have at least kitchenware in context
        assert len(result.usage_context) > 0

    def test_schema_valid(self) -> None:
        """Enriched metadata should be a valid MetadataSchema."""
        enricher = RuleBasedMetadataEnricher()
        result = enricher.enrich("Laptop Stand", "Aluminum adjustable laptop riser")
        # Should not raise
        assert result.category is not None
        assert isinstance(result.tags, list)
