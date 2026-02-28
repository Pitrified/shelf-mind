"""Custom middleware for the webapp."""

from collections.abc import Callable
import time
import uuid

from fastapi import Request
from fastapi import Response
from loguru import logger as lg
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shelf_mind.config.webapp import WebappConfig


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Add request ID to request state and response headers.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with X-Request-ID header.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Implements CSP route-splitting: strict policy for app pages,
    relaxed policy for ``/docs`` and ``/redoc`` (Swagger UI).
    """

    # Paths that require the relaxed (Swagger UI) CSP
    _DOCS_PREFIXES = ("/docs", "/redoc", "/openapi.json")

    def __init__(self, app: ASGIApp, *, is_production: bool = False) -> None:
        """Initialize middleware.

        Args:
            app: ASGI application.
            is_production: Whether running in production mode.
        """
        super().__init__(app)
        self.is_production = is_production

        # ── Strict CSP (app / UI pages) ──────────────────────
        # style-src needs 'unsafe-inline' because HTMX applies inline
        # styles during swap/settle transitions (opacity, display).
        # img-src allows Google profile pictures (lh3.googleusercontent.com).
        self.strict_csp = (
            "default-src 'self'"
            "; script-src 'self'"
            "; style-src 'self' 'unsafe-inline'"
            "; img-src 'self' data: https://lh3.googleusercontent.com"
            "; font-src 'self'"
            "; connect-src 'self'"
            "; frame-ancestors 'none'"
            "; base-uri 'self'"
            "; form-action 'self'"
            "; object-src 'none'"
            "; worker-src 'self'"
            "; manifest-src 'self'"
        )

        # ── Relaxed CSP (Swagger UI / ReDoc) ─────────────────
        # Swagger UI is self-hosted from /static/swagger/ — no CDN needed.
        # 'unsafe-inline' is required for Swagger UI's own inline scripts/styles.
        self.docs_csp = (
            "default-src 'self'"
            "; script-src 'self' 'unsafe-inline'"
            "; style-src 'self' 'unsafe-inline'"
            "; img-src 'self' data:"
            "; font-src 'self'"
            "; connect-src 'self'"
            "; frame-ancestors 'none'"
            "; base-uri 'self'"
            "; form-action 'self'"
            "; object-src 'none'"
            "; worker-src 'self'"
            "; manifest-src 'self'"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Add security headers to response.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with security headers.
        """
        response = await call_next(request)

        # Always add these headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP route-splitting: relaxed for docs, strict for everything else
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self._DOCS_PREFIXES):
            response.headers["Content-Security-Policy"] = self.docs_csp
        else:
            response.headers["Content-Security-Policy"] = self.strict_csp

        # HSTS only in production (requires HTTPS)
        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request and response details."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Log request details and timing.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from handler.
        """
        start_time = time.perf_counter()

        # Get request ID if available
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request
        lg.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        lg.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration_ms:.2f}ms)"
        )

        return response


def setup_middleware(app: ASGIApp, config: WebappConfig) -> None:
    """Configure all custom middleware on the application.

    Args:
        app: FastAPI application.
        config: Webapp configuration.
    """
    from fastapi import FastAPI  # noqa: PLC0415

    if not isinstance(app, FastAPI):
        return

    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        SecurityHeadersMiddleware,
        is_production=not config.debug,
    )
    app.add_middleware(RequestIDMiddleware)
