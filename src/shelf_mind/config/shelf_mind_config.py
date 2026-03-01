"""ShelfMind domain configuration (Pydantic BaseSettings-style)."""

from pydantic import BaseModel
from pydantic import Field


class ShelfMindConfig(BaseModel):
    """Central configuration for the ShelfMind domain layer.

    Attributes:
        database_url: SQLite connection string.
        qdrant_url: Qdrant server URL.
        qdrant_collection: Qdrant collection name.
        text_model_name: sentence-transformers model for text embeddings.
        image_model_name: Model for image embeddings.
        text_vector_dim: Dimensionality of text vectors.
        image_vector_dim: Dimensionality of image vectors.
        rank_alpha: Weight for vector similarity in scoring.
        rank_beta: Weight for metadata overlap in scoring.
        rank_gamma: Weight for location bonus in scoring.
    """

    database_url: str = Field(default="sqlite:///data/shelf_mind.db")
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_path: str | None = Field(
        default=None,
        description=(
            "Local disk path for Qdrant persistent storage. "
            "When set, Qdrant runs in embedded/local mode instead of "
            "connecting to a remote server via qdrant_url."
        ),
    )
    qdrant_collection: str = Field(default="things")
    text_model_name: str = Field(default="all-MiniLM-L6-v2")
    image_model_name: str = Field(default="clip-ViT-B-32")
    text_vector_dim: int = Field(default=384)
    image_vector_dim: int = Field(default=512)
    rank_alpha: float = Field(default=0.7)
    rank_beta: float = Field(default=0.2)
    rank_gamma: float = Field(default=0.1)
