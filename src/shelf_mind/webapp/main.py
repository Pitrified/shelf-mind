"""FastAPI application factory.

Creates and configures the FastAPI application instance.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from loguru import logger as lg
from starlette.staticfiles import StaticFiles

from shelf_mind.config.webapp import WebappConfig
from shelf_mind.core.container import Container
from shelf_mind.params.shelf_mind_params import get_shelf_mind_paths
from shelf_mind.params.shelf_mind_params import get_webapp_params
from shelf_mind.webapp.api.v1 import api_router
from shelf_mind.webapp.core.exceptions import NotAuthenticatedException
from shelf_mind.webapp.core.exceptions import NotAuthorizedException
from shelf_mind.webapp.core.exceptions import RateLimitExceededException
from shelf_mind.webapp.core.middleware import setup_middleware
from shelf_mind.webapp.core.templating import configure_templates
from shelf_mind.webapp.routers import auth_router
from shelf_mind.webapp.routers import health_router
from shelf_mind.webapp.routers import pages_router
from shelf_mind.webapp.schemas.common_schemas import ErrorResponse
from shelf_mind.webapp.services.auth_service import GoogleAuthService
from shelf_mind.webapp.services.auth_service import SessionStore
from shelf_mind.webapp.services.auth_service import SqliteSessionStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan context manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance.

    Yields:
        None during application lifetime.
    """
    # Startup
    lg.info("Starting webapp...")

    # Initialize session store (persistent SQLite-backed)
    session_store: SessionStore = SqliteSessionStore()
    app.state.session_store = session_store

    # Initialize auth service
    config: WebappConfig = app.state.config
    auth_service = GoogleAuthService(
        oauth_config=config.google_oauth,
        session_config=config.session,
        session_store=session_store,
    )
    app.state.auth_service = auth_service

    # Initialize domain DI container
    domain_container = Container()
    try:
        domain_container.initialize()
        lg.info("Domain container initialized")
    except Exception:  # noqa: BLE001
        lg.warning(
            "Domain container initialization failed "
            "(Qdrant may not be running). Domain APIs will be unavailable.",
        )
    app.state.domain_container = domain_container

    lg.info("Webapp started successfully")

    yield

    # Shutdown
    lg.info("Shutting down webapp...")
    # Cleanup resources here if needed
    lg.info("Webapp shutdown complete")


def create_app(config: WebappConfig | None = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        config: Webapp configuration. If None, loads from environment.

    Returns:
        Configured FastAPI application instance.
    """
    # Load configuration
    if config is None:
        webapp_params = get_webapp_params()
        config = webapp_params.to_config()

    # Create FastAPI app
    # docs_url and redoc_url are disabled; self-hosted routes below
    # serve local Swagger/ReDoc assets so no external CDN is needed.
    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
        description=(
            "A FastAPI web application with Google OAuth authentication. "
            "Built with security best practices including rate limiting, "
            "CSRF protection, and secure session management."
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.debug else None,
        lifespan=lifespan,
    )

    # Store config in app state
    app.state.config = config

    # Configure Jinja2 template globals
    configure_templates(config)

    # Mount static assets (before routers so /static/… is resolved first)
    paths = get_shelf_mind_paths()
    app.mount("/static", StaticFiles(directory=str(paths.static_fol)), name="static")

    # Self-hosted API docs (Swagger UI + ReDoc) — no CDN dependencies
    if config.debug:
        _register_docs_routes(app)

    # Setup CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors.allow_origins,
        allow_credentials=config.cors.allow_credentials,
        allow_methods=config.cors.allow_methods,
        allow_headers=config.cors.allow_headers,
    )

    # Setup custom middleware
    setup_middleware(app, config)

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(pages_router)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(api_router)

    lg.info(f"Created FastAPI app: {config.app_name} v{config.app_version}")

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers.

    Args:
        app: FastAPI application instance.
    """

    @app.exception_handler(NotAuthenticatedException)
    async def not_authenticated_handler(
        request: Request,
        exc: NotAuthenticatedException,
    ) -> JSONResponse | RedirectResponse:
        """Handle authentication errors.

        Browser requests are redirected to the landing page.
        API requests receive a JSON 401 response.
        """
        # Browser/HTMX callers get a redirect to login
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/", status_code=302)

        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.detail,
                error_code="NOT_AUTHENTICATED",
                request_id=request_id,
            ).model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(NotAuthorizedException)
    async def not_authorized_handler(
        request: Request,
        exc: NotAuthorizedException,
    ) -> JSONResponse:
        """Handle authorization errors."""
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.detail,
                error_code="NOT_AUTHORIZED",
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(RateLimitExceededException)
    async def rate_limit_handler(
        request: Request,
        exc: RateLimitExceededException,
    ) -> JSONResponse:
        """Handle rate limit errors."""
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.detail,
                error_code="RATE_LIMIT_EXCEEDED",
                request_id=request_id,
            ).model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected errors."""
        request_id = getattr(request.state, "request_id", None)
        lg.exception(f"Unhandled exception: {exc}")

        # Don't expose internal errors in production
        config: WebappConfig = request.app.state.config
        detail = str(exc) if config.debug else "Internal server error"

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                detail=detail,
                error_code="INTERNAL_ERROR",
                request_id=request_id,
            ).model_dump(),
        )


def _register_docs_routes(app: FastAPI) -> None:
    """Register self-hosted Swagger UI and ReDoc routes.

    These serve locally-bundled JS/CSS from ``/static/swagger/`` so no
    external CDN is referenced, keeping CSP strict.

    Args:
        app: FastAPI application instance.
    """

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        """Serve Swagger UI from local static assets."""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - Swagger UI",
            swagger_js_url="/static/swagger/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger/swagger-ui.css",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        )

    @app.get(
        app.swagger_ui_oauth2_redirect_url or "/docs/oauth2-redirect",
        include_in_schema=False,
    )
    async def swagger_ui_redirect() -> HTMLResponse:
        """Serve the OAuth2 redirect page for Swagger UI."""
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html() -> HTMLResponse:
        """Serve ReDoc from local static assets."""
        return get_redoc_html(
            openapi_url=app.openapi_url or "/openapi.json",
            title=f"{app.title} - ReDoc",
            redoc_js_url="/static/swagger/redoc.standalone.js",
        )
