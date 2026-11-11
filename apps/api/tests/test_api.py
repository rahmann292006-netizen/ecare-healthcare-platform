"""Integration tests for eCare API endpoints.

Tests use the real PostgreSQL database via the DATABASE_URL environment
variable. All database changes are rolled back after each test using an
isolated connection and transaction, so no data persists between tests.

No credentials are printed or logged.
"""

import os
from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from tests.database_guard import require_test_database  # noqa: E402

require_test_database()

from app.main import app  # noqa: E402
from app.database import get_db  # noqa: E402


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a TestClient with an isolated database transaction per test.

    Each test gets its own database connection and transaction. All changes
    are rolled back when the test completes, ensuring test isolation without
    persisting data to the actual database.
    """
    monkeypatch.setenv("ECARE_ENVIRONMENT", "test")
    monkeypatch.setenv("ECARE_DEV_MODE", "true")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set")

    engine = create_engine(database_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()

    def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

def test_health_endpoint(client: TestClient):
    """GET /health returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_endpoint(client: TestClient):
    """GET /health/db returns database ok."""
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


# ---------------------------------------------------------------------------
# Hospital API tests
# ---------------------------------------------------------------------------

TEST_MARKER = uuid4().hex

HOSPITAL_PAYLOAD = {
    "name": f"eCare Test Hospital {TEST_MARKER}",
    "address": "123 Station Road, Raichur",
    "locality": "Station Area",
    "hospital_type": "General",
    "phone": "08532-123456",
    "emergency_services": True,
}


def _auth_headers(dev_mode: bool = False):
    headers = {}
    if dev_mode:
        headers["X-Ecare-Dev-Mode"] = "true"
    return headers


def test_create_hospital_unauthorized(client: TestClient):
    """POST /hospitals without dev mode returns 403."""
    response = client.post("/api/v1/hospitals", json=HOSPITAL_PAYLOAD)
    assert response.status_code == 403


