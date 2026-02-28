"""Security utilities for the webapp.

Provides token generation, CSRF protection, and input sanitization.
"""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
import hashlib
import html
import secrets

from itsdangerous import BadSignature
from itsdangerous import SignatureExpired
from itsdangerous import URLSafeTimedSerializer


class TokenManager:
    """Manages secure token generation and validation."""

    def __init__(self, secret_key: str) -> None:
        """Initialize token manager.

        Args:
            secret_key: Secret key for signing tokens.
        """
        self.secret_key = secret_key
        self.serializer = URLSafeTimedSerializer(secret_key)

    def generate_token(self, data: str, salt: str = "default") -> str:
        """Generate a signed token.

        Args:
            data: Data to encode in the token.
            salt: Salt for token generation (different salts for different uses).

        Returns:
            Signed token string.
        """
        return self.serializer.dumps(data, salt=salt)

    def validate_token(
        self,
        token: str,
        salt: str = "default",
        max_age: int = 3600,
    ) -> str | None:
        """Validate and decode a signed token.

        Args:
            token: Token to validate.
            salt: Salt used during generation.
            max_age: Maximum age of token in seconds.

        Returns:
            Decoded data or None if invalid/expired.
        """
        try:
            return self.serializer.loads(token, salt=salt, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None

    def generate_csrf_token(self) -> str:
        """Generate a CSRF token.

        Returns:
            CSRF token string.
        """
        return self.generate_token(secrets.token_hex(16), salt="csrf")

    def validate_csrf_token(self, token: str, max_age: int = 3600) -> bool:
        """Validate a CSRF token.

        Args:
            token: CSRF token to validate.
            max_age: Maximum age in seconds.

        Returns:
            True if valid, False otherwise.
        """
        return self.validate_token(token, salt="csrf", max_age=max_age) is not None


def generate_session_id() -> str:
    """Generate a secure random session ID.

    Returns:
        64-character hex string.
    """
    return secrets.token_hex(32)


def generate_state_token() -> str:
    """Generate a state token for OAuth flows.

    Returns:
        32-character hex string.
    """
    return secrets.token_hex(16)


def hash_token(token: str) -> str:
    """Hash a token for storage.

    Args:
        token: Token to hash.

    Returns:
        SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def sanitize_html(text: str) -> str:
    """Sanitize text by escaping HTML entities.

    Args:
        text: Text to sanitize.

    Returns:
        Sanitized text with HTML entities escaped.
    """
    return html.escape(text)


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize string values in a dictionary.

    Args:
        data: Dictionary to sanitize.

    Returns:
        Sanitized dictionary.
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_html(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_html(item) if isinstance(item, str) else item for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def get_expiration_time(seconds: int) -> datetime:
    """Get expiration datetime from now.

    Args:
        seconds: Number of seconds until expiration.

    Returns:
        Datetime of expiration in UTC.
    """
    return datetime.now(UTC) + timedelta(seconds=seconds)


def is_expired(expiration: datetime) -> bool:
    """Check if a datetime has passed.

    Args:
        expiration: Expiration datetime to check.

    Returns:
        True if expired, False otherwise.
    """
    return datetime.now(UTC) > expiration
