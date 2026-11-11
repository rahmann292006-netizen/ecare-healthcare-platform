"""Authentication API tests.

Tests use the real PostgreSQL database via the DATABASE_URL environment
variable. All database changes are rolled back after each test using an
isolated connection and transaction, so no data persists between tests.

No credentials or tokens are printed or logged.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from tests.database_guard import require_test_database

require_test_database()

from app.main import app  # noqa: E402
from app.database import get_db  # noqa: E402
from app.database import Base  # noqa: E402
from app.auth import (  # noqa: E402
    create_access_token,
    decode_access_token,
    ALGORITHM,
)
from app.models import Hospital, User  # noqa: E402


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create a transactional SQLAlchemy session with all tables created.

    Tables are created within the transaction and rolled back after the test.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set")

    engine = create_engine(database_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    # Create all tables within the transaction; rolled back after the test.
    Base.metadata.create_all(connection)
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a TestClient sharing the same test transaction as db_session."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


REGISTER_PAYLOAD = {
    "email": "newuser@example.com",
    "full_name": "New User",
    "password": "securePass123",
}

REGISTER_WITH_PROVIDER_ROLE = {
    "email": "provider-via-register@example.com",
    "full_name": "Should Be Patient",
    "password": "securePass123",
    "role": "provider",
}

REGISTER_WITH_ADMIN_ROLE = {
    "email": "admin-via-register@example.com",
    "full_name": "Should Be Patient",
    "password": "securePass123",
    "role": "admin",
}


def _register(client: TestClient, payload: dict = None):
    return client.post("/api/v1/auth/register", json=payload or REGISTER_PAYLOAD)


def _login_json(client: TestClient, email: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# Registration tests — public registration always creates patient
# ---------------------------------------------------------------------------

def test_register_success(client: TestClient):
    """POST /auth/register creates a user and returns it without password."""
    response = _register(client)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == REGISTER_PAYLOAD["email"]
    assert data["full_name"] == REGISTER_PAYLOAD["full_name"]
    assert data["role"] == "patient"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data
    assert "hashed_password" not in data
    assert "created_at" in data
    assert "updated_at" in data


def test_register_client_supplied_provider_role_is_ignored(client: TestClient):
    """Public registration cannot create a provider account even if role=provider is sent."""
    response = _register(client, REGISTER_WITH_PROVIDER_ROLE)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == REGISTER_WITH_PROVIDER_ROLE["email"]
    assert data["role"] == "patient", "Public registration must force patient role"


def test_register_client_supplied_admin_role_is_ignored(client: TestClient):
    """Public registration cannot create an admin account even if role=admin is sent."""
    response = _register(client, REGISTER_WITH_ADMIN_ROLE)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == REGISTER_WITH_ADMIN_ROLE["email"]
    assert data["role"] == "patient", "Public registration must force patient role"


def test_register_default_role_is_patient(client: TestClient):
    """Registration without a role defaults to patient."""
    response = _register(client)
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "patient"


def test_register_duplicate_email(client: TestClient):
    """POST /auth/register with existing email returns 409."""
    _register(client)
    response = _register(client)
    assert response.status_code == 409, response.text


def test_register_password_too_short(client: TestClient):
    """POST /auth/register with short password returns 422."""
    payload = {**REGISTER_PAYLOAD, "password": "short"}
    response = _register(client, payload)
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Provisioning tests — admin only can create provider/admin accounts
# ---------------------------------------------------------------------------

def _create_admin(db_session: Session) -> User:
    """Helper to create an admin user directly in the test transaction."""
    admin = User(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="fakehash",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.flush()
    return admin


def _admin_token(admin_email: str = "admin@example.com") -> str:
    return create_access_token(subject=admin_email)


def test_provision_requires_admin_role(client: TestClient, db_session: Session):
    """POST /auth/provision without admin role returns 403."""
    patient = User(
        email="patient@example.com",
        full_name="Patient User",
        hashed_password="fakehash",
        role="patient",
        is_active=True,
    )
    db_session.add(patient)
    db_session.flush()
    token = create_access_token(subject="patient@example.com")

    response = client.post(
        "/api/v1/auth/provision",
        json={
            "email": "newprovider@example.com",
            "full_name": "New Provider",
            "password": "securePass123",
            "role": "provider",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403, response.text


def test_provision_admin_can_create_provider(client: TestClient, db_session: Session):
    """POST /auth/provision with admin token can create a provider account."""
    _create_admin(db_session)
    token = _admin_token()

    response = client.post(
        "/api/v1/auth/provision",
        json={
            "email": "newprovider@example.com",
            "full_name": "New Provider",
            "password": "securePass123",
            "role": "provider",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "newprovider@example.com"
    assert data["role"] == "provider"


def test_provision_admin_can_create_admin(client: TestClient, db_session: Session):
    """POST /auth/provision with admin token can create another admin account."""
    _create_admin(db_session)
    token = _admin_token()

    response = client.post(
        "/api/v1/auth/provision",
        json={
            "email": "newadmin@example.com",
            "full_name": "New Admin",
            "password": "securePass123",
            "role": "admin",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == "newadmin@example.com"
    assert data["role"] == "admin"


def test_provision_requires_authentication(client: TestClient):
    """POST /auth/provision without a token returns 401."""
    response = client.post(
        "/api/v1/auth/provision",
        json={
            "email": "newprovider@example.com",
            "full_name": "New Provider",
            "password": "securePass123",
            "role": "provider",
        },
    )
    assert response.status_code == 401, response.text


def test_provision_duplicate_email(client: TestClient, db_session: Session):
    """POST /auth/provision with existing email returns 409."""
    _create_admin(db_session)
    token = _admin_token()
    existing = User(
        email="dup@example.com",
        full_name="Dup User",
        hashed_password="fakehash",
        role="patient",
        is_active=True,
    )
    db_session.add(existing)
    db_session.flush()

    response = client.post(
        "/api/v1/auth/provision",
        json={
            "email": "dup@example.com",
            "full_name": "Dup User",
            "password": "securePass123",
            "role": "patient",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409, response.text


def test_dev_header_cannot_authorize_directory_write_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ECARE_ENVIRONMENT", "production")
    monkeypatch.setenv("ECARE_DEV_MODE", "true")
    response = client.post(
        "/api/v1/hospitals",
        json={"name": "Blocked Test Listing", "address": "Test address"},
        headers={"X-Ecare-Dev-Mode": "true"},
    )
    assert response.status_code == 403


def test_admin_can_write_directory_listing_outside_development(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ECARE_ENVIRONMENT", "production")
    monkeypatch.setenv("ECARE_DEV_MODE", "false")
    admin = _create_admin(db_session)
    response = client.post(
        "/api/v1/hospitals",
        json={"name": "Admin Test Listing", "address": "Test address"},
        headers={"Authorization": f"Bearer {_admin_token(admin.email)}"},
    )
    assert response.status_code == 201
    assert response.json()["verification_status"] == "unverified"
    assert db_session.query(Hospital).filter_by(name="Admin Test Listing").one()


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

def test_login_valid_credentials(client: TestClient):
    """POST /auth/login with valid credentials returns a token."""
    _register(client)
    response = _login_json(client, REGISTER_PAYLOAD["email"], REGISTER_PAYLOAD["password"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient):
    """POST /auth/login with wrong password returns 401."""
    _register(client)
    response = _login_json(client, REGISTER_PAYLOAD["email"], "wrongPassword123")
    assert response.status_code == 401, response.text


def test_login_nonexistent_email(client: TestClient):
    """POST /auth/login with unknown email returns 401."""
    response = _login_json(client, "nonexistent@example.com", "securePass123")
    assert response.status_code == 401, response.text


def test_login_inactive_user(client: TestClient, db_session: Session):
    """Login fails for an inactive user (data created within test transaction)."""
    from app.auth import hash_password

    inactive = User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password=hash_password("securePass123"),
        role="patient",
        is_active=False,
    )
    db_session.add(inactive)
    db_session.flush()

    response = _login_json(client, "inactive@example.com", "securePass123")
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# Current user tests
# ---------------------------------------------------------------------------

def test_get_me_authenticated(client: TestClient):
    """GET /auth/me with valid Bearer token returns the user."""
    reg_resp = _register(client)
    user_id = reg_resp.json()["id"]
    login_resp = _login_json(client, REGISTER_PAYLOAD["email"], REGISTER_PAYLOAD["password"])
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == REGISTER_PAYLOAD["email"]


def test_get_me_no_token(client: TestClient):
    """GET /auth/me without a token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401, response.text


