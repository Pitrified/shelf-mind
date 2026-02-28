"""Custom HTTP exceptions for the webapp."""

from fastapi import HTTPException
from fastapi import status


class NotAuthenticatedException(HTTPException):
    """Raised when authentication is required but not provided."""

    def __init__(self, detail: str = "Not authenticated") -> None:
        """Initialize exception.

        Args:
            detail: Error detail message.
        """
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class NotAuthorizedException(HTTPException):
    """Raised when user lacks permission for the requested action."""

    def __init__(self, detail: str = "Not authorized") -> None:
        """Initialize exception.

        Args:
            detail: Error detail message.
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class RateLimitExceededException(HTTPException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        """Initialize exception.

        Args:
            detail: Error detail message.
            retry_after: Seconds until rate limit resets.
        """
        headers = {}
        if retry_after is not None:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers or None,
        )


class ValidationException(HTTPException):
    """Raised when request validation fails."""

    def __init__(
        self,
        detail: str = "Validation error",
        errors: list[dict] | None = None,
    ) -> None:
        """Initialize exception.

        Args:
            detail: Error detail message.
            errors: List of validation error details.
        """
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": detail, "errors": errors or []},
        )


class ServiceUnavailableException(HTTPException):
    """Raised when a required service is unavailable."""

    def __init__(self, detail: str = "Service unavailable") -> None:
        """Initialize exception.

        Args:
            detail: Error detail message.
        """
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
