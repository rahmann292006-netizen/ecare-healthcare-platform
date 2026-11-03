"""Preview or explicitly apply an offline, source-backed provider JSON file.

This tool never fetches provider information. Preview is read-only. Applying is
an explicit operation and defaults to databases whose names end in ``_test``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.database_safety import parse_database_target, require_import_target
from app.models import DiagnosticLab, Doctor, Hospital, Speciality


PROVIDER_MODELS = {
    "hospitals": Hospital,
    "doctors": Doctor,
    "labs": DiagnosticLab,
}
NAME_FIELDS = {"hospitals": "name", "doctors": "full_name", "labs": "name"}
ALLOWED_STATUSES = {"unverified", "pending", "verified", "rejected"}
OPERATIONAL_STATUSES = {"unknown", "operational", "not_operational"}
COMMON_FIELDS = {
    "slug", "source", "source_url", "verified_at", "verification_status",
    "is_verified", "is_demo", "operational_status",
}
FIELDS = {
    "hospitals": COMMON_FIELDS | {
        "name", "description", "hospital_type", "address", "locality", "city",
        "state", "pincode", "latitude", "longitude", "phone", "email",
        "website", "emergency_services", "operating_hours", "speciality_slugs",
    },
    "doctors": COMMON_FIELDS | {
        "full_name", "qualifications", "specializations", "experience_years",
        "languages", "consultation_fee", "phone", "hospital_slug", "speciality_slugs",
    },
    "labs": COMMON_FIELDS | {
        "name", "description", "address", "locality", "city", "state", "phone",
        "home_sample_collection",
    },
}
REQUIRED_FIELDS = {
    "hospitals": {
        "name", "address", "city", "state", "source", "source_url",
        "verified_at", "verification_status", "is_verified", "is_demo",
    },
    "doctors": {
        "full_name", "source", "source_url", "verified_at",
        "verification_status", "is_verified", "is_demo",
    },
    "labs": {
        "name", "address", "city", "state", "source", "source_url",
        "verified_at", "verification_status", "is_verified", "is_demo",
    },
}
TEXT_LIMITS = {
    "hospitals": {"description": None, "hospital_type": 100, "address": None, "locality": 255, "city": 100, "state": 100, "pincode": 20, "phone": 50, "email": 255, "website": 500, "operating_hours": None},
    "doctors": {"qualifications": None, "specializations": 255, "languages": 255, "phone": 50, "hospital_slug": 255},
    "labs": {"description": None, "address": None, "locality": 255, "city": 100, "state": 100, "phone": 50},
}
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class ExistingData:
    """Read-only snapshot of identifiers needed to validate an import."""

    slugs: dict[str, set[str]]
    names: dict[str, list[str]]
    speciality_slugs: set[str]


@dataclass(frozen=True)
class Issue:
    kind: str
    record: str
    field: str | None
    message: str


@dataclass
class ImportPlan:
    records: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def can_apply(self) -> bool:
        return not self.issues


def _nonempty_text(value: Any, max_length: int | None = None) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and (max_length is None or len(value) <= max_length)
    )


def _valid_url(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or len(value) > 1000:
        return False
    try:
        parsed = urlparse(value)
        # Accessing .port also rejects malformed port text.
        parsed.port
        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _record_issue(plan: ImportPlan, kind: str, index: int, message: str, field_name: str | None = None) -> None:
    plan.issues.append(Issue("error", f"{kind}[{index}]", field_name, message))


def _validate_record(kind: str, index: int, row: Any, plan: ImportPlan) -> dict[str, Any] | None:
    label = f"{kind}[{index}]"
    if not isinstance(row, dict):
        plan.issues.append(Issue("error", label, None, "record must be a JSON object"))
        return None

    unknown = set(row) - FIELDS[kind]
    for field_name in sorted(unknown):
        _record_issue(plan, kind, index, "field is not supported", field_name)
    for field_name in sorted(REQUIRED_FIELDS[kind] - set(row)):
        _record_issue(plan, kind, index, "required field is missing", field_name)

    name_field = NAME_FIELDS[kind]
    name = row.get(name_field)
    if not _nonempty_text(name, 255):
        _record_issue(plan, kind, index, "must be non-empty text (maximum 255 characters)", name_field)

    for field_name, max_length in TEXT_LIMITS[kind].items():
        value = row.get(field_name)
        if value is not None and not _nonempty_text(value, max_length):
            _record_issue(plan, kind, index, "must be non-empty text with a supported length or null", field_name)

    raw_slug = row.get("slug")
    if raw_slug is None and isinstance(name, str) and name.strip():
        raw_slug = re.sub(r"[^a-z0-9\s-]", "", name.strip().lower())
        raw_slug = re.sub(r"[\s-]+", "-", raw_slug).strip("-") or "untitled"
    if not _nonempty_text(raw_slug, 255) or not SLUG_PATTERN.fullmatch(raw_slug):
        _record_issue(plan, kind, index, "must be a lowercase URL-safe slug", "slug")

    # These columns are non-nullable and default to Raichur/Karnataka in the
    # database. Require actual location values rather than letting omissions
    # silently acquire those defaults.
    for field_name, max_length in (("city", 100), ("state", 100)):
        location_value = row.get(field_name)
        unknown_location = isinstance(location_value, str) and location_value.strip().casefold() in {
            "unknown", "not known", "unspecified", "n/a", "na", "null",
        }
        if kind in {"hospitals", "labs"} and (
            not _nonempty_text(location_value, max_length) or unknown_location
        ):
            _record_issue(plan, kind, index, "must be supplied explicitly; unknown locations cannot be stored by the current schema", field_name)

    for field_name in ("source",):
        if not _nonempty_text(row.get(field_name), 500):
            _record_issue(plan, kind, index, "source attribution is required", field_name)
    if "source_url" not in row:
        _record_issue(plan, kind, index, "include source_url (use null when the source has no URL)", "source_url")
    elif not _valid_url(row.get("source_url")):
        _record_issue(plan, kind, index, "must be an absolute HTTP(S) URL or null", "source_url")

    status_value = row.get("verification_status")
    verified = row.get("is_verified")
    demo = row.get("is_demo")
    for field_name, value in (("verification_status", status_value), ("is_verified", verified), ("is_demo", demo)):
        if field_name not in row:
            _record_issue(plan, kind, index, "field is required", field_name)
    if not isinstance(status_value, str) or status_value not in ALLOWED_STATUSES:
        _record_issue(plan, kind, index, "unsupported verification status", "verification_status")
    operational_status = row.get("operational_status", "unknown")
    if not isinstance(operational_status, str) or operational_status not in OPERATIONAL_STATUSES:
        _record_issue(plan, kind, index, "unsupported operational status", "operational_status")
    if type(verified) is not bool:
        _record_issue(plan, kind, index, "must be true or false", "is_verified")
    if type(demo) is not bool:
        _record_issue(plan, kind, index, "must be true or false", "is_demo")
    if type(verified) is bool and type(demo) is bool:
        if demo and (verified or status_value != "unverified"):
            _record_issue(plan, kind, index, "sample/demo providers must remain unverified", "is_demo")
        if status_value == "verified" and not verified:
            _record_issue(plan, kind, index, "verified status requires is_verified=true", "verification_status")
        if verified and status_value != "verified":
            _record_issue(plan, kind, index, "is_verified=true requires verification_status=verified", "is_verified")

    verified_at = row.get("verified_at")
    if verified_at is not None:
        if not isinstance(verified_at, str):
            _record_issue(plan, kind, index, "must be an ISO-8601 timestamp or null", "verified_at")
        else:
            try:
                verified_at = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
                if verified_at.utcoffset() is None:
                    raise ValueError
            except ValueError:
                _record_issue(plan, kind, index, "must be an ISO-8601 timestamp or null", "verified_at")
    if verified is True and (verified_at is None or row.get("source_url") is None):
        _record_issue(plan, kind, index, "verified records require a timestamp and evidence source URL", "verified_at")
    if verified is not True and verified_at is not None:
        _record_issue(plan, kind, index, "must be null unless the provider is verified", "verified_at")

    for field_name in ("website",):
        if field_name in row and row[field_name] is not None and not _valid_url(row[field_name]):
            _record_issue(plan, kind, index, "must be an absolute HTTP(S) URL or null", field_name)
            break
    if row.get("email") is not None and (
        not isinstance(row["email"], str)
        or len(row["email"]) > 255
        or not EMAIL_PATTERN.fullmatch(row["email"])
    ):
        _record_issue(plan, kind, index, "must be a valid email address or null", "email")

    int_fields = {"experience_years"} if kind == "doctors" else set()
    for field_name in int_fields:
        value = row.get(field_name)
        if value is not None and (type(value) is not int or value < 0):
            _record_issue(plan, kind, index, "must be a non-negative integer or null", field_name)
    numeric_fields = {"latitude", "longitude"} if kind == "hospitals" else set()
    numeric_fields |= {"consultation_fee"} if kind == "doctors" else set()
    for field_name in numeric_fields:
        value = row.get(field_name)
        if value is None:
            continue
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            number = Decimal("NaN")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not number.is_finite():
            _record_issue(plan, kind, index, "must be a finite number or null", field_name)
        elif field_name == "latitude" and not -90 <= value <= 90:
            _record_issue(plan, kind, index, "is outside the valid range", field_name)
        elif field_name == "longitude" and not -180 <= value <= 180:
            _record_issue(plan, kind, index, "is outside the valid range", field_name)
        elif field_name == "consultation_fee" and value < 0:
            _record_issue(plan, kind, index, "must not be negative", field_name)
        elif field_name == "consultation_fee" and number > Decimal("99999999.99"):
            _record_issue(plan, kind, index, "exceeds the database precision", field_name)
        elif field_name == "consultation_fee" and max(0, -number.as_tuple().exponent) > 2:
            _record_issue(plan, kind, index, "supports at most two decimal places", field_name)
        elif field_name in {"latitude", "longitude"} and max(0, -number.as_tuple().exponent) > 6:
            _record_issue(plan, kind, index, "supports at most six decimal places", field_name)
    for field_name in {"emergency_services", "home_sample_collection"} & set(row):
        if row[field_name] is not None and type(row[field_name]) is not bool:
            _record_issue(plan, kind, index, "must be true, false, or null", field_name)

    speciality_slugs = row.get("speciality_slugs", [])
    if kind == "labs" and "speciality_slugs" in row:
        _record_issue(plan, kind, index, "structured speciality links are unsupported for labs", "speciality_slugs")
    elif not isinstance(speciality_slugs, list) or any(not _nonempty_text(item, 140) for item in speciality_slugs):
        _record_issue(plan, kind, index, "must be an array of speciality slugs", "speciality_slugs")
    elif len({item.casefold() for item in speciality_slugs}) != len(speciality_slugs):
        _record_issue(plan, kind, index, "contains duplicate speciality slugs", "speciality_slugs")
    if kind == "doctors" and row.get("hospital_slug") is not None and not _nonempty_text(row.get("hospital_slug"), 255):
        _record_issue(plan, kind, index, "must be a hospital slug or null", "hospital_slug")

    result = dict(row)
    result["operational_status"] = (
        operational_status
        if isinstance(operational_status, str) and operational_status in OPERATIONAL_STATUSES
        else "unknown"
    )
    if isinstance(raw_slug, str):
        result["slug"] = raw_slug
    if isinstance(verified_at, datetime):
        result["verified_at"] = verified_at
    result["speciality_slugs"] = speciality_slugs if isinstance(speciality_slugs, list) else []
    if kind == "doctors":
        result["hospital_slug"] = row.get("hospital_slug")
    return result


def build_preview(payload: Any, existing: ExistingData) -> ImportPlan:
    """Validate a manifest and compare it with a read-only database snapshot."""
    plan = ImportPlan()
    if not isinstance(payload, dict) or payload.get("version") != 1:
        plan.issues.append(Issue("error", "manifest", "version", "manifest version must be 1"))
        return plan
    unsupported = set(payload) - {"version", *PROVIDER_MODELS}
    for field_name in sorted(unsupported):
        plan.issues.append(Issue("error", "manifest", field_name, "section is not supported"))

    seen_slugs: dict[str, set[str]] = {kind: set() for kind in PROVIDER_MODELS}
    seen_names: dict[str, list[tuple[str, str]]] = {kind: [] for kind in PROVIDER_MODELS}
    imported_hospital_slugs: set[str] = set()
    for kind in PROVIDER_MODELS:
        rows = payload.get(kind, [])
        if not isinstance(rows, list):
            plan.issues.append(Issue("error", kind, None, "section must be an array"))
            continue
        for index, row in enumerate(rows):
            before_count = len(plan.issues)
            record = _validate_record(kind, index, row, plan)
            if record is None:
                continue
            slug = record.get("slug")
            if isinstance(slug, str):
                folded_slug = slug.casefold()
                if folded_slug in seen_slugs[kind] or folded_slug in {item.casefold() for item in existing.slugs.get(kind, set())}:
                    _record_issue(plan, kind, index, "slug already exists in this file or database", "slug")
                seen_slugs[kind].add(folded_slug)
                if kind == "hospitals":
                    imported_hospital_slugs.add(slug)
            display_name = row.get(NAME_FIELDS[kind]) if isinstance(row, dict) else None
            if isinstance(display_name, str):
                normalized = _normalized_name(display_name)
                candidates = existing.names.get(kind, []) + [name for _, name in seen_names[kind]]
                if any(
                    normalized == _normalized_name(candidate)
                    or SequenceMatcher(None, normalized, _normalized_name(candidate)).ratio() >= 0.92
                    for candidate in candidates
                ):
                    plan.issues.append(Issue("review", f"{kind}[{index}]", NAME_FIELDS[kind], "name resembles an existing or incoming provider; human review required"))
                seen_names[kind].append((slug if isinstance(slug, str) else "", display_name))
            for speciality_slug in record["speciality_slugs"]:
                if speciality_slug not in existing.speciality_slugs:
                    _record_issue(plan, kind, index, "speciality slug does not exist in the database", "speciality_slugs")
            if kind == "doctors" and record.get("hospital_slug"):
                hospital_slug = record["hospital_slug"]
                if not _nonempty_text(hospital_slug, 255):
                    _record_issue(plan, kind, index, "must be a hospital slug or null", "hospital_slug")
                elif hospital_slug not in imported_hospital_slugs | existing.slugs.get("hospitals", set()):
                    _record_issue(plan, kind, index, "hospital slug does not exist in this file or database", "hospital_slug")
            if len(plan.issues) == before_count:
                plan.records.append((kind, record))
    if plan.issues:
        # A preview may show individually valid rows, but applying any part of
        # a conflicted manifest is intentionally all-or-nothing.
        return plan
    return plan


def load_existing_data(session: Session) -> ExistingData:
    """Read only the columns required for validation and duplicate checks."""
    slugs: dict[str, set[str]] = {}
    names: dict[str, list[str]] = {}
    for kind, model in PROVIDER_MODELS.items():
        name_field = getattr(model, NAME_FIELDS[kind])
        rows = session.query(model.slug, name_field).all()
        slugs[kind] = {row[0] for row in rows}
        names[kind] = [row[1] for row in rows]
    speciality_slugs = {
        slug for (slug,) in session.query(Speciality.slug).filter(Speciality.is_active.is_(True)).all()
    }
    return ExistingData(slugs=slugs, names=names, speciality_slugs=speciality_slugs)


def preview_manifest(session: Session, payload: Any) -> ImportPlan:
    """Build a preview using database reads only; this function has no write path."""
    return build_preview(payload, load_existing_data(session))


def _model_values(kind: str, record: dict[str, Any]) -> dict[str, Any]:
    values = {key: value for key, value in record.items() if key not in {"speciality_slugs", "hospital_slug"}}
    if kind == "doctors":
        values["specializations"] = record.get("specializations")
    return values


def apply_preview(session: Session, plan: ImportPlan) -> None:
    """Insert a clean plan as one transaction; caller owns commit/rollback."""
    if not plan.can_apply:
        raise ValueError("Import plan has validation errors or review conflicts")
    hospitals_by_slug = {
        row.slug: row for row in session.query(Hospital).all()
    }
    specialities_by_slug = {
        row.slug: row for row in session.query(Speciality).filter(Speciality.is_active.is_(True)).all()
    }
    for kind, record in plan.records:
        values = _model_values(kind, record)
        if kind == "hospitals":
            provider = Hospital(**values)
            provider.specialities = [specialities_by_slug[item] for item in record["speciality_slugs"]]
        elif kind == "doctors":
            hospital_slug = record.get("hospital_slug")
            provider = Doctor(**values)
            if hospital_slug:
                provider.hospital = hospitals_by_slug[hospital_slug]
            provider.specialities = [specialities_by_slug[item] for item in record["speciality_slugs"]]
        else:
            provider = DiagnosticLab(**values)
        session.add(provider)
        session.flush()
        if kind == "hospitals":
            hospitals_by_slug[provider.slug] = provider


def ensure_safe_apply_database(
    database_url: str | None,
    allow_non_test: bool = False,
    *,
    environment: str | None = None,
    confirmation: str | None = None,
) -> str:
    """Return a classified target name; never expose URL parsing details."""
    return require_import_target(
        database_url,
        environment,
        allow_non_test=allow_non_test,
        confirmation=confirmation,
    )


def _load_manifest(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        # JSON parser errors can include source text; do not echo exception text.
        raise ValueError("Could not read a valid UTF-8 JSON manifest") from None


def _report(plan: ImportPlan) -> dict[str, Any]:
    create_counts = {kind: 0 for kind in PROVIDER_MODELS}
    for kind, _ in plan.records:
        create_counts[kind] += 1
    return {
        "records_to_create": create_counts,
        "total_to_create": len(plan.records),
        "conflicts": [issue.__dict__ for issue in plan.issues if issue.kind == "review"],
        "validation_errors": [issue.__dict__ for issue in plan.issues if issue.kind == "error"],
        "can_apply": plan.can_apply,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or apply an offline provider JSON manifest")
    parser.add_argument("manifest", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate and preview only (default)")
    mode.add_argument("--apply", action="store_true", help="Insert the entire clean plan in one transaction")
    parser.add_argument(
        "--allow-non-test-database",
        action="store_true",
        help="Allow a staging/production import only after environment checks and typing the exact database name",
    )
    args = parser.parse_args()
    if args.allow_non_test_database and not args.apply:
        parser.error("--allow-non-test-database is only valid with --apply")

    try:
        payload = _load_manifest(args.manifest)
        database_url = os.environ.get("DATABASE_URL")
        environment = os.environ.get("ECARE_DATABASE_ENV")
        confirmation = None
        if args.allow_non_test_database:
            target_name, _ = parse_database_target(database_url)
            if not target_name.casefold().endswith("_test"):
                print(
                    "WARNING: non-test provider import target "
                    f"environment={environment or 'unset'} database={target_name}."
                )
                confirmation = input("Type the exact database name to continue: ")
        database_name = ensure_safe_apply_database(
            database_url,
            allow_non_test=args.allow_non_test_database,
            environment=environment,
            confirmation=confirmation,
        )
        with SessionLocal() as session:
            existing = load_existing_data(session)
            plan = build_preview(payload, existing)
            print(json.dumps(_report(plan), indent=2))
            if not args.apply or not plan.can_apply:
                return 0 if plan.can_apply else 2
            apply_preview(session, plan)
            session.commit()
            print(json.dumps({"applied": len(plan.records), "database": database_name}))
        return 0
    except ValueError:
        print("Import refused due to invalid input or a database safety check; details suppressed.")
        return 2
    except Exception as exc:
        print(f"Import failed ({type(exc).__name__}); details suppressed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
