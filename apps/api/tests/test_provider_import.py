"""Pure validation and safety tests for the offline provider importer."""

import pytest

from scripts.import_providers import (
    ExistingData,
    _model_values,
    build_preview,
    ensure_safe_apply_database,
    preview_manifest,
)


def _existing():
    return ExistingData(
        slugs={"hospitals": set(), "doctors": set(), "labs": set()},
        names={"hospitals": [], "doctors": [], "labs": []},
        speciality_slugs={"cardiology"},
    )


def _provider(**overrides):
    # Synthetic reserved test data, used only for pure validation; never persisted.
    row = {
        "name": "Fixture Hospital",
        "address": "Fixture address",
        "city": "Fixture city",
        "state": "Fixture state",
        "source": "Test fixture source",
        "source_url": "https://source.invalid/fixture",
        "verified_at": None,
        "verification_status": "unverified",
        "is_verified": False,
        "is_demo": True,
        "speciality_slugs": [],
    }
    row.update(overrides)
    return row


def _manifest(*, hospitals=None, doctors=None, labs=None):
    return {
        "version": 1,
        "hospitals": hospitals or [],
        "doctors": doctors or [],
        "labs": labs or [],
    }


def test_valid_provider_types_and_explicit_speciality_mapping_are_accepted():
    hospital = _provider(slug="fixture-hospital", speciality_slugs=["cardiology"])
    doctor = {
        "full_name": "Fixture Doctor",
        "hospital_slug": "fixture-hospital",
        "source": "Test fixture source",
        "source_url": None,
        "verified_at": None,
        "verification_status": "unverified",
        "is_verified": False,
        "is_demo": True,
        "speciality_slugs": ["cardiology"],
    }
    lab = _provider(name="Fixture Lab", address="Fixture lab address", speciality_slugs=None)
    lab.pop("speciality_slugs")
    plan = build_preview(
        _manifest(hospitals=[hospital], doctors=[doctor], labs=[lab]), _existing()
    )

    assert plan.can_apply
    assert len(plan.records) == 3
    assert [kind for kind, _ in plan.records] == ["hospitals", "doctors", "labs"]


def test_missing_required_fields_and_nonempty_location_values_are_rejected():
    plan = build_preview(_manifest(hospitals=[{"name": "Missing Address"}]), _existing())

    assert not plan.can_apply
    assert {issue.field for issue in plan.issues} >= {"address", "city", "state", "source"}


def test_unknown_location_placeholder_is_rejected_instead_of_saved_as_a_default():
    plan = build_preview(_manifest(hospitals=[_provider(city="Unknown")]), _existing())

    assert any(issue.field == "city" for issue in plan.issues)


def test_duplicate_slugs_in_manifest_are_rejected():
    plan = build_preview(
        _manifest(hospitals=[_provider(slug="same-slug"), _provider(name="Other Hospital", slug="same-slug")]),
        _existing(),
    )

    assert any(issue.field == "slug" and "already exists" in issue.message for issue in plan.issues)


def test_existing_slug_is_rejected():
    existing = ExistingData(
        slugs={"hospitals": {"fixture-hospital"}, "doctors": set(), "labs": set()},
        names={"hospitals": [], "doctors": [], "labs": []},
        speciality_slugs=set(),
    )
    plan = build_preview(_manifest(hospitals=[_provider(slug="fixture-hospital")]), existing)

    assert any(issue.field == "slug" for issue in plan.issues)


def test_potential_duplicate_name_requires_human_review_and_blocks_apply():
    existing = ExistingData(
        slugs={"hospitals": set(), "doctors": set(), "labs": set()},
        names={"hospitals": ["Fixture Hospital!"], "doctors": [], "labs": []},
        speciality_slugs=set(),
    )
    plan = build_preview(_manifest(hospitals=[_provider()]), existing)

    assert not plan.can_apply
    assert any(issue.kind == "review" for issue in plan.issues)


def test_unknown_speciality_slug_is_rejected_without_inferring_from_text():
    plan = build_preview(
        _manifest(hospitals=[_provider(speciality_slugs=["not-in-vocabulary"])]), _existing()
    )

    assert any(issue.field == "speciality_slugs" for issue in plan.issues)


def test_missing_source_attribution_is_rejected():
    row = _provider()
    del row["source"]
    plan = build_preview(_manifest(hospitals=[row]), _existing())

    assert any(issue.field == "source" for issue in plan.issues)


def test_demo_records_must_be_unverified_and_verified_records_need_evidence_timestamp():
    demo = _provider()
    plan = build_preview(_manifest(hospitals=[demo]), _existing())
    assert plan.can_apply
    assert plan.records[0][1]["is_verified"] is False

    invalid_demo = _provider(is_demo=True, verification_status="verified", is_verified=True)
    plan = build_preview(_manifest(hospitals=[invalid_demo]), _existing())
    assert any(issue.field == "is_demo" for issue in plan.issues)

    no_evidence_time = _provider(verification_status="verified", is_verified=True)
    plan = build_preview(_manifest(hospitals=[no_evidence_time]), _existing())
    assert any(issue.field == "verified_at" for issue in plan.issues)


