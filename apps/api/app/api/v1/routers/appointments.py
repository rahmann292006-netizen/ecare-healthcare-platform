"""Account-scoped demo appointments, invoices, and doctor schedules."""

from datetime import date, datetime, time, timezone
from decimal import Decimal
from secrets import token_hex
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user_email, require_admin, require_provider
from app.database import get_db
from app.models import Appointment, Doctor, Hospital, Invoice, Package, PaymentRecord, User
from app.schemas import (
    AppointmentAvailabilitySlot,
    AppointmentCreate,
    AppointmentDetail,
    AppointmentRead,
    AppointmentStatusUpdate,
    DoctorAppointmentAvailability,
    DoctorScheduleUpdate,
    InvoiceRead,
    PaymentRead,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _schedule_minutes(value, field_name: str) -> int:
    if not isinstance(value, str):
        raise HTTPException(status_code=409, detail=f"Doctor schedule has an invalid {field_name}")
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=409, detail=f"Doctor schedule has an invalid {field_name}") from None
    return parsed.hour * 60 + parsed.minute


def _clock_time(minutes: int) -> time:
    return time(hour=minutes // 60, minute=minutes % 60)


def _valid_schedule_session(schedule: dict, weekday: int):
    private_opd = schedule.get("privateOpd")
    unavailable = schedule.get("unavailableDays", [])
    if not isinstance(private_opd, dict) or not isinstance(unavailable, list):
        return None
    if any(not isinstance(day, int) or isinstance(day, bool) for day in unavailable):
        return None
    if weekday in unavailable:
        return None
    session = private_opd.get(str(weekday))
    if not isinstance(session, dict) or not str(session.get("location") or "").strip():
        return None
    try:
        start = _schedule_minutes(session.get("start"), "OPD start time")
        end = _schedule_minutes(session.get("end"), "OPD end time")
    except HTTPException:
        return None
    return (start, end, session) if end > start else None


def _doctor_consultation_days(schedule: dict) -> list[str]:
    days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
    return [
        days[weekday]
        for weekday in range(7)
        if _valid_schedule_session(schedule, weekday) is not None
    ]


@router.get(
    "/availability/{doctor_id}",
    response_model=DoctorAppointmentAvailability,
)
def get_doctor_appointment_availability(
    doctor_id: int,
    appointment_date: date = Query(...),
    db: Session = Depends(get_db),
):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.hospital))
        .filter(Doctor.id == doctor_id, Doctor.is_active.is_(True))
        .first()
    )
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor listing is not available")

    schedule = doctor.schedule_json
    no_booking_message = "Currently unavailable for online appointment booking."
    base = {
        "doctor_id": doctor.id,
        "appointment_date": appointment_date,
        "consultation_days": [],
        "consultation_fee": doctor.consultation_fee,
        "duration_minutes": None,
        "slots": [],
        "fully_booked": False,
    }
    if (
        not isinstance(schedule, dict)
        or doctor.consultation_fee is None
        or doctor.hospital is None
        or not doctor.hospital.city
        or not doctor.hospital.state
    ):
        return DoctorAppointmentAvailability(**base, message=no_booking_message)

    duration = schedule.get("durationMinutes", 30)
    if not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 1440:
        return DoctorAppointmentAvailability(**base, message=no_booking_message)

    consultation_days = _doctor_consultation_days(schedule)
    base["consultation_days"] = consultation_days
    base["duration_minutes"] = duration
    if not consultation_days:
        return DoctorAppointmentAvailability(**base, message=no_booking_message)

    weekday = (appointment_date.weekday() + 1) % 7
    session_data = _valid_schedule_session(schedule, weekday)
    if session_data is None:
        return DoctorAppointmentAvailability(
            **base,
            message="No private OPD is scheduled for this doctor on the selected date.",
        )

    start, end, session = session_data
    base["opd_start"] = _clock_time(start)
    base["opd_end"] = _clock_time(end)
    base["clinic_location"] = str(session["location"]).strip()
    government_duty = schedule.get("governmentDuty", {})
    if not isinstance(government_duty, dict):
        return DoctorAppointmentAvailability(**base, message=no_booking_message)
    duty = government_duty.get(str(weekday))
    if duty and not isinstance(duty, dict):
        return DoctorAppointmentAvailability(**base, message=no_booking_message)
    try:
        duty_range = (
            (
                _schedule_minutes(duty.get("start"), "government duty start time"),
                _schedule_minutes(duty.get("end"), "government duty end time"),
            )
            if duty
            else None
        )
        if duty_range and duty_range[1] <= duty_range[0]:
            raise HTTPException(status_code=409, detail="Invalid government duty hours")
        break_start_value = session.get("breakStart")
        break_end_value = session.get("breakEnd")
        if (break_start_value is None) != (break_end_value is None):
            raise HTTPException(status_code=409, detail="Incomplete break hours")
        break_range = (
            (
                _schedule_minutes(break_start_value, "break start time"),
                _schedule_minutes(break_end_value, "break end time"),
            )
            if break_start_value is not None
            else None
        )
        if break_range and break_range[1] <= break_range[0]:
            raise HTTPException(status_code=409, detail="Invalid break hours")
    except HTTPException:
        return DoctorAppointmentAvailability(**base, message=no_booking_message)

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    booked_times = {
        booked_time.hour * 60 + booked_time.minute
        for (booked_time,) in db.query(Appointment.appointment_time)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == appointment_date,
            Appointment.status != "cancelled",
        )
        .all()
    }
    slots = []
    for selected in range(start, end - duration + 1, duration):
        reason = None
        if appointment_date < now.date() or (
            appointment_date == now.date()
            and selected <= now.hour * 60 + now.minute
        ):
            reason = "This time has already passed."
        elif selected in booked_times:
            reason = "This slot has already been booked."
        elif duty_range and selected < duty_range[1] and selected + duration > duty_range[0]:
            reason = "This slot overlaps the doctor's government duty."
        elif break_range and selected < break_range[1] and selected + duration > break_range[0]:
            reason = "This slot overlaps the doctor's break."
        slots.append(
            AppointmentAvailabilitySlot(
                time=_clock_time(selected),
                status="unavailable" if reason else "available",
                reason=reason,
            )
        )

    available_slots = [slot for slot in slots if slot.status == "available"]
    fully_booked = bool(slots) and all(
        slot.reason == "This slot has already been booked." for slot in slots
    )
    return DoctorAppointmentAvailability(
        **{**base, "slots": slots, "fully_booked": fully_booked},
        message=(
            "All appointment slots are booked for this date."
            if fully_booked
            else "No appointment slots are available on this date."
            if not available_slots
            else None
        ),
    )


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
        "patient_name": appointment.user.full_name if appointment.user else None,
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
    private_opd = schedule.get("privateOpd")
    unavailable = schedule.get("unavailableDays", [])
    if (
        not isinstance(private_opd, dict)
        or not isinstance(unavailable, list)
        or any(not isinstance(day, int) or isinstance(day, bool) for day in unavailable)
    ):
        raise HTTPException(status_code=409, detail="Doctor schedule is invalid; booking is unavailable")
    session = private_opd.get(str(weekday))
    if not isinstance(session, dict) or weekday in unavailable:
        raise HTTPException(status_code=409, detail="This doctor has no private OPD on the selected date")
    clinic_location = str(session.get("location") or "").strip()
    if not clinic_location:
        raise HTTPException(status_code=409, detail="The selected OPD location is not available")
    start_minutes = _schedule_minutes(session.get("start"), "OPD start time")
    end_minutes = _schedule_minutes(session.get("end"), "OPD end time")
    if end_minutes <= start_minutes:
        raise HTTPException(status_code=409, detail="Doctor schedule has invalid OPD hours")
    duration = schedule.get("durationMinutes", 30)
    if not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 1440:
        raise HTTPException(status_code=409, detail="Doctor schedule has an invalid appointment duration")
    selected = request.appointment_time
    if selected.tzinfo is not None or selected.second or selected.microsecond:
        raise HTTPException(status_code=422, detail="Appointment time must be an exact local minute")
    selected_minutes = selected.hour * 60 + selected.minute
    if selected_minutes < start_minutes or selected_minutes >= end_minutes:
        raise HTTPException(status_code=409, detail="Choose a time within this doctor's private OPD hours")
    if (selected_minutes - start_minutes) % duration != 0 or selected_minutes + duration > end_minutes:
        raise HTTPException(status_code=409, detail="This is not a valid appointment slot for this doctor")
    government_duty = schedule.get("governmentDuty", {})
    if not isinstance(government_duty, dict):
        raise HTTPException(status_code=409, detail="Doctor schedule has invalid government duty hours")
    duty = government_duty.get(str(weekday))
    selected_end_minutes = selected_minutes + duration
    if duty:
        if not isinstance(duty, dict):
            raise HTTPException(status_code=409, detail="Doctor schedule has invalid government duty hours")
        duty_start = _schedule_minutes(duty.get("start"), "government duty start time")
        duty_end = _schedule_minutes(duty.get("end"), "government duty end time")
        if duty_end <= duty_start:
            raise HTTPException(status_code=409, detail="Doctor schedule has invalid government duty hours")
        if selected_minutes < duty_end and selected_end_minutes > duty_start:
            raise HTTPException(status_code=409, detail="The selected time overlaps government duty")
    break_start_value = session.get("breakStart")
    break_end_value = session.get("breakEnd")
    if (break_start_value is None) != (break_end_value is None):
        raise HTTPException(status_code=409, detail="Doctor schedule has incomplete break hours")
    if break_start_value is not None:
        break_start = _schedule_minutes(break_start_value, "break start time")
        break_end = _schedule_minutes(break_end_value, "break end time")
        if break_end <= break_start:
            raise HTTPException(status_code=409, detail="Doctor schedule has invalid break hours")
        if selected_minutes < break_end and selected_end_minutes > break_start:
            raise HTTPException(status_code=409, detail="The selected time overlaps the doctor's break")
    local_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if request.appointment_date < local_now.date() or (request.appointment_date == local_now.date() and selected <= local_now.time().replace(tzinfo=None)):
        raise HTTPException(status_code=422, detail="Past appointment dates and times are not allowed")
    taken = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.appointment_date == request.appointment_date, Appointment.appointment_time == selected, Appointment.status != "cancelled").first()
    if taken:
        raise HTTPException(status_code=409, detail="That sample appointment slot has already been reserved")

    package = None
    if request.package_id:
        package = db.query(Package).filter(
            Package.id == request.package_id,
            Package.is_active.is_(True),
        ).first()
        if package is None:
            raise HTTPException(status_code=404, detail="Selected package is not available")
        if package.is_demo:
            raise HTTPException(status_code=409, detail="Demo/sample packages cannot be booked online")
        if (
            not package.is_verified
            or package.verified_at is None
            or not package.source
            or not package.source.strip()
        ):
            raise HTTPException(
                status_code=409,
                detail="Only provider-sourced, verified packages can be booked online",
            )
        if package.city.casefold() != city.casefold() or package.state.casefold() != state.casefold():
            raise HTTPException(status_code=409, detail="Selected package is not available in this doctor's location")
    package_amount = Decimal(str(package.price)) if package else Decimal("0")
    package_name = package.name if package else None
    consultation_fee = Decimal(str(doctor.consultation_fee))
    service_charge = Decimal("0")  # No service charge is applied in this demo.
    total = package_amount + consultation_fee + service_charge
    reference = f"EC-DEMO-{token_hex(5).upper()}"
    appointment = Appointment(
        reference=reference, user_id=user.id, doctor_id=doctor.id,
        appointment_date=request.appointment_date, appointment_time=selected,
        location=clinic_location, city=city, state=state,
        package_id=package.id if package else None, package_name=package_name, package_amount=package_amount,
        consultation_fee=consultation_fee, service_charge=service_charge,
        total_amount=total, advance_paid=total, remaining_balance=Decimal("0.00"),
        status="demo_confirmed", payment_status="demo_recorded", is_demo=True,
    )
    try:
        db.add(appointment)
        db.flush()
        invoice = Invoice(
            invoice_number=f"INV-{reference}", appointment_id=appointment.id, user_id=user.id,
            package_amount=package_amount, consultation_fee=consultation_fee,
            service_charge=service_charge, total_amount=total, advance_paid=total,
            outstanding_balance=Decimal("0.00"), is_demo=True,
        )
        db.add(invoice)
        db.flush()
        db.add(PaymentRecord(
            user_id=user.id,
            appointment_id=appointment.id,
            invoice_id=invoice.id,
            amount=total,
            method_label="DEMO PAYMENT - NOT A REAL TRANSACTION",
            status="simulated",
        ))
        db.flush()
        db.refresh(appointment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This appointment slot has already been booked") from exc
    return _detail(appointment)


@router.get("/me", response_model=list[AppointmentRead])
def list_my_appointments(current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    rows = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities)).filter(Appointment.user_id == user.id).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    return [AppointmentRead(**_appointment_data(row)) for row in rows]


