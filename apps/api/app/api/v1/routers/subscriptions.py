"""Health checkup plan subscriptions and in-app expiry reminders."""

import calendar
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth import get_current_user_email, require_admin, require_patient
from app.database import get_db
from app.models import (
    FamilyMember,
    Package,
    Reminder,
    Subscription,
    SubscriptionEvent,
    User,
)
from app.schemas import (
    SubscriptionCancellationRequest,
    SubscriptionCreate,
    SubscriptionPaymentOptionsRead,
    SubscriptionRead,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
SUBSCRIPTION_ID = Annotated[int, Path(ge=1, le=2_147_483_647)]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _simulated_payment_enabled() -> bool:
    return (
        os.environ.get("ECARE_ENVIRONMENT", "production").casefold()
        in {"development", "test"}
        and os.environ.get("ECARE_SIMULATED_PAYMENTS_ENABLED", "false").casefold()
        == "true"
    )


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _validity_months(plan: Package) -> int:
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}.get(plan.validity_period)
    if months is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This plan has no provider-supplied validity period.",
        )
    return months


def _active_user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


def _verified_plan(db: Session, plan_id: int) -> Package:
    plan = (
        db.query(Package)
        .options(selectinload(Package.inclusions))
        .filter(Package.id == plan_id, Package.is_active.is_(True))
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    if (
        plan.is_demo
        or not plan.is_verified
        or not plan.verified_at
        or not plan.source
        or not plan.source.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="Only provider-sourced, verified plans can be subscribed to.",
        )
    _validity_months(plan)
    return plan


def _validate_age(plan: Package, age_years: int | None) -> None:
    if plan.min_age_years is None and plan.max_age_years is None:
        return
    if age_years is None:
        raise HTTPException(
            status_code=422,
            detail="Enter the person's self-reported age to check this plan's eligibility.",
        )
    if plan.min_age_years is not None and age_years < plan.min_age_years:
        raise HTTPException(status_code=422, detail="The age is below this plan's stated range.")
    if plan.max_age_years is not None and age_years > plan.max_age_years:
        raise HTTPException(status_code=422, detail="The age is above this plan's stated range.")


def _record_event(
    db: Session,
    subscription: Subscription,
    actor_user_id: int | None,
    event_type: str,
    previous_status: str | None,
    details: str | None = None,
) -> None:
    subscription.events.append(
        SubscriptionEvent(
            subscription_id=subscription.id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=subscription.status,
            payment_status=subscription.payment_status,
            amount=subscription.amount,
            details=details,
        )
    )
    db.flush()


def _set_reminder_completed(subscription: Subscription) -> None:
    if subscription.reminder is not None:
        subscription.reminder.completed = True


def _refresh_status(
    db: Session, subscription: Subscription, now: datetime | None = None
) -> None:
    current_time = _as_utc(now or _utc_now())
    start_at = _as_utc(subscription.start_at)
    expires_at = _as_utc(subscription.expires_at)
    previous_status = subscription.status
    if subscription.status in {"active", "scheduled"} and current_time >= expires_at:
        subscription.status = "expired"
        _set_reminder_completed(subscription)
        _record_event(
            db,
            subscription,
            None,
            "expired",
            previous_status,
            "Validity period ended; expiry is applied when the record is accessed.",
        )
    elif (
        subscription.status == "scheduled"
        and current_time >= start_at
        and subscription.payment_status in {"paid", "simulated"}
    ):
        subscription.status = "active"
        _record_event(db, subscription, None, "activated", previous_status)


def _add_expiry_reminder(db: Session, subscription: Subscription) -> None:
    existing = (
        db.query(Reminder.id)
        .filter(Reminder.subscription_id == subscription.id)
        .first()
    )
    if existing is not None:
        return
    subscription.reminder = Reminder(
        user_id=subscription.user_id,
        family_member_id=subscription.family_member_id,
        subscription_id=subscription.id,
        title=f"{subscription.plan.name} validity ends",
        category="checkup",
        reminder_date=_as_utc(subscription.expires_at).date(),
        repeat_interval="none",
    )


def _subscription_query(db: Session):
    return db.query(Subscription).options(
        joinedload(Subscription.plan).selectinload(Package.inclusions),
        selectinload(Subscription.events),
        joinedload(Subscription.reminder),
        selectinload(Subscription.renewal),
    )


def _create_subscription(
    db: Session,
    user: User,
    plan: Package,
    family_member_id: int | None,
    age_years: int | None,
    start_at: datetime,
    renewal_of_id: int | None,
    event_type: str,
) -> Subscription:
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        family_member_id=family_member_id,
        age_years_at_start=age_years,
        amount=Decimal(plan.price),
        currency=plan.currency,
        start_at=start_at,
        expires_at=_add_months(start_at, _validity_months(plan)),
        status="pending_payment",
        payment_status="pending",
        renewal_of_id=renewal_of_id,
    )
    db.add(subscription)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An active or pending subscription already exists for this plan.",
        ) from exc
    _record_event(
        db,
        subscription,
        user.id,
        event_type,
        None,
        "Payment is pending; no payment gateway is configured.",
    )
    db.flush()
    return subscription


