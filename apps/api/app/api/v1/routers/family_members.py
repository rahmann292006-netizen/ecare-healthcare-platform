from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_email
from app.database import get_db
from app.models import FamilyMember, User
from app.schemas import FamilyMemberCreate, FamilyMemberRead

router = APIRouter(prefix="/family-members", tags=["family-members"])


def _get_active_user(db: Session, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")

    return user


@router.post("/", response_model=FamilyMemberRead, status_code=status.HTTP_201_CREATED)
def create_family_member(
    request: FamilyMemberCreate,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

    member = FamilyMember(
        user_id=user.id,
        name=request.name.strip(),
        relationship_type=request.relationship_type,
    )

    if not member.name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")

    db.add(member)
    db.flush()
    db.refresh(member)

    return member


@router.get("/me", response_model=list[FamilyMemberRead])
def list_family_members(
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

    return (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == user.id)
        .order_by(FamilyMember.created_at.desc())
        .all()
    )


@router.delete("/{member_id}")
def delete_family_member(
    member_id: int,
    current_user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
):
    user = _get_active_user(db, current_user_email)

    member = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.id == member_id,
            FamilyMember.user_id == user.id,
        )
        .first()
    )

    if member is None:
        raise HTTPException(status_code=404, detail="Family member not found")

    db.delete(member)
    db.flush()

    return {"message": "Family member deleted successfully"}
