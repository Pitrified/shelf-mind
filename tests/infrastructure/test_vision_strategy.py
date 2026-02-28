"""Tests for VisionStrategy implementations."""

from shelf_mind.infrastructure.vision.vision_strategy import NoOpVisionStrategy


class TestNoOpVisionStrategy:
    """Tests for the NoOp vision strategy."""

    def test_embed_returns_zero_vector(self) -> None:
        """Should return a single zero vector."""
        strategy = NoOpVisionStrategy(vector_dim=512)
        result = strategy.embed(b"image_data")
        assert len(result) == 1
        assert len(result[0]) == 512
        assert all(v == 0.0 for v in result[0])

    def test_preprocess_passthrough(self) -> None:
        """Should return input unchanged."""
        strategy = NoOpVisionStrategy()
        data = b"raw_image_bytes"
        assert strategy.preprocess(data) == data

    def test_custom_dimension(self) -> None:
        """Should respect custom vector dimension."""
        strategy = NoOpVisionStrategy(vector_dim=256)
        result = strategy.embed(None)
        assert len(result[0]) == 256
