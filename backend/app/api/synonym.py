from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..models.base import SynonymGroup
from ..core.database import get_db

router = APIRouter(prefix="/api/v1/synonyms", tags=["synonyms"])


class SynonymGroupCreate(BaseModel):
    standard_term: str
    synonyms: List[str]
    category: Optional[str] = None
    enabled: bool = True


class SynonymGroupUpdate(BaseModel):
    standard_term: Optional[str] = None
    synonyms: Optional[List[str]] = None
    category: Optional[str] = None
    enabled: Optional[bool] = None


def _to_dict(row: SynonymGroup) -> dict:
    return {
        "id": str(row.id),
        "standard_term": row.standard_term,
        "synonyms": row.synonyms or [],
        "category": row.category,
        "enabled": bool(row.enabled),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
def list_synonyms(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(SynonymGroup)
    if category:
        query = query.filter(SynonymGroup.category == category)
    rows = query.order_by(SynonymGroup.created_at.desc()).all()
    return {
        "code": 200,
        "message": "success",
        "data": {"items": [_to_dict(r) for r in rows], "total": len(rows)},
    }


@router.post("")
def create_synonym(payload: SynonymGroupCreate, db: Session = Depends(get_db)):
    term = (payload.standard_term or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="standard_term is required")
    synonyms = [str(s).strip() for s in (payload.synonyms or []) if str(s or "").strip()]
    if not synonyms:
        raise HTTPException(status_code=400, detail="synonyms is required")
    existing = db.query(SynonymGroup).filter(SynonymGroup.standard_term == term).first()
    if existing:
        raise HTTPException(status_code=400, detail="standard_term already exists")
    row = SynonymGroup(
        standard_term=term,
        synonyms=synonyms,
        category=payload.category,
        enabled=payload.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"code": 200, "message": "created", "data": _to_dict(row)}


@router.put("/{group_id}")
def update_synonym(group_id: str, payload: SynonymGroupUpdate, db: Session = Depends(get_db)):
    row = db.query(SynonymGroup).filter(SynonymGroup.id == group_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    update_data = payload.dict(exclude_unset=True)
    if "standard_term" in update_data:
        term = (update_data["standard_term"] or "").strip()
        if not term:
            raise HTTPException(status_code=400, detail="standard_term is required")
        dup = db.query(SynonymGroup).filter(
            SynonymGroup.standard_term == term, SynonymGroup.id != group_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="standard_term already exists")
        row.standard_term = term
    if "synonyms" in update_data:
        synonyms = [str(s).strip() for s in (update_data["synonyms"] or []) if str(s or "").strip()]
        if not synonyms:
            raise HTTPException(status_code=400, detail="synonyms is required")
        row.synonyms = synonyms
    if "category" in update_data:
        row.category = update_data["category"]
    if "enabled" in update_data:
        row.enabled = update_data["enabled"]
    db.commit()
    db.refresh(row)
    return {"code": 200, "message": "updated", "data": _to_dict(row)}


@router.delete("/{group_id}")
def delete_synonym(group_id: str, db: Session = Depends(get_db)):
    row = db.query(SynonymGroup).filter(SynonymGroup.id == group_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    db.delete(row)
    db.commit()
    return {"code": 200, "message": "deleted"}
