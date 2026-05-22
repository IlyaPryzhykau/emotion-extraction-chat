"""Test fixtures.

Tests run against a real Postgres (the same engine features we use in prod —
UUID, native enums, a dedicated schema — can't be faithfully mocked). Each test
runs inside a transaction that is rolled back afterwards, so nothing persists and
tests don't interfere with each other. ``join_transaction_mode="create_savepoint"``
lets the app's own ``commit()`` calls run as savepoints within that outer
transaction.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.main import app

# Defaults to the local dev Postgres exposed by docker-compose on 5439.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5439/emotions",
)

_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture
def db_session() -> Iterator[Session]:
    """A session wrapped in a transaction that is rolled back after the test."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient whose DB dependency is bound to the rolled-back session."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
