"""Search API router - text and vision search endpoints."""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status

from shelf_mind.core.container import Container
from shelf_mind.webapp.core.dependencies import get_domain_container
from shelf_mind.webapp.schemas.domain_schemas import SearchRequest
from shelf_mind.webapp.schemas.domain_schemas import SearchResponse
from shelf_mind.webapp.schemas.domain_schemas import SearchResultResponse

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post(
    "/text",
    summary="Text search",
)
async def search_text(
    body: SearchRequest,
    container: Annotated[Container, Depends(get_domain_container)],
) -> SearchResponse:
    """Search Things by text query.

    Pipeline: embed query, vector search, payload filter, rank.

    Args:
        body: Search request data.
        container: DI container.

    Returns:
        Ranked search results.
    """
    search_svc = container.search_service()
    try:
        results = search_svc.search_text(
            query=body.q,
            location_filter=body.location_filter,
            limit=body.limit,
        )
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Search service error: {e}",
        ) from e

    return SearchResponse(
        results=[
            SearchResultResponse(
                thing_id=r.thing_id,
                name=r.name,
                description=r.description,
                category=r.category,
                tags=r.tags,
                location_path=r.location_path,
                score=r.score,
            )
            for r in results
        ],
        total=len(results),
        query=body.q,
    )


@router.post(
    "/image",
    summary="Vision search",
)
async def search_image(
    image: Annotated[UploadFile, File(...)],
    container: Annotated[Container, Depends(get_domain_container)],
    limit: int = 10,
) -> SearchResponse:
    """Search Things by image similarity.

    Pipeline: preprocess image, embed, vector search, rank.

    Args:
        image: Uploaded image file.
        limit: Max results.
        container: DI container.

    Returns:
        Ranked search results.
    """
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Empty image file",
        )

    search_svc = container.search_service()
    try:
        results = search_svc.search_image(
            image_bytes=image_bytes,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vision search error: {e}",
        ) from e

    return SearchResponse(
        results=[
            SearchResultResponse(
                thing_id=r.thing_id,
                name=r.name,
                description=r.description,
                category=r.category,
                tags=r.tags,
                location_path=r.location_path,
                score=r.score,
            )
            for r in results
        ],
        total=len(results),
        query="[image]",
    )
