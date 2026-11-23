"""Package validation and existing appointment behavior for demo bookings."""

from collections.abc import Generator
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models import (
    Appointment,
    Doctor,
    DoctorSpeciality,
    FamilyMember,
    Hospital,
    Invoice,
    Package,
    PackageInclusion,
    PaymentRecord,
    Reminder,
    Speciality,
    Subscription,
    SubscriptionEvent,
    User,
)


@pytest.fixture
def booking_context() -> Generator[tuple[TestClient, Session, User, Doctor, Package, dict[str, str], str, str], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Avoid creating the duplicate hospital_id index declared on the Doctor model.
    doctor_indexes = [
        index
        for index in Doctor.__table__.indexes
        if index.name == "ix_doctors_hospital_id"
    ]
    for duplicate in doctor_indexes[1:]:
        Doctor.__table__.indexes.remove(duplicate)
    try:
        Base.metadata.create_all(
            engine,
            tables=[
                User.__table__,
                Hospital.__table__,
                Doctor.__table__,
                Speciality.__table__,
                DoctorSpeciality.__table__,
                Package.__table__,
                PackageInclusion.__table__,
                Appointment.__table__,
                Invoice.__table__,
                PaymentRecord.__table__,
                FamilyMember.__table__,
                Reminder.__table__,
                Subscription.__table__,
                SubscriptionEvent.__table__,
            ],
        )
    finally:
        Doctor.__table__.indexes.update(doctor_indexes[1:])
    session = sessionmaker(bind=engine)()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    appointment_date = datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=2)
    weekday = (appointment_date.weekday() + 1) % 7
    user = User(
        email="patient@example.com",
        full_name="Test Patient",
        hashed_password="not-used-in-this-test",
        role="patient",
    )
    hospital = Hospital(
        name="Test Hospital",
        slug="test-hospital",
        address="1 Test Road",
        locality="Central",
        city="Raichur",
        state="Karnataka",
    )
    doctor = Doctor(
        full_name="Test Doctor",
        slug="test-doctor",
        hospital=hospital,
        consultation_fee=100,
        is_active=True,
        schedule_json={
            "privateOpd": {
                str(weekday): {
                    "start": "10:00",
                    "end": "13:00",
                    "location": "Test Clinic",
                }
            },
            "governmentDuty": {},
            "durationMinutes": 30,
            "unavailableDays": [],
        },
    )
    package = Package(
        name="Annual Health Check",
        slug="annual-health-check",
        provider_name="Test Lab",
        price=1250,
        city="Raichur",
        state="Karnataka",
        locality="Central",
        source="Provider-supplied test fixture",
        verified_at=datetime.now(timezone.utc),
        is_verified=True,
        is_demo=False,
        is_active=True,
    )
    session.add_all([user, hospital, doctor, package])
    session.commit()

    token = create_access_token(user.email)
    headers = {"Authorization": f"Bearer {token}"}
    request_data = {
        "doctor_id": str(doctor.id),
        "appointment_date": appointment_date.isoformat(),
        "appointment_time": time(10, 0).isoformat(),
        "payment_method": "demo",
    }

    try:
        with TestClient(app) as client:
            yield client, session, user, doctor, package, headers, request_data, appointment_date.isoformat()
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_booking_uses_database_package_details_not_client_values(booking_context):
    client, session, _, doctor, package, headers, request_data, _ = booking_context
    assert session.query(Doctor).filter(
        Doctor.id == doctor.id,
        Doctor.is_active.is_(True),
    ).first() is not None

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={
            **request_data,
            "package_id": package.id,
            "package_name": "Forged package name",
            "package_amount": 1,
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["package_id"] == package.id
    assert result["package_name"] == package.name
    assert Decimal(result["package_amount"]) == Decimal("1250")
    assert result["city"] == "Raichur"
    saved = session.query(Package).filter(Package.id == package.id).one()
    assert saved.name == result["package_name"]


@pytest.mark.parametrize("package_id", ["static-sample", 0, -1])
def test_booking_rejects_malformed_or_nonpositive_package_ids(booking_context, package_id):
    client, _, _, _, _, headers, request_data, _ = booking_context

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "package_id": package_id},
    )

    assert response.status_code == 422


def test_booking_rejects_a_missing_database_package(booking_context):
    client, _, _, _, _, headers, request_data, _ = booking_context

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "package_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Selected package is not available"


