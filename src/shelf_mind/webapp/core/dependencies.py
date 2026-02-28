"""FastAPI dependency injection functions."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING
from typing import Annotated

from fastapi import Cookie
from fastapi import Depends
from fastapi import Request

from shelf_mind.params.shelf_mind_params import get_webapp_params
from shelf_mind.webapp.core.exceptions import NotAuthenticatedException
from shelf_mind.webapp.schemas.auth_schemas import SessionData  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Generator

    from shelf_mind.config.webapp import WebappConfig
    from shelf_mind.webapp.services.auth_service import SessionStore


@lru_cache
def get_settings() -> WebappConfig:
    """Get webapp configuration settings.

    Returns:
        WebappConfig instance.
    """
    return get_webapp_params().to_config()


def get_session_store(request: Request) -> SessionStore:
    """Get the session store from app state.

    Args:
        request: FastAPI request object.

    Returns:
        SessionStore instance.
    """
    return request.app.state.session_store


async def get_current_session(
    request: Request,
    session: Annotated[str | None, Cookie(alias="session")] = None,
) -> SessionData | None:
    """Get current session from cookie.

    Args:
        request: FastAPI request object.
        session: Session ID from cookie.

    Returns:
        SessionData if valid session exists, None otherwise.
    """
    if not session:
        return None

    session_store = get_session_store(request)
    session_data = session_store.get_session(session)

    # SessionStore.get_session() already handles expiration cleanup
    return session_data


async def get_current_user(
    session: Annotated[SessionData | None, Depends(get_current_session)],
) -> SessionData:
    """Get current authenticated user.

    Args:
        session: Current session data.

    Returns:
        SessionData for authenticated user.

    Raises:
        NotAuthenticatedException: If no valid session.
    """
    if session is None:
        raise NotAuthenticatedException
    return session


async def get_optional_user(
    session: Annotated[SessionData | None, Depends(get_current_session)],
) -> SessionData | None:
    """Get current user if authenticated, None otherwise.

    Args:
        session: Current session data.

    Returns:
        SessionData if authenticated, None otherwise.
    """
    return session


def get_db_session() -> Generator[None]:
    """Get database session (placeholder for future DB integration).

    Yields:
        Database session (currently None).
    """
    # Placeholder for future database integration
    yield None