@router.get("/me/invoices", response_model=list[InvoiceRead])
def list_my_invoices(current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    rows = db.query(Invoice).options(joinedload(Invoice.payments)).filter(Invoice.user_id == user.id).order_by(Invoice.created_at.desc()).all()
    return [_invoice_data(item) for item in rows]


@router.patch("/me/{reference}/cancel", response_model=AppointmentRead)
def cancel_my_appointment(
    reference: str,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _user_for_email(db, current_user_email)
    if user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patient accounts can cancel appointments")
    appointment = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.hospital),
            joinedload(Appointment.doctor).joinedload(Doctor.specialities),
        )
        .filter(Appointment.reference == reference, Appointment.user_id == user.id)
        .first()
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status == "cancelled":
        return AppointmentRead(**_appointment_data(appointment))
    if appointment.status not in {"pending", "demo_confirmed"}:
        raise HTTPException(status_code=409, detail="Only active demo appointments can be cancelled")
    appointment.status = "cancelled"
    db.flush()
    return AppointmentRead(**_appointment_data(appointment))


@router.get("/me/{reference}", response_model=AppointmentDetail)
def get_my_appointment(reference: str, current_user_email: str = Depends(get_current_user_email), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    row = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities), joinedload(Appointment.invoice).joinedload(Invoice.payments)).filter(Appointment.reference == reference, Appointment.user_id == user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _detail(row)


@router.get("/doctor/me", response_model=list[AppointmentRead])
def list_doctor_appointments(current_user_email: str = Depends(require_provider), db: Session = Depends(get_db)):
    user = _user_for_email(db, current_user_email)
    doctor = _doctor_for_user(db, user)
    rows = db.query(Appointment).options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities)).filter(Appointment.doctor_id == doctor.id).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    return [AppointmentRead(**_appointment_data(row)) for row in rows]


@router.patch("/doctor/me/{appointment_id}/status", response_model=AppointmentRead)
def update_doctor_appointment_status(
    appointment_id: int,
    request: AppointmentStatusUpdate,
    current_user_email: str = Depends(require_provider),
    db: Session = Depends(get_db),
):
    user = _user_for_email(db, current_user_email)
    doctor = _doctor_for_user(db, user)
    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor).joinedload(Doctor.hospital), joinedload(Appointment.doctor).joinedload(Doctor.specialities))
        .filter(Appointment.id == appointment_id, Appointment.doctor_id == doctor.id)
        .first()
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending appointment requests can be reviewed")
    appointment.status = request.status
    db.flush()
    return AppointmentRead(**_appointment_data(appointment))


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