def test_booking_rejects_demo_package_records(booking_context):
    client, session, _, _, _, headers, request_data, _ = booking_context
    demo_package = Package(
        name="Display-only Package",
        slug="display-only-package",
        provider_name="Sample Lab",
        price=0,
        is_demo=True,
        is_active=True,
    )
    session.add(demo_package)
    session.commit()

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "package_id": demo_package.id},
    )

    assert response.status_code == 409
    assert "Demo/sample" in response.json()["detail"]


def test_booking_rejects_unverified_package_records(booking_context):
    client, session, _, _, _, headers, request_data, _ = booking_context
    unverified_package = Package(
        name="Unverified Package",
        slug="unverified-package",
        provider_name="Test Lab",
        price=900,
        city="Raichur",
        state="Karnataka",
        is_demo=False,
        is_active=True,
    )
    session.add(unverified_package)
    session.flush()

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "package_id": unverified_package.id},
    )

    assert response.status_code == 409
    assert "verified" in response.json()["detail"]


def test_booking_rejects_package_outside_doctor_city(booking_context):
    client, session, _, _, package, headers, request_data, _ = booking_context
    package.city = "Different City"
    session.flush()

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "package_id": package.id},
    )

    assert response.status_code == 409
    assert "location" in response.json()["detail"]


def test_package_list_can_filter_by_city_and_locality(booking_context):
    client, _, _, _, package, _, _, _ = booking_context

    response = client.get("/api/v1/packages?city=Raichur&locality=Central")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [package.id]


def test_package_browsing_hides_inactive_packages(booking_context):
    client, session, _, _, _, _, _, _ = booking_context
    inactive = Package(
        name="Inactive Package",
        slug="inactive-package",
        provider_name="Test Lab",
        price=500,
        is_active=False,
    )
    session.add(inactive)
    session.flush()

    response = client.get("/api/v1/packages")

    assert response.status_code == 200
    assert inactive.id not in [item["id"] for item in response.json()["items"]]
    assert client.get(f"/api/v1/packages/{inactive.id}").status_code == 404


def test_appointment_package_column_has_database_foreign_key():
    foreign_key = next(iter(Appointment.__table__.c.package_id.foreign_keys))

    assert foreign_key.target_fullname == "packages.id"
    assert foreign_key.ondelete == "SET NULL"


def test_deleting_package_preserves_appointment_and_clears_its_reference(booking_context):
    client, session, _, _, package, headers, request_data, _ = booking_context
    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "package_id": package.id},
    )
    assert response.status_code == 201

    session.delete(package)
    session.flush()
    session.expire_all()
    appointment = session.query(Appointment).one()

    assert appointment.package_id is None
    assert appointment.package_name == "Annual Health Check"


def test_booking_without_package_remains_supported(booking_context):
    client, _, _, _, _, headers, request_data, _ = booking_context

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )

    assert response.status_code == 201
    result = response.json()
    assert result["package_id"] is None
    assert result["package_name"] is None
    assert Decimal(result["package_amount"]) == Decimal("0")
    assert Decimal(result["total_amount"]) == Decimal("100")


def test_demo_doctor_cannot_be_booked_or_show_availability(booking_context):
    client, session, _, doctor, _, headers, request_data, appointment_date = booking_context
    doctor.is_demo = True
    session.flush()

    availability = client.get(
        f"/api/v1/appointments/availability/{doctor.id}",
        params={"appointment_date": appointment_date},
    )
    assert availability.status_code == 200
    assert availability.json()["slots"] == []
    assert availability.json()["message"] == (
        "Demo/sample doctor records cannot be booked."
    )

    booking = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )
    assert booking.status_code == 409
    assert booking.json()["detail"] == "Demo/sample doctor records cannot be booked"


def test_availability_uses_provider_schedule_and_marks_booked_slots(booking_context):
    client, _, _, doctor, _, headers, request_data, appointment_date = booking_context

    before = client.get(
        f"/api/v1/appointments/availability/{doctor.id}",
        params={"appointment_date": appointment_date},
    )
    assert before.status_code == 200
    result = before.json()
    assert result["doctor_id"] == doctor.id
    assert result["consultation_fee"] == "100.00"
    assert result["opd_start"] == "10:00:00"
    assert result["opd_end"] == "13:00:00"
    assert result["clinic_location"] == "Test Clinic"
    assert result["consultation_days"]
    assert result["slots"][0]["time"] == "10:00:00"
    assert result["slots"][0]["status"] == "available"

    booking = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )
    assert booking.status_code == 201

    after = client.get(
        f"/api/v1/appointments/availability/{doctor.id}",
        params={"appointment_date": appointment_date},
    )
    assert after.status_code == 200
    booked_slot = next(
        slot for slot in after.json()["slots"] if slot["time"] == "10:00:00"
    )
    assert booked_slot["status"] == "unavailable"
    assert "already been booked" in booked_slot["reason"]


