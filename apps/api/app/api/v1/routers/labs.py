"""Diagnostic Laboratory API routes.

Endpoints:
- GET    /api/v1/labs              - list laboratories (pagination + filters)
- GET    /api/v1/labs/{lab_id}     - get laboratory details
- POST   /api/v1/labs              - create laboratory (write-protected)
- PATCH  /api/v1/labs/{lab_id}     - update laboratory (write-protected)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DiagnosticLab, DiagnosticTest
from app.schemas import (
    LabCreate,
    LabUpdate,
    LabResponse,
    LabListResponse,
    TestCreate,
    TestResponse,
    TestListResponse,
)
from app.auth import require_write_access

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

router = APIRouter(prefix="/labs", tags=["labs"])


def _apply_lab_filters(query, search: Optional[str], locality: Optional[str],
                       home_sample_collection: Optional[bool],
                       verification_status: Optional[str]):
    if search:
        query = query.filter(DiagnosticLab.name.ilike(f"%{search}%"))
    if locality:
        query = query.filter(DiagnosticLab.locality.ilike(f"%{locality}%"))
    if home_sample_collection is not None:
        query = query.filter(DiagnosticLab.home_sample_collection == home_sample_collection)
    if verification_status:
        query = query.filter(DiagnosticLab.verification_status == verification_status)
    return query


@router.get("", response_model=LabListResponse)
def list_labs(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by laboratory name"),
    locality: Optional[str] = Query(None, description="Filter by locality"),
    home_sample_collection: Optional[bool] = Query(None, description="Filter by home sample collection"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List diagnostic laboratories with optional filters and pagination."""
    query = db.query(DiagnosticLab).filter(DiagnosticLab.is_active.is_(True))
    query = _apply_lab_filters(
        query, search, locality, home_sample_collection, verification_status
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return LabListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{lab_id}", response_model=LabResponse)
def get_lab(lab_id: int, db: Session = Depends(get_db)):
    """Get a single diagnostic laboratory by ID."""
    lab = db.query(DiagnosticLab).filter(
        DiagnosticLab.id == lab_id, DiagnosticLab.is_active.is_(True)
    ).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laboratory not found")
    return lab


@router.post("", response_model=LabResponse, status_code=status.HTTP_201_CREATED)
def create_lab(
    lab_in: LabCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Create a new diagnostic laboratory listing. Write-protected.

    verification_status always defaults to "unverified" server-side.
    """
    existing = db.query(DiagnosticLab).filter(DiagnosticLab.slug == lab_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Laboratory with slug '{lab_in.slug}' already exists",
        )

    lab = DiagnosticLab(
        name=lab_in.name,
        slug=lab_in.slug,
        description=lab_in.description,
        address=lab_in.address,
        locality=lab_in.locality,
        city=lab_in.city,
        state=lab_in.state,
        phone=lab_in.phone,
        operational_status=lab_in.operational_status,
        home_sample_collection=lab_in.home_sample_collection,
    )
    db.add(lab)
    try:
        db.flush()
        db.refresh(lab)
    except Exception:
        db.rollback()
        raise
    return lab


@router.patch("/{lab_id}", response_model=LabResponse)
def update_lab(
    lab_id: int,
    lab_in: LabUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Update an existing diagnostic laboratory. Write-protected.

    verification_status cannot be changed via this endpoint.
    """
    lab = db.query(DiagnosticLab).filter(
        DiagnosticLab.id == lab_id, DiagnosticLab.is_active.is_(True)
    ).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laboratory not found")

    update_data = lab_in.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"] != lab.slug:
        existing = db.query(DiagnosticLab).filter(DiagnosticLab.slug == update_data["slug"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Laboratory with slug '{update_data['slug']}' already exists",
            )

    for field, value in update_data.items():
        setattr(lab, field, value)

    try:
        db.flush()
        db.refresh(lab)
    except Exception:
        db.rollback()
        raise
    return lab


# ---------------------------------------------------------------------------
# Diagnostic test routes nested under a laboratory
# ---------------------------------------------------------------------------

@router.post("/{lab_id}/tests", response_model=TestResponse, status_code=status.HTTP_201_CREATED)
def create_test_for_lab(
    lab_id: int,
    test_in: TestCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Add a diagnostic test to a laboratory. Write-protected."""
    lab = db.query(DiagnosticLab).filter(DiagnosticLab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laboratory not found")

    test = DiagnosticTest(
        lab_id=lab_id,
        name=test_in.name,
        description=test_in.description,
        price=test_in.price,
        preparation_instructions=test_in.preparation_instructions,
        availability_status=test_in.availability_status or "available",
    )
    db.add(test)
    try:
        db.flush()
        db.refresh(test)
    except Exception:
        db.rollback()
        raise
    return test


@router.get("/{lab_id}/tests", response_model=TestListResponse)
def list_tests_for_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List diagnostic tests offered by a laboratory."""
    lab = db.query(DiagnosticLab).filter(DiagnosticLab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Laboratory not found")

    query = db.query(DiagnosticTest).filter(DiagnosticTest.lab_id == lab_id)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return TestListResponse(items=items, total=total, limit=limit, offset=offset)