# -*- coding: utf-8 -*-
"""feedback.py - 用户反馈闭环 API（融合设计 §6.1 G5）

POST /api/v1/data-intelligence/feedback {run_id, message_id, verdict: up|down, corrected_sql?, comment?}
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.database import SessionLocal
from app.services import feedback_service

router = APIRouter(tags=["feedback"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class FeedbackIn(BaseModel):
    run_id: str
    message_id: Optional[str] = None
    verdict: str  # up | down
    corrected_sql: Optional[str] = None
    comment: Optional[str] = None


@router.post("/data-intelligence/feedback")
def submit_feedback(body: FeedbackIn, db=Depends(_db)):
    res = feedback_service.process_feedback(
        db, run_id=body.run_id, message_id=body.message_id, verdict=body.verdict,
        corrected_sql=body.corrected_sql, comment=body.comment)
    return res
