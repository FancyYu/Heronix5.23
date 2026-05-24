from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Status
from app.schemas import StatusCreate, StatusOut

router = APIRouter(prefix="/status", tags=["status"])


@router.post("", response_model=StatusOut, status_code=201)
def create_status(data: StatusCreate, db: Session = Depends(get_db)):
    st = Status(**data.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@router.get("/{user_id}/latest", response_model=StatusOut)
def get_latest_status(user_id: str, db: Session = Depends(get_db)):
    st = (
        db.query(Status)
        .filter(Status.user_id == user_id)
        .order_by(Status.recorded_at.desc())
        .first()
    )
    if not st:
        return StatusOut(
            id="none",
            user_id=user_id,
            recorded_at=None,
            energy_level=5,
            mood="calm",
            focus_level=5,
            sensory_load="comfortable",
            context="alone",
            trigger_note="",
            inferred_mode="",
            suggestion="",
        )
    return st


@router.get("/{user_id}/history", response_model=list[StatusOut])
def get_status_history(user_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Status)
        .filter(Status.user_id == user_id)
        .order_by(Status.recorded_at.desc())
        .limit(50)
        .all()
    )