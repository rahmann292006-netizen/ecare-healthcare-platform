import pytest

from app.database_safety import require_alembic_test_target


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://localhost/ecare_test",
        "postgresql+psycopg://127.0.0.1/ecare_test",
        "postgresql+psycopg://[::1]/ecare_test",
    ],
)
def test_alembic_accepts_loopback_postgresql_test_targets(url):
    assert require_alembic_test_target(url, "test") == "ecare_test"


@pytest.mark.parametrize(
    "url,environment",
    [
        (None, "test"),
        ("not-a-database-url", "test"),
        ("sqlite:///ecare_test", "test"),
        ("postgresql+psycopg://localhost/ecare", "test"),
        ("postgresql+psycopg://localhost/ecare_prod_test", "test"),
        ("postgresql+psycopg://db.example/ecare_test", "test"),
        ("postgresql+psycopg:///ecare_test", "test"),
        ("postgresql+psycopg://localhost/ecare_test", None),
        ("postgresql+psycopg://localhost/ecare_test", "TEST"),
        ("postgresql+psycopg://localhost/ecare_test", "production"),
    ],
)
def test_alembic_rejects_unsafe_or_missing_targets(url, environment):
    with pytest.raises(ValueError):
        require_alembic_test_target(url, environment)


def test_alembic_rejection_does_not_expose_database_credentials():
    url = "postgresql+psycopg://test-user:top-secret@db.example/ecare_test"

    with pytest.raises(ValueError) as error:
        require_alembic_test_target(url, "test")

    assert "top-secret" not in str(error.value)
    assert "test-user" not in str(error.value)