def test_get_me_invalid_token(client: TestClient):
    """GET /auth/me with an invalid token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401, response.text


# ---------------------------------------------------------------------------
# Token tests — hashing, expiration, signature
# ---------------------------------------------------------------------------

def test_password_hashing_is_secure():
    """Passwords are hashed with bcrypt and never match plaintext."""
    from app.auth import hash_password, verify_password

    hashed = hash_password("securePass123")
    assert hashed != "securePass123"
    assert len(hashed) == 60  # bcrypt hash length
    assert verify_password("securePass123", hashed) is True
    assert verify_password("wrongPassword", hashed) is False


def test_access_token_encodes_correct_email():
    """create_access_token produces a token decodable to the subject email."""
    token = create_access_token("roleuser@example.com")
    assert decode_access_token(token) == "roleuser@example.com"


def test_access_token_expires():
    """A token with a negative expiry is rejected as expired."""
    expired_token = create_access_token(
        "expired@example.com",
        expires_delta=timedelta(minutes=-1),
    )
    assert decode_access_token(expired_token) is None


def test_access_token_invalid_signature_is_rejected():
    """A token signed with a different secret key fails verification."""
    tampered_token = jwt.encode(
        {"sub": "tampered@example.com", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
        "wrong-secret-key-that-is-not-the-real-one",
        algorithm=ALGORITHM,
    )
    assert decode_access_token(tampered_token) is None


def test_access_token_malformed_is_rejected():
    """A malformed token string fails verification."""
    assert decode_access_token("not.a.valid.token") is None
    assert decode_access_token("") is None