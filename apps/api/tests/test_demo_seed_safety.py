"""Offline tests for local demo seeding safeguards and synthetic fixtures."""

import pytest

from scripts.demo_database import build_test_database_url, read_configured_database_url
from scripts.seed_demo_data import (
    DEMO_SOURCE,
    _read_manifests,
    _validate_demo_record,
    has_private_opd,
    sample_schedule,
)


def test_database_url_is_forced_to_loopback_ecare_test():
    target = build_test_database_url(
        "postgresql+psycopg://demo_user:unit-test-only@remote.example:5432/production"
    )

    assert target.username == "demo_user"
    assert target.password == "unit-test-only"
    assert target.host == "127.0.0.1"
    assert target.port == 5432
    assert target.database == "ecare_test"


def test_configured_url_comes_from_process_environment(monkeypatch):
    configured = "postgresql://demo_user:unit-test-only@remote.example:5432/production"
    monkeypatch.setenv("DATABASE_URL", configured)

    assert read_configured_database_url() == configured


@pytest.mark.parametrize(
    "configured_url",
    [
        "sqlite:///ecare_test",
        "postgresql://@127.0.0.1/ecare_test",
        "not a database URL",
    ],
)
def test_database_url_requires_configured_postgresql_user(configured_url):
    with pytest.raises(ValueError):
        build_test_database_url(configured_url)


def test_demo_provider_and_package_manifests_are_unverified():
    providers, packages = _read_manifests()

    for collection in providers.values():
        if not isinstance(collection, list):
            continue
        for record in collection:
            _validate_demo_record(record, record["slug"])
            assert record["source"] == DEMO_SOURCE

    for record in packages["packages"]:
        _validate_demo_record(
            record,
            record["slug"],
            require_verification_status=False,
        )
        assert record["source"] == DEMO_SOURCE


def test_seeded_doctor_schedule_has_explicit_demo_opd_slots():
    schedule = sample_schedule("DEMO Example Hospital")

    assert set(schedule["privateOpd"]) == {"1", "2", "3", "4", "5"}
    assert all(
        entry["start"] < entry["end"]
        and "DEMO" in entry["location"]
        for entry in schedule["privateOpd"].values()
    )
    assert has_private_opd(schedule)
    assert not has_private_opd({"privateOpd": {"1": {"start": "09:00", "end": "12:00"}}})
