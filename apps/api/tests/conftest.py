"""Pytest configuration and fixtures for eCare API tests."""

import os

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from tests.database_guard import require_test_database  # noqa: E402

require_test_database()

from app.database import Base  # noqa: E402


@pytest.fixture(scope="session")
def db_engine():
    """Create a SQLAlchemy engine connected to the test database.

    Uses process-scoped DATABASE_URL. No credentials are logged.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Create a transactional SQLAlchemy session for a test.

    Rolls back all changes after the test completes so tests do not
    leave data in the database.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
