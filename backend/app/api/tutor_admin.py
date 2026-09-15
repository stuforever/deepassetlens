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


# ---------- A-3 步骤 1：progress 跨用户学情看板 + schedule 生效 FSRS 参数 ----------

@router.get("/progress")
def progress_board(request: Request):
    """跨用户学情看板（教师视角）→ [{user_id, cards, due_now, mastery:[{kp, retention}]}]。"""
    _require_admin(request)
    return {"code": 200, "data": {"items": learning_dao.progress_aggregate()}}


def _fsrs_overrides() -> dict:
    from ..services.learning.fsrs import active_params
    return active_params()


@router.get("/schedule")
def schedule_get(request: Request):
    """生效 FSRS 参数 = tutor 卡 params.fsrs 覆写 ∪ fsrs 默认（浅合并展示）。"""
    _require_admin(request)
    from ..services.learning.fsrs import DEFAULT_W, TARGET_RETENTION
    ov = _fsrs_overrides()
    return {"code": 200, "data": {
        "defaults": {"desired_retention": TARGET_RETENTION, "w": DEFAULT_W},
        "overrides": ov,
        "effective": {"desired_retention": ov.get("desired_retention", TARGET_RETENTION),
                      "w": ov.get("w", DEFAULT_W)},
    }}


class ScheduleBody(BaseModel):
    desired_retention: Optional[float] = None      # 0.5~0.99
    w: Optional[list[float]] = None                # 19 个 FSRS-5 权重

    class Config:
        extra = "forbid"


@router.put("/schedule")
def schedule_put(request: Request, body: ScheduleBody):
    """覆写（白名单 desired_retention/w）→ 写回 tutor 卡 params.fsrs（version+1+事件留痕）。"""
    _require_admin(request)
    from ..services.learning.fsrs import DEFAULT_W, TARGET_RETENTION
    from ..services.expert_config import get_card, update_card
    if body.desired_retention is None and body.w is None:
        raise HTTPException(status_code=422, detail="至少提供 desired_retention 或 w 之一")
    if body.desired_retention is not None and not (0.5 <= body.desired_retention <= 0.99):
        raise HTTPException(status_code=422, detail="desired_retention 须在 0.5~0.99")
    if body.w is not None and len(body.w) != len(DEFAULT_W):
        raise HTTPException(status_code=422, detail=f"w 须为 {len(DEFAULT_W)} 个 FSRS-5 权重")
    card = get_card("tutor") or {}
    params = dict(card.get("params") or {})
    fsrs = dict(params.get("fsrs") or {})
    if body.desired_retention is not None:
        fsrs["desired_retention"] = round(body.desired_retention, 4)
    if body.w is not None:
        fsrs["w"] = [round(float(x), 6) for x in body.w]
    params["fsrs"] = fsrs
    update_card("tutor", params=params, updated_by="tutor-admin")
    return {"code": 200, "data": {"effective": fsrs, "fallback": {
        "desired_retention": TARGET_RETENTION, "w": DEFAULT_W}}}
