"""API v1 main router aggregating all v1 routes."""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends

from shelf_mind.webapp.api.v1.location_router import router as location_router
from shelf_mind.webapp.api.v1.search_router import router as search_router
from shelf_mind.webapp.api.v1.thing_router import router as thing_router
from shelf_mind.webapp.core.dependencies import get_current_user
from shelf_mind.webapp.schemas.auth_schemas import SessionData
from shelf_mind.webapp.schemas.common_schemas import MessageResponse

router = APIRouter(prefix="/api/v1", tags=["api-v1"])

# Include domain routers
router.include_router(location_router)
router.include_router(thing_router)
router.include_router(search_router)


@router.get(
    "/",
    summary="API v1 root",
    description="Returns API version information.",
)
async def api_root() -> MessageResponse:
    """Return API v1 root information.

    Returns:
        MessageResponse with API info.
    """
    return MessageResponse(message="Shelf Mind API v1")


@router.get(
    "/protected",
    summary="Protected endpoint example",
    description="Example of an endpoint that requires authentication.",
)
async def protected_endpoint(
    session: Annotated[SessionData, Depends(get_current_user)],
) -> MessageResponse:
    """Return a protected endpoint greeting.

    Args:
        session: Current user session (requires authentication).

    Returns:
        MessageResponse with personalized greeting.
    """
    return MessageResponse(message=f"Hello, {session.name}! You are authenticated.")


# To add more API routers as the application grows, import and include them here.
