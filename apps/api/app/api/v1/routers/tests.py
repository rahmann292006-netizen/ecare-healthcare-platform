"""Diagnostic Test API routes.

Endpoints:
- POST   /api/v1/labs/{lab_id}/tests         - add a test to a lab (write-protected)
- GET    /api/v1/labs/{lab_id}/tests         - list tests offered by a lab
- GET    /api/v1/tests/{test_id}             - get diagnostic test details
- PATCH  /api/v1/tests/{test_id}             - update test information (write-protected)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DiagnosticLab, DiagnosticTest
from app.schemas import (
    TestCreate,
    TestUpdate,
    TestResponse,
    TestListResponse,
)
from app.auth import require_write_access

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get("/{test_id}", response_model=TestResponse)
def get_test(test_id: int, db: Session = Depends(get_db)):
    """Get a single diagnostic test by ID."""
    test = (
        db.query(DiagnosticTest)
        .join(DiagnosticLab)
        .filter(
            DiagnosticTest.id == test_id,
            DiagnosticLab.is_active.is_(True),
        )
        .first()
    )
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic test not found")
    return test


@router.patch("/{test_id}", response_model=TestResponse)
def update_test(
    test_id: int,
    test_in: TestUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_write_access),
):
    """Update an existing diagnostic test. Write-protected."""
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic test not found")

    update_data = test_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test, field, value)

    try:
        db.flush()
        db.refresh(test)
    except Exception:
        db.rollback()
        raise
    return test