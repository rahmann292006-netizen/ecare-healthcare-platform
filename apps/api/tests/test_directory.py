"""Backend tests for the read-only finder directory API."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.main import app
from app.models import Doctor, DiagnosticLab, Hospital, OPD, Speciality
from scripts.seed_specialities import SPECIALITIES, seed_specialities


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _hospital(db_session, *, name="A Hospital", locality="Central"):
    row = Hospital(name=name, slug=name.lower().replace(" ", "-"), address="Address", locality=locality)
    db_session.add(row)
    db_session.flush()
    return row


def test_specialities_endpoint_lists_only_active(api_client, db_session):
    db_session.add_all([
        Speciality(name="Directory Active", slug="directory-active"),
        Speciality(name="Directory Inactive", slug="directory-inactive", is_active=False),
    ])
    db_session.flush()

    response = api_client.get("/api/v1/specialities")

    assert response.status_code == 200
    active_slugs = {item["slug"] for item in response.json()}
    assert "directory-active" in active_slugs
    assert "directory-inactive" not in active_slugs


def test_provider_directory_filters_and_never_infers_specialities(api_client, db_session):
    hospital = _hospital(db_session, name="Cardiac Center", locality="West")
    speciality = Speciality(name="Finder Cardiology", slug="finder-cardiology")
    doctor = Doctor(
        full_name="Dr Sample", slug="dr-sample", hospital=hospital,
        specializations="Cardiology", source=None,
    )
    unlinked_doctor = Doctor(
        full_name="Dr Legacy", slug="dr-legacy", hospital=hospital,
        specializations="Cardiology",
    )
    lab = DiagnosticLab(name="West Lab", slug="west-lab", address="Lab address", locality="West")
    db_session.add_all([speciality, doctor, unlinked_doctor, lab])
    db_session.flush()
    hospital.specialities.append(speciality)
    doctor.specialities.append(speciality)

    response = api_client.get(f"/api/v1/providers?speciality_id={speciality.id}&locality=West")
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 2
    assert {item["provider_type"] for item in result["items"]} == {"hospital", "doctor"}
    assert all(item["specialities"][0]["slug"] == "finder-cardiology" for item in result["items"])

    # Legacy free text remains for compatibility but does not create a link.
    doctor_result = api_client.get(f"/api/v1/providers/doctor/{unlinked_doctor.id}").json()
    assert doctor_result["specialities"] == []
    assert doctor_result["is_verified"] is False
    assert doctor_result["is_demo"] is False
    assert doctor_result["source"] is None


def test_provider_directory_types_pagination_sort_and_total(api_client, db_session):
    _hospital(db_session, name="FinderCheck Alpha Hospital")
    db_session.add_all([
        DiagnosticLab(name="FinderCheck Zulu Lab", slug="findercheck-zulu-lab", address="Address"),
        OPD(name="FinderCheck Beta OPD", slug="findercheck-beta-opd"),
    ])
    db_session.flush()

    asc = api_client.get("/api/v1/providers?search=FinderCheck&sort=name_asc&limit=2&offset=0").json()
    assert asc["total"] == 3
    assert asc["limit"] == 2
    assert asc["offset"] == 0
    assert [item["name"] for item in asc["items"]] == ["FinderCheck Alpha Hospital", "FinderCheck Beta OPD"]

    desc = api_client.get("/api/v1/providers?provider_type=opd&search=FinderCheck&sort=name_desc").json()
    assert desc["total"] == 1
    assert desc["items"][0]["provider_type"] == "opd"
    assert api_client.get("/api/v1/providers?provider_type=unknown").status_code == 422


def test_opd_standalone_and_linked_detail(api_client, db_session):
    hospital = _hospital(db_session)
    standalone = OPD(name="Independent OPD", slug="independent-opd")
    linked = OPD(name="Hospital OPD", slug="hospital-opd", hospital_id=hospital.id)
    db_session.add_all([standalone, linked])
    db_session.flush()

    standalone_result = api_client.get(f"/api/v1/providers/opd/{standalone.id}")
    linked_result = api_client.get(f"/api/v1/providers/opd/{linked.id}")
    assert standalone_result.status_code == 200
    assert standalone_result.json()["hospital_id"] is None
    assert linked_result.json()["hospital_id"] == hospital.id
    assert api_client.get("/api/v1/providers/opd/-999999").status_code == 404
    assert api_client.get("/api/v1/providers/not-a-type/1").status_code == 404


def test_speciality_seed_is_idempotent_and_creates_no_provider_links(db_session):
    hospital_links_before = db_session.query(Hospital.id).join(Hospital.specialities).count()
    doctor_links_before = db_session.query(Doctor.id).join(Doctor.specialities).count()
    seed_specialities(db_session)
    seed_specialities(db_session)
    db_session.flush()

    seeded = db_session.query(Speciality).all()
    assert set(SPECIALITIES).issubset({item.name for item in seeded})
    assert len([item for item in seeded if item.name in SPECIALITIES]) == len(SPECIALITIES)
    assert db_session.query(Hospital.id).join(Hospital.specialities).count() == hospital_links_before
    assert db_session.query(Doctor.id).join(Doctor.specialities).count() == doctor_links_before


@pytest.mark.parametrize(
    "flags",
    [
        {"is_verified": True},
        {"is_verified": True, "is_demo": True, "source": "provider-supplied", "verified_at": "2026-01-01"},
    ],
)
def test_provider_verification_checks_reject_invalid_provenance(db_session, flags):
    from datetime import datetime, timezone

    if isinstance(flags.get("verified_at"), str):
        flags["verified_at"] = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(Hospital(
                name="Constraint Hospital", slug="constraint-hospital",
                address="Address", **flags,
            ))
            db_session.flush()
