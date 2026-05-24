from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Action
from app.schemas import ActionCreate, ActionOut

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("", response_model=ActionOut, status_code=201)
def create_action(data: ActionCreate, db: Session = Depends(get_db)):
    act = Action(**data.model_dump())
    db.add(act)
    db.commit()
    db.refresh(act)
    return act


@router.get("/{user_id}/recent", response_model=list[ActionOut])
def get_recent_actions(user_id: str, limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(Action)
        .filter(Action.user_id == user_id)
        .order_by(Action.created_at.desc())
        .limit(limit)
        .all()
    )