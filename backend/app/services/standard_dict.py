from sqlalchemy.orm import Session
from app.models.base import StandardDict
import uuid


def list_standard_dict(db: Session, keyword: str = None, category: str = None, enabled: bool = None):
    q = db.query(StandardDict)
    if enabled is not None:
        q = q.filter(StandardDict.enabled == enabled)
    if category:
        q = q.filter(StandardDict.category == category)
    if keyword:
        kw = keyword.lower()
        q = q.filter(
            (StandardDict.non_standard.ilike(f"%{kw}%")) |
            (StandardDict.standard.ilike(f"%{kw}%"))
        )
    return q.order_by(StandardDict.updated_at.desc()).all()


def create_standard_dict(db: Session, non_standard: str, standard: str, category: str = None, description: str = "") -> tuple:
    check = db.query(StandardDict).filter(StandardDict.non_standard == non_standard).first()
    if check:
        return check, True
    item = StandardDict(non_standard=non_standard, standard=standard, category=category, description=description, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_standard_dict(db: Session, item_id: str, non_standard: str = None, standard: str = None, category: str = None, enabled: bool = None, description: str = None):
    item = db.query(StandardDict).filter(StandardDict.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if non_standard is not None:
        item.non_standard = non_standard
    if standard is not None:
        item.standard = standard
    if category is not None:
        item.category = category
    if enabled is not None:
        item.enabled = enabled
    if description is not None:
        item.description = description
    db.commit()
    db.refresh(item)
    return item


def delete_standard_dict(db: Session, item_id: str):
    item = db.query(StandardDict).filter(StandardDict.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
