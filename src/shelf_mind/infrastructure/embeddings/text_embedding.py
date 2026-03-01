"""Text embedding provider using sentence-transformers."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
import asyncio
from typing import TYPE_CHECKING

from loguru import logger as lg

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class TextEmbeddingProvider(ABC):
    """Interface for text embedding generation."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            Float vector of model-specific dimensionality.
        """

    async def embed_async(self, text: str) -> list[float]:
        """Generate an embedding vector asynchronously.

        Wraps the synchronous embed() call in asyncio.to_thread()
        to avoid blocking the event loop.

        Args:
            text: Input text to embed.

        Returns:
            Float vector of model-specific dimensionality.
        """
        return await asyncio.to_thread(self.embed, text)


class SentenceTransformerEmbedder(TextEmbeddingProvider):
    """Text embedder backed by sentence-transformers.

    Lazy-loads the model on first call to avoid startup overhead.

    Args:
        model_name: HuggingFace model identifier.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize with the model name.

        Args:
            model_name: HuggingFace model identifier.
        """
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> SentenceTransformer:
        """Load the sentence-transformer model.

        Returns:
            Loaded SentenceTransformer model.
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            lg.info(f"Loading text embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            lg.info("Text embedding model loaded")
        return self._model

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            Float vector (384-dim for all-MiniLM-L6-v2).
        """
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
