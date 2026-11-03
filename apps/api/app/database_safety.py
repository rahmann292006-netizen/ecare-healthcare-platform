"""Fail-closed classification of database targets used by offline tools/tests."""

from __future__ import annotations

from sqlalchemy.engine import make_url


LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
PRODUCTION_LIKE_NAME_PARTS = {"prod", "production", "stage", "staging"}
DEVELOPMENT_NAMES = {"ecare", "ecare_dev", "ecare_development"}


def parse_database_target(database_url: str | None) -> tuple[str, str]:
    """Return database name and normalized host without exposing parse errors."""
    try:
        url = make_url(database_url) if database_url else None
        name = url.database if url else None
        host = url.host if url else None
        backend = url.get_backend_name() if url else None
    except Exception:
        name = host = backend = None
    if backend != "postgresql" or not name or not host:
        raise ValueError("Database target is missing or cannot be classified") from None
    return name, host.rstrip(".").casefold()


def require_test_target(database_url: str | None, environment: str | None) -> str:
    """Accept only explicitly marked test databases on a loopback host."""
    name, host = parse_database_target(database_url)
    folded_name = name.casefold()
    parts = set(folded_name.replace("-", "_").split("_"))
    if (
        (environment or "").casefold() != "test"
        or not folded_name.endswith("_test")
        or host not in LOOPBACK_HOSTS
        or folded_name in DEVELOPMENT_NAMES
        or parts & PRODUCTION_LIKE_NAME_PARTS
    ):
        raise ValueError("Database target is not classified as a safe test database") from None
    return name


def require_import_target(
    database_url: str | None,
    environment: str | None,
    *,
    allow_non_test: bool = False,
    confirmation: str | None = None,
) -> str:
    """Require a safe test target or deliberate, confirmed non-test opt-in."""
    name, host = parse_database_target(database_url)
    if name.casefold().endswith("_test"):
        # The override can never relax the host/environment requirements for tests.
        return require_test_target(database_url, environment)

    folded_name = name.casefold()
    parts = set(folded_name.replace("-", "_").split("_"))
    if folded_name in DEVELOPMENT_NAMES or parts & {"dev", "development"}:
        raise ValueError("Provider import into a development database is refused") from None
    if not allow_non_test:
        raise ValueError("Non-test import requires explicit opt-in and confirmation") from None
    if (
        (environment or "").casefold() not in {"staging", "production"}
        or host in LOOPBACK_HOSTS
        or confirmation != name
    ):
        raise ValueError("Non-test database target is not explicitly classified and confirmed") from None
    return name