def test_availability_reports_unavailable_doctors_and_closed_days(booking_context):
    client, session, _, doctor, _, _, _, appointment_date = booking_context
    doctor.schedule_json = None
    session.flush()

    unavailable = client.get(
        f"/api/v1/appointments/availability/{doctor.id}",
        params={"appointment_date": appointment_date},
    )
    assert unavailable.status_code == 200
    assert unavailable.json()["message"] == (
        "Currently unavailable for online appointment booking."
    )

    doctor.schedule_json = {
        "privateOpd": {},
        "governmentDuty": {},
        "durationMinutes": 30,
        "unavailableDays": [],
    }
    session.flush()
    no_sessions = client.get(
        f"/api/v1/appointments/availability/{doctor.id}",
        params={"appointment_date": appointment_date},
    )
    assert no_sessions.status_code == 200
    assert no_sessions.json()["consultation_days"] == []
    assert no_sessions.json()["message"] == (
        "Currently unavailable for online appointment booking."
    )


def test_booking_records_simulated_payment_and_demo_invoice(booking_context):
    client, session, _, _, _, headers, request_data, _ = booking_context
    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )

    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "demo_confirmed"
    assert result["payment_status"] == "demo_recorded"
    assert result["advance_paid"] == "100.00"
    assert result["remaining_balance"] == "0.00"
    assert result["invoice"]["outstanding_balance"] == "0.00"
    assert result["invoice"]["payment_status"] == "simulated"
    assert "NOT A REAL TRANSACTION" in result["invoice"]["payment_method"]
    payment = session.query(PaymentRecord).one()
    assert payment.status == "simulated"
    assert payment.amount == Decimal("100.00")
    assert payment.method_label == "DEMO PAYMENT - NOT A REAL TRANSACTION"


def test_booking_does_not_accept_cash_payment_option(booking_context):
    client, _, _, _, _, headers, request_data, _ = booking_context

    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "payment_method": "demo-cash"},
    )

    assert response.status_code == 422


def test_booking_rejects_unsupported_payment_method(booking_context):
    client, _, _, _, _, headers, request_data, _ = booking_context
    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "payment_method": "demo-card"},
    )
    assert response.status_code == 422


def test_appointment_routes_are_registered_in_openapi(booking_context):
    client, _, _, _, _, _, _, _ = booking_context
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/appointments/availability/{doctor_id}" in paths
    assert "/api/v1/appointments/me/{reference}/cancel" in paths


def test_invoice_list_route_is_not_captured_by_appointment_reference(booking_context):
    client, _, _, _, _, headers, request_data, _ = booking_context

    booking = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )
    assert booking.status_code == 201

    response = client.get(
        "/api/v1/appointments/me/invoices",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["appointment_id"] == booking.json()["id"]


def test_patient_can_cancel_owned_demo_appointment_and_release_slot(booking_context):
    client, session, user, _, _, headers, request_data, _ = booking_context
    first = client.post("/api/v1/appointments/", headers=headers, json=request_data)
    assert first.status_code == 201
    reference = first.json()["reference"]

    history = client.get("/api/v1/appointments/me", headers=headers)
    assert history.status_code == 200
    assert [item["reference"] for item in history.json()] == [reference]

    cancelled = client.patch(
        f"/api/v1/appointments/me/{reference}/cancel",
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert session.query(Appointment).filter_by(reference=reference).one().status == "cancelled"

    repeated = client.patch(
        f"/api/v1/appointments/me/{reference}/cancel",
        headers=headers,
    )
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "cancelled"

    second = client.post("/api/v1/appointments/", headers=headers, json=request_data)
    assert second.status_code == 201
    assert second.json()["reference"] != reference
    assert user.id == second.json()["user_id"]


def test_patient_cannot_cancel_another_patients_appointment(booking_context):
    client, session, _, _, _, headers, request_data, _ = booking_context
    booking = client.post("/api/v1/appointments/", headers=headers, json=request_data)
    assert booking.status_code == 201

    other_user = User(
        email="other-patient@example.com",
        full_name="Other Patient",
        hashed_password="not-used-in-this-test",
        role="patient",
        is_active=True,
    )
    session.add(other_user)
    session.flush()
    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.email)}"}
    response = client.patch(
        f"/api/v1/appointments/me/{booking.json()['reference']}/cancel",
        headers=other_headers,
    )
    assert response.status_code == 404


