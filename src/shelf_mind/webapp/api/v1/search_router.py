"""Search API router - text and vision search endpoints."""

from collections.abc import AsyncGenerator
import json
import re
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import StreamingResponse

from shelf_mind.core.container import Container
from shelf_mind.webapp.core.dependencies import get_domain_container
from shelf_mind.webapp.schemas.domain_schemas import SearchRequest
from shelf_mind.webapp.schemas.domain_schemas import SearchResponse
from shelf_mind.webapp.schemas.domain_schemas import SearchResultResponse

router = APIRouter(prefix="/api/v1/search", tags=["search"])

# Regex to strip HTML/script tags for sanitization
_STRIP_HTML_RE = re.compile(r"<[^>]+>")


def _sanitize_query(query: str) -> str:
    """Sanitize a search query string.

    Strips HTML tags, normalizes whitespace, and enforces length limits.

    Args:
        query: Raw query string.

    Returns:
        Sanitized query.

    Raises:
        HTTPException: If query is empty after sanitization.
    """
    # Strip HTML tags
    cleaned = _STRIP_HTML_RE.sub("", query)
    # Normalize whitespace
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Query is empty after sanitization",
        )
    return cleaned


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
    sanitized_query = _sanitize_query(body.q)
    try:
        results = search_svc.search_text(
            query=sanitized_query,
            location_filter=body.location_filter,
            category_filter=body.category_filter,
            material_filter=body.material_filter,
            tags_filter=body.tags_filter,
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
        query=sanitized_query,
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


def _sse_event(event: str, data: dict[str, object]) -> str:
    """Format a server-sent event message.

    Args:
        event: Event name.
        data: JSON-serializable data payload.

    Returns:
        Formatted SSE string.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get(
    "/stream",
    summary="Streaming text search (SSE)",
)
async def search_text_stream(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    container: Annotated[Container, Depends(get_domain_container)],
    location_filter: str | None = None,
    category_filter: str | None = None,
    material_filter: str | None = None,
    limit: int = 10,
) -> StreamingResponse:
    """Stream search progress and results via Server-Sent Events.

    Emits events: ``progress`` (status updates) and ``result`` (each hit),
    followed by a ``done`` event with result count.

    Args:
        q: Search query string.
        container: DI container.
        location_filter: Optional location prefix filter.
        category_filter: Optional category filter.
        material_filter: Optional material filter.
        limit: Max results.

    Returns:
        SSE streaming response.
    """
    sanitized_query = _sanitize_query(q)

    async def event_generator() -> AsyncGenerator[str]:
        yield _sse_event(
            "progress",
            {"step": "embedding", "message": "Embedding query..."},
        )

        embedder = container.get_embedder()
        query_vector = await embedder.embed_async(sanitized_query)

        yield _sse_event(
            "progress",
            {"step": "searching", "message": "Searching vector store..."},
        )

        vector_repo = container.get_vector_repo()
        raw_results = vector_repo.search_text(
            vector=query_vector,
            limit=limit,
            location_filter=location_filter,
            category_filter=category_filter,
            material_filter=material_filter,
        )

        n_raw = len(raw_results)
        yield _sse_event(
            "progress",
            {"step": "ranking", "message": f"Ranking {n_raw} results..."},
        )

        ranker = container.get_ranker()
        query_tags = sanitized_query.lower().split()
        ranked = ranker.rank(
            results=raw_results,
            query_tags=query_tags,
            location_path=location_filter,
        )

        for r in ranked:
            yield _sse_event(
                "result",
                {
                    "thing_id": str(r.thing_id),
                    "name": r.name,
                    "description": r.description,
                    "category": r.category,
                    "tags": r.tags,
                    "location_path": r.location_path,
                    "score": r.score,
                },
            )

        yield _sse_event("done", {"total": len(ranked), "query": sanitized_query})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
