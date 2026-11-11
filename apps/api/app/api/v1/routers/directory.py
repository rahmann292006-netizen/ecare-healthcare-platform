"""Read-only unified provider directory endpoints."""

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Boolean, cast, func, literal, null, or_, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.database import get_db
from app.models import Doctor, DiagnosticLab, Hospital, OPD, Speciality
from app.schemas import (
    ProviderDirectoryItem,
    ProviderDirectoryResponse,
    SpecialityResponse,
)

router = APIRouter(tags=["directory"])

PROVIDER_TYPES = ("hospital", "doctor", "lab", "opd")
MAX_LIMIT = 100

# Provider type -> (model, name column) shared by the directory endpoints.
_PROVIDER_MODELS = {
    "hospital": (Hospital, Hospital.name),
    "doctor": (Doctor, Doctor.full_name),
    "lab": (DiagnosticLab, DiagnosticLab.name),
    "opd": (OPD, OPD.name),
}

# Provider types that expose a many-to-many specialities relationship.
_SPECIALITY_RELATIONSHIPS = {
    "hospital": Hospital.specialities,
    "doctor": Doctor.specialities,
}


def _optional_column(model, attr: str, fallback_type):
    """Return the model column or a correctly typed SQL NULL."""
    column = getattr(model, attr, None)

    if column is not None:
        return column.label(attr)

    return cast(null(), fallback_type).label(attr)


def _provider_select(
    model,
    provider_type: str,
    name_column,
    speciality_id: Optional[int] = None,
) -> Select:
    """Build a select that flattens one provider model into the common
    ProviderDirectoryItem shape.

    Doctors do not store a locality, so the hospital's locality is surfaced
    through an outer join; every other model selects its own locality column.
    Labs and OPDs have no direct specialities, so they never match a
    speciality_id filter.
    """
    locality_column = (
        Hospital.locality
        if model is Doctor
        else getattr(model, "locality", literal(None))
    )
    city_column = Hospital.city if model is Doctor else getattr(model, "city", literal(None))
    state_column = Hospital.state if model is Doctor else getattr(model, "state", literal(None))

    query = select(
        model.id.label("id"),
        literal(provider_type).label("provider_type"),
        name_column.label("name"),
        model.slug.label("slug"),
        getattr(model, "description", literal(None)).label("description"),
        getattr(model, "address", literal(None)).label("address"),
        locality_column.label("locality"),
        city_column.label("city"),
        state_column.label("state"),
        getattr(model, "phone", literal(None)).label("phone"),
        getattr(model, "email", literal(None)).label("email"),
        getattr(model, "website", literal(None)).label("website"),
        getattr(model, "hospital_type", literal(None)).label("hospital_type"),
        getattr(model, "opd_type", literal(None)).label("opd_type"),
        getattr(model, "operating_hours", literal(None)).label("operating_hours"),
        getattr(model, "hospital_id", literal(None)).label("hospital_id"),
        (Hospital.name if model is Doctor else literal(None)).label("hospital_name"),
        getattr(model, "qualifications", literal(None)).label("qualifications"),
        getattr(model, "experience_years", literal(None)).label("experience_years"),
        getattr(model, "consultation_fee", literal(None)).label("consultation_fee"),
        getattr(model, "schedule_json", literal(None)).label("schedule"),
        model.source,
        model.source_url,
        model.verified_at,
        model.is_verified,
        model.is_demo,
        model.verification_status,
        model.operational_status,
        _optional_column(model, "emergency_services", Boolean),
        _optional_column(model, "home_sample_collection", Boolean),
    ).where(model.is_active.is_(True))

    if model is Doctor:
        query = query.select_from(Doctor).outerjoin(
            Hospital,
            Doctor.hospital_id == Hospital.id,
        )

    if speciality_id is not None:
        if model is Hospital:
            query = query.join(Hospital.specialities).where(
                Speciality.id == speciality_id
            )
        elif model is Doctor:
            query = query.join(Doctor.specialities).where(
                Speciality.id == speciality_id
            )
        else:
            query = query.where(literal(False))

    return query


def _item(row, specialities):
    return ProviderDirectoryItem(
        **dict(row),
        specialities=specialities,
    )


def _fetch_speciality_map(
    db: Session,
    provider_type: str,
    ids: list[int],
) -> dict[int, list[Speciality]]:
    """Fetch linked specialities for providers of one type, keyed by provider id."""
    if not ids or provider_type not in _SPECIALITY_RELATIONSHIPS:
        return {}

    id_column = Hospital.id if provider_type == "hospital" else Doctor.id
    relationship = _SPECIALITY_RELATIONSHIPS[provider_type]

    rows = db.execute(
        select(id_column, Speciality)
        .join(relationship)
        .where(id_column.in_(ids))
    ).all()

    mapping: dict[int, list[Speciality]] = defaultdict(list)

    for provider_id, speciality in rows:
        mapping[provider_id].append(speciality)

    return dict(mapping)


