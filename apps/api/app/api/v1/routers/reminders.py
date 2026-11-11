from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_email
from app.database import get_db
from app.models import FamilyMember, Reminder, User
from app.schemas import ReminderCreate, ReminderUpdate, ReminderRead

router = APIRouter(prefix="/reminders", tags=["reminders"])


def _get_active_user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")

    return user


@router.post("/", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
def create_reminder(
    request: ReminderCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

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

    reminder = Reminder(
        user_id=user.id,
        family_member_id=member.id,
        title=request.title.strip(),
        category=request.category,
        reminder_date=request.reminder_date,
        repeat_interval=request.repeat_interval,
    )

    if not reminder.title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    db.add(reminder)
    db.flush()
    db.refresh(reminder)

    return reminder


@router.get("/me", response_model=list[ReminderRead])
def list_my_reminders(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

    return (
        db.query(Reminder)
        .filter(Reminder.user_id == user.id)
        .order_by(Reminder.reminder_date.asc())
        .all()
    )


@router.patch("/{reminder_id}", response_model=ReminderRead)
def update_reminder(
    reminder_id: int,
    request: ReminderUpdate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

    reminder = (
        db.query(Reminder)
        .filter(
            Reminder.id == reminder_id,
            Reminder.user_id == user.id,
        )
        .first()
    )

    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")

    updates = request.model_dump(exclude_unset=True)
    if reminder.subscription_id is not None and set(updates) - {"completed"}:
        raise HTTPException(
            status_code=409,
            detail="Subscription expiry reminders are managed through the subscription.",
        )

    if "title" in updates:
        updates["title"] = updates["title"].strip()

        if not updates["title"]:
            raise HTTPException(status_code=422, detail="Title cannot be empty")

    for field, value in updates.items():
        setattr(reminder, field, value)

    db.flush()
    db.refresh(reminder)

    return reminder


@router.delete("/{reminder_id}")
def delete_reminder(
    reminder_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

    reminder = (
        db.query(Reminder)
        .filter(
            Reminder.id == reminder_id,
            Reminder.user_id == user.id,
        )
        .first()
    )

    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if reminder.subscription_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Subscription expiry reminders are managed through the subscription.",
        )

    db.delete(reminder)
    db.flush()

    return {"message": "Reminder deleted successfully"}
