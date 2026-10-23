"""Idempotently add the approved speciality vocabulary.

Run explicitly with DATABASE_URL set in the process environment. This script
does not create provider-to-speciality links or any provider records.
"""

from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Speciality


SPECIALITIES = (
    "General Medicine",
    "Cardiology",
    "Orthopaedics",
    "Paediatrics",
    "Gynaecology",
    "ENT",
    "Dermatology",
    "Ophthalmology",
    "Dentistry",
    "Diabetology",
)


def seed_specialities(session) -> None:
    rows = [
        {"name": name, "slug": "-".join(name.lower().split())}
        for name in SPECIALITIES
    ]
    session.execute(
        insert(Speciality.__table__).values(rows).on_conflict_do_nothing(
            index_elements=["slug"]
        )
    )


def main() -> None:
    with SessionLocal.begin() as session:
        seed_specialities(session)


if __name__ == "__main__":
    main()
