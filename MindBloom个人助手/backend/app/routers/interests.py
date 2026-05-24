from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Interest
from app.schemas import InterestCreate, InterestOut, InterestUpdate

router = APIRouter(prefix="/interests", tags=["interests"])


@router.get("/{user_id}", response_model=list[InterestOut])
def list_interests(user_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Interest)
        .filter(Interest.user_id == user_id)
        .order_by(Interest.created_at.desc())
        .all()
    )


@router.post("", response_model=InterestOut, status_code=201)
def create_interest(data: InterestCreate, db: Session = Depends(get_db)):
    obj = Interest(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{interest_id}", response_model=InterestOut)
def update_interest(
    interest_id: str, data: InterestUpdate, db: Session = Depends(get_db)
):
    obj = db.query(Interest).filter(Interest.id == interest_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Interest not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    db.commit()
    db.refresh(obj)
    return obj