"""Repository interfaces (abstract base classes)."""

from shelf_mind.domain.repositories.location_repository import LocationRepository
from shelf_mind.domain.repositories.placement_repository import PlacementRepository
from shelf_mind.domain.repositories.thing_repository import ThingRepository
from shelf_mind.domain.repositories.vector_repository import VectorRepository

__all__ = [
    "LocationRepository",
    "PlacementRepository",
    "ThingRepository",
    "VectorRepository",
]
