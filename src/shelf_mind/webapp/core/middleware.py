"""Custom middleware for the webapp."""

from collections import defaultdict
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding window rate limiter per client IP.

    Tracks request timestamps per IP and rejects requests that exceed
    the configured requests-per-minute threshold.

    Args:
        app: ASGI application.
        requests_per_minute: Max requests per minute per IP.
        burst_size: Extra burst allowance above the per-minute rate.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        requests_per_minute: int = 100,
        burst_size: int = 10,
    ) -> None:
        """Initialize rate limiter.

        Args:
            app: ASGI application.
            requests_per_minute: Max requests per minute per IP.
            burst_size: Extra burst allowance above the per-minute rate.
        """
        super().__init__(app)
        self._rpm = requests_per_minute
        self._burst = burst_size
        self._window = 60.0  # seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Check rate limit before processing request.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from handler, or 429 if rate limited.
        """
        from shelf_mind.webapp.core.exceptions import (  # noqa: PLC0415
            RateLimitExceededException,
        )

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        # Clean old entries
        cutoff = now - self._window
        self._requests[client_ip] = [t for t in self._requests[client_ip] if t > cutoff]

        max_allowed = self._rpm + self._burst
        if len(self._requests[client_ip]) >= max_allowed:
            # Calculate retry_after from oldest entry
            oldest = self._requests[client_ip][0]
            retry_after = int(self._window - (now - oldest)) + 1
            raise RateLimitExceededException(retry_after=max(1, retry_after))

        self._requests[client_ip].append(now)
        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing requests.

    For browser requests (Accept: text/html or HTMX), validates that
    the X-CSRF-Token header matches the csrf_token cookie.
    Sets the csrf_token cookie on responses if not present.

    API-only callers (JSON Accept header, no session cookie) are exempt
    since they authenticate with tokens, not cookies.
    """

    _UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    _EXEMPT_PATHS = frozenset({"/auth/google/callback", "/auth/logout"})

    def __init__(self, app: ASGIApp, *, secret_key: str) -> None:
        """Initialize CSRF middleware.

        Args:
            app: ASGI application.
            secret_key: Secret for signing tokens.
        """
        super().__init__(app)
        self._secret_key = secret_key

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Validate CSRF token for unsafe methods.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from handler.
        """
        import secrets  # noqa: PLC0415

        from starlette.responses import JSONResponse  # noqa: PLC0415

        # Only enforce for unsafe methods
        if request.method in self._UNSAFE_METHODS:
            path = request.url.path

            # Skip exempt paths (OAuth callback, etc.)
            if path not in self._EXEMPT_PATHS:
                # Check if this is a browser request (has session cookie)
                session_cookie = request.cookies.get("session")
                if session_cookie:
                    csrf_cookie = request.cookies.get("csrf_token", "")
                    csrf_header = request.headers.get("x-csrf-token", "")

                    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "CSRF token validation failed"},
                        )

        response = await call_next(request)

        # Set CSRF cookie if not present
        if "csrf_token" not in request.cookies:
            token = secrets.token_hex(32)
            response.set_cookie(
                key="csrf_token",
                value=token,
                httponly=False,  # Must be readable by JavaScript/HTMX
                samesite="lax",
                secure=request.url.scheme == "https",
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
    app.add_middleware(
        CSRFMiddleware,
        secret_key=config.session.secret_key,
    )
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=config.rate_limit.requests_per_minute,
        burst_size=config.rate_limit.burst_size,
    )
    app.add_middleware(RequestIDMiddleware)
