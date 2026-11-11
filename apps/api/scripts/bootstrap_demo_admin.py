"""Interactively create the first admin in the verified local ecare_test DB."""

from __future__ import annotations

import getpass
import os
from pathlib import Path
import re
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from scripts.demo_database import (  # noqa: E402
    build_test_database_url,
    configure_test_environment,
    read_configured_database_url,
    verify_test_database,
)


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BOOTSTRAP_LOCK_ID = 8_301_459_314_521


def main() -> int:
    target = build_test_database_url(read_configured_database_url())
    secret_key = os.environ.get("ECARE_SECRET_KEY")
    if not secret_key:
        print("Admin bootstrap stopped: ECARE_SECRET_KEY must be provided in the process environment.")
        return 1

    configure_test_environment(target)

    try:
        from app.auth import hash_password
        from app.database import SessionLocal, engine
        from app.models import User

        revision = verify_test_database(engine, target.username or "")
        print(f"Verified loopback ecare_test on port 5432 at revision {revision}.")
        with SessionLocal() as session:
            active_admin_exists = (
                session.query(User.id)
                .filter(User.role == "admin", User.is_active.is_(True))
                .first()
                is not None
            )
        if active_admin_exists:
            print("An active admin already exists; no account was changed.")
            return 1

        email = input("New admin email: ").strip().casefold()
        if not EMAIL_PATTERN.fullmatch(email):
            print("Admin bootstrap stopped: enter a valid email address.")
            return 1
        full_name = input("New admin display name: ").strip()
        if not full_name or len(full_name) > 255:
            print("Admin bootstrap stopped: display name must be 1-255 characters.")
            return 1
        password = getpass.getpass("New admin password (hidden): ")
        confirmation = getpass.getpass("Confirm admin password (hidden): ")
        password_bytes = password.encode("utf-8")
        if len(password_bytes) < 12 or len(password_bytes) > 72:
            print("Admin bootstrap stopped: password must be 12-72 UTF-8 bytes.")
            return 1
        if password != confirmation:
            print("Admin bootstrap stopped: passwords did not match.")
            return 1
        if input("Type ecare_test to create this admin: ").strip() != "ecare_test":
            print("Confirmation did not match; no account was changed.")
            return 1

        with SessionLocal.begin() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": BOOTSTRAP_LOCK_ID},
            )
            active_admin = (
                session.query(User.id)
                .filter(User.role == "admin", User.is_active.is_(True))
                .first()
            )
            if active_admin:
                print("An active admin was created concurrently; no account was changed.")
                return 1
            if session.query(User.id).filter(User.email == email).first():
                print("That email already belongs to an account; no account was changed.")
                return 1
            session.add(
                User(
                    email=email,
                    full_name=full_name,
                    hashed_password=hash_password(password),
                    role="admin",
                    is_active=True,
                    is_verified=False,
                )
            )
        password = ""
        confirmation = ""
        print("Admin bootstrap completed. Credentials were not displayed.")
        return 0
    except (RuntimeError, ValueError, SQLAlchemyError) as error:
        print(f"Admin bootstrap stopped ({type(error).__name__}); no credentials were displayed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
