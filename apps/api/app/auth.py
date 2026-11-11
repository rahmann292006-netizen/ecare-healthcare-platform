"""Authentication and authorization for eCare API.

This module provides:
- Password hashing with bcrypt (never stores plaintext passwords).
- JWT access token creation and verification.
- Current-user dependency for authenticated endpoints.
- Role-based authorization dependencies (patient, provider, admin).
- A development-header shortcut is limited to explicit development and test
  environments; production directory writes require an active administrator.

Security notes:
- Secrets (SECRET_KEY) must come from environment variables only.
- Passwords are hashed before storage; plaintext passwords never persist.
- Tokens are not logged or printed.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Header, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db

_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plaintext password.

    Bcrypt has a 72-byte input limit; longer passwords are truncated
    before hashing (documented bcrypt behaviour).
    """
    pwd_bytes = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT configuration (from environment, never hardcoded)
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("ECARE_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("ECARE_SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("ECARE_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token.

    The token subject is the user's email. No credentials or secrets are
    embedded in the token payload beyond the subject and expiry.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"sub": subject, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """Verify a JWT and return its subject (email), or None if invalid.

    Does not log or print the token.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        return email
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Current-user dependency (real authentication)
# ---------------------------------------------------------------------------

def get_current_user_email(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """Extract and validate the current user's email from a Bearer token.

    Expects the Authorization header: "Bearer <token>".
    Returns the user's email (token subject) if valid.
    Raises 401 if missing or invalid.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("Bearer "):]
    email = decode_access_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


def get_optional_current_user_email(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """Return a valid token subject when supplied, without requiring login."""
    if authorization is None:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = decode_access_token(authorization[len("Bearer "):])
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


# ---------------------------------------------------------------------------
# Directory write authorization
# ---------------------------------------------------------------------------

def require_write_access(
    x_ecare_dev_mode: Optional[str] = Header(None, alias="X-Ecare-Dev-Mode"),
    current_user_email: Optional[str] = Depends(get_optional_current_user_email),
    db: Session = Depends(get_db),
) -> None:
    """Allow explicit local demo writes or authenticated administrators."""
    environment = os.environ.get("ECARE_ENVIRONMENT", "production").casefold()
    dev_mode = os.environ.get("ECARE_DEV_MODE", "false").casefold() == "true"
    header_dev_mode = (x_ecare_dev_mode or "").casefold() == "true"
    if environment in {"development", "test"} and dev_mode and header_dev_mode:
        return

    if current_user_email is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Directory writes require an administrator account.",
        )

    from app.models import User

    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is unavailable",
        )
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role",
        )


# ---------------------------------------------------------------------------
# Role-based authorization dependencies
# ---------------------------------------------------------------------------

VALID_ROLES = ("patient", "provider", "admin")


def require_role(allowed_roles: tuple[str, ...]):
    """Return a dependency that requires the current user to have one of
    the given roles.

    Uses the same database session as the request (injected via Depends).

    Usage:
        router.get("/admin-only", dependencies=[Depends(require_role(("admin",)))])
    """

    def _role_checker(
        current_user_email: str = Depends(get_current_user_email),
        db: Session = Depends(get_db),
    ) -> str:
        from app.models import User

        user = db.query(User).filter(User.email == current_user_email).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is unavailable",
            )
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user_email

    return _role_checker


# Convenience aliases
require_patient = require_role(("patient",))
require_provider = require_role(("provider", "admin"))
require_admin = require_role(("admin",))