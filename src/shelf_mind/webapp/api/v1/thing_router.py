"""Thing management API router."""

from typing import Annotated
import uuid

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from loguru import logger as lg
from sqlmodel import Session

from shelf_mind.application.errors import LocationNotFoundError
from shelf_mind.application.errors import ThingNotFoundError
from shelf_mind.core.container import Container
from shelf_mind.webapp.core.dependencies import get_domain_container
from shelf_mind.webapp.core.dependencies import get_domain_session
from shelf_mind.webapp.schemas.domain_schemas import PlacementCreate
from shelf_mind.webapp.schemas.domain_schemas import PlacementResponse
from shelf_mind.webapp.schemas.domain_schemas import ThingCreate
from shelf_mind.webapp.schemas.domain_schemas import ThingListResponse
from shelf_mind.webapp.schemas.domain_schemas import ThingResponse
from shelf_mind.webapp.schemas.domain_schemas import ThingUpdate

router = APIRouter(prefix="/api/v1/things", tags=["things"])


def _thing_to_response(
    thing,  # noqa: ANN001
    location_path: str | None = None,
) -> ThingResponse:
    """Convert a Thing entity to a ThingResponse DTO.

    Args:
        thing: Thing entity.
        location_path: Current location path.

    Returns:
        ThingResponse DTO.
    """
    return ThingResponse(
        id=thing.id,
        name=thing.name,
        description=thing.description,
        metadata_json=thing.metadata_json,
        location_path=location_path,
        created_at=thing.created_at,
        updated_at=thing.updated_at,
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new thing",
)
async def create_thing(
    body: ThingCreate,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> ThingResponse:
    """Register a new Thing with metadata enrichment and vector indexing.

    Args:
        body: Thing creation data.
        session: Database session.
        container: DI container.

    Returns:
        Created Thing.
    """
    thing_svc = container.thing_service(session)

    # Resolve location path if placing
    location_path = None
    if body.location_id is not None:
        loc_svc = container.location_service(session)
        try:
            loc = loc_svc.get_location(body.location_id)
            location_path = loc.path
        except Exception:  # noqa: BLE001
            lg.debug("Could not resolve location path for placement")

    thing = thing_svc.create_thing(
        name=body.name,
        description=body.description,
        location_path=location_path,
    )

    # Create placement if location provided
    if body.location_id is not None:
        placement_svc = container.placement_service(session)
        placement_svc.place_thing(thing.id, body.location_id)

    return _thing_to_response(thing, location_path)


@router.get(
    "/",
    summary="List things",
)
async def list_things(
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ThingListResponse:
    """List Things with pagination.

    Args:
        offset: Page offset.
        limit: Page size.
        session: Database session.
        container: DI container.

    Returns:
        Paginated list of Things.
    """
    thing_svc = container.thing_service(session)
    things = thing_svc.list_things(offset=offset, limit=limit)
    total = thing_svc.count_things()

    items = [_thing_to_response(t) for t in things]
    return ThingListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get(
    "/{thing_id}",
    summary="Get a thing",
)
async def get_thing(
    thing_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> ThingResponse:
    """Get a Thing by id.

    Args:
        thing_id: UUID of the Thing.
        session: Database session.
        container: DI container.

    Returns:
        The Thing.
    """
    thing_svc = container.thing_service(session)
    try:
        thing = thing_svc.get_thing(thing_id)
    except ThingNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    # Get current location
    placement_svc = container.placement_service(session)
    placement = placement_svc.get_current_placement(thing_id)
    location_path = None
    if placement:
        loc_svc = container.location_service(session)
        try:
            loc = loc_svc.get_location(placement.location_id)
            location_path = loc.path
        except Exception:  # noqa: BLE001
            lg.debug("Could not resolve location path for thing retrieval")

    return _thing_to_response(thing, location_path)


@router.patch(
    "/{thing_id}",
    summary="Update a thing",
)
async def update_thing(
    thing_id: uuid.UUID,
    body: ThingUpdate,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> ThingResponse:
    """Update a Thing's name, description, or regenerate metadata.

    Args:
        thing_id: UUID of the Thing.
        body: Update data.
        session: Database session.
        container: DI container.

    Returns:
        Updated Thing.
    """
    thing_svc = container.thing_service(session)
    try:
        thing = thing_svc.update_thing(
            thing_id=thing_id,
            name=body.name,
            description=body.description,
            regenerate_metadata=body.regenerate_metadata,
        )
    except ThingNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return _thing_to_response(thing)


@router.delete(
    "/{thing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a thing",
)
async def delete_thing(
    thing_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> None:
    """Delete a Thing and its vectors.

    Args:
        thing_id: UUID of the Thing.
        session: Database session.
        container: DI container.
    """
    thing_svc = container.thing_service(session)
    try:
        thing_svc.delete_thing(thing_id)
    except ThingNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/{thing_id}/place",
    summary="Place a thing at a location",
)
async def place_thing(
    thing_id: uuid.UUID,  # noqa: ARG001
    body: PlacementCreate,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> PlacementResponse:
    """Place or move a Thing to a Location.

    Args:
        thing_id: UUID of the Thing (path param).
        body: Placement data.
        session: Database session.
        container: DI container.

    Returns:
        New Placement.
    """
    placement_svc = container.placement_service(session)

    try:
        placement = placement_svc.place_thing(body.thing_id, body.location_id)
    except ThingNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except LocationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return PlacementResponse(
        id=placement.id,
        thing_id=placement.thing_id,
        location_id=placement.location_id,
        placed_at=placement.placed_at,
        active=placement.active,
    )


@router.get(
    "/{thing_id}/placements",
    summary="Get placement history",
)
async def get_placement_history(
    thing_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> list[PlacementResponse]:
    """Get placement history for a Thing.

    Args:
        thing_id: UUID of the Thing.
        session: Database session.
        container: DI container.

    Returns:
        List of placements.
    """
    placement_svc = container.placement_service(session)
    placements = placement_svc.get_placement_history(thing_id)
    return [
        PlacementResponse(
            id=p.id,
            thing_id=p.thing_id,
            location_id=p.location_id,
            placed_at=p.placed_at,
            active=p.active,
        )
        for p in placements
    ]