@router.get("/specialities", response_model=list[SpecialityResponse])
def list_specialities(db: Session = Depends(get_db)):
    """List all active specialities, ordered by name."""
    stmt = (
        select(Speciality)
        .where(Speciality.is_active.is_(True))
        .order_by(func.lower(Speciality.name), Speciality.id)
    )

    return db.execute(stmt).scalars().all()


@router.get("/providers", response_model=ProviderDirectoryResponse)
def list_providers(
    db: Session = Depends(get_db),
    provider_type: Optional[str | list[str]] = Query(
        None,
        description="hospital, doctor, lab, or opd",
    ),
    speciality_id: Optional[int] = Query(None, ge=1),
    locality: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("name_asc", pattern="^(name_asc|name_desc)$"),
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> ProviderDirectoryResponse:
    """Return a paginated, combined listing of providers across all types."""
    if provider_type:
        if isinstance(provider_type, str):
            requested_types = [provider_type]
        else:
            requested_types = list(provider_type)

        selected_types = tuple(dict.fromkeys(requested_types))

        invalid_types = [
            kind for kind in selected_types if kind not in PROVIDER_TYPES
        ]

        if invalid_types:
            raise HTTPException(
                status_code=422,
                detail="Invalid provider_type",
            )
    else:
        selected_types = PROVIDER_TYPES

    selects = []

    for kind in selected_types:
        model, name_column = _PROVIDER_MODELS[kind]

        query = _provider_select(
            model,
            kind,
            name_column,
            speciality_id,
        )

        if locality:
            location_col = (
                Hospital.locality
                if model is Doctor
                else getattr(model, "locality", None)
            )
            city_col = Hospital.city if model is Doctor else getattr(model, "city", None)

            if location_col is not None:
                predicates = [location_col.ilike(f"%{locality}%")]
                if city_col is not None:
                    predicates.append(city_col.ilike(f"%{locality}%"))
                query = query.where(or_(*predicates))
            elif city_col is not None:
                query = query.where(city_col.ilike(f"%{locality}%"))
            else:
                query = query.where(literal(False))

        if city:
            city_column = Hospital.city if model is Doctor else getattr(model, "city", None)
            if city_column is not None:
                query = query.where(city_column.ilike(city))
            else:
                query = query.where(literal(False))

        if search:
            query = query.where(
                name_column.ilike(f"%{search}%")
            )

        selects.append(query)

    combined = union_all(*selects).subquery()

    total = db.execute(
        select(func.count()).select_from(combined)
    ).scalar_one()

    name_order = func.lower(combined.c.name)

    ordering = (
        name_order.desc()
        if sort == "name_desc"
        else name_order.asc()
    )

    rows = (
        db.execute(
            select(combined)
            .order_by(
                ordering,
                combined.c.provider_type,
                combined.c.id,
            )
            .limit(limit)
            .offset(offset)
        )
        .mappings()
        .all()
    )

    speciality_map: dict[tuple[str, int], list[Speciality]] = {}

    for kind in selected_types:
        if kind not in _SPECIALITY_RELATIONSHIPS:
            continue

        ids = [
            row["id"]
            for row in rows
            if row["provider_type"] == kind
        ]

        for provider_id, specialities in _fetch_speciality_map(
            db,
            kind,
            ids,
        ).items():
            speciality_map[(kind, provider_id)] = specialities

    items = [
        _item(
            row,
            [
                SpecialityResponse.model_validate(speciality)
                for speciality in speciality_map.get(
                    (row["provider_type"], row["id"]),
                    [],
                )
            ],
        )
        for row in rows
    ]

    return ProviderDirectoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/providers/{provider_type}/{provider_id}",
    response_model=ProviderDirectoryItem,
)
def get_provider(
    provider_type: str,
    provider_id: int,
    db: Session = Depends(get_db),
) -> ProviderDirectoryItem:
    """Return a single provider by type and id."""
    if provider_type not in _PROVIDER_MODELS:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    model, name_column = _PROVIDER_MODELS[provider_type]

    query = _provider_select(
        model,
        provider_type,
        name_column,
    ).where(model.id == provider_id)

    row = db.execute(query).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    speciality_map = _fetch_speciality_map(
        db,
        provider_type,
        [provider_id],
    )

    return _item(
        row,
        [
            SpecialityResponse.model_validate(speciality)
            for speciality in speciality_map.get(provider_id, [])
        ],
    )
