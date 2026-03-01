"""API v1 main router aggregating all v1 routes."""

from fastapi import APIRouter
from fastapi import Depends

from shelf_mind.webapp.api.v1.location_router import router as location_router
from shelf_mind.webapp.api.v1.search_router import router as search_router
from shelf_mind.webapp.api.v1.thing_router import router as thing_router
from shelf_mind.webapp.core.dependencies import get_current_user
from shelf_mind.webapp.schemas.common_schemas import MessageResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["api-v1"],
    dependencies=[Depends(get_current_user)],
)

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


# To add more API routers as the application grows, import and include them here.
