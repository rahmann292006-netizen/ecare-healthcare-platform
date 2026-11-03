"""Tests for database configuration and session management.

No credentials are printed or logged.
"""

import os
from tests.database_guard import require_test_database  # noqa: E402

require_test_database()

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.models import Hospital, Doctor, DiagnosticLab, DiagnosticTest  # noqa: E402


def test_database_url_configured():
    """DATABASE_URL is set in the environment."""
    assert os.environ.get("DATABASE_URL"), "DATABASE_URL must be set"


def test_engine_created():
    """SQLAlchemy engine is created without exposing the URL."""
    assert engine is not None
    # Verify the URL is not printed - just check the engine exists
    assert str(engine.url).startswith("postgresql")


def test_session_local_created():
    """SessionLocal factory is created."""
    assert SessionLocal is not None


def test_base_metadata_has_tables():
    """Base.metadata contains all four model tables."""
    table_names = set(Base.metadata.tables.keys())
    expected = {"hospitals", "doctors", "diagnostic_labs", "diagnostic_tests"}
    assert expected.issubset(table_names)


def test_all_models_inherit_from_base():
    """All model classes inherit from SQLAlchemy Base."""
    for model in [Hospital, Doctor, DiagnosticLab, DiagnosticTest]:
        assert issubclass(model, Base)
