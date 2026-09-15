# -*- coding: utf-8 -*-
"""⑤批4（⑤e spec §二）：/api/tutor 页面数据端点——H5 四页数据面。
铁律（同⑤b）：全端点 user 取自登录会话，**不收 user_id 参数**（多用户体系未建前
user=会话标识，②的 {expert}/{user} 语义就位）。
practice=agent run 薄包装（surface=quiz）——走既有 chat 管线，不复制逻辑。"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tutor", tags=["tutor"])


def _uid(request: Request) -> str:
    """会话标识（⑤e §二隔离：端点不收 user_id——登录会话取）。"""
    user = get_current_user(request)
    return (user.sub if user and user.sub else "anonymous")


def _require_tutor_enabled(request: Request) -> None:
    """卡关 → 422（⑤c/①关停判据后端语义：卡关=面不可用）。"""
    from app.services import expert_config
    try:
        card = expert_config.get_card("tutor")
    except KeyError:
        raise HTTPException(status_code=422, detail="教学专家未配置")
    if not card.get("enabled", False):
        raise HTTPException(status_code=422, detail="教学专家未开放（⑤e 联调后启用）")


# ---------- 复习页 ----------

@router.get("/profile")
def get_profile(request: Request):
    """⑤补补-2：画像聚合端点（streak/due/weak/今日活跃）——u 从会话取（auth=0=anonymous）。"""
    _require_tutor_enabled(request)
    from app.services.learning.learner_profile import build_learner_profile
    p = build_learner_profile(_uid(request))
    return {"code": 200, "data": {
        "streak_days": p.streak_days, "today_reviews": p.today_reviews,
        "due_count": len(p.due_reviews), "weak_points": p.weak_points,
        "strong_points": p.strong_points, "kp_mastery": p.kp_mastery,
    }}


@router.get("/chapters")
def get_chapters(request: Request):
    """⑤补补-3：图谱章节树列表（chapter 节点+所属教材）。"""
    _require_tutor_enabled(request)
    from app.services.learning.chapter_service import chapters_list
    items = chapters_list()
    return {"code": 200, "data": {"items": items, "count": len(items)}}


@router.get("/chapter/{chapter_id}/overview")
def get_chapter_overview(chapter_id: str, request: Request):
    """⑤补补-3：D2 语义一屏聚合（章节/知识点明细+精讲/错题/掌握度）——u 从会话取，?u= 废弃。"""
    _require_tutor_enabled(request)
    from app.services.learning.chapter_service import chapter_overview
    data = chapter_overview(chapter_id, _uid(request))
    if data is None:
        raise HTTPException(status_code=404, detail=f"章节不存在: {chapter_id}")
    return {"code": 200, "data": data}


@router.get("/today-tasks")
def get_today_tasks(request: Request, limit: int = 10):
    """⑤补补-3 步骤 2：今日任务（due 到期 + weak 薄弱点选题组合——policy 语义迁移）。"""
    _require_tutor_enabled(request)
    from app.services.learning.policy import today_tasks
    items = today_tasks(_uid(request), limit=max(1, min(limit, 30)))
    return {"code": 200, "data": {"items": items, "count": len(items)}}


@router.get("/path")
def get_path(request: Request):
    """⑤补补-4：精通之路（图谱结构×PG 掌握度→模块三色——pass_threshold 0.7 语义）。"""
    _require_tutor_enabled(request)
    from app.services.learning.chapter_service import path_overview
    return {"code": 200, "data": path_overview(_uid(request))}


@router.get("/due")
def get_due(request: Request, kind: str = "", limit: int = 20):
    _require_tutor_enabled(request)
    from app.services.learning.service import due_cards
    items = due_cards(_uid(request), kind=kind or None, limit=limit)
    import time as _t
    now = _t.time()
    for it in items:                       # 逾期天数（页面直读）
        due = it.get("due") or 0
        # A6 对账修复（批0 0.1）：PG timestamptz 直出为 datetime——float(datetime) 即 500
        # （⑤期四页为空态走查，无到期卡不进循环，故未暴露）。
        due = float(due.timestamp()) if hasattr(due, "timestamp") else float(due or 0)
        it["overdue_days"] = round(max(0.0, now - due) / 86400.0, 2)
    return {"code": 200, "data": {"items": items, "count": len(items)}}


class ReviewSubmit(BaseModel):
    item_id: str
    rating: int
    kind: str = "mother_question"


@router.post("/review-submit")
def review_submit(payload: ReviewSubmit, request: Request):
    _require_tutor_enabled(request)
    from app.services.learning.service import review_card
    try:
        out = review_card(_uid(request), payload.kind, payload.item_id, payload.rating)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"code": 200, "data": out}


# ---------- 错题本 ----------

@router.get("/wrong-questions")
def wrong_questions(request: Request, status: str = "", page: int = 1, page_size: int = 20):
    _require_tutor_enabled(request)
    from app.services.learning.learning_dao import wrong_question_query
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    items = wrong_question_query(_uid(request), status=status or "",
                                 limit=page_size * page)      # 引擎面 limit 简单分页
    return {"code": 200, "data": {"items": items[(page - 1) * page_size: page * page_size],
                                  "total": len(items), "page": page, "page_size": page_size}}


# ---------- 学情页 ----------

@router.get("/mastery")
def mastery(request: Request, db: Session = Depends(get_db)):
    """掌握度+图谱关联（图谱着色数据源）——知识点列表逐个 mastery 摘要。"""
    _require_tutor_enabled(request)
    from app.services.learning.service import mastery_query
    uid = _uid(request)
    # 知识点清单=图谱节点（轻量：entity_id 前 50 个）——着色=retention 阈值映射（前端色阶）
    kps: list[str] = []
    try:
        import os
        from neo4j import GraphDatabase
        uri = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
        pwd = os.environ.get("NEO4J_PASSWORD", "")
        if pwd:
            drv = GraphDatabase.driver(uri, auth=(os.environ.get("NEO4J_USER", "neo4j"), pwd))
            with drv.session() as s:
                kps = [r["eid"] for r in s.run(
                    "MATCH (n) WHERE n.entity_id IS NOT NULL RETURN n.entity_id AS eid LIMIT 50")]
            drv.close()
    except Exception as e:
        logger.warning("图谱知识点清单退化（空着色面）: %s", e)
    items = []
    for kp in kps:
        m = mastery_query(uid, kp)
        items.append({"knowledge_point_id": kp, "mastery": m["mastery"],
                      "attempts": m["attempts"]})
    return {"code": 200, "data": {"items": items, "count": len(items)}}


# ---------- 教材课程块（⑤d 读取面） ----------

@router.get("/book-blocks/{doc_id}")
def book_blocks(doc_id: str, request: Request, db: Session = Depends(get_db)):
    _require_tutor_enabled(request)
    from app.models.knowledge_base import KnowledgeDocument
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    blocks = getattr(doc, "blocks_json", None) or []
    _types: dict = {}
    for b in blocks:
        t = str(b.get("type", "text"))
        _types[t] = _types.get(t, 0) + 1
    return {"code": 200, "data": {"doc_id": doc.id, "filename": doc.filename,
                                  "blocks": blocks,
                                  "summary": {"count": len(blocks), "types": _types}}}


# ---------- 练习页（agent run 薄包装） ----------

class PracticeBody(BaseModel):
    user_input: str
    thread_id: Optional[str] = None


@router.post("/practice")
def practice(payload: PracticeBody, request: Request):
    """练习判分走 agent run（surface=quiz）——薄包装转发既有 chat 管线
    （expert_id=tutor 参数化版本），不复制管线逻辑（⑤e §二）。"""
    from app.api.data_intelligence import ChatRequest
    from app.api.freeplan.endpoint import chat_freeplan_stream
    _require_tutor_enabled(request)
    body = ChatRequest(
        thread_id=payload.thread_id or __import__("uuid").uuid4().hex,
        user_input=payload.user_input,
        expert_id="tutor",
        surface="quiz",                     # ⑤b：L1 记 quiz surface（练习轨迹）
    )
    return chat_freeplan_stream(body, request)
