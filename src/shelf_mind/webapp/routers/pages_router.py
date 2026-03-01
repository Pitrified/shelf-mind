"""HTML page routes.

Serves server-rendered Jinja2 templates for the browser UI.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Form
from fastapi import Query
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from loguru import logger as lg
from sqlmodel import Session  # noqa: TC002

from shelf_mind.core.container import Container  # noqa: TC001
from shelf_mind.webapp.core.dependencies import get_current_user
from shelf_mind.webapp.core.dependencies import get_domain_container
from shelf_mind.webapp.core.dependencies import get_domain_session
from shelf_mind.webapp.core.dependencies import get_optional_user
from shelf_mind.webapp.core.templating import templates
from shelf_mind.webapp.schemas.auth_schemas import SessionData  # noqa: TC001

# Map OAuth error codes to user-friendly messages
_ERROR_MESSAGES: dict[str, str] = {
    "access_denied": "Access was denied. Please try again.",
    "auth_failed": "Authentication failed. Please try again.",
    "invalid_state": "Session expired. Please try again.",
}

router = APIRouter(tags=["pages"])


@router.get(
    "/",
    response_model=None,
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def landing(
    request: Request,
    user: Annotated[SessionData | None, Depends(get_optional_user)],
    error: Annotated[str | None, Query()] = None,
) -> HTMLResponse | RedirectResponse:
    """Render public landing page or redirect authenticated users.

    Args:
        request: Incoming request.
        user: Current user session, if any.
        error: OAuth error code from callback redirect.

    Returns:
        Landing page HTML or redirect to dashboard.
    """
    if user is not None:
        return RedirectResponse(url="/dashboard", status_code=302)

    flash = None
    if error:
        flash = {
            "type": "danger",
            "message": _ERROR_MESSAGES.get(error, f"An error occurred: {error}"),
        }

    return templates.TemplateResponse(
        request,
        "pages/landing.html",
        {"user": None, "flash": flash, "active_page": "landing"},
    )


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render authenticated dashboard.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Dashboard page HTML.
    """
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {"user": user, "active_page": "dashboard"},
    )


