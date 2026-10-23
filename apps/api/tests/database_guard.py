"""Safety guard for tests that use DATABASE_URL."""

import os

import pytest
from sqlalchemy.engine import make_url


def require_test_database() -> None:
    """Abort test collection unless DATABASE_URL names a *_test database."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise pytest.UsageError(
            "Refusing to run API tests: DATABASE_URL must target a database "
            "whose name ends with '_test'."
        )

    try:
        database_name = make_url(database_url).database
    except Exception:
        database_name = None

    if not database_name or not database_name.endswith("_test"):
        raise pytest.UsageError(
            "Refusing to run API tests: DATABASE_URL must target a database "
            "whose name ends with '_test'."
        )
