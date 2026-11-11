"""API coverage for provider-verified health checkup subscriptions."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.database import get_db
from app.main import app
from app.models import FamilyMember, Package, PackageInclusion, Subscription, User
from app.api.v1.routers import subscriptions as subscription_routes


@pytest.fixture
def subscription_context(db_session, monkeypatch):
    monkeypatch.setenv("ECARE_ENVIRONMENT", "test")
    monkeypatch.setenv("ECARE_SIMULATED_PAYMENTS_ENABLED", "true")

    users = {
        "patient": User(
            email="patient-subscription@example.com",
            full_name="Patient Subscription User",
            hashed_password="not-used-in-this-test",
            role="patient",
        ),
        "other": User(
            email="other-subscription@example.com",
            full_name="Other Subscription User",
            hashed_password="not-used-in-this-test",
            role="patient",
        ),
        "admin": User(
            email="admin-subscription@example.com",
            full_name="Admin Subscription User",
            hashed_password="not-used-in-this-test",
            role="admin",
        ),
        "provider": User(
            email="provider-subscription@example.com",
            full_name="Provider Subscription User",
            hashed_password="not-used-in-this-test",
            role="provider",
        ),
    }
    package = Package(
        name="Provider Monthly Checkup",
        slug="provider-monthly-checkup",
        provider_name="Verified Test Provider",
        provider_type="diagnostic_lab",
        price=Decimal("1250.00"),
        currency="INR",
        city="Raichur",
        state="Karnataka",
        category="checkup",
        source="Provider-supplied test fixture",
        verified_at=datetime.now(timezone.utc),
        is_verified=True,
        is_demo=False,
        is_active=True,
        min_age_years=18,
        max_age_years=65,
        validity_period="monthly",
        validity_description="One month",
        inclusions=[
            PackageInclusion(test_name="Provider-supplied test", display_order=0)
        ],
    )
    db_session.add_all([*users.values(), package])
    db_session.flush()
    family_member = FamilyMember(
        user_id=users["patient"].id,
        name="Test Family Member",
        relationship_type="child",
    )
    db_session.add(family_member)
    db_session.flush()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    headers = {
        role: {
            "Authorization": f"Bearer {create_access_token(user.email)}"
        }
        for role, user in users.items()
    }
    try:
        with TestClient(app) as client:
            yield client, db_session, users, package, family_member, headers
    finally:
        app.dependency_overrides.clear()


def _create(client, headers, package, **extra):
    return client.post(
        "/api/v1/subscriptions",
        headers=headers,
        json={"plan_id": package.id, **extra},
    )


def test_subscription_uses_verified_plan_price_and_blocks_duplicate(
    subscription_context,
):
    client, db, users, package, member, headers = subscription_context
    response = _create(
        client,
        headers["patient"],
        package,
        family_member_id=member.id,
        age_years=24,
        amount=1,
        currency="BAD",
    )

    assert response.status_code == 201
    record = response.json()
    assert Decimal(record["amount"]) == Decimal("1250.00")
    assert record["currency"] == "INR"
    assert record["family_member_id"] == member.id
    assert record["status"] == "pending_payment"
    assert record["payment_status"] == "pending"
    assert record["events"][0]["event_type"] == "created"
    assert db.query(Subscription).filter_by(user_id=users["patient"].id).count() == 1
    assert _create(client, headers["patient"], package, age_years=24).status_code == 409
    assert client.get(
        f"/api/v1/subscriptions/{record['id']}",
        headers=headers["other"],
    ).status_code == 404


def test_simulated_payment_creates_in_app_reminder_and_entitlement(
    subscription_context,
):
    client, db, _, package, _, headers = subscription_context
    created = _create(client, headers["patient"], package, age_years=30)
    assert created.status_code == 201

    response = client.post(
        f"/api/v1/subscriptions/{created.json()['id']}/simulate-payment",
        headers=headers["patient"],
    )

    assert response.status_code == 200
    subscription = response.json()
    assert subscription["status"] == "active"
    assert subscription["payment_status"] == "simulated"
    payment_event = next(
        event for event in subscription["events"]
        if event["event_type"] == "payment_simulated"
    )
    assert "no real charge" in payment_event["details"].lower()
    assert subscription["reminder"]["reminder_date"] == subscription["expires_at"][:10]
    assert client.get(
        "/api/v1/subscriptions/me/entitlements",
        headers=headers["patient"],
    ).json() == [package.id]
    reminder = db.query(Subscription).one().reminder
    assert reminder is not None
    edit = client.patch(
        f"/api/v1/reminders/{reminder.id}",
        headers=headers["patient"],
        json={"title": "Changed expiry"},
    )
    assert edit.status_code == 409
    delete = client.delete(
        f"/api/v1/reminders/{reminder.id}",
        headers=headers["patient"],
    )
    assert delete.status_code == 409
    complete = client.patch(
        f"/api/v1/reminders/{reminder.id}",
        headers=headers["patient"],
        json={"completed": True},
    )
    assert complete.status_code == 200
    assert complete.json()["completed"] is True


def test_renewal_is_server_priced_scheduled_and_cannot_be_duplicated(
    subscription_context,
):
    client, db, users, package, _, headers = subscription_context
    created = _create(client, headers["patient"], package, age_years=30)
    subscription_id = created.json()["id"]
    activated = client.post(
        f"/api/v1/subscriptions/{subscription_id}/simulate-payment",
        headers=headers["patient"],
    )
    assert activated.status_code == 200

    renewal_response = client.post(
        f"/api/v1/subscriptions/{subscription_id}/renew",
        headers=headers["patient"],
        json={"plan_id": package.id, "amount": 1},
    )

    assert renewal_response.status_code == 201
    renewal = renewal_response.json()
    assert Decimal(renewal["amount"]) == Decimal("1250.00")
    assert renewal["renewal_of_id"] == subscription_id
    assert datetime.fromisoformat(renewal["start_at"]) == datetime.fromisoformat(
        activated.json()["expires_at"]
    )
    assert renewal["status"] == "pending_payment"

    duplicate = client.post(
        f"/api/v1/subscriptions/{subscription_id}/renew",
        headers=headers["patient"],
        json={"plan_id": package.id},
    )
    assert duplicate.status_code == 409

    simulated = client.post(
        f"/api/v1/subscriptions/{renewal['id']}/simulate-payment",
        headers=headers["patient"],
    )
    patient = db.query(User).filter_by(email=users["patient"].email).one_or_none()
    assert simulated.status_code == 200, (
        f"{simulated.text}; patient exists={patient is not None}; "
        f"patient active={patient.is_active if patient else None}"
    )
    assert simulated.json()["status"] == "scheduled"
    assert simulated.json()["payment_status"] == "simulated"


def test_age_and_role_checks_and_cancellation(subscription_context):
    client, db, users, package, member, headers = subscription_context
    assert _create(client, headers["patient"], package).status_code == 422
    assert _create(
        client,
        headers["patient"],
        package,
        age_years=17,
    ).status_code == 422
    assert _create(
        client,
        headers["admin"],
        package,
        age_years=30,
    ).status_code == 403
    assert _create(
        client,
        headers["provider"],
        package,
        age_years=30,
    ).status_code == 403

    created = _create(
        client,
        headers["patient"],
        package,
        age_years=30,
        family_member_id=member.id,
    )
    assert created.status_code == 201
    subscription_id = created.json()["id"]
    forbidden = client.post(
        f"/api/v1/subscriptions/admin/{subscription_id}/cancel",
        headers=headers["patient"],
        json={"reason": "not an admin"},
    )
    assert forbidden.status_code == 403

    cancelled = client.post(
        f"/api/v1/subscriptions/admin/{subscription_id}/cancel",
        headers=headers["admin"],
        json={"reason": "Admin cancellation"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["events"][-1]["event_type"] == "cancelled"
    assert db.query(Subscription).filter_by(user_id=users["patient"].id).one().status == "cancelled"


def test_expiry_is_applied_on_access_and_completes_reminder(
    subscription_context,
    monkeypatch,
):
    client, _, _, package, _, headers = subscription_context
    created = _create(client, headers["patient"], package, age_years=30)
    activated = client.post(
        f"/api/v1/subscriptions/{created.json()['id']}/simulate-payment",
        headers=headers["patient"],
    )
    assert activated.status_code == 200
    expires_at = datetime.fromisoformat(activated.json()["expires_at"])
    monkeypatch.setattr(
        subscription_routes,
        "_utc_now",
        lambda: expires_at + timedelta(seconds=1),
    )

    response = client.get("/api/v1/subscriptions/me", headers=headers["patient"])

    assert response.status_code == 200
    assert response.json()[0]["status"] == "expired"
    assert response.json()[0]["reminder"]["completed"] is True
    assert response.json()[0]["events"][-1]["event_type"] == "expired"


def test_simulated_payments_are_disabled_outside_test_mode(subscription_context, monkeypatch):
    client, _, _, package, _, headers = subscription_context
    created = _create(client, headers["patient"], package, age_years=30)
    monkeypatch.setenv("ECARE_ENVIRONMENT", "production")

    response = client.post(
        f"/api/v1/subscriptions/{created.json()['id']}/simulate-payment",
        headers=headers["patient"],
    )

    assert response.status_code == 503
    options = client.get("/api/v1/subscriptions/payment-options")
    assert options.json()["mode"] == "unavailable"
    assert "no payment gateway" in options.json()["message"].lower()
