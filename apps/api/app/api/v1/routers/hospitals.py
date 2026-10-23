"""Hospital API routes.

Endpoints:
- GET    /api/v1/hospitals              - list hospitals (pagination + filters)
- GET    /api/v1/hospitals/{hospital_id} - get hospital details
- POST   /api/v1/hospitals              - create hospital (write-protected)
- PATCH  /api/v1/hospitals/{hospital_id} - update hospital (write-protected)
- GET    /api/v1/hospitals/{hospital_id}/doctors - list doctors at a hospital
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Hospital, Doctor
from app.schemas import (
    HospitalCreate,
    HospitalUpdate,
    HospitalResponse,
    HospitalListResponse,
    DoctorListResponse,
)
from app.auth import require_write_access

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


def _apply_hospital_filters(query, search: Optional[str], locality: Optional[str],
                            hospital_type: Optional[str],
                            verification_status: Optional[str],
                            emergency_services: Optional[bool]):
    if search:
        query = query.filter(Hospital.name.ilike(f"%{search}%"))
    if locality:
        query = query.filter(Hospital.locality.ilike(f"%{locality}%"))
    if hospital_type:
        query = query.filter(Hospital.hospital_type == hospital_type)
    if verification_status:
        query = query.filter(Hospital.verification_status == verification_status)
    if emergency_services is not None:
        query = query.filter(Hospital.emergency_services == emergency_services)
    return query


@router.get("", response_model=HospitalListResponse)
def list_hospitals(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by hospital name"),
    locality: Optional[str] = Query(None, description="Filter by locality"),
    hospital_type: Optional[str] = Query(None, description="Filter by hospital type"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    emergency_services: Optional[bool] = Query(None, description="Filter by emergency services"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List hospitals with optional filters and pagination."""
    query = db.query(Hospital)
    query = _apply_hospital_filters(
        query, search, locality, hospital_type,
        verification_status, emergency_services,
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return HospitalListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{hospital_id}", response_model=HospitalResponse)
def get_hospital(hospital_id: int, db: Session = Depends(get_db)):
    """Get a single hospital by ID."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return hospital


@router.post("", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
def create_hospital(
    hospital_in: HospitalCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Create a new hospital listing. Write-protected.

    verification_status always defaults to "unverified" server-side.
    """
    existing = db.query(Hospital).filter(Hospital.slug == hospital_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hospital with slug '{hospital_in.slug}' already exists",
        )

    hospital = Hospital(
        name=hospital_in.name,
        slug=hospital_in.slug,
        description=hospital_in.description,
        hospital_type=hospital_in.hospital_type,
        address=hospital_in.address,
        locality=hospital_in.locality,
        city=hospital_in.city,
        state=hospital_in.state,
        pincode=hospital_in.pincode,
        latitude=hospital_in.latitude,
        longitude=hospital_in.longitude,
        phone=hospital_in.phone,
        email=hospital_in.email,
        website=hospital_in.website,
        emergency_services=hospital_in.emergency_services,
        operating_hours=hospital_in.operating_hours,
    )
    db.add(hospital)
    try:
        db.flush()
        db.refresh(hospital)
    except Exception:
        db.rollback()
        raise
    return hospital


@router.patch("/{hospital_id}", response_model=HospitalResponse)
def update_hospital(
    hospital_id: int,
    hospital_in: HospitalUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Update an existing hospital. Write-protected.

    verification_status cannot be changed via this endpoint.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    update_data = hospital_in.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != hospital.slug:
        existing = db.query(Hospital).filter(Hospital.slug == update_data["slug"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Hospital with slug '{update_data['slug']}' already exists",
            )

    for field, value in update_data.items():
        setattr(hospital, field, value)

    try:
        db.flush()
        db.refresh(hospital)
    except Exception:
        db.rollback()
        raise
    return hospital


@router.get("/{hospital_id}/doctors", response_model=DoctorListResponse)
def list_hospital_doctors(
    hospital_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List doctors associated with a hospital."""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    query = db.query(Doctor).filter(Doctor.hospital_id == hospital_id)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return DoctorListResponse(items=items, total=total, limit=limit, offset=offset)