"""Idempotently seed fictional demo listings and packages into ecare_test."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from scripts.demo_database import (
    build_test_database_url,
    configure_test_environment,
    read_configured_database_url,
    verify_test_database,
)


PROVIDER_MANIFEST = API_ROOT / "docs" / "demo-provider-expansion.json"
PACKAGE_MANIFEST = API_ROOT / "docs" / "demo-package-manifest.json"
DEMO_SOURCE = "Synthetic fictional demo record; no real provider or evidence"
DEMO_FEE = Decimal("500.00")


def has_private_opd(schedule: object) -> bool:
    if not isinstance(schedule, dict):
        return False
    sessions = schedule.get("privateOpd")
    if not isinstance(sessions, dict):
        return False
    return any(
        isinstance(session, dict)
        and isinstance(session.get("start"), str)
        and isinstance(session.get("end"), str)
        and isinstance(session.get("location"), str)
        and bool(session["location"].strip())
        for session in sessions.values()
    )


def sample_schedule(hospital_name: str) -> dict:
    """Return a visibly fictional, valid weekday OPD schedule for seeded doctors."""
    location = f"DEMO OPD room at {hospital_name}"
    return {
        "privateOpd": {
            str(day): {"start": "09:00", "end": "12:00", "location": location}
            for day in range(1, 6)
        },
        "governmentDuty": {},
        "durationMinutes": 30,
        "unavailableDays": [0, 6],
    }


def _read_manifests() -> tuple[dict, dict]:
    try:
        providers = json.loads(PROVIDER_MANIFEST.read_text(encoding="utf-8"))
        packages = json.loads(PACKAGE_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Demo manifest could not be loaded ({type(error).__name__})") from None
    for kind in ("hospitals", "doctors", "labs"):
        if not isinstance(providers.get(kind), list):
            raise RuntimeError(f"Provider manifest is missing the {kind} list")
    if not isinstance(packages.get("packages"), list):
        raise RuntimeError("Package manifest is missing its packages list")
    return providers, packages


def _validate_demo_record(
    record: dict, label: str, *, require_verification_status: bool = True
) -> None:
    if (
        record.get("is_demo") is not True
        or record.get("is_verified") is not False
        or record.get("verified_at") is not None
        or (
            require_verification_status
            and record.get("verification_status") != "unverified"
        )
        or not str(record.get("name", record.get("full_name", ""))).startswith("DEMO ")
        or DEMO_SOURCE not in str(record.get("source", ""))
    ):
        raise RuntimeError(f"{label} is not explicitly marked as fictional and unverified")


def _specialities(session: Session, slugs: list[str], model) -> list:
    if not slugs:
        return []
    return session.query(model).filter(model.slug.in_(slugs)).all()


def _count_plan(session: Session, providers: dict, packages: dict) -> dict[str, int]:
    from app.models import Doctor, DiagnosticLab, Hospital, Package

    counts = {
        "hospitals_to_add": 0,
        "doctors_to_add": 0,
        "labs_to_add": 0,
        "packages_to_add": 0,
        "doctors_needing_booking_fields": 0,
        "unlinked_demo_doctors_not_in_manifest": 0,
    }
    manifest_doctor_slugs = {row["slug"] for row in providers["doctors"]}
    for row in providers["hospitals"]:
        counts["hospitals_to_add"] += int(
            session.query(Hospital.id).filter_by(slug=row["slug"]).first() is None
        )
    for row in providers["doctors"]:
        doctor = session.query(Doctor).filter_by(slug=row["slug"]).first()
        if doctor is None:
            counts["doctors_to_add"] += 1
            counts["doctors_needing_booking_fields"] += 1
        elif doctor.is_demo and (
            doctor.consultation_fee is None or not has_private_opd(doctor.schedule_json)
        ):
            counts["doctors_needing_booking_fields"] += 1
    counts["unlinked_demo_doctors_not_in_manifest"] = (
        session.query(Doctor)
        .filter(
            Doctor.is_demo.is_(True),
            Doctor.is_active.is_(True),
            Doctor.hospital_id.is_(None),
        )
        .filter(~Doctor.slug.in_(manifest_doctor_slugs))
        .count()
    )
    for row in providers["labs"]:
        counts["labs_to_add"] += int(
            session.query(DiagnosticLab.id).filter_by(slug=row["slug"]).first() is None
        )
    for row in packages["packages"]:
        counts["packages_to_add"] += int(
            session.query(Package.id).filter_by(slug=row["slug"]).first() is None
        )
    return counts


def seed_demo_data(session: Session, *, apply: bool) -> dict[str, int]:
    """Insert only missing synthetic records; fill only missing demo booking fields."""
    from app.models import (
        Doctor,
        DiagnosticLab,
        Hospital,
        Package,
        PackageInclusion,
        Speciality,
    )

    providers, packages = _read_manifests()
    for kind in ("hospitals", "doctors", "labs"):
        for row in providers[kind]:
            _validate_demo_record(row, f"{kind} record {row.get('slug', '<missing slug>')}")
    for row in packages["packages"]:
        _validate_demo_record(
            row,
            f"package {row.get('slug', '<missing slug>')}",
            require_verification_status=False,
        )

    stats = _count_plan(session, providers, packages)
    if not apply:
        return stats

    from scripts.seed_specialities import seed_specialities

    seed_specialities(session)
    session.flush()
    referenced_specialities = {
        slug
        for collection in providers.values()
        if isinstance(collection, list)
        for row in collection
        for slug in row.get("speciality_slugs", [])
    }
    known_specialities = {
        row.slug for row in session.query(Speciality.slug).all()
    }
    missing_specialities = referenced_specialities - known_specialities
    if missing_specialities:
        raise RuntimeError(
            "Demo records reference unsupported specialities: "
            + ", ".join(sorted(missing_specialities))
        )

    for row in providers["hospitals"]:
        existing = session.query(Hospital).filter_by(slug=row["slug"]).one_or_none()
        if existing is None:
            fields = {
                key: value
                for key, value in row.items()
                if key not in {"speciality_slugs", "is_demo", "is_verified"}
            }
            existing = Hospital(**fields, is_demo=True, is_verified=False)
            session.add(existing)
            session.flush()
        elif not existing.is_demo:
            raise RuntimeError(f"Slug collision with non-demo hospital: {row['slug']}")
        existing_specialities = {item.slug for item in existing.specialities}
        for speciality in _specialities(session, row.get("speciality_slugs", []), Speciality):
            if speciality.slug not in existing_specialities:
                existing.specialities.append(speciality)

    hospitals_by_slug = {
        row.slug: row for row in session.query(Hospital).filter(Hospital.is_demo.is_(True)).all()
    }
    for row in providers["labs"]:
        existing = session.query(DiagnosticLab).filter_by(slug=row["slug"]).one_or_none()
        if existing is None:
            fields = {
                key: value
                for key, value in row.items()
                if key not in {"is_demo", "is_verified"}
            }
            session.add(DiagnosticLab(**fields, is_demo=True, is_verified=False))
        elif not existing.is_demo:
            raise RuntimeError(f"Slug collision with non-demo laboratory: {row['slug']}")

    for row in providers["doctors"]:
        existing = session.query(Doctor).filter_by(slug=row["slug"]).one_or_none()
        hospital = hospitals_by_slug.get(row.get("hospital_slug"))
        if hospital is None:
            raise RuntimeError(f"Demo doctor has no linked demo hospital: {row['slug']}")
        if existing is None:
            fields = {
                key: value
                for key, value in row.items()
                if key not in {
                    "speciality_slugs",
                    "hospital_slug",
                    "consultation_fee",
                    "is_demo",
                    "is_verified",
                }
            }
            existing = Doctor(
                **fields,
                hospital_id=hospital.id,
                consultation_fee=DEMO_FEE,
                schedule_json=sample_schedule(hospital.name),
                is_demo=True,
                is_verified=False,
            )
            session.add(existing)
            session.flush()
        elif not existing.is_demo:
            raise RuntimeError(f"Slug collision with non-demo doctor: {row['slug']}")
        else:
            if existing.consultation_fee is None:
                existing.consultation_fee = DEMO_FEE
            if not has_private_opd(existing.schedule_json):
                existing.schedule_json = sample_schedule(hospital.name)
        existing_specialities = {item.slug for item in existing.specialities}
        for speciality in _specialities(session, row.get("speciality_slugs", []), Speciality):
            if speciality.slug not in existing_specialities:
                existing.specialities.append(speciality)

    for row in packages["packages"]:
        existing = session.query(Package).filter_by(slug=row["slug"]).one_or_none()
        inclusions = row.get("inclusions", [])
        if existing is None:
            fields = {
                key: value
                for key, value in row.items()
                if key not in {"inclusions", "is_demo", "is_verified"}
            }
            existing = Package(**fields, is_demo=True, is_verified=False)
            session.add(existing)
            session.flush()
        elif not existing.is_demo:
            raise RuntimeError(f"Slug collision with non-demo package: {row['slug']}")
        existing_inclusions = {item.test_name for item in existing.inclusions}
        for order, test_name in enumerate(inclusions):
            if test_name not in existing_inclusions:
                session.add(
                    PackageInclusion(
                        package_id=existing.id,
                        test_name=test_name,
                        display_order=order,
                    )
                )
    session.flush()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Insert missing fictional records (default is a read-only dry run)",
    )
    parser.add_argument(
        "--confirm-target",
        help="Must be exactly ecare_test when --apply is used",
    )
    args = parser.parse_args()
    if args.apply and args.confirm_target != "ecare_test":
        parser.error("--apply requires --confirm-target ecare_test")
    if not args.apply and args.confirm_target:
        parser.error("--confirm-target is only valid with --apply")

    target = build_test_database_url(read_configured_database_url())
    configure_test_environment(target)
    engine = create_engine(
        target,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        revision = verify_test_database(engine, target.username or "")
        print(f"Verified loopback ecare_test on port 5432 at revision {revision}.")
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        with factory() as session:
            if args.apply:
                if input("Type ecare_test to add missing fictional records: ").strip() != "ecare_test":
                    print("Confirmation did not match; no records were changed.")
                    return 1
                with session.begin():
                    stats = seed_demo_data(session, apply=True)
            else:
                stats = seed_demo_data(session, apply=False)
        mode = "Applied" if args.apply else "Read-only plan"
        print(mode + ": " + ", ".join(f"{key}={value}" for key, value in stats.items()))
        return 0
    except (OSError, RuntimeError, ValueError, SQLAlchemyError) as error:
        print(f"Demo seeding stopped ({type(error).__name__}); no credentials were displayed.")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())