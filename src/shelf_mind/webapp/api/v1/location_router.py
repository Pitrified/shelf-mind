"""Location management API router."""

from typing import Annotated
import uuid

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlmodel import Session

from shelf_mind.application.errors import DuplicateSiblingNameError
from shelf_mind.application.errors import LocationHasChildrenError
from shelf_mind.application.errors import LocationHasThingsError
from shelf_mind.application.errors import LocationNotFoundError
from shelf_mind.core.container import Container
from shelf_mind.webapp.core.dependencies import get_domain_container
from shelf_mind.webapp.core.dependencies import get_domain_session
from shelf_mind.webapp.schemas.domain_schemas import BatchLocationCreate
from shelf_mind.webapp.schemas.domain_schemas import BatchResultResponse
from shelf_mind.webapp.schemas.domain_schemas import LocationCreate
from shelf_mind.webapp.schemas.domain_schemas import LocationResponse
from shelf_mind.webapp.schemas.domain_schemas import LocationUpdate

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a location",
)
async def create_location(
    body: LocationCreate,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> LocationResponse:
    """Create a new Location in the hierarchy.

    Args:
        body: Location creation data.
        session: Database session.
        container: DI container.

    Returns:
        Created Location.
    """
    svc = container.location_service(session)
    try:
        location = svc.create_location(
            name=body.name,
            parent_id=body.parent_id,
        )
    except LocationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except DuplicateSiblingNameError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e

    return LocationResponse(
        id=location.id,
        name=location.name,
        parent_id=location.parent_id,
        path=location.path,
        created_at=location.created_at,
    )


@router.get(
    "/",
    summary="List all locations",
)
async def list_locations(
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> list[LocationResponse]:
    """List all locations ordered by path.

    Args:
        session: Database session.
        container: DI container.

    Returns:
        All locations.
    """
    svc = container.location_service(session)
    locations = svc.list_locations()
    return [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            parent_id=loc.parent_id,
            path=loc.path,
            created_at=loc.created_at,
        )
        for loc in locations
    ]


@router.get(
    "/{location_id}",
    summary="Get a location",
)
async def get_location(
    location_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> LocationResponse:
    """Get a Location by id.

    Args:
        location_id: UUID of the Location.
        session: Database session.
        container: DI container.

    Returns:
        The Location.
    """
    svc = container.location_service(session)
    try:
        location = svc.get_location(location_id)
    except LocationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return LocationResponse(
        id=location.id,
        name=location.name,
        parent_id=location.parent_id,
        path=location.path,
        created_at=location.created_at,
    )


@router.get(
    "/{location_id}/children",
    summary="List children of a location",
)
async def get_children(
    location_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> list[LocationResponse]:
    """List direct children of a location.

    Args:
        location_id: UUID of the parent Location.
        session: Database session.
        container: DI container.

    Returns:
        Child locations.
    """
    svc = container.location_service(session)
    children = svc.get_children(location_id)
    return [
        LocationResponse(
            id=c.id,
            name=c.name,
            parent_id=c.parent_id,
            path=c.path,
            created_at=c.created_at,
        )
        for c in children
    ]


@router.get(
    "/{location_id}/subtree",
    summary="Get full subtree of a location",
)
async def get_subtree(
    location_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> list[LocationResponse]:
    """List all descendants under a location.

    Args:
        location_id: UUID of the root Location.
        session: Database session.
        container: DI container.

    Returns:
        All descendant locations.
    """
    svc = container.location_service(session)
    try:
        descendants = svc.get_subtree(location_id)
    except LocationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            parent_id=loc.parent_id,
            path=loc.path,
            created_at=loc.created_at,
        )
        for loc in descendants
    ]


@router.patch(
    "/{location_id}",
    summary="Update a location (rename or move)",
)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdate,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> LocationResponse:
    """Update a Location - rename and/or move.

    Args:
        location_id: UUID of the Location.
        body: Update data.
        session: Database session.
        container: DI container.

    Returns:
        Updated Location.
    """
    svc = container.location_service(session)

    try:
        location = svc.get_location(location_id)

        if body.move:
            location = svc.move_location(location_id, body.parent_id)

        if body.name is not None:
            location = svc.rename_location(location.id, body.name)

    except LocationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except DuplicateSiblingNameError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e

    return LocationResponse(
        id=location.id,
        name=location.name,
        parent_id=location.parent_id,
        path=location.path,
        created_at=location.created_at,
    )


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a location",
)
async def delete_location(
    location_id: uuid.UUID,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    force: Annotated[bool, Query()] = False,  # noqa: FBT002
) -> None:
    """Delete a Location.

    Prevents deletion if children exist. Use force=true to bypass
    the check for placed Things.

    Args:
        location_id: UUID of the Location.
        force: Allow deletion even if Things are placed here.
        session: Database session.
        container: DI container.
    """
    svc = container.location_service(session)
    try:
        svc.delete_location(location_id, force=force)
    except LocationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except LocationHasChildrenError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e
    except LocationHasThingsError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    summary="Batch create locations",
)
async def batch_create_locations(
    body: BatchLocationCreate,
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> BatchResultResponse:
    """Create multiple Locations in one request.

    Args:
        body: Batch creation data (1-50 items).
        session: Database session.
        container: DI container.

    Returns:
        Batch result with success/failure counts.
    """
    svc = container.location_service(session)
    succeeded = 0
    errors: list[str] = []

    for item in body.items:
        try:
            svc.create_location(name=item.name, parent_id=item.parent_id)
            succeeded += 1
        except (LocationNotFoundError, DuplicateSiblingNameError) as e:
            errors.append(f"{item.name}: {e}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{item.name}: {e}")

    return BatchResultResponse(
        succeeded=succeeded,
        failed=len(errors),
        errors=errors,
    )
