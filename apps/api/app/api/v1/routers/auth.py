"""Authentication API routes.

Endpoints:
- POST   /api/v1/auth/register - register a new user (public)
- POST   /api/v1/auth/login    - authenticate and receive a JWT (public)
- GET    /api/v1/auth/me       - get the current authenticated user (protected)

Passwords are hashed with bcrypt before storage. JWTs are signed with the
ECARE_SECRET_KEY environment variable. No credentials or tokens are logged.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user_email,
    require_admin,
)
from app.database import get_db
from app.models import User
from app.models import Doctor, DoctorApplication
from app.schemas import (
    UserCreate,
    UserProvisionCreate,
    UserRead,
    UserLogin,
    Token,
    UserUpdate,
    UserChangePassword,
    DoctorApplicationCreate,
    DoctorApplicationRead,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user via public registration.

    The password is hashed server-side and never stored in plaintext.
    The role is always forced to "patient" — client-supplied roles are
    ignored. Provider and admin accounts cannot be created through this
    endpoint.
    """
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        phone=user_in.phone,
        hashed_password=hash_password(user_in.password),
        role="patient",  # Always patient for public registration
    )
    db.add(user)
    try:
        db.flush()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user


@router.post(
    "/provision",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def provision_user(
    user_in: UserProvisionCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Provision a new user account (admin only).

    Requires an authenticated admin via Bearer token. Allows creating
    patient, provider, or admin accounts. This is the only path for
    creating non-patient accounts.

    Provider account ownership of specific listings is NOT established
    here; provider_listing_id remains null until a future step links it.
    """
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    try:
        db.flush()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise
    return user


@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token.

    Returns 401 for invalid credentials without distinguishing whether
    the email exists, to prevent user enumeration.
    """
    user = db.query(User).filter(User.email == login_in.email).first()
    if user is None or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def get_me(current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    """Return the currently authenticated user's profile."""
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.patch("/me", response_model=UserRead)
def update_me(
    user_in: UserUpdate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in user_in.model_dump(exclude_unset=True).items():
        if field == "full_name" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="Full name cannot be blank")
        setattr(user, field, value)
    db.flush()
    db.refresh(user)
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    user_in: UserChangePassword,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None or not verify_password(user_in.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.hashed_password = hash_password(user_in.new_password)
    db.flush()


@router.post("/doctor-applications", response_model=DoctorApplicationRead, status_code=201)
def submit_doctor_application(
    application_in: DoctorApplicationCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None or not user.is_active or user.role != "patient":
        raise HTTPException(status_code=403, detail="Apply using a patient account")
    doctor = db.query(Doctor).filter(Doctor.id == application_in.doctor_id, Doctor.is_active.is_(True)).first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor listing not found")
    existing = db.query(DoctorApplication).filter(DoctorApplication.doctor_id == doctor.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="A doctor account application already exists for this listing")
    application = DoctorApplication(user_id=user.id, doctor_id=doctor.id, status="pending")
    db.add(application)
    db.flush()
    return DoctorApplicationRead(
        id=application.id, user_id=user.id, doctor_id=doctor.id, status=application.status,
        created_at=application.created_at, reviewed_at=None, applicant_name=user.full_name,
        applicant_email=user.email, doctor_name=doctor.full_name,
    )


@router.get("/doctor-applications/me", response_model=list[DoctorApplicationRead])
def my_doctor_applications(
    current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == current_user_email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = db.query(DoctorApplication).filter(DoctorApplication.user_id == user.id).order_by(DoctorApplication.created_at.desc()).all()
    return [DoctorApplicationRead(id=row.id, user_id=user.id, doctor_id=row.doctor_id, status=row.status, created_at=row.created_at, reviewed_at=row.reviewed_at, applicant_name=user.full_name, applicant_email=user.email, doctor_name=row.doctor.full_name if row.doctor else None) for row in rows]


@router.get("/admin/doctor-applications", response_model=list[DoctorApplicationRead])
def list_doctor_applications(
    db: Session = Depends(get_db), _: str = Depends(require_admin)
):
    rows = db.query(DoctorApplication).order_by(DoctorApplication.created_at.desc()).all()
    return [DoctorApplicationRead(id=row.id, user_id=row.user_id, doctor_id=row.doctor_id, status=row.status, created_at=row.created_at, reviewed_at=row.reviewed_at, applicant_name=row.applicant.full_name if row.applicant else None, applicant_email=row.applicant.email if row.applicant else None, doctor_name=row.doctor.full_name if row.doctor else None) for row in rows]


def _review_application(application_id: int, approved: bool, admin_email: str, db: Session):
    admin = db.query(User).filter(User.email == admin_email, User.role == "admin").first()
    application = db.query(DoctorApplication).filter(DoctorApplication.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Doctor application not found")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="This application has already been reviewed")
    application.status = "approved" if approved else "rejected"
    application.reviewed_by = admin.id if admin else None
    application.reviewed_at = datetime.now(timezone.utc)
    if approved:
        applicant = db.query(User).filter(User.id == application.user_id).first()
        if applicant is None:
            raise HTTPException(status_code=404, detail="Applicant account not found")
        if applicant.provider_doctor_id not in (None, application.doctor_id):
            raise HTTPException(status_code=409, detail="Applicant is already linked to another doctor profile")
        applicant.role = "provider"
        applicant.provider_doctor_id = application.doctor_id
        applicant.provider_listing_id = application.doctor_id
        applicant.provider_listing_type = "doctor"
    db.flush()
    return application


@router.post("/admin/doctor-applications/{application_id}/approve", response_model=DoctorApplicationRead)
def approve_doctor_application(application_id: int, current_user_email: str = Depends(require_admin), db: Session = Depends(get_db)):
    row = _review_application(application_id, True, current_user_email, db)
    return DoctorApplicationRead(id=row.id, user_id=row.user_id, doctor_id=row.doctor_id, status=row.status, created_at=row.created_at, reviewed_at=row.reviewed_at, applicant_name=row.applicant.full_name, applicant_email=row.applicant.email, doctor_name=row.doctor.full_name)


@router.post("/admin/doctor-applications/{application_id}/reject", response_model=DoctorApplicationRead)
def reject_doctor_application(application_id: int, current_user_email: str = Depends(require_admin), db: Session = Depends(get_db)):
    row = _review_application(application_id, False, current_user_email, db)
    return DoctorApplicationRead(id=row.id, user_id=row.user_id, doctor_id=row.doctor_id, status=row.status, created_at=row.created_at, reviewed_at=row.reviewed_at, applicant_name=row.applicant.full_name, applicant_email=row.applicant.email, doctor_name=row.doctor.full_name)
