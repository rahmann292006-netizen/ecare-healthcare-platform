"""Safety guard for tests that use DATABASE_URL."""

import os

import pytest
from app.database_safety import require_test_target


def require_test_database() -> None:
    """Abort test collection unless the target is explicitly a local test DB."""
    try:
        require_test_target(
            os.environ.get("DATABASE_URL"),
            os.environ.get("ECARE_DATABASE_ENV"),
        )
    except ValueError:
        raise pytest.UsageError(
            "Refusing to run API tests: set ECARE_DATABASE_ENV=test and use a PostgreSQL "
            "database ending in '_test' on localhost or a loopback address."
        ) from None
