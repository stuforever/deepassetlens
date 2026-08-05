from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.base import CommonStopWord


def list_stop_words(db: Session, category: Optional[str] = None, enabled_only: bool = False) -> List[CommonStopWord]:
    q = db.query(CommonStopWord)
    if category:
        q = q.filter(CommonStopWord.category == category)
    if enabled_only:
        q = q.filter(CommonStopWord.enabled == True)
    return q.order_by(CommonStopWord.created_at.desc()).all()


def create_stop_word(db: Session, word: str, category: str = "filler", description: str = "") -> tuple:
    check = db.query(CommonStopWord).filter(CommonStopWord.word == word).first()
    if check:
        return check, True
    sw = CommonStopWord(word=word, category=category, description=description, enabled=True)
    db.add(sw)
    db.commit()
    db.refresh(sw)
    return sw, False


def update_stop_word(db: Session, word_id: str, word: str = None, description: str = None, enabled: bool = None) -> Optional[CommonStopWord]:
    sw = db.query(CommonStopWord).filter(CommonStopWord.id == word_id).first()
    if not sw:
        return None
    if word is not None:
        sw.word = word
    if description is not None:
        sw.description = description
    if enabled is not None:
        sw.enabled = enabled
    db.commit()
    db.refresh(sw)
    return sw


def delete_stop_word(db: Session, word_id: str) -> bool:
    sw = db.query(CommonStopWord).filter(CommonStopWord.id == word_id).first()
    if not sw:
        return False
    db.delete(sw)
    db.commit()
    return True