@router.get(
    "/pages/partials/user-card",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def user_card_partial(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Return user card HTML fragment for HTMX swap.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        User card partial HTML (no base layout).
    """
    return templates.TemplateResponse(
        request,
        "partials/user_card.html",
        {"user": user},
    )


@router.get(
    "/error/{status_code}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def error_page(
    request: Request,
    status_code: int,
    user: Annotated[SessionData | None, Depends(get_optional_user)],
) -> HTMLResponse:
    """Render a generic error page.

    Args:
        request: Incoming request.
        status_code: HTTP status code to display.
        user: Current user session, if any.

    Returns:
        Error page HTML.
    """
    messages: dict[int, str] = {
        400: "Bad request.",
        401: "You need to log in to access this page.",
        403: "You don't have permission to view this page.",
        404: "The page you're looking for doesn't exist.",
        500: "Something went wrong on our end.",
    }
    message = messages.get(status_code, "An unexpected error occurred.")

    return templates.TemplateResponse(
        request,
        "pages/error.html",
        {
            "user": user,
            "status_code": status_code,
            "message": message,
        },
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Location pages (HTMX)
# ---------------------------------------------------------------------------


@router.get("/pages/locations", response_class=HTMLResponse, include_in_schema=False)
async def locations_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render the location browser page."""
    return templates.TemplateResponse(
        request,
        "pages/locations.html",
        {"user": user, "active_page": "locations"},
    )


@router.get(
    "/pages/locations/tree",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def location_tree_partial(
    request: Request,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> HTMLResponse:
    """Return the location tree partial (root locations)."""
    svc = container.location_service(session)
    roots = svc.get_children(parent_id=None)
    return templates.TemplateResponse(
        request,
        "partials/location_tree.html",
        {"locations": roots},
    )


@router.post(
    "/pages/locations/create",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def create_location_page(
    request: Request,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    name: Annotated[str, Form()],
    parent_id: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Create a location and return the updated tree partial."""
    import uuid as _uuid  # noqa: PLC0415

    svc = container.location_service(session)
    pid = _uuid.UUID(parent_id) if parent_id else None
    try:
        svc.create_location(name=name, parent_id=pid)
    except (ValueError, RuntimeError):
        lg.opt(exception=True).warning("Location creation failed")

    roots = svc.get_children(parent_id=None)
    return templates.TemplateResponse(
        request,
        "partials/location_tree.html",
        {"locations": roots},
    )


@router.get(
    "/pages/locations/{location_id}/detail",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def location_detail_partial(
    request: Request,
    location_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> HTMLResponse:
    """Return the location detail partial."""
    import uuid as _uuid  # noqa: PLC0415

    svc = container.location_service(session)
    loc = svc.get_location(_uuid.UUID(location_id))
    children = svc.get_children(loc.id)
    return templates.TemplateResponse(
        request,
        "partials/location_detail.html",
        {"location": loc, "children": children},
    )


# ---------------------------------------------------------------------------
# Thing pages (HTMX)
# ---------------------------------------------------------------------------


@router.get("/pages/things", response_class=HTMLResponse, include_in_schema=False)
async def things_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render the thing registration page."""
    return templates.TemplateResponse(
        request,
        "pages/things.html",
        {"user": user, "active_page": "things"},
    )


@router.post(
    "/pages/things/create",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def create_thing_page(
    request: Request,  # noqa: ARG001
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    location_id: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Create a thing from form data and return a success message."""
    import uuid as _uuid  # noqa: PLC0415

    thing_svc = container.thing_service(session)
    location_path: str | None = None

    if location_id:
        loc_svc = container.location_service(session)
        try:
            loc = loc_svc.get_location(_uuid.UUID(location_id))
            location_path = loc.path
        except (ValueError, RuntimeError):
            lg.opt(exception=True).warning("Location lookup failed")

    try:
        thing = thing_svc.create_thing(
            name=name,
            description=description,
            location_path=location_path,
        )
        # Place the thing if location was specified
        if location_id:
            placement_svc = container.placement_service(session)
            placement_svc.place_thing(
                thing_id=thing.id,
                location_id=_uuid.UUID(location_id),
            )
        html = (
            '<article class="message is-success">'
            '<div class="message-body">'
            f"Registered <strong>{thing.name}</strong> successfully."
            "</div></article>"
        )
    except (ValueError, RuntimeError):
        lg.opt(exception=True).warning("Thing creation failed")
        html = (
            '<article class="message is-danger">'
            '<div class="message-body">Failed to register thing.</div>'
            "</article>"
        )

    return HTMLResponse(content=html)


@router.post(
    "/pages/things/preview",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def thing_preview_partial(
    request: Request,  # noqa: ARG001
    _user: Annotated[SessionData, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_domain_container)],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Return a metadata preview card for the given name/description."""
    enricher = container.get_enricher()
    meta = enricher.enrich(name, description or None)
    html = (
        '<div class="box">'
        f"<p><strong>Category:</strong> {meta.category}</p>"
        f"<p><strong>Material:</strong> {meta.material}</p>"
        f"<p><strong>Room hint:</strong> {meta.room_hint}</p>"
        f"<p><strong>Tags:</strong> {', '.join(meta.tags)}</p>"
        f"<p><strong>Usage:</strong> {meta.usage_context}</p>"
        "</div>"
    )
    return HTMLResponse(content=html)


@router.get(
    "/pages/things/location-options",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def thing_location_options(
    request: Request,  # noqa: ARG001
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> HTMLResponse:
    """Return select <option> elements for all locations."""
    svc = container.location_service(session)
    locations = svc.list_locations()
    options = [
        '<option value="">-- Select location --</option>',
        *[f'<option value="{loc.id}">{loc.path}</option>' for loc in locations],
    ]
    return HTMLResponse(content="\n".join(options))


# ---------------------------------------------------------------------------
# Search pages (HTMX)
# ---------------------------------------------------------------------------


@router.get("/pages/search", response_class=HTMLResponse, include_in_schema=False)
async def search_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render the search page."""
    return templates.TemplateResponse(
        request,
        "pages/search.html",
        {"user": user, "active_page": "search"},
    )


@router.post(
    "/pages/search/results",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def search_results_partial(
    request: Request,
    _user: Annotated[SessionData, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_domain_container)],
    q: Annotated[str, Form()],
    category: Annotated[str, Form()] = "",
    material: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
    location_filter: Annotated[str, Form()] = "",
    limit: Annotated[int, Form()] = 10,
) -> HTMLResponse:
    """Execute a text search and return results partial."""
    search_svc = container.search_service()
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] or None
    results = search_svc.search_text(
        query=q,
        category_filter=category or None,
        material_filter=material or None,
        tags_filter=tags_list,
        location_filter=location_filter or None,
        limit=max(1, min(100, limit)),
    )

    template_results = [
        {
            "name": r.name,
            "description": r.description,
            "score": r.score,
            "category": r.category,
            "location_path": r.location_path,
            "tags": r.tags,
        }
        for r in results
    ]

    return templates.TemplateResponse(
        request,
        "partials/search_results.html",
        {
            "results": template_results,
            "total": len(template_results),
            "query": q,
        },
    )


@router.post(
    "/pages/search/vision",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def vision_search_results_partial(
    request: Request,
    _user: Annotated[SessionData, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_domain_container)],
    limit: Annotated[int, Form()] = 10,
) -> HTMLResponse:
    """Execute a vision (image) search and return results partial.

    Accepts a multipart image upload (field name ``image``). Returns
    the same search_results partial populated with vision-ranked hits.

    Args:
        request: Incoming request (also used to read multipart).
        _user: Authenticated user session.
        container: Domain DI container.
        limit: Max results (1-100).

    Returns:
        Search results partial HTML.
    """
    import json as _json  # noqa: PLC0415

    form = await request.form()
    upload = form.get("image")
    if upload is None or not hasattr(upload, "read"):
        return HTMLResponse(
            content='<div class="notification is-warning">No image provided.</div>',
        )

    image_bytes = await upload.read()  # type: ignore[union-attr]
    if not image_bytes:
        return HTMLResponse(
            content='<div class="notification is-warning">Empty image file.</div>',
        )

    search_svc = container.search_service()
    results = search_svc.search_image(
        image_bytes=image_bytes,
        limit=max(1, min(100, limit)),
    )

    template_results = [
        {
            "name": r.name,
            "description": r.description,
            "score": r.score,
            "category": r.category,
            "location_path": r.location_path,
            "tags": r.tags,
        }
        for r in results
    ]

    return templates.TemplateResponse(
        request,
        "partials/search_results.html",
        {
            "results": template_results,
            "total": len(template_results),
            "query": f"image ({_json.dumps(len(image_bytes))} bytes)",
        },
    )


# ---------------------------------------------------------------------------
# Thing list / detail / edit / delete  (HTMX)
# ---------------------------------------------------------------------------


@router.post(
    "/pages/things/list",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def things_list_partial(
    request: Request,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    q: Annotated[str, Form()] = "",
    offset: Annotated[int, Form()] = 0,
    limit: Annotated[int, Form()] = 20,
) -> HTMLResponse:
    """Return paginated things list partial, optionally filtered by name.

    Args:
        request: Incoming request.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.
        q: Optional name substring filter.
        offset: Pagination offset.
        limit: Page size.

    Returns:
        Things list partial HTML.
    """
    import json as _json  # noqa: PLC0415

    thing_svc = container.thing_service(session)
    placement_repo = container.placement_service(session)._placement_repo  # noqa: SLF001

    all_things = thing_svc.list_things(offset=0, limit=10_000)
    if q:
        q_lower = q.lower()
        all_things = [t for t in all_things if q_lower in t.name.lower()]

    total = len(all_things)
    page = all_things[offset : offset + limit]

    things_data = []
    for t in page:
        meta = _json.loads(t.metadata_json or "{}")
        placement = placement_repo.get_active_for_thing(t.id)
        location_path: str | None = None
        if placement is not None:
            loc_svc = container.location_service(session)
            try:
                loc = loc_svc.get_location(placement.location_id)
                location_path = loc.path
            except (ValueError, RuntimeError):
                pass
        things_data.append(
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": meta.get("category"),
                "location_path": location_path,
            },
        )

    return templates.TemplateResponse(
        request,
        "partials/things_list.html",
        {
            "things": things_data,
            "total": total,
            "offset": offset,
            "limit": limit,
        },
    )


@router.get(
    "/pages/things/{thing_id}/detail",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def thing_detail_partial(
    request: Request,
    thing_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> HTMLResponse:
    """Return the thing detail partial.

    Args:
        request: Incoming request.
        thing_id: UUID of the Thing.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.

    Returns:
        Thing detail partial HTML.
    """
    import json as _json  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415

    thing_svc = container.thing_service(session)
    try:
        thing = thing_svc.get_thing(_uuid.UUID(thing_id))
    except (ValueError, RuntimeError):
        return HTMLResponse(
            content='<p class="has-text-danger">Thing not found.</p>',
        )

    meta = _json.loads(thing.metadata_json or "{}")
    placement_svc = container.placement_service(session)
    placement = placement_svc._placement_repo.get_active_for_thing(thing.id)  # noqa: SLF001
    location_path: str | None = None
    if placement is not None:
        loc_svc = container.location_service(session)
        try:
            loc = loc_svc.get_location(placement.location_id)
            location_path = loc.path
        except (ValueError, RuntimeError):
            pass

    thing_ctx = {
        "id": thing.id,
        "name": thing.name,
        "description": thing.description,
        "category": meta.get("category"),
        "material": meta.get("material"),
        "room_hint": meta.get("room_hint"),
        "tags": meta.get("tags", []),
        "usage_context": meta.get("usage_context", []),
        "location_path": location_path,
        "created_at": thing.created_at.strftime("%Y-%m-%d %H:%M"),
    }

    return templates.TemplateResponse(
        request,
        "partials/thing_detail.html",
        {"thing": thing_ctx},
    )


@router.get(
    "/pages/things/{thing_id}/edit-form",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def thing_edit_form_partial(
    request: Request,
    thing_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> HTMLResponse:
    """Return the thing inline edit form partial.

    Args:
        request: Incoming request.
        thing_id: UUID of the Thing.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.

    Returns:
        Thing edit form partial HTML.
    """
    import uuid as _uuid  # noqa: PLC0415

    thing_svc = container.thing_service(session)
    try:
        thing = thing_svc.get_thing(_uuid.UUID(thing_id))
    except (ValueError, RuntimeError):
        return HTMLResponse(
            content='<p class="has-text-danger">Thing not found.</p>',
        )

    return templates.TemplateResponse(
        request,
        "partials/thing_edit_form.html",
        {"thing": thing},
    )


@router.post(
    "/pages/things/{thing_id}/update",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def update_thing_page(
    request: Request,
    thing_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()] = "",
    regenerate_metadata: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Update a thing from the inline edit form.

    After updating, returns the detail partial for the same thing.

    Args:
        request: Incoming request.
        thing_id: UUID of the Thing.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.
        name: New name.
        description: New description.
        regenerate_metadata: If "1", re-run enrichment.

    Returns:
        Updated thing detail partial HTML.
    """
    import uuid as _uuid  # noqa: PLC0415

    thing_svc = container.thing_service(session)
    try:
        thing_svc.update_thing(
            _uuid.UUID(thing_id),
            name=name,
            description=description,
            regenerate_metadata=bool(regenerate_metadata),
        )
    except (ValueError, RuntimeError):
        lg.opt(exception=True).warning("Thing update failed")

    # Re-use the detail partial handler logic
    return await thing_detail_partial(
        request=request,
        thing_id=thing_id,
        _user=_user,
        session=session,
        container=container,
    )


@router.delete(
    "/pages/things/{thing_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def delete_thing_page(
    request: Request,
    thing_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
) -> HTMLResponse:
    """Delete a thing and return the refreshed things list.

    Args:
        request: Incoming request.
        thing_id: UUID of the Thing.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.

    Returns:
        Refreshed things list partial HTML.
    """
    import uuid as _uuid  # noqa: PLC0415

    thing_svc = container.thing_service(session)
    try:
        thing_svc.delete_thing(_uuid.UUID(thing_id))
        lg.info(f"Deleted thing: {thing_id}")
    except (ValueError, RuntimeError):
        lg.opt(exception=True).warning("Thing deletion failed")

    return await things_list_partial(
        request=request,
        _user=_user,
        session=session,
        container=container,
    )


# ---------------------------------------------------------------------------
# Location rename / delete  (HTMX)
# ---------------------------------------------------------------------------


@router.post(
    "/pages/locations/{location_id}/rename",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def rename_location_page(
    request: Request,
    location_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    name: Annotated[str, Form()],
) -> HTMLResponse:
    """Rename a location and return the refreshed tree + detail.

    Args:
        request: Incoming request.
        location_id: UUID of the Location.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.
        name: New name for the location.

    Returns:
        Updated location detail partial HTML (tree is also refreshed via OOB).
    """
    import uuid as _uuid  # noqa: PLC0415

    svc = container.location_service(session)
    try:
        loc = svc.rename_location(_uuid.UUID(location_id), name)
    except (ValueError, RuntimeError):
        lg.opt(exception=True).warning("Location rename failed")
        loc = svc.get_location(_uuid.UUID(location_id))

    children = svc.get_children(loc.id)
    roots = svc.get_children(parent_id=None)

    # Primary swap: detail panel; OOB swap: location tree
    detail_html = templates.get_template("partials/location_detail.html").render(
        {"request": request, "location": loc, "children": children},
    )
    tree_html = (
        '<div id="location-tree" hx-swap-oob="innerHTML">'
        + templates.get_template("partials/location_tree.html").render(
            {"request": request, "locations": roots},
        )
        + "</div>"
    )
    return HTMLResponse(content=detail_html + tree_html)


@router.delete(
    "/pages/locations/{location_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def delete_location_page(
    request: Request,
    location_id: str,
    _user: Annotated[SessionData, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_domain_session)],
    container: Annotated[Container, Depends(get_domain_container)],
    force: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Delete a location and return the refreshed location tree.

    Args:
        request: Incoming request.
        location_id: UUID of the Location.
        _user: Authenticated user session.
        session: Database session.
        container: Domain DI container.
        force: If "1", force-delete even when Things are present.

    Returns:
        Updated location tree partial HTML.
    """
    import uuid as _uuid  # noqa: PLC0415

    from shelf_mind.application.errors import LocationHasChildrenError  # noqa: PLC0415
    from shelf_mind.application.errors import LocationHasThingsError  # noqa: PLC0415

    svc = container.location_service(session)
    error_html = ""
    try:
        svc.delete_location(_uuid.UUID(location_id), force=bool(force))
    except LocationHasChildrenError:
        error_html = (
            '<p class="has-text-danger">Cannot delete: location has children.</p>'
        )
    except LocationHasThingsError:
        error_html = (
            '<p class="has-text-warning">'
            "Things are placed here. "
            '<button class="button is-danger is-small ml-2"'
            f'  hx-delete="/pages/locations/{location_id}"'
            '  hx-target="#location-tree"'
            '  hx-swap="innerHTML"'
            '  hx-vals=\'{"force": "1"}\'>'
            "Force Delete"
            "</button>"
            "</p>"
        )
    except (ValueError, RuntimeError):
        lg.opt(exception=True).warning("Location deletion failed")
        error_html = '<p class="has-text-danger">Deletion failed.</p>'

    roots = svc.get_children(parent_id=None)
    tree_html = templates.get_template("partials/location_tree.html").render(
        {"request": request, "locations": roots},
    )
    return HTMLResponse(content=tree_html + error_html)
