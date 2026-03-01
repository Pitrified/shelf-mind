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
) -> HTMLResponse:
    """Execute a text search and return results partial."""
    search_svc = container.search_service()
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] or None
    results = search_svc.search_text(
        query=q,
        category_filter=category or None,
        material_filter=material or None,
        tags_filter=tags_list,
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