def test_create_hospital_authorized(client: TestClient):
    """POST /hospitals with dev mode returns 201 and unverified status."""
    response = client.post(
        "/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == HOSPITAL_PAYLOAD["name"]
    assert data["slug"] == HOSPITAL_PAYLOAD["name"].lower().replace(" ", "-")
    assert data["verification_status"] == "unverified"
    assert data["is_active"] is True
    assert data["operational_status"] == "unknown"
    assert data["id"] is not None


@pytest.mark.parametrize(
    "operational_status,emergency_services",
    [("unknown", None), ("operational", True), ("not_operational", False)],
)
def test_hospital_status_and_emergency_unknown_are_returned(
    client: TestClient, operational_status, emergency_services
):
    payload = {
        **HOSPITAL_PAYLOAD,
        "name": f"Status Hospital {operational_status}",
        "operational_status": operational_status,
        "emergency_services": emergency_services,
    }
    response = client.post(
        "/api/v1/hospitals", json=payload, headers=_auth_headers(True)
    )

    assert response.status_code == 201
    assert response.json()["operational_status"] == operational_status
    assert response.json()["emergency_services"] is emergency_services


def test_create_hospital_duplicate_slug(client: TestClient):
    """POST /hospitals with duplicate slug returns 409."""
    client.post("/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True))
    response = client.post(
        "/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_hospital_invalid_input(client: TestClient):
    """POST /hospitals with missing required fields returns 422."""
    response = client.post(
        "/api/v1/hospitals", json={"name": "Only Name"}, headers=_auth_headers(True)
    )
    assert response.status_code == 422


def test_list_hospitals_empty(client: TestClient):
    """GET /hospitals returns an empty filtered result without assuming a blank DB."""
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}-absent")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_hospitals_with_data(client: TestClient):
    """GET /hospitals returns created hospitals."""
    client.post("/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True))
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == HOSPITAL_PAYLOAD["name"]


def test_get_hospital_not_found(client: TestClient):
    """GET /hospitals/{id} for nonexistent ID returns 404."""
    response = client.get("/api/v1/hospitals/99999")
    assert response.status_code == 404


def test_get_hospital_found(client: TestClient):
    """GET /hospitals/{id} returns the created hospital."""
    create_resp = client.post(
        "/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True)
    )
    hospital_id = create_resp.json()["id"]
    response = client.get(f"/api/v1/hospitals/{hospital_id}")
    assert response.status_code == 200
    assert response.json()["id"] == hospital_id


def test_update_hospital_unauthorized(client: TestClient):
    """PATCH /hospitals/{id} without dev mode returns 403."""
    response = client.patch(
        "/api/v1/hospitals/1", json={"name": "Updated"}, headers=_auth_headers(False)
    )
    assert response.status_code == 403


def test_update_hospital_not_found(client: TestClient):
    """PATCH /hospitals/{id} for nonexistent ID returns 404."""
    response = client.patch(
        "/api/v1/hospitals/99999",
        json={"name": "Updated"},
        headers=_auth_headers(True),
    )
    assert response.status_code == 404


def test_update_hospital(client: TestClient):
    """PATCH /hospitals/{id} updates the hospital."""
    create_resp = client.post(
        "/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True)
    )
    hospital_id = create_resp.json()["id"]
    response = client.patch(
        f"/api/v1/hospitals/{hospital_id}",
        json={"hospital_type": "Specialty", "emergency_services": False},
        headers=_auth_headers(True),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hospital_type"] == "Specialty"
    assert data["emergency_services"] is False
    assert data["verification_status"] == "unverified"


def test_update_hospital_duplicate_slug(client: TestClient):
    """PATCH /hospitals/{id} with duplicate slug returns 409."""
    client.post(
        "/api/v1/hospitals",
        json={**HOSPITAL_PAYLOAD, "name": "Hospital One"},
        headers=_auth_headers(True),
    )
    resp2 = client.post(
        "/api/v1/hospitals",
        json={**HOSPITAL_PAYLOAD, "name": "Hospital Two"},
        headers=_auth_headers(True),
    )
    hospital_two_id = resp2.json()["id"]
    response = client.patch(
        f"/api/v1/hospitals/{hospital_two_id}",
        json={"slug": "hospital-one"},
        headers=_auth_headers(True),
    )
    assert response.status_code == 409


def test_list_hospitals_pagination(client: TestClient):
    """GET /hospitals respects limit and offset."""
    for i in range(5):
        client.post(
            "/api/v1/hospitals",
            json={**HOSPITAL_PAYLOAD, "name": f"eCare {TEST_MARKER} Hospital {i}"},
            headers=_auth_headers(True),
        )
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}&limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert data["total"] == 5
    assert len(data["items"]) == 2


def test_list_hospitals_filters(client: TestClient):
    """GET /hospitals filters by search, locality, type, verification, emergency."""
    client.post(
        "/api/v1/hospitals",
        json={**HOSPITAL_PAYLOAD, "name": f"eCare {TEST_MARKER} City Clinic", "locality": f"{TEST_MARKER} City Center", "hospital_type": "Clinic", "emergency_services": False},
        headers=_auth_headers(True),
    )
    client.post(
        "/api/v1/hospitals",
        json={**HOSPITAL_PAYLOAD, "name": f"eCare {TEST_MARKER} District Hospital", "locality": f"{TEST_MARKER} District Area", "hospital_type": "General", "emergency_services": True},
        headers=_auth_headers(True),
    )
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER} City")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == f"eCare {TEST_MARKER} City Clinic"
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}&locality={TEST_MARKER} District Area")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}&hospital_type=Clinic")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}&emergency_services=true")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    response = client.get(f"/api/v1/hospitals?search={TEST_MARKER}&verification_status=unverified")
    assert response.status_code == 200
    assert response.json()["total"] == 2


# ---------------------------------------------------------------------------
# Doctor API tests
# ---------------------------------------------------------------------------

DOCTOR_PAYLOAD = {
    "full_name": f"Dr. eCare Test Doctor {TEST_MARKER}",
    "qualifications": "MBBS, MD",
    "specializations": "General Medicine",
    "experience_years": 10,
    "languages": "Kannada, English, Hindi",
    "consultation_fee": 200.00,
    "phone": "08532-789012",
}


def test_create_doctor_unauthorized(client: TestClient):
    """POST /doctors without dev mode returns 403."""
    response = client.post("/api/v1/doctors", json=DOCTOR_PAYLOAD)
    assert response.status_code == 403


