from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FocusSession
from app.schemas import FocusSessionCreate, FocusSessionOut, FocusSessionUpdate

router = APIRouter(prefix="/focus_sessions", tags=["focus_sessions"])


@router.post("", response_model=FocusSessionOut, status_code=201)
def create_session(data: FocusSessionCreate, db: Session = Depends(get_db)):
    obj = FocusSession(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{session_id}", response_model=FocusSessionOut)
def update_session(
    session_id: str, data: FocusSessionUpdate, db: Session = Depends(get_db)
):
    obj = db.query(FocusSession).filter(FocusSession.id == session_id).first()
    if not obj:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Focus session not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{user_id}/recent", response_model=list[FocusSessionOut])
def get_recent_sessions(
    user_id: str, limit: int = 10, db: Session = Depends(get_db)
):
    return (
        db.query(FocusSession)
        .filter(FocusSession.user_id == user_id)
        .order_by(FocusSession.started_at.desc())
        .limit(limit)
        .all()
    )