# -*- coding: utf-8 -*-
"""⑤补补-1（附件五 C 件）：tutor 后台 admin 端点族第一支——题库（母题 CRUD）。

- admin 门（`_require_admin`——§10.1 惯例，与 experts.py 同款）；
- kp 必填（knowledge_point_id 422——D7「母题挂真实 kp 节点」）；
- A-3 批将扩另两端点族（progress/schedule——本文件只放题库）。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..core.auth import get_current_user
from ..services.learning import learning_dao

router = APIRouter(prefix="/api/tutor-admin")


def _require_admin(request: Request) -> object:
    user = get_current_user(request)
    if user is None or not user.is_admin():
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return user


class QuestionBody(BaseModel):
    title: str
    archetype_text: str
    knowledge_point_id: str        # kp 必填（D7）

    class Config:
        extra = "forbid"


class QuestionPatchBody(BaseModel):
    title: Optional[str] = None
    archetype_text: Optional[str] = None
    knowledge_point_id: Optional[str] = None
    enabled: Optional[bool] = None
    variant_count: Optional[int] = None

    class Config:
        extra = "forbid"


@router.get("/questions")
def questions_list(request: Request, kp: str = Query(default=""), limit: int = Query(default=100, le=500)):
    _require_admin(request)
    items = learning_dao.mother_questions_list(kp=kp, limit=limit)
    return {"code": 200, "data": {"items": items, "total": len(items)}}


@router.post("/questions")
def question_create(request: Request, body: QuestionBody):
    _require_admin(request)
    if not body.knowledge_point_id.strip():
        raise HTTPException(status_code=422, detail="knowledge_point_id 必填（母题必须挂真实 kp 节点）")
    row = learning_dao.mother_question_create(
        title=body.title.strip(), archetype_text=body.archetype_text.strip(),
        knowledge_point_id=body.knowledge_point_id.strip())
    return {"code": 200, "data": row}


@router.put("/questions/{mq_id}")
def question_update(request: Request, mq_id: str, body: QuestionPatchBody):
    _require_admin(request)
    row = learning_dao.mother_question_update(mq_id, body.model_dump(exclude_none=True))
    if row is None:
        raise HTTPException(status_code=404, detail=f"母题不存在: {mq_id}")
    return {"code": 200, "data": row}


@router.delete("/questions/{mq_id}")
def question_delete(request: Request, mq_id: str):
    _require_admin(request)
    if not learning_dao.mother_question_delete(mq_id):
        raise HTTPException(status_code=404, detail=f"母题不存在: {mq_id}")
    return {"code": 200, "data": {"deleted": mq_id}}