def test_preview_uses_read_only_session_and_has_no_write_methods():
    class Query:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    class ReadOnlySession:
        def __init__(self):
            self.queries = 0

        def query(self, *_entities):
            self.queries += 1
            return Query()

        def add(self, *_args):
            raise AssertionError("preview must not add rows")

        def flush(self, *_args):
            raise AssertionError("preview must not flush")

        def commit(self, *_args):
            raise AssertionError("preview must not commit")

    session = ReadOnlySession()
    plan = preview_manifest(session, _manifest(hospitals=[_provider()]))

    assert plan.can_apply
    assert session.queries == 4


@pytest.mark.parametrize(
    "url,environment,allow_non_test,confirmation,accepted",
    [
        ("postgresql+psycopg://localhost/ecare_test", "test", False, None, True),
        ("postgresql+psycopg://db.prod.example/ecare_test", "test", False, None, False),
        ("postgresql+psycopg://db.prod.example/ecare_test", "test", True, "ecare_test", False),
        ("postgresql+psycopg://localhost/ecare", "test", True, "ecare", False),
        ("postgresql+psycopg://localhost/ecare_dev", "test", False, None, False),
        ("postgresql+psycopg://db.prod.example/ecare_prod", "production", False, None, False),
        ("postgresql+psycopg://db.prod.example/ecare_prod", "production", True, None, False),
        ("postgresql+psycopg://db.prod.example/ecare_prod", "production", True, "other", False),
        ("postgresql+psycopg://db.prod.example/ecare_prod", "production", True, "ecare_prod", True),
        ("postgresql+psycopg:///ecare_test", "test", False, None, False),
        ("not-a-database-url", "test", False, None, False),
    ],
)
def test_apply_target_database_safety(url, environment, allow_non_test, confirmation, accepted):
    if accepted:
        assert ensure_safe_apply_database(
            url,
            allow_non_test,
            environment=environment,
            confirmation=confirmation,
        ) in {"ecare_test", "ecare_prod"}
    else:
        with pytest.raises(ValueError):
            ensure_safe_apply_database(
                url,
                allow_non_test,
                environment=environment,
                confirmation=confirmation,
            )


def test_duplicate_speciality_mapping_values_are_rejected():
    plan = build_preview(
        _manifest(hospitals=[_provider(speciality_slugs=["cardiology", "cardiology"])]), _existing()
    )

    assert any(issue.field == "speciality_slugs" for issue in plan.issues)


@pytest.mark.parametrize("operational_status", ["unknown", "operational", "not_operational"])
@pytest.mark.parametrize("emergency_services", [None, True, False])
def test_importer_preserves_status_and_nullable_hospital_service(
    operational_status, emergency_services
):
    row = _provider(
        operational_status=operational_status,
        emergency_services=emergency_services,
    )
    plan = build_preview(_manifest(hospitals=[row]), _existing())

    assert plan.can_apply
    _, record = plan.records[0]
    values = _model_values("hospitals", record)
    assert values["operational_status"] == operational_status
    assert values["emergency_services"] is emergency_services


@pytest.mark.parametrize("home_sample_collection", [None, True, False])
def test_importer_preserves_nullable_lab_home_collection(home_sample_collection):
    row = _provider(name="Fixture Lab", home_sample_collection=home_sample_collection)
    row.pop("speciality_slugs")
    row["operational_status"] = "unknown"
    plan = build_preview(_manifest(labs=[row]), _existing())

    assert plan.can_apply
    _, record = plan.records[0]
    values = _model_values("labs", record)
    assert values["home_sample_collection"] is home_sample_collection
    assert values["operational_status"] == "unknown"


def test_importer_defaults_missing_operational_status_to_unknown_and_rejects_invalid_value():
    row = _provider()
    plan = build_preview(_manifest(hospitals=[row]), _existing())
    assert plan.can_apply
    assert plan.records[0][1]["operational_status"] == "unknown"

    invalid = _provider(operational_status="active")
    plan = build_preview(_manifest(hospitals=[invalid]), _existing())
    assert any(issue.field == "operational_status" for issue in plan.issues)


def test_pytest_database_guard_requires_local_explicit_test_target(monkeypatch):
    from tests.database_guard import require_test_database

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/ecare_test")
    monkeypatch.setenv("ECARE_DATABASE_ENV", "test")
    require_test_database()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db.prod.example/ecare_test")
    with pytest.raises(pytest.UsageError):
        require_test_database()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/ecare")
    with pytest.raises(pytest.UsageError):
        require_test_database()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg:///ecare_test")
    with pytest.raises(pytest.UsageError):
        require_test_database()
    monkeypatch.delenv("ECARE_DATABASE_ENV")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/ecare_test")
    with pytest.raises(pytest.UsageError):
        require_test_database()
