"""Account-scoped demo appointments, invoices, and doctor schedules."""

from datetime import datetime, timezone
from decimal import Decimal
from secrets import token_hex
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user_email, require_admin, require_provider
from app.database import get_db
from app.models import Appointment, Doctor, Hospital, Invoice, PaymentRecord, User
from app.schemas import AppointmentCreate, AppointmentDetail, AppointmentRead, DoctorScheduleUpdate, InvoiceRead, PaymentRead

router = APIRouter(prefix="/appointments", tags=["appointments"])
def _user_for_email(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


def _doctor_for_user(db: Session, user: User) -> Doctor:
    if user.role != "provider" or not user.provider_doctor_id:
        raise HTTPException(status_code=403, detail="This account is not linked to a doctor listing")
    doctor = db.query(Doctor).filter(Doctor.id == user.provider_doctor_id, Doctor.is_active.is_(True)).first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Linked doctor profile not found")
    return doctor


def _appointment_data(appointment: Appointment) -> dict:
    doctor = appointment.doctor
    hospital = doctor.hospital if doctor else None
    speciality = doctor.specialities[0].name if doctor and doctor.specialities else None
    return {
        "id": appointment.id,
        "reference": appointment.reference,
        "user_id": appointment.user_id,
        "doctor_id": appointment.doctor_id,
        "doctor_name": doctor.full_name if doctor else "Doctor listing unavailable",
        "doctor_qualification": doctor.qualifications if doctor else None,
        "doctor_speciality": speciality,
        "hospital_id": hospital.id if hospital else None,
        "hospital_name": hospital.name if hospital else None,
        "appointment_date": appointment.appointment_date,
        "appointment_time": appointment.appointment_time,
        "location": appointment.location,
        "city": appointment.city,
        "state": appointment.state,
        "package_id": appointment.package_id,
        "package_name": appointment.package_name,
        "package_amount": appointment.package_amount,
        "consultation_fee": appointment.consultation_fee,
        "service_charge": appointment.service_charge,
        "total_amount": appointment.total_amount,
        "advance_paid": appointment.advance_paid,
        "remaining_balance": appointment.remaining_balance,
        "status": appointment.status,
        "payment_status": appointment.payment_status,
        "is_demo": appointment.is_demo,
        "created_at": appointment.created_at,
    }


def _invoice_data(invoice: Invoice) -> InvoiceRead:
    appointment = invoice.appointment
    doctor = appointment.doctor if appointment else None
    user = invoice.user
    return InvoiceRead(
        invoice_number=invoice.invoice_number,
        appointment_id=invoice.appointment_id,
        package_amount=invoice.package_amount,
        consultation_fee=invoice.consultation_fee,
        service_charge=invoice.service_charge,
        total_amount=invoice.total_amount,
        advance_paid=invoice.advance_paid,
        outstanding_balance=invoice.outstanding_balance,
        is_demo=invoice.is_demo,
        created_at=invoice.created_at,
        payments=[PaymentRead.model_validate(payment) for payment in invoice.payments],
        patient_name=user.full_name if user else None,
        doctor_name=doctor.full_name if doctor else None,
        appointment_date=appointment.appointment_date if appointment else None,
        appointment_time=appointment.appointment_time if appointment else None,
        location=appointment.location if appointment else None,
        payment_method=invoice.payments[0].method_label if invoice.payments else None,
        payment_status=invoice.payments[0].status if invoice.payments else None,
    )


def _detail(appointment: Appointment) -> AppointmentDetail:
    return AppointmentDetail(**_appointment_data(appointment), invoice=_invoice_data(appointment.invoice))


@router.post("/", response_model=AppointmentDetail, status_code=status.HTTP_201_CREATED)
def create_demo_appointment(
    request: AppointmentCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _user_for_email(db, current_user_email)
    if user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patient accounts can create appointments")
    doctor = db.query(Doctor).options(joinedload(Doctor.hospital)).filter(Doctor.id == request.doctor_id, Doctor.is_active.is_(True)).with_for_update().first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor listing is not available in the provider API")
    if doctor.hospital is None or not doctor.hospital.city or not doctor.hospital.state:
        raise HTTPException(status_code=409, detail="This doctor has no complete hospital location in the provider record")
    city, state = doctor.hospital.city, doctor.hospital.state
    schedule = doctor.schedule_json
    if not isinstance(schedule, dict):
        raise HTTPException(status_code=409, detail="No schedule was supplied for this doctor; booking is unavailable")
    if doctor.consultation_fee is None:
        raise HTTPException(status_code=409, detail="No consultation fee was supplied for this doctor; booking is unavailable")
    weekday = (request.appointment_date.weekday() + 1) % 7  # Sunday=0, matching the directory schedule format
    unavailable = schedule.get("unavailableDays", [])
    session = (schedule.get("privateOpd") or {}).get(str(weekday))
    if not session or weekday in unavailable:
        raise HTTPException(status_code=409, detail="This doctor has no private OPD on the selected date")
    clinic_location = str(session.get("location") or "").strip()
    if not clinic_location:
        raise HTTPException(status_code=409, detail="The selected OPD location is not available")
    start = datetime.strptime(session["start"], "%H:%M").time()
    end = datetime.strptime(session["end"], "%H:%M").time()
    duration = int(schedule.get("durationMinutes") or 30)
    selected = request.appointment_time
    if selected < start or selected >= end:
        raise HTTPException(status_code=409, detail="Choose a time within this doctor's private OPD hours")
    selected_minutes = selected.hour * 60 + selected.minute
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    if selected_minutes < start_minutes or (selected_minutes - start_minutes) % duration != 0 or selected_minutes + duration > end_minutes:
        raise HTTPException(status_code=409, detail="This is not a valid appointment slot for this doctor")
    duty = (schedule.get("governmentDuty") or {}).get(str(weekday))
    selected_end_minutes = selected_minutes + duration
    if duty:
        duty_start = datetime.strptime(duty["start"], "%H:%M").hour * 60 + int(duty["start"][3:])
        duty_end = datetime.strptime(duty["end"], "%H:%M").hour * 60 + int(duty["end"][3:])
        if selected_minutes < duty_end and selected_end_minutes > duty_start:
            raise HTTPException(status_code=409, detail="The selected time overlaps government duty")
    if session.get("breakStart") and session.get("breakEnd"):
        break_start = datetime.strptime(session["breakStart"], "%H:%M").hour * 60 + int(session["breakStart"][3:])
        break_end = datetime.strptime(session["breakEnd"], "%H:%M").hour * 60 + int(session["breakEnd"][3:])
        if selected_minutes < break_end and selected_end_minutes > break_start:
            raise HTTPException(status_code=409, detail="The selected time overlaps the doctor's break")
    local_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if request.appointment_date < local_now.date() or (request.appointment_date == local_now.date() and selected <= local_now.time().replace(tzinfo=None)):
        raise HTTPException(status_code=422, detail="Past appointment dates and times are not allowed")
    taken = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.appointment_date == request.appointment_date, Appointment.appointment_time == selected, Appointment.status != "cancelled").first()
    if taken:
        raise HTTPException(status_code=409, detail="That sample appointment slot has already been reserved")

    package_amount = request.package_amount if request.package_id else Decimal("0")
    package_name = request.package_name.strip() if request.package_id and request.package_name else None
    if request.package_id and not package_name:
        raise HTTPException(status_code=422, detail="A package name is required when a package is selected")
    consultation_fee = Decimal(str(doctor.consultation_fee))
    service_charge = Decimal("0")  # No service charge is applied in this demo.
    total = package_amount + consultation_fee + service_charge
    reference = f"EC-DEMO-{token_hex(5).upper()}"
    appointment = Appointment(
        reference=reference, user_id=user.id, doctor_id=doctor.id,
        appointment_date=request.appointment_date, appointment_time=selected,
        location=clinic_location, city=city, state=state,
        package_id=request.package_id, package_name=package_name, package_amount=package_amount,
        consultation_fee=consultation_fee, service_charge=service_charge,
        total_amount=total, advance_paid=total, remaining_balance=Decimal("0"),
        status="demo_confirmed", payment_status="demo_recorded", is_demo=True,
    )
    db.add(appointment)
    db.flush()
    invoice = Invoice(
        invoice_number=f"INV-{reference}", appointment_id=appointment.id, user_id=user.id,
        package_amount=package_amount, consultation_fee=consultation_fee,
        service_charge=service_charge, total_amount=total, advance_paid=total,
        outstanding_balance=Decimal("0"), is_demo=True,
    )
    db.add(invoice)
    db.flush()
    db.add(PaymentRecord(user_id=user.id, appointment_id=appointment.id, invoice_id=invoice.id, amount=total, method_label=request.payment_method, status="demo_success"))
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This appointment slot or its demo payment has already been saved") from exc
    db.refresh(appointment)
    return _detail(appointment)


@router.get("/me", response_model=list[AppointmentRead])
def list_my_appointments(current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    rows = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities)).filter(Appointment.user_id == user.id).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    return [AppointmentRead(**_appointment_data(row)) for row in rows]


