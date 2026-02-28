"""Health check router for monitoring endpoints."""

from datetime import UTC
from datetime import datetime

from fastapi import APIRouter

from shelf_mind.webapp.core.dependencies import get_settings
from shelf_mind.webapp.schemas.common_schemas import HealthResponse
from shelf_mind.webapp.schemas.common_schemas import ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="Health check",
    description="Basic health check endpoint for monitoring.",
)
async def health_check() -> HealthResponse:
    """Return basic health status.

    Returns:
        HealthResponse with status and version.
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Checks if the application is ready to serve requests.",
)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe for Kubernetes/container orchestration.

    Checks critical dependencies before declaring ready.

    Returns:
        ReadinessResponse with component check results.
    """
    checks: dict[str, bool] = {}

    # Check configuration loaded
    try:
        settings = get_settings()
        checks["config"] = True
    except (ValueError, AttributeError, KeyError):
        checks["config"] = False

    # Check Google OAuth configured
    try:
        settings = get_settings()
        checks["google_oauth"] = bool(settings.google_oauth.client_id)
    except (ValueError, AttributeError, KeyError):
        checks["google_oauth"] = False

    # Add more checks as needed:
    # - Database connectivity
    # - Redis connectivity
    # - External service availability

    all_ready = all(checks.values())

    return ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        checks=checks,
    )


@router.get(
    "/live",
    summary="Liveness probe",
    description="Simple liveness check - returns 200 if the process is alive.",
)
async def liveness_check() -> dict:
    """Liveness probe for Kubernetes/container orchestration.

    Simply returns OK if the process can respond.

    Returns:
        Simple alive status.
    """
    return {"status": "alive"}
