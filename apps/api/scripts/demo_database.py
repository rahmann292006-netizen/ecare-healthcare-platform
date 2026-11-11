"""Helpers for tooling restricted to the local ecare_test database."""

from __future__ import annotations

import ipaddress
import os
from pathlib import Path
import sys

from sqlalchemy import Engine
from sqlalchemy.engine import URL, make_url

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.database_safety import require_test_target

DEMO_TEST_REVISION = "d9f3a761c482"


def read_configured_database_url() -> str:
    """Use a process-provided URL without reading local configuration files."""
    configured = os.environ.get("DATABASE_URL")
    if not configured:
        raise RuntimeError("DATABASE_URL must be provided in the process environment")
    return configured


def build_test_database_url(configured_url: str) -> URL:
    """Preserve the configured PostgreSQL role/password but force the safe target."""
    try:
        source = make_url(configured_url)
    except Exception:
        raise ValueError("Configured database URL could not be parsed") from None
    if source.get_backend_name() != "postgresql" or not source.username:
        raise ValueError("Configured URL must identify a PostgreSQL role")

    target = URL.create(
        drivername=source.drivername,
        username=source.username,
        password=source.password,
        host="127.0.0.1",
        port=5432,
        database="ecare_test",
    )
    require_test_target(target.render_as_string(hide_password=False), "test")
    if (target.host, target.port, target.database) != ("127.0.0.1", 5432, "ecare_test"):
        raise ValueError("Configured URL did not resolve to the required test target")
    return target


def configure_test_environment(target: URL) -> None:
    """Set only process-local settings before importing the application database."""
    os.environ["DATABASE_URL"] = target.render_as_string(hide_password=False)
    os.environ["ECARE_DATABASE_ENV"] = "test"
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["PYTHONPATH"] = str(API_ROOT)


def verify_test_database(engine: Engine, expected_user: str) -> str:
    """Verify the actual server identity and expected already-applied schema."""
    with engine.connect() as connection:
        database, user, address, port = connection.exec_driver_sql(
            "SELECT current_database(), current_user, "
            "inet_server_addr()::text, inet_server_port()"
        ).one()
        if database != "ecare_test":
            raise RuntimeError("Connected database is not ecare_test; operation stopped")
        if user != expected_user:
            raise RuntimeError("Connected PostgreSQL role does not match the configured role")
        if not address or int(port) != 5432:
            raise RuntimeError("Connected PostgreSQL server is not on port 5432")
        try:
            host = ipaddress.ip_interface(address).ip
        except ValueError:
            raise RuntimeError("Connected PostgreSQL server address could not be verified") from None
        if not host.is_loopback:
            raise RuntimeError("Connected PostgreSQL server is not loopback; operation stopped")

        revisions = [
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).all()
        ]
    if revisions != [DEMO_TEST_REVISION]:
        raise RuntimeError(
            "ecare_test schema revision is not the expected demo revision; "
            "no migration was attempted"
        )
    return revisions[0]
