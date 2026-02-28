"""Tests for ShelfMindConfig."""

import pytest

from shelf_mind.config.shelf_mind_config import ShelfMindConfig


class TestShelfMindConfig:
    """Tests for the domain configuration."""

    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = ShelfMindConfig()
        assert config.database_url == "sqlite:///data/shelf_mind.db"
        assert config.qdrant_url == "http://localhost:6333"
        assert config.qdrant_collection == "things"
        assert config.text_model_name == "all-MiniLM-L6-v2"
        assert config.text_vector_dim == 384
        assert config.image_vector_dim == 512

    def test_custom_values(self) -> None:
        """Config should accept custom values."""
        config = ShelfMindConfig(
            database_url="sqlite:///custom.db",
            rank_alpha=0.5,
            rank_beta=0.3,
            rank_gamma=0.2,
        )
        assert config.database_url == "sqlite:///custom.db"
        assert config.rank_alpha == 0.5
        assert config.rank_beta == 0.3
        assert config.rank_gamma == 0.2

    def test_scoring_weights(self) -> None:
        """Default scoring weights should sum to 1.0."""
        config = ShelfMindConfig()
        total = config.rank_alpha + config.rank_beta + config.rank_gamma
        assert total == pytest.approx(1.0)
