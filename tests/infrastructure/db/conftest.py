"""Shared fixtures for database tests."""

from collections.abc import Generator

import pytest
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import create_engine


@pytest.fixture
def db_session() -> Generator[Session]:
    """Create an in-memory SQLite session for testing.

    Yields:
        SQLModel Session backed by in-memory SQLite.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