@router.get("/me/{reference}", response_model=AppointmentDetail)
def get_my_appointment(reference: str, current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    row = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities), joinedload(Appointment.invoice).joinedload(Invoice.payments)).filter(Appointment.reference == reference, Appointment.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _detail(row)


@router.get("/me/invoices", response_model=list[InvoiceRead])
def list_my_invoices(current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    rows = db.query(Invoice).options(joinedload(Invoice.payments)).filter(Invoice.user_id == user.id).order_by(Invoice.created_at.desc()).all()
    return [_invoice_data(item) for item in rows]


@router.get("/doctor/me", response_model=list[AppointmentRead])
def list_doctor_appointments(current_user_email: str = Depends(require_provider), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    doctor = _doctor_for_user(db, user)
    rows = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities)).filter(Appointment.doctor_id == doctor.id).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    return [AppointmentRead(**_appointment_data(row)) for row in rows]


@router.get("/doctor/me/schedule")
def get_doctor_schedule(current_user_email: str = Depends(require_provider), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    doctor = _doctor_for_user(db, user)
    return {"doctor_id": doctor.id, "schedule": doctor.schedule_json}


@router.put("/doctor/me/schedule")
def update_doctor_schedule(request: DoctorScheduleUpdate, current_user_email: str = Depends(require_provider), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    doctor = _doctor_for_user(db, user)
    schedule = request.schedule
    if "privateOpd" not in schedule or not isinstance(schedule.get("privateOpd"), dict):
        raise HTTPException(status_code=422, detail="Schedule requires a privateOpd weekly map")
    doctor.schedule_json = schedule
    db.flush()
    return {"doctor_id": doctor.id, "schedule": doctor.schedule_json}


@router.get("/admin/all", response_model=list[AppointmentRead])
def admin_all_appointments(current_user_email: str = Depends(require_admin), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    rows = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities)).order_by(Appointment.created_at.desc()).all()
    return [AppointmentRead(**_appointment_data(row)) for row in rows]