def _user_subscription(
    db: Session, user_id: int, subscription_id: int
) -> Subscription:
    subscription = (
        _subscription_query(db)
        .filter(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id,
        )
        .first()
    )
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    _refresh_status(db, subscription)
    return subscription


def _cancel_subscription(
    db: Session,
    subscription: Subscription,
    actor_user_id: int,
    reason: str | None,
) -> None:
    _refresh_status(db, subscription)
    if subscription.status in {"cancelled", "expired"}:
        raise HTTPException(
            status_code=409,
            detail=f"A {subscription.status} subscription cannot be cancelled.",
        )
    previous_status = subscription.status
    subscription.status = "cancelled"
    _set_reminder_completed(subscription)
    _record_event(
        db,
        subscription,
        actor_user_id,
        "cancelled",
        previous_status,
        reason.strip() if reason and reason.strip() else None,
    )
    db.flush()


@router.get("/payment-options", response_model=SubscriptionPaymentOptionsRead)
def payment_options():
    if _simulated_payment_enabled():
        return SubscriptionPaymentOptionsRead(
            mode="simulated",
            message="Demo payment only; no real charge is made.",
        )
    return SubscriptionPaymentOptionsRead(
        mode="unavailable",
        message="No payment gateway is configured. Subscriptions remain pending payment.",
    )


