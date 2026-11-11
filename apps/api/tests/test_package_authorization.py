"""Authorization tests for health checkup package write endpoints."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import (
    Package,
    PackageInclusion,
    Subscription,
    SubscriptionEvent,
    User,
)

PACKAGE_PAYLOAD = {
    "name": "Annual Health Check",
    "provider_name": "Example Clinic",
    "price": 1000,
}

WRITE_REQUESTS = [
    ("POST", "/api/v1/packages", PACKAGE_PAYLOAD, 201),
    ("PATCH", "/api/v1/packages/1", {"description": "Updated description"}, 200),
    ("DELETE", "/api/v1/packages/1", None, 204),
]


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Package.__table__,
            PackageInclusion.__table__,
            Subscription.__table__,
            SubscriptionEvent.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def _create_user(db_session: Session, role: str) -> str:
    email = f"{role}@example.com"
    db_session.add(
        User(
            email=email,
            full_name=role.title(),
            hashed_password="not-used-in-this-test",
            role=role,
        )
    )
    db_session.commit()
    return create_access_token(email)


def _seed_package(db_session: Session) -> None:
    db_session.add(
        Package(
            name="Existing Package",
            slug="existing-package",
            provider_name="Example Clinic",
            price=1000,
        )
    )
    db_session.commit()


def _write_request(
    client: TestClient,
    method: str,
    path: str,
    payload: dict | None,
    headers: dict[str, str],
):
    kwargs = {"headers": headers}
    if payload is not None:
        kwargs["json"] = payload
    return client.request(method, path, **kwargs)


@pytest.mark.parametrize(
    ("method", "path", "payload", "_success_status"),
    WRITE_REQUESTS,
)
def test_package_writes_reject_dev_header_without_authentication(
    client: TestClient,
    method: str,
    path: str,
    payload: dict | None,
    _success_status: int,
):
    response = _write_request(
        client,
        method,
        path,
        payload,
        {"X-Ecare-Dev-Mode": "true"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "payload", "_success_status"),
    WRITE_REQUESTS,
)
def test_package_writes_reject_non_admin_users(
    client: TestClient,
    db_session: Session,
    method: str,
    path: str,
    payload: dict | None,
    _success_status: int,
):
    _seed_package(db_session)
    token = _create_user(db_session, "patient")

    response = _write_request(
        client,
        method,
        path,
        payload,
        {
            "Authorization": f"Bearer {token}",
            "X-Ecare-Dev-Mode": "true",
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "path", "payload", "success_status"),
    WRITE_REQUESTS,
)
def test_package_writes_allow_admin_users(
    client: TestClient,
    db_session: Session,
    method: str,
    path: str,
    payload: dict | None,
    success_status: int,
):
    _seed_package(db_session)
    token = _create_user(db_session, "admin")

    response = _write_request(
        client,
        method,
        path,
        payload,
        {"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == success_status
