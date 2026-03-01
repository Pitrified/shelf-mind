"""Authentication service for Google OAuth and session management."""

from datetime import UTC
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlencode

import httpx
from loguru import logger as lg

from shelf_mind.config.webapp import GoogleOAuthConfig
from shelf_mind.config.webapp import SessionConfig
from shelf_mind.webapp.core.security import generate_session_id
from shelf_mind.webapp.core.security import generate_state_token
from shelf_mind.webapp.core.security import get_expiration_time
from shelf_mind.webapp.core.security import is_expired
from shelf_mind.webapp.schemas.auth_schemas import GoogleUserInfo
from shelf_mind.webapp.schemas.auth_schemas import SessionData

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class SessionStore:
    """In-memory session storage.

    Suitable for development and testing. For production, use
    SqliteSessionStore for persistent sessions.
    """

    def __init__(self) -> None:
        """Initialize empty session store."""
        self._sessions: dict[str, SessionData] = {}
        self._state_tokens: dict[str, datetime] = {}

    def create_session(self, session_data: SessionData) -> None:
        """Store a new session.

        Args:
            session_data: Session data to store.
        """
        self._sessions[session_data.session_id] = session_data
        lg.debug(f"Created session for user {session_data.email}")

    def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve a session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            SessionData if found and not expired, None otherwise.
        """
        session = self._sessions.get(session_id)
        if session and is_expired(session.expires_at):
            self.delete_session(session_id)
            return None
        return session

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session identifier to delete.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            lg.debug(f"Deleted session {session_id[:8]}...")

    def store_state_token(self, state: str, ttl_seconds: int = 600) -> None:
        """Store OAuth state token for CSRF protection.

        Args:
            state: State token to store.
            ttl_seconds: Time-to-live in seconds.
        """
        self._state_tokens[state] = get_expiration_time(ttl_seconds)

    def validate_state_token(self, state: str) -> bool:
        """Validate and consume a state token.

        Args:
            state: State token to validate.

        Returns:
            True if valid, False otherwise.
        """
        expiration = self._state_tokens.pop(state, None)
        if expiration is None:
            return False
        return not is_expired(expiration)

    def cleanup_expired(self) -> int:
        """Remove expired sessions and state tokens.

        Returns:
            Number of removed items.
        """
        now = datetime.now(UTC)
        removed = 0

        # Cleanup sessions
        expired_sessions = [
            sid for sid, data in self._sessions.items() if is_expired(data.expires_at)
        ]
        for sid in expired_sessions:
            del self._sessions[sid]
            removed += 1

        # Cleanup state tokens
        expired_states = [
            state for state, exp in self._state_tokens.items() if now > exp
        ]
        for state in expired_states:
            del self._state_tokens[state]
            removed += 1

        if removed > 0:
            lg.debug(f"Cleaned up {removed} expired sessions/tokens")

        return removed


class SqliteSessionStore(SessionStore):
    """SQLite-backed session storage for persistent sessions across restarts.

    Extends SessionStore to persist sessions in a SQLite database file
    while keeping the same API. State tokens remain in-memory since they
    are short-lived.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str = "data/sessions.db") -> None:
        """Initialize with database path.

        Args:
            db_path: Path to the SQLite database file.
        """
        super().__init__()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection.

        Returns:
            SQLite connection.
        """
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        """Create the sessions table if it does not exist."""
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """,
            )
            conn.commit()

    def create_session(self, session_data: SessionData) -> None:
        """Store a new session in SQLite.

        Args:
            session_data: Session data to store.
        """
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, data, expires_at) "
                "VALUES (?, ?, ?)",
                (
                    session_data.session_id,
                    session_data.model_dump_json(),
                    session_data.expires_at.isoformat(),
                ),
            )
            conn.commit()
        lg.debug(f"Created persistent session for user {session_data.email}")

    def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve a session by ID from SQLite.

        Args:
            session_id: Session identifier.

        Returns:
            SessionData if found and not expired, None otherwise.
        """
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        data_json, expires_at_str = row
        expires_at = datetime.fromisoformat(expires_at_str)

        if is_expired(expires_at):
            self.delete_session(session_id)
            return None

        return SessionData(**json.loads(data_json))

    def delete_session(self, session_id: str) -> None:
        """Delete a session from SQLite.

        Args:
            session_id: Session identifier to delete.
        """
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
        lg.debug(f"Deleted persistent session {session_id[:8]}...")

    def cleanup_expired(self) -> int:
        """Remove expired sessions from SQLite and state tokens from memory.

        Returns:
            Number of removed items.
        """
        now_iso = datetime.now(UTC).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (now_iso,),
            )
            removed = cursor.rowcount
            conn.commit()

        # Also clean up in-memory state tokens
        now = datetime.now(UTC)
        expired_states = [
            state for state, exp in self._state_tokens.items() if now > exp
        ]
        for state in expired_states:
            del self._state_tokens[state]
            removed += 1

        if removed > 0:
            lg.debug(f"Cleaned up {removed} expired sessions/tokens")

        return removed


class GoogleAuthService:
    """Service for Google OAuth 2.0 authentication."""

    def __init__(
        self,
        oauth_config: GoogleOAuthConfig,
        session_config: SessionConfig,
        session_store: SessionStore,
    ) -> None:
        """Initialize auth service.

        Args:
            oauth_config: Google OAuth configuration.
            session_config: Session configuration.
            session_store: Session storage instance.
        """
        self.oauth_config = oauth_config
        self.session_config = session_config
        self.session_store = session_store

    def get_authorization_url(self) -> tuple[str, str]:
        """Generate Google OAuth authorization URL.

        Returns:
            Tuple of (authorization_url, state_token).
        """
        state = generate_state_token()
        self.session_store.store_state_token(state)

        params = {
            "client_id": self.oauth_config.client_id,
            "redirect_uri": self.oauth_config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.oauth_config.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }

        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return auth_url, state

    def validate_state(self, state: str) -> bool:
        """Validate OAuth state parameter.

        Args:
            state: State token from callback.

        Returns:
            True if valid, False otherwise.
        """
        return self.session_store.validate_state_token(state)

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from Google.

        Returns:
            Token response dictionary.

        Raises:
            httpx.HTTPStatusError: If token exchange fails.
        """
        data = {
            "client_id": self.oauth_config.client_id,
            "client_secret": self.oauth_config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.oauth_config.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user information from Google.

        Args:
            access_token: Google access token.

        Returns:
            GoogleUserInfo with user details.

        Raises:
            httpx.HTTPStatusError: If API call fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return GoogleUserInfo(**response.json())

    async def authenticate(self, code: str, state: str) -> SessionData:
        """Complete authentication flow.

        Args:
            code: Authorization code from Google.
            state: State parameter for CSRF validation.

        Returns:
            SessionData for the authenticated user.

        Raises:
            ValueError: If state validation fails.
            httpx.HTTPStatusError: If OAuth flow fails.
        """
        # Validate state
        if not self.validate_state(state):
            msg = "Invalid state parameter"
            raise ValueError(msg)

        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(code)
        access_token = tokens["access_token"]

        # Get user info
        user_info = await self.get_user_info(access_token)

        # Create session
        session = self.create_session(user_info)

        return session

    def create_session(self, user_info: GoogleUserInfo) -> SessionData:
        """Create a new session for authenticated user.

        Args:
            user_info: Google user information.

        Returns:
            SessionData for the new session.
        """
        now = datetime.now(UTC)
        session = SessionData(
            session_id=generate_session_id(),
            user_id=user_info.sub,
            email=user_info.email,
            name=user_info.name,
            picture=user_info.picture,
            created_at=now,
            expires_at=get_expiration_time(self.session_config.max_age),
        )

        self.session_store.create_session(session)
        lg.info(f"User {user_info.email} authenticated successfully")

        return session

    def get_session(self, session_id: str) -> SessionData | None:
        """Get session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            SessionData if valid session exists.
        """
        return self.session_store.get_session(session_id)

    def revoke_session(self, session_id: str) -> None:
        """Revoke a session.

        Args:
            session_id: Session identifier to revoke.
        """
        self.session_store.delete_session(session_id)