def test_cancelled_appointment_slot_can_be_rebooked(booking_context):
    client, session, _, _, _, headers, request_data, _ = booking_context

    first = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )
    assert first.status_code == 201
    appointment = session.query(Appointment).filter_by(reference=first.json()["reference"]).one()
    appointment.status = "cancelled"
    session.flush()

    second = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )

    assert second.status_code == 201
    assert second.json()["reference"] != first.json()["reference"]


def test_booking_rejects_seconds_not_represented_by_slot_grid(booking_context):
    client, _, _, _, _, headers, request_data, _ = booking_context
    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={**request_data, "appointment_time": "10:00:30"},
    )
    assert response.status_code == 422


def test_booking_returns_conflict_for_invalid_provider_schedule(booking_context):
    client, session, _, doctor, _, headers, request_data, _ = booking_context
    doctor.schedule_json["durationMinutes"] = 0
    session.flush()
    response = client.post(
        "/api/v1/appointments/",
        headers=headers,
        json=request_data,
    )
    assert response.status_code == 409


def test_booking_requires_authentication(booking_context):
    client, _, _, _, _, _, request_data, _ = booking_context

    response = client.post("/api/v1/appointments/", json=request_data)

    assert response.status_code == 401


def test_inactive_admin_cannot_write_packages(booking_context):
    client, session, _, _, _, _, _, _ = booking_context
    inactive_admin = User(
        email="disabled-admin@example.com",
        full_name="Disabled Admin",
        hashed_password="not-used-in-this-test",
        role="admin",
        is_active=False,
    )
    session.add(inactive_admin)
    session.flush()
    token = create_access_token(inactive_admin.email)

    response = client.post(
        "/api/v1/packages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Sample Package",
            "provider_name": "Sample Provider",
            "price": 0,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Account is unavailable"


def test_family_members_and_reminders_are_account_scoped(booking_context):
    client, session, user, _, _, headers, _, _ = booking_context
    other_user = User(
        email="other-patient@example.com",
        full_name="Other Patient",
        hashed_password="not-used-in-this-test",
        role="patient",
        is_active=True,
    )
    session.add(other_user)
    session.flush()
    other_headers = {
        "Authorization": f"Bearer {create_access_token(other_user.email)}"
    }

    member_response = client.post(
        "/api/v1/family-members/",
        headers=headers,
        json={"name": "My Child", "relationship_type": "child"},
    )
    assert member_response.status_code == 201
    member_id = member_response.json()["id"]
    assert [
        item["id"]
        for item in client.get("/api/v1/family-members/me", headers=headers).json()
    ] == [member_id]
    assert client.get("/api/v1/family-members/me", headers=other_headers).json() == []
    assert client.delete(
        f"/api/v1/family-members/{member_id}",
        headers=other_headers,
    ).status_code == 404

    reminder_response = client.post(
        "/api/v1/reminders/",
        headers=headers,
        json={
            "family_member_id": member_id,
            "title": "Annual checkup",
            "category": "checkup",
            "reminder_date": (date.today() + timedelta(days=30)).isoformat(),
            "repeat_interval": "yearly",
        },
    )
    assert reminder_response.status_code == 201
    reminder_id = reminder_response.json()["id"]
    assert [
        item["id"]
        for item in client.get("/api/v1/reminders/me", headers=headers).json()
    ] == [reminder_id]
    assert client.get("/api/v1/reminders/me", headers=other_headers).json() == []
    updated = client.patch(
        f"/api/v1/reminders/{reminder_id}",
        headers=headers,
        json={"completed": True, "title": "Completed annual checkup"},
    )
    assert updated.status_code == 200
    assert updated.json()["completed"] is True
    assert updated.json()["title"] == "Completed annual checkup"
    assert client.patch(
        f"/api/v1/reminders/{reminder_id}",
        headers=other_headers,
        json={"completed": True},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/reminders/{reminder_id}",
        headers=other_headers,
    ).status_code == 404

    assert client.post(
        "/api/v1/reminders/",
        headers=other_headers,
        json={
            "family_member_id": member_id,
            "title": "Not mine",
            "category": "checkup",
            "reminder_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    ).status_code == 404
    assert client.delete(
        f"/api/v1/reminders/{reminder_id}",
        headers=headers,
    ).status_code == 200
    assert client.get("/api/v1/reminders/me", headers=headers).json() == []
    assert user.id != other_user.id
