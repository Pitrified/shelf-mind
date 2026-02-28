"""Webapp routers module."""

from shelf_mind.webapp.routers.auth_router import router as auth_router
from shelf_mind.webapp.routers.health_router import router as health_router
from shelf_mind.webapp.routers.pages_router import router as pages_router

__all__ = [
    "auth_router",
    "health_router",
    "pages_router",
]