@router.get("/me", response_model=list[SubscriptionRead])
def list_my_subscriptions(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _active_user(db, current_user_email)
    subscriptions = (
        _subscription_query(db)
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
        .all()
    )
    for subscription in subscriptions:
        _refresh_status(db, subscription)
    return subscriptions


@router.get("/me/entitlements", response_model=list[int])
def list_my_entitlements(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _active_user(db, current_user_email)
    now = _utc_now()
    subscriptions = (
        _subscription_query(db)
        .filter(Subscription.user_id == user.id)
        .all()
    )
    entitlements: set[int] = set()
    for subscription in subscriptions:
        _refresh_status(db, subscription, now)
        payment_valid = subscription.payment_status == "paid" or (
            subscription.payment_status == "simulated"
            and _simulated_payment_enabled()
        )
        if (
            subscription.status == "active"
            and _as_utc(subscription.start_at) <= now < _as_utc(subscription.expires_at)
            and payment_valid
        ):
            entitlements.add(subscription.plan_id)
    return sorted(entitlements)


@router.get("/admin", response_model=list[SubscriptionRead])
def list_all_subscriptions(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    subscriptions = (
        _subscription_query(db)
        .order_by(Subscription.created_at.desc())
        .all()
    )
    for subscription in subscriptions:
        _refresh_status(db, subscription)
    return subscriptions


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(
    request: SubscriptionCreate,
    current_user_email: str = Depends(require_patient),
    db: Session = Depends(get_db),
):
    user = _active_user(db, current_user_email)
    plan = _verified_plan(db, request.plan_id)
    _validate_age(plan, request.age_years)
    family_member_id = None
    if request.family_member_id is not None:
        member = (
            db.query(FamilyMember)
            .filter(
                FamilyMember.id == request.family_member_id,
                FamilyMember.user_id == user.id,
            )
            .first()
        )
        if member is None:
            raise HTTPException(status_code=404, detail="Family member not found")
        family_member_id = member.id

    existing = (
        db.query(Subscription.id)
        .filter(
            Subscription.user_id == user.id,
            Subscription.plan_id == plan.id,
            Subscription.status.in_(("pending_payment", "scheduled", "active")),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="An active or pending subscription already exists for this plan.",
        )

    subscription = _create_subscription(
        db,
        user,
        plan,
        family_member_id,
        request.age_years,
        _utc_now(),
        None,
        "created",
    )
    return _user_subscription(db, user.id, subscription.id)


@router.post(
    "/admin/{subscription_id}/cancel",
    response_model=SubscriptionRead,
)
def admin_cancel_subscription(
    subscription_id: SUBSCRIPTION_ID,
    request: SubscriptionCancellationRequest,
    actor_email: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    actor = _active_user(db, actor_email)
    subscription = (
        _subscription_query(db)
        .filter(Subscription.id == subscription_id)
        .first()
    )
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    _cancel_subscription(db, subscription, actor.id, request.reason)
    return subscription


@router.get("/{subscription_id}", response_model=SubscriptionRead)
def get_my_subscription(
    subscription_id: SUBSCRIPTION_ID,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _active_user(db, current_user_email)
    return _user_subscription(db, user.id, subscription_id)


@router.post(
    "/{subscription_id}/renew",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def renew_subscription(
    subscription_id: SUBSCRIPTION_ID,
    request: SubscriptionCreate,
    current_user_email: str = Depends(require_patient),
    db: Session = Depends(get_db),
):
    user = _active_user(db, current_user_email)
    previous = _user_subscription(db, user.id, subscription_id)
    if previous.status == "cancelled":
        raise HTTPException(status_code=409, detail="A cancelled subscription cannot be renewed.")
    if previous.status == "pending_payment":
        raise HTTPException(
            status_code=409,
            detail="Complete or cancel the pending subscription before renewing.",
        )
    existing_renewal = (
        db.query(Subscription.id)
        .filter(Subscription.renewal_of_id == previous.id)
        .first()
    )
    if existing_renewal is not None:
        raise HTTPException(status_code=409, detail="This subscription already has a renewal.")

    plan_id = request.plan_id
    if plan_id != previous.plan_id:
        raise HTTPException(status_code=422, detail="Renewal must use the same plan.")
    plan = _verified_plan(db, plan_id)
    age_years = (
        request.age_years
        if request.age_years is not None
        else previous.age_years_at_start
    )
    _validate_age(plan, age_years)
    family_member_id = request.family_member_id
    if family_member_id is None:
        family_member_id = previous.family_member_id
    if family_member_id is not None:
        member = (
            db.query(FamilyMember)
            .filter(
                FamilyMember.id == family_member_id,
                FamilyMember.user_id == user.id,
            )
            .first()
        )
        if member is None:
            raise HTTPException(status_code=404, detail="Family member not found")

    start_at = max(_utc_now(), _as_utc(previous.expires_at))
    renewed = _create_subscription(
        db,
        user,
        plan,
        family_member_id,
        age_years,
        start_at,
        previous.id,
        "renewed",
    )
    previous.renewal = renewed
    return _user_subscription(db, user.id, renewed.id)


@router.post("/{subscription_id}/simulate-payment", response_model=SubscriptionRead)
def simulate_subscription_payment(
    subscription_id: SUBSCRIPTION_ID,
    current_user_email: str = Depends(require_patient),
    db: Session = Depends(get_db),
):
    if not _simulated_payment_enabled():
        raise HTTPException(
            status_code=503,
            detail="Simulated payments are disabled; no payment gateway is configured.",
        )
    user = _active_user(db, current_user_email)
    subscription = _user_subscription(db, user.id, subscription_id)
    if subscription.status != "pending_payment" or subscription.payment_status != "pending":
        raise HTTPException(status_code=409, detail="This subscription is not awaiting payment.")

    previous_status = subscription.status
    subscription.payment_status = "simulated"
    subscription.status = (
        "scheduled" if _utc_now() < _as_utc(subscription.start_at) else "active"
    )
    _record_event(
        db,
        subscription,
        user.id,
        "payment_simulated",
        previous_status,
        "Demo payment recorded; no real charge was made.",
    )
    _add_expiry_reminder(db, subscription)
    db.flush()
    return _user_subscription(db, user.id, subscription.id)


@router.post("/{subscription_id}/cancel", response_model=SubscriptionRead)
def cancel_my_subscription(
    subscription_id: SUBSCRIPTION_ID,
    request: SubscriptionCancellationRequest,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _active_user(db, current_user_email)
    subscription = _user_subscription(db, user.id, subscription_id)
    _cancel_subscription(db, subscription, user.id, request.reason)
    return subscription
