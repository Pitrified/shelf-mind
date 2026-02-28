"""SQLModel database engine and session management."""

from collections.abc import Generator

from loguru import logger as lg
from sqlalchemy import Engine
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine

# Module-level engine reference, initialized via create_db_engine()
_engine = None


def create_db_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create and store the global SQLModel engine.

    Args:
        database_url: Database connection string (e.g. sqlite:///data/shelf_mind.db).
        echo: Whether to echo SQL statements.

    Returns:
        The SQLAlchemy engine.
    """
    global _engine  # noqa: PLW0603
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(database_url, echo=echo, connect_args=connect_args)
    lg.info(f"Database engine created: {database_url}")
    return _engine


def get_engine() -> Engine:
    """Return the current engine (must call create_db_engine first).

    Returns:
        The SQLAlchemy engine.

    Raises:
        RuntimeError: If engine has not been initialized.
    """
    if _engine is None:
        msg = "Database engine not initialized. Call create_db_engine() first."
        raise RuntimeError(msg)
    return _engine


def init_db() -> None:
    """Create all tables defined by SQLModel metadata.

    Must be called after create_db_engine().
    """
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    lg.info("Database tables created")


def get_session() -> Generator[Session]:
    """Yield a Session scoped to a single unit of work.

    Yields:
        SQLModel Session.
    """
    engine = get_engine()
    with Session(engine) as session:
        yield session