def test_create_doctor_authorized(client: TestClient):
    """POST /doctors with dev mode returns 201 and unverified status."""
    response = client.post(
        "/api/v1/doctors", json=DOCTOR_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == DOCTOR_PAYLOAD["full_name"]
    assert data["slug"] == f"dr-ecare-test-doctor-{TEST_MARKER}"
    assert data["verification_status"] == "unverified"
    assert data["operational_status"] == "unknown"
    assert data["id"] is not None


def test_create_doctor_duplicate_slug(client: TestClient):
    """POST /doctors with duplicate slug returns 409."""
    client.post("/api/v1/doctors", json=DOCTOR_PAYLOAD, headers=_auth_headers(True))
    response = client.post(
        "/api/v1/doctors", json=DOCTOR_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 409


def test_create_doctor_invalid_hospital(client: TestClient):
    """POST /doctors with nonexistent hospital_id returns 404."""
    payload = {**DOCTOR_PAYLOAD, "hospital_id": 99999}
    response = client.post(
        "/api/v1/doctors", json=payload, headers=_auth_headers(True)
    )
    assert response.status_code == 404


def test_list_doctors_empty(client: TestClient):
    """GET /doctors returns an empty filtered result without assuming a blank DB."""
    response = client.get(f"/api/v1/doctors?search={TEST_MARKER}-absent")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_doctors_with_data(client: TestClient):
    """GET /doctors returns created doctors."""
    client.post("/api/v1/doctors", json=DOCTOR_PAYLOAD, headers=_auth_headers(True))
    response = client.get(f"/api/v1/doctors?search={TEST_MARKER}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["full_name"] == DOCTOR_PAYLOAD["full_name"]


def test_get_doctor_not_found(client: TestClient):
    """GET /doctors/{id} for nonexistent ID returns 404."""
    response = client.get("/api/v1/doctors/99999")
    assert response.status_code == 404


def test_get_doctor_found(client: TestClient):
    """GET /doctors/{id} returns the created doctor."""
    create_resp = client.post(
        "/api/v1/doctors", json=DOCTOR_PAYLOAD, headers=_auth_headers(True)
    )
    doctor_id = create_resp.json()["id"]
    response = client.get(f"/api/v1/doctors/{doctor_id}")
    assert response.status_code == 200
    assert response.json()["id"] == doctor_id


def test_update_doctor_unauthorized(client: TestClient):
    """PATCH /doctors/{id} without dev mode returns 403."""
    response = client.patch(
        "/api/v1/doctors/1", json={"specializations": "Cardiology"}, headers=_auth_headers(False)
    )
    assert response.status_code == 403


def test_update_doctor_not_found(client: TestClient):
    """PATCH /doctors/{id} for nonexistent ID returns 404."""
    response = client.patch(
        "/api/v1/doctors/99999",
        json={"specializations": "Cardiology"},
        headers=_auth_headers(True),
    )
    assert response.status_code == 404


def test_update_doctor(client: TestClient):
    """PATCH /doctors/{id} updates the doctor."""
    create_resp = client.post(
        "/api/v1/doctors", json=DOCTOR_PAYLOAD, headers=_auth_headers(True)
    )
    doctor_id = create_resp.json()["id"]
    response = client.patch(
        f"/api/v1/doctors/{doctor_id}",
        json={"specializations": "Cardiology", "experience_years": 15},
        headers=_auth_headers(True),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["specializations"] == "Cardiology"
    assert data["experience_years"] == 15
    assert data["verification_status"] == "unverified"


def test_list_doctors_filters(client: TestClient):
    """GET /doctors filters by search, specialization, hospital, verification."""
    client.post(
        "/api/v1/doctors",
        json={**DOCTOR_PAYLOAD, "full_name": f"Dr. {TEST_MARKER} Anita Rao", "specializations": "Pediatrics"},
        headers=_auth_headers(True),
    )
    client.post(
        "/api/v1/doctors",
        json={**DOCTOR_PAYLOAD, "full_name": f"Dr. {TEST_MARKER} Sunil Desai", "specializations": "General Medicine"},
        headers=_auth_headers(True),
    )
    response = client.get(f"/api/v1/doctors?search={TEST_MARKER} Anita")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["full_name"] == f"Dr. {TEST_MARKER} Anita Rao"
    response = client.get(f"/api/v1/doctors?search={TEST_MARKER}&specialization=Pediatrics")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    response = client.get(f"/api/v1/doctors?search={TEST_MARKER}&verification_status=unverified")
    assert response.status_code == 200
    assert response.json()["total"] == 2


# ---------------------------------------------------------------------------
# Diagnostic Lab API tests
# ---------------------------------------------------------------------------

LAB_PAYLOAD = {
    "name": f"eCare Test Diagnostic Lab {TEST_MARKER}",
    "address": "45 Hospital Road, Raichur",
    "locality": "Hospital Area",
    "phone": "08532-345678",
    "home_sample_collection": True,
}


def test_create_lab_unauthorized(client: TestClient):
    """POST /labs without dev mode returns 403."""
    response = client.post("/api/v1/labs", json=LAB_PAYLOAD)
    assert response.status_code == 403


def test_create_lab_authorized(client: TestClient):
    """POST /labs with dev mode returns 201 and unverified status."""
    response = client.post(
        "/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == LAB_PAYLOAD["name"]
    assert data["slug"] == LAB_PAYLOAD["name"].lower().replace(" ", "-")
    assert data["verification_status"] == "unverified"
    assert data["operational_status"] == "unknown"
    assert data["id"] is not None


@pytest.mark.parametrize(
    "operational_status,home_sample_collection",
    [("unknown", None), ("operational", True), ("not_operational", False)],
)
def test_lab_status_and_home_collection_unknown_are_returned(
    client: TestClient, operational_status, home_sample_collection
):
    payload = {
        **LAB_PAYLOAD,
        "name": f"eCare {TEST_MARKER} Status Lab {operational_status}",
        "operational_status": operational_status,
        "home_sample_collection": home_sample_collection,
    }
    response = client.post("/api/v1/labs", json=payload, headers=_auth_headers(True))

    assert response.status_code == 201
    assert response.json()["operational_status"] == operational_status
    assert response.json()["home_sample_collection"] is home_sample_collection


def test_create_lab_duplicate_slug(client: TestClient):
    """POST /labs with duplicate slug returns 409."""
    client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    response = client.post(
        "/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 409


def test_list_labs_empty(client: TestClient):
    """GET /labs returns an empty filtered result without assuming a blank DB."""
    response = client.get(f"/api/v1/labs?search={TEST_MARKER}-absent")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_labs_with_data(client: TestClient):
    """GET /labs returns created labs."""
    client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    response = client.get(f"/api/v1/labs?search={TEST_MARKER}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == LAB_PAYLOAD["name"]


def test_get_lab_not_found(client: TestClient):
    """GET /labs/{id} for nonexistent ID returns 404."""
    response = client.get("/api/v1/labs/99999")
    assert response.status_code == 404


def test_get_lab_found(client: TestClient):
    """GET /labs/{id} returns the created lab."""
    create_resp = client.post(
        "/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True)
    )
    lab_id = create_resp.json()["id"]
    response = client.get(f"/api/v1/labs/{lab_id}")
    assert response.status_code == 200
    assert response.json()["id"] == lab_id


def test_update_lab_unauthorized(client: TestClient):
    """PATCH /labs/{id} without dev mode returns 403."""
    response = client.patch(
        "/api/v1/labs/1", json={"home_sample_collection": False}, headers=_auth_headers(False)
    )
    assert response.status_code == 403


def test_update_lab_not_found(client: TestClient):
    """PATCH /labs/{id} for nonexistent ID returns 404."""
    response = client.patch(
        "/api/v1/labs/99999",
        json={"home_sample_collection": False},
        headers=_auth_headers(True),
    )
    assert response.status_code == 404


def test_update_lab(client: TestClient):
    """PATCH /labs/{id} updates the lab."""
    create_resp = client.post(
        "/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True)
    )
    lab_id = create_resp.json()["id"]
    response = client.patch(
        f"/api/v1/labs/{lab_id}",
        json={"home_sample_collection": False, "locality": "New Area"},
        headers=_auth_headers(True),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["home_sample_collection"] is False
    assert data["locality"] == "New Area"
    assert data["verification_status"] == "unverified"


def test_list_labs_filters(client: TestClient):
    """GET /labs filters by search, locality, home_sample_collection, verification."""
    client.post(
        "/api/v1/labs",
        json={**LAB_PAYLOAD, "name": f"eCare {TEST_MARKER} City Lab", "locality": f"{TEST_MARKER} City Center", "home_sample_collection": True},
        headers=_auth_headers(True),
    )
    client.post(
        "/api/v1/labs",
        json={**LAB_PAYLOAD, "name": f"eCare {TEST_MARKER} District Lab", "locality": f"{TEST_MARKER} District Area", "home_sample_collection": False},
        headers=_auth_headers(True),
    )
    response = client.get(f"/api/v1/labs?search={TEST_MARKER} City")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == f"eCare {TEST_MARKER} City Lab"
    response = client.get(f"/api/v1/labs?search={TEST_MARKER}&locality={TEST_MARKER} District Area")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    response = client.get(f"/api/v1/labs?search={TEST_MARKER}&home_sample_collection=true")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    response = client.get(f"/api/v1/labs?search={TEST_MARKER}&verification_status=unverified")
    assert response.status_code == 200
    assert response.json()["total"] == 2


# ---------------------------------------------------------------------------
# Diagnostic Test API tests
# ---------------------------------------------------------------------------

TEST_PAYLOAD = {
    "name": "Blood Glucose Test",
    "description": "Fasting blood sugar test",
    "price": 80.00,
    "preparation_instructions": "Fast for 8-12 hours before the test",
    "availability_status": "available",
}


def test_create_test_for_lab_unauthorized(client: TestClient):
    """POST /labs/{lab_id}/tests without dev mode returns 403."""
    response = client.post("/api/v1/labs/1/tests", json=TEST_PAYLOAD)
    assert response.status_code == 403


def test_create_test_for_lab_not_found_lab(client: TestClient):
    """POST /labs/{lab_id}/tests for nonexistent lab returns 404."""
    response = client.post(
        "/api/v1/labs/99999/tests", json=TEST_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 404


def test_create_test_for_lab_authorized(client: TestClient):
    """POST /labs/{lab_id}/tests with dev mode returns 201."""
    lab_resp = client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    lab_id = lab_resp.json()["id"]
    response = client.post(
        f"/api/v1/labs/{lab_id}/tests", json=TEST_PAYLOAD, headers=_auth_headers(True)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == TEST_PAYLOAD["name"]
    assert data["lab_id"] == lab_id
    assert data["price"] == TEST_PAYLOAD["price"]
    assert data["id"] is not None


def test_list_tests_for_lab_empty(client: TestClient):
    """GET /labs/{lab_id}/tests returns empty list when no tests exist."""
    lab_resp = client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    lab_id = lab_resp.json()["id"]
    response = client.get(f"/api/v1/labs/{lab_id}/tests")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_tests_for_lab_not_found_lab(client: TestClient):
    """GET /labs/{lab_id}/tests for nonexistent lab returns 404."""
    response = client.get("/api/v1/labs/99999/tests")
    assert response.status_code == 404


def test_list_tests_for_lab_with_data(client: TestClient):
    """GET /labs/{lab_id}/tests returns created tests."""
    lab_resp = client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    lab_id = lab_resp.json()["id"]
    client.post(
        f"/api/v1/labs/{lab_id}/tests", json=TEST_PAYLOAD, headers=_auth_headers(True)
    )
    response = client.get(f"/api/v1/labs/{lab_id}/tests")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == TEST_PAYLOAD["name"]


def test_get_test_not_found(client: TestClient):
    """GET /tests/{id} for nonexistent ID returns 404."""
    response = client.get("/api/v1/tests/99999")
    assert response.status_code == 404


def test_get_test_found(client: TestClient):
    """GET /tests/{id} returns the created test."""
    lab_resp = client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    lab_id = lab_resp.json()["id"]
    test_resp = client.post(
        f"/api/v1/labs/{lab_id}/tests", json=TEST_PAYLOAD, headers=_auth_headers(True)
    )
    test_id = test_resp.json()["id"]
    response = client.get(f"/api/v1/tests/{test_id}")
    assert response.status_code == 200
    assert response.json()["id"] == test_id


def test_update_test_unauthorized(client: TestClient):
    """PATCH /tests/{id} without dev mode returns 403."""
    response = client.patch(
        "/api/v1/tests/1", json={"price": 100.00}, headers=_auth_headers(False)
    )
    assert response.status_code == 403


def test_update_test_not_found(client: TestClient):
    """PATCH /tests/{id} for nonexistent ID returns 404."""
    response = client.patch(
        "/api/v1/tests/99999",
        json={"price": 100.00},
        headers=_auth_headers(True),
    )
    assert response.status_code == 404


def test_update_test(client: TestClient):
    """PATCH /tests/{id} updates the test."""
    lab_resp = client.post("/api/v1/labs", json=LAB_PAYLOAD, headers=_auth_headers(True))
    lab_id = lab_resp.json()["id"]
    test_resp = client.post(
        f"/api/v1/labs/{lab_id}/tests", json=TEST_PAYLOAD, headers=_auth_headers(True)
    )
    test_id = test_resp.json()["id"]
    response = client.patch(
        f"/api/v1/tests/{test_id}",
        json={"price": 90.00, "availability_status": "temporarily_unavailable"},
        headers=_auth_headers(True),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 90.00
    assert data["availability_status"] == "temporarily_unavailable"


def test_list_hospital_doctors(client: TestClient):
    """GET /hospitals/{id}/doctors returns doctors for that hospital."""
    hosp_resp = client.post(
        "/api/v1/hospitals", json=HOSPITAL_PAYLOAD, headers=_auth_headers(True)
    )
    hospital_id = hosp_resp.json()["id"]
    client.post(
        "/api/v1/doctors",
        json={**DOCTOR_PAYLOAD, "hospital_id": hospital_id},
        headers=_auth_headers(True),
    )
    client.post(
        "/api/v1/doctors",
        json={**DOCTOR_PAYLOAD, "full_name": "Dr. Other", "hospital_id": hospital_id},
        headers=_auth_headers(True),
    )
    response = client.get(f"/api/v1/hospitals/{hospital_id}/doctors")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["hospital_id"] == hospital_id
