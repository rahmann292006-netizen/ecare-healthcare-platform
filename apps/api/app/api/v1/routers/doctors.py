"""Doctor API routes.

Endpoints:
- GET    /api/v1/doctors              - list doctors (pagination + filters)
- GET    /api/v1/doctors/{doctor_id}  - get doctor details
- POST   /api/v1/doctors              - create doctor (write-protected)
- PATCH  /api/v1/doctors/{doctor_id}  - update doctor (write-protected)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor, Hospital
from app.schemas import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    DoctorListResponse,
)
from app.auth import require_write_access

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _apply_doctor_filters(query, search: Optional[str], specialization: Optional[str],
                          hospital_id: Optional[int],
                          verification_status: Optional[str]):
    if search:
        query = query.filter(Doctor.full_name.ilike(f"%{search}%"))
    if specialization:
        query = query.filter(Doctor.specializations.ilike(f"%{specialization}%"))
    if hospital_id is not None:
        query = query.filter(Doctor.hospital_id == hospital_id)
    if verification_status:
        query = query.filter(Doctor.verification_status == verification_status)
    return query


@router.get("", response_model=DoctorListResponse)
def list_doctors(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by doctor name"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    hospital_id: Optional[int] = Query(None, description="Filter by hospital ID"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List doctors with optional filters and pagination."""
    query = db.query(Doctor).filter(Doctor.is_active.is_(True))
    query = _apply_doctor_filters(
        query, search, specialization, hospital_id, verification_status
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return DoctorListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    """Get a single doctor by ID."""
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id, Doctor.is_active.is_(True)
    ).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    doctor_in: DoctorCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Create a new doctor listing. Write-protected.

    verification_status always defaults to "unverified" server-side.
    """
    existing = db.query(Doctor).filter(Doctor.slug == doctor_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Doctor with slug '{doctor_in.slug}' already exists",
        )

    # Validate hospital_id if provided
    if doctor_in.hospital_id is not None:
        hospital = db.query(Hospital).filter(Hospital.id == doctor_in.hospital_id).first()
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hospital with id {doctor_in.hospital_id} not found",
            )

    doctor = Doctor(
        full_name=doctor_in.full_name,
        slug=doctor_in.slug,
        qualifications=doctor_in.qualifications,
        specializations=doctor_in.specializations,
        experience_years=doctor_in.experience_years,
        languages=doctor_in.languages,
        consultation_fee=doctor_in.consultation_fee,
        phone=doctor_in.phone,
        hospital_id=doctor_in.hospital_id,
        operational_status=doctor_in.operational_status,
    )
    db.add(doctor)
    try:
        db.flush()
        db.refresh(doctor)
    except Exception:
        db.rollback()
        raise
    return doctor


@router.patch("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    doctor_in: DoctorUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Update an existing doctor. Write-protected.

    verification_status cannot be changed via this endpoint.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    update_data = doctor_in.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != doctor.slug:
        existing = db.query(Doctor).filter(Doctor.slug == update_data["slug"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Doctor with slug '{update_data['slug']}' already exists",
            )

    if "hospital_id" in update_data and update_data["hospital_id"] is not None:
        hospital = db.query(Hospital).filter(Hospital.id == update_data["hospital_id"]).first()
        if not hospital:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hospital with id {update_data['hospital_id']} not found",
            )

    for field, value in update_data.items():
        setattr(doctor, field, value)

    try:
        db.flush()
        db.refresh(doctor)
    except Exception:
        db.rollback()
        raise
    return doctor