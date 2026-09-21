# -*- coding: utf-8 -*-
"""三轨M15(批9) 9.1：curriculum 路由 PG 换芯——课本/章节/知识点读面（vendor
CurriculumStore 同形状），PG sishu_textbooks/sishu_chapters/sishu_knowledge_points 三表族。
vendor curriculum 路由仍挂（内含 LLM 建树等写面）；本件承接设置中心 curriculum 3 tab
与自主学习/教材阅读的读面。执法=SISHU_ROUTER_DEPS 统一注入（require_expert use）。
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.services.sishu_data.pg import engine

router = APIRouter()


@router.get("/textbooks")
def list_textbooks():
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT payload FROM sishu_textbooks ORDER BY created_at")).mappings().all()
    return {"items": [dict(r["payload"]) for r in rows]}


@router.get("/knowledge-points")
def list_kps():
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT payload FROM sishu_knowledge_points ORDER BY payload->>'created_at' NULLS LAST, kp_id")).mappings().all()
    return {"items": [dict(r["payload"]) for r in rows]}


@router.get("/knowledge-points/tree")
def kp_tree():
    items = list_kps()["items"]
    by_parent: dict = {}
    for kp in items:
        by_parent.setdefault(kp.get("parent_id"), []).append(kp)

    def build(pid):
        return [
            {**kp, "children": build(kp.get("id"))}
            for kp in by_parent.get(pid, [])
        ]
    return {"items": build(None)}


@router.get("/textbooks/{textbook_id}/chapters")
def list_chapters(textbook_id: str):
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT payload FROM sishu_chapters WHERE payload->>'textbook_id'=:t "
            "ORDER BY payload->>'created_at' NULLS LAST, chapter_id"), {"t": textbook_id}).mappings().all()
    return {"items": [dict(r["payload"]) for r in rows]}
