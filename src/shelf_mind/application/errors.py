"""Domain-specific error types for the application layer."""


class DomainError(Exception):
    """Base class for domain errors."""


class LocationNotFoundError(DomainError):
    """Raised when a Location cannot be found."""


class LocationHasChildrenError(DomainError):
    """Raised when attempting to delete a Location that has children."""


class LocationHasThingsError(DomainError):
    """Raised when attempting to delete a Location that has placed Things."""


class DuplicateSiblingNameError(DomainError):
    """Raised when a sibling Location with the same name already exists."""


class ThingNotFoundError(DomainError):
    """Raised when a Thing cannot be found."""


class PlacementNotFoundError(DomainError):
    """Raised when a Placement cannot be found."""


class VectorStoreUnavailableError(DomainError):
    """Raised when the vector store is not reachable."""


class EmbeddingModelUnavailableError(DomainError):
    """Raised when the embedding model fails to load or run."""
