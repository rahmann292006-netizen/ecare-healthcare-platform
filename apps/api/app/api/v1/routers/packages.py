"""Health checkup package API routes.

Endpoints:
- GET    /api/v1/packages              - list packages (pagination + filters)
- GET    /api/v1/packages/{package_id} - get package details
- POST   /api/v1/packages              - create package (admin only)
- PATCH  /api/v1/packages/{package_id} - update package (admin only)
- DELETE /api/v1/packages/{package_id} - delete package (admin only)
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Package, PackageInclusion
from app.schemas import (
    PackageCreate,
    PackageUpdate,
    PackageRead,
    PackageListResponse,
    PackageInclusionCreate,
    PackageVerificationUpdate,
)
from app.auth import require_admin

MAX_LIMIT = 100
DEFAULT_LIMIT = 20

router = APIRouter(prefix="/packages", tags=["packages"])


def _apply_package_filters(
    query,
    search: Optional[str],
    category: Optional[str],
    city: Optional[str],
    locality: Optional[str],
    provider_type: Optional[str],
    is_active: Optional[bool],
):
    if search:
        query = query.filter(Package.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Package.category == category)
    if city:
        query = query.filter(Package.city.ilike(f"%{city}%"))
    if locality:
        query = query.filter(Package.locality.ilike(f"%{locality}%"))
    if provider_type:
        query = query.filter(Package.provider_type == provider_type)
    if is_active is not None:
        query = query.filter(Package.is_active == is_active)
    return query


@router.get("", response_model=PackageListResponse)
def list_packages(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by package name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    city: Optional[str] = Query(None, description="Filter by city"),
    locality: Optional[str] = Query(None, description="Filter by locality"),
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List health checkup packages with optional filters and pagination."""
    query = (
        db.query(Package)
        .options(joinedload(Package.inclusions))
        .filter(Package.is_active.is_(True))
    )
    query = _apply_package_filters(
        query, search, category, city, locality, provider_type, is_active
    )
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return PackageListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/admin", response_model=list[PackageRead])
def list_admin_packages(
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    return (
        db.query(Package)
        .options(joinedload(Package.inclusions))
        .order_by(Package.created_at.desc())
        .limit(MAX_LIMIT)
        .all()
    )


@router.get("/{package_id}", response_model=PackageRead)
def get_package(
    package_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    db: Session = Depends(get_db),
):
    """Get a single health checkup package by ID."""
    package = (
        db.query(Package)
        .options(joinedload(Package.inclusions))
        .filter(Package.id == package_id, Package.is_active.is_(True))
        .first()
    )
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )
    return package


@router.post(
    "", response_model=PackageRead, status_code=status.HTTP_201_CREATED
)
def create_package(
    package_in: PackageCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Create a new health checkup package. Admin only."""
    existing = db.query(Package).filter(Package.slug == package_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Package with slug '{package_in.slug}' already exists",
        )

    package = Package(
        name=package_in.name,
        slug=package_in.slug,
        description=package_in.description,
        provider_name=package_in.provider_name,
        provider_type=package_in.provider_type,
        price=package_in.price,
        currency=package_in.currency,
        city=package_in.city,
        state=package_in.state,
        locality=package_in.locality,
        category=package_in.category,
        source=package_in.source,
        source_url=package_in.source_url,
        min_age_years=package_in.min_age_years,
        max_age_years=package_in.max_age_years,
        validity_period=package_in.validity_period,
        validity_description=package_in.validity_description,
    )
    db.add(package)
    db.flush()
    db.refresh(package)

    for inclusion_in in package_in.inclusions:
        inclusion = PackageInclusion(
            package_id=package.id,
            test_name=inclusion_in.test_name,
            display_order=inclusion_in.display_order,
        )
        db.add(inclusion)

    try:
        db.flush()
        db.refresh(package)
    except Exception:
        db.rollback()
        raise

    return package


@router.patch("/{package_id}", response_model=PackageRead)
def update_package(
    package_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    package_in: PackageUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Update an existing health checkup package. Admin only."""
    package = db.query(Package).filter(Package.id == package_id).first()
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )

    update_data = package_in.model_dump(exclude_unset=True)
    inclusions = update_data.pop("inclusions", None)
    if "min_age_years" in update_data and "max_age_years" not in update_data:
        update_data["max_age_years"] = package.max_age_years
    elif "max_age_years" in update_data and "min_age_years" not in update_data:
        update_data["min_age_years"] = package.min_age_years
    if (
        update_data.get("min_age_years") is not None
        and update_data.get("max_age_years") is not None
        and update_data["min_age_years"] > update_data["max_age_years"]
    ):
        raise HTTPException(
            status_code=422,
            detail="min_age_years cannot exceed max_age_years.",
        )

    if "slug" in update_data and update_data["slug"] != package.slug:
        existing = db.query(Package).filter(Package.slug == update_data["slug"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Package with slug '{update_data['slug']}' already exists",
            )

    verification_sensitive_fields = {
        "name",
        "provider_name",
        "provider_type",
        "price",
        "currency",
        "city",
        "state",
        "locality",
        "category",
        "source",
        "source_url",
        "min_age_years",
        "max_age_years",
        "validity_period",
        "validity_description",
    }
    if verification_sensitive_fields.intersection(update_data) or inclusions is not None:
        package.is_verified = False
        package.verified_at = None

    for field, value in update_data.items():
        setattr(package, field, value)

    try:
        if inclusions is not None:
            package.inclusions.clear()
            package.inclusions.extend(
                PackageInclusion(
                    test_name=item.test_name,
                    display_order=item.display_order,
                )
                for item in inclusions
            )
        db.flush()
        db.refresh(package)
    except Exception:
        db.rollback()
        raise

    return package


@router.post("/{package_id}/verify", response_model=PackageRead)
def verify_package(
    package_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    request: PackageVerificationUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    package = db.query(Package).filter(Package.id == package_id).first()
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")
    if package.is_demo:
        raise HTTPException(status_code=422, detail="Demo packages cannot be verified.")
    source = request.source.strip()
    if not source:
        raise HTTPException(status_code=422, detail="A non-empty provider source is required.")
    if not package.validity_period:
        raise HTTPException(
            status_code=422,
            detail="A provider-supplied validity period is required before verification.",
        )

    package.source = source
    package.source_url = request.source_url
    package.is_verified = True
    package.verified_at = datetime.now(timezone.utc)
    db.flush()
    return package


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Delete a health checkup package. Admin only."""
    package = db.query(Package).filter(Package.id == package_id).first()
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Package not found"
        )

    db.delete(package)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A plan with subscriptions cannot be deleted; deactivate it instead.",
        ) from exc
    return None
