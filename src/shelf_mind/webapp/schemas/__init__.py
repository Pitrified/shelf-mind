"""Webapp schemas module."""

from shelf_mind.webapp.schemas.auth_schemas import GoogleUserInfo
from shelf_mind.webapp.schemas.auth_schemas import LoginResponse
from shelf_mind.webapp.schemas.auth_schemas import SessionData
from shelf_mind.webapp.schemas.auth_schemas import UserResponse
from shelf_mind.webapp.schemas.common_schemas import ErrorResponse
from shelf_mind.webapp.schemas.common_schemas import HealthResponse

__all__ = [
    "ErrorResponse",
    "GoogleUserInfo",
    "HealthResponse",
    "LoginResponse",
    "SessionData",
    "UserResponse",
]
