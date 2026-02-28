"""Vision strategy interface and implementations for image embedding."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from loguru import logger as lg


class VisionStrategy(ABC):
    """Interface for image embedding generation."""

    @abstractmethod
    def embed(self, image_array: Any) -> list[list[float]]:  # noqa: ANN401
        """Generate embedding vectors for an image.

        Args:
            image_array: Image data (numpy array, PIL Image, etc.).

        Returns:
            List of embedding vectors (one per detected region or the whole image).
        """

    @abstractmethod
    def preprocess(self, image_bytes: bytes) -> Any:  # noqa: ANN401
        """Preprocess raw image bytes for embedding.

        Performs: convert to RGB, resize (max 512px), normalize.

        Args:
            image_bytes: Raw image data.

        Returns:
            Preprocessed image suitable for embed().
        """


class NoOpVisionStrategy(VisionStrategy):
    """Placeholder vision strategy for Phase 1 (no vision support).

    Returns zero vectors, allowing the system to operate without
    a vision model loaded.
    """

    def __init__(self, vector_dim: int = 512) -> None:
        """Initialize with the target vector dimensionality.

        Args:
            vector_dim: Size of the zero vector to return.
        """
        self._dim = vector_dim
        lg.info("Using NoOp vision strategy (Phase 1)")

    def embed(self, image_array: Any) -> list[list[float]]:  # noqa: ANN401, ARG002
        """Return a single zero vector.

        Args:
            image_array: Ignored.

        Returns:
            List with one zero vector.
        """
        return [[0.0] * self._dim]

    def preprocess(self, image_bytes: bytes) -> Any:  # noqa: ANN401
        """No-op preprocessing.

        Args:
            image_bytes: Raw image data.

        Returns:
            The bytes unchanged.
        """
        return image_bytes
