"""Read-only unified provider directory endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor, DiagnosticLab, Hospital, OPD, Speciality
from app.schemas import ProviderDirectoryItem, ProviderDirectoryResponse, SpecialityResponse

router = APIRouter(tags=["directory"])
PROVIDER_TYPES = ("hospital", "doctor", "lab", "opd")
MAX_LIMIT = 100


@router.get("/specialities", response_model=list[SpecialityResponse])
def list_specialities(db: Session = Depends(get_db)):
    return db.query(Speciality).filter(Speciality.is_active.is_(True)).order_by(
        func.lower(Speciality.name), Speciality.id
    ).all()


def _provider_select(model, provider_type: str, name_column, speciality_id: Optional[int]):
    locality_column = Hospital.locality if model is Doctor else getattr(model, "locality", literal(None))
    query = select(
        model.id.label("id"), literal(provider_type).label("provider_type"),
        name_column.label("name"), model.slug.label("slug"),
        getattr(model, "description", literal(None)).label("description"),
        getattr(model, "address", literal(None)).label("address"),
        locality_column.label("locality"),
        getattr(model, "city", literal(None)).label("city"),
        getattr(model, "state", literal(None)).label("state"),
        getattr(model, "phone", literal(None)).label("phone"),
        getattr(model, "email", literal(None)).label("email"),
        getattr(model, "website", literal(None)).label("website"),
        getattr(model, "hospital_type", literal(None)).label("hospital_type"),
        getattr(model, "opd_type", literal(None)).label("opd_type"),
        getattr(model, "hospital_id", literal(None)).label("hospital_id"),
        model.source, model.source_url, model.verified_at, model.is_verified,
        model.is_demo, model.verification_status,
    ).where(model.is_active.is_(True))
    if model is Doctor:
        query = query.select_from(Doctor).outerjoin(Hospital, Doctor.hospital_id == Hospital.id)

    if speciality_id is not None:
        if model is Hospital:
            query = query.join(Hospital.specialities).where(Speciality.id == speciality_id)
        elif model is Doctor:
            query = query.join(Doctor.specialities).where(Speciality.id == speciality_id)
        else:
            query = query.where(False)
    return query


def _item(row, specialities):
    return ProviderDirectoryItem(
        **{key: row[key] for key in row.keys()}, specialities=specialities
    )


@router.get("/providers", response_model=ProviderDirectoryResponse)
def list_providers(
    db: Session = Depends(get_db),
    provider_type: Optional[str] = Query(None, description="hospital, doctor, lab, or opd"),
    speciality_id: Optional[int] = Query(None, ge=1),
    locality: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("name_asc", pattern="^(name_asc|name_desc)$"),
    limit: int = Query(20, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
):
    if provider_type and provider_type not in PROVIDER_TYPES:
        raise HTTPException(status_code=422, detail="Invalid provider_type")
    selected_types = (provider_type,) if provider_type else PROVIDER_TYPES
    models = {
        "hospital": (Hospital, Hospital.name),
        "doctor": (Doctor, Doctor.full_name),
        "lab": (DiagnosticLab, DiagnosticLab.name),
        "opd": (OPD, OPD.name),
    }
    selects = []
    for kind in selected_types:
        model, name_col = models[kind]
        query = _provider_select(model, kind, name_col, speciality_id)
        if locality:
            location_col = Hospital.locality if model is Doctor else getattr(model, "locality", None)
            if location_col is not None:
                query = query.where(location_col.ilike(f"%{locality}%"))
            else:
                query = query.where(False)
        if search:
            query = query.where(name_col.ilike(f"%{search}%"))
        selects.append(query)

    combined = union_all(*selects).subquery()
    total = db.execute(select(func.count()).select_from(combined)).scalar_one()
    name_order = func.lower(combined.c.name)
    ordering = (name_order.desc() if sort == "name_desc" else name_order.asc())
    rows = db.execute(
        select(combined).order_by(ordering, combined.c.provider_type, combined.c.id)
        .limit(limit).offset(offset)
    ).mappings().all()

    hospital_ids = [r["id"] for r in rows if r["provider_type"] == "hospital"]
    doctor_ids = [r["id"] for r in rows if r["provider_type"] == "doctor"]
    speciality_map = {}
    if hospital_ids:
        for hospital_id, speciality in db.query(Hospital.id, Speciality).join(
            Hospital.specialities
        ).filter(Hospital.id.in_(hospital_ids)).all():
            speciality_map[("hospital", hospital_id)] = speciality_map.get(("hospital", hospital_id), []) + [speciality]
    if doctor_ids:
        for doctor_id, speciality in db.query(Doctor.id, Speciality).join(
            Doctor.specialities
        ).filter(Doctor.id.in_(doctor_ids)).all():
            speciality_map[("doctor", doctor_id)] = speciality_map.get(("doctor", doctor_id), []) + [speciality]
    items = [
        _item(row, [SpecialityResponse.model_validate(s) for s in speciality_map.get((row["provider_type"], row["id"]), [])])
        for row in rows
    ]
    return ProviderDirectoryResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/providers/{provider_type}/{provider_id}", response_model=ProviderDirectoryItem)
def get_provider(provider_type: str, provider_id: int, db: Session = Depends(get_db)):
    models = {
        "hospital": (Hospital, Hospital.name),
        "doctor": (Doctor, Doctor.full_name),
        "lab": (DiagnosticLab, DiagnosticLab.name),
        "opd": (OPD, OPD.name),
    }
    if provider_type not in models:
        raise HTTPException(status_code=404, detail="Provider not found")
    model, name_column = models[provider_type]
    query = _provider_select(model, provider_type, name_column, None).where(model.id == provider_id)
    row = db.execute(query).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    speciality_map = {}
    if provider_type == "hospital":
        speciality_map = db.query(Speciality).join(Hospital.specialities).filter(Hospital.id == provider_id).all()
    elif provider_type == "doctor":
        speciality_map = db.query(Speciality).join(Doctor.specialities).filter(Doctor.id == provider_id).all()
    return _item(row, [SpecialityResponse.model_validate(s) for s in speciality_map])
