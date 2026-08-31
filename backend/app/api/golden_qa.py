# -*- coding: utf-8 -*-
"""golden_qa.py - 金标锚定管理 API（融合设计 §6.2 G6；批13-C 升级为运行时唯一锚定源）

GET    /api/v1/golden-qa             列表（?enabled_only=true；含 engine/hit_count/last_hit_at）
POST   /api/v1/golden-qa             新增（缺 digest 时实时执行期望 SQL 计算；同步 Qdrant tupu_golden_qa）
POST   /api/v1/golden-qa/seed        种子灌入（模板 + 历史成功查询；同步向量；不再灌示例库）
POST   /api/v1/golden-qa/reseed      重建向量集合（全量金标重新向量化 upsert；Qdrant 丢失/换库时用）
GET    /api/v1/golden-qa/candidates  候选推荐：近 N 天高频反馈且金标无覆盖问题 TopM（批13-C 管理页新页签）
PATCH  /api/v1/golden-qa/{id}        启停（同步向量 enabled 快照）
DELETE /api/v1/golden-qa/{id}        删除（同步删 Qdrant 点）
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.core.database import SessionLocal
from app.services import golden_qa_service as gsvc

router = APIRouter(tags=["golden_qa"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class GoldenAdd(BaseModel):
    question: str
    expected_sql: str
    expected_result_digest: Optional[Dict[str, Any]] = None
    route_type: str = "generic"
    scenario_tag: Optional[str] = None
    engine: Optional[str] = None


class GoldenStatus(BaseModel):
    enabled: bool


@router.get("/golden-qa")
def list_golden(enabled_only: bool = False, db=Depends(_db)):
    items = gsvc.list_golden(db, enabled_only)
    return {"ok": True, "data": {"total": len(items), "items": items}}


@router.post("/golden-qa")
def add_golden(body: GoldenAdd, db=Depends(_db)):
    return gsvc.add_golden(db, question=body.question, expected_sql=body.expected_sql,
                           expected_result_digest=body.expected_result_digest,
                           route_type=body.route_type, scenario_tag=body.scenario_tag,
                           engine=body.engine)


@router.post("/golden-qa/seed")
def seed_golden(db=Depends(_db)):
    return gsvc.seed_golden(db)


@router.post("/golden-qa/reseed")
def reseed_vectors(db=Depends(_db)):
    """批13-C：全量金标重建 tupu_golden_qa 向量（集合丢失/维度变更/换库后一键恢复）。"""
    items = gsvc.list_golden(db, enabled_only=False)
    synced = 0
    for it in items:
        gsvc._sync_golden_qdrant(it["id"], it["question"], it.get("expected_sql") or "",
                                 it.get("engine"), bool(it.get("enabled")))
        synced += 1
    return {"ok": True, "synced": synced, "collection": gsvc.GOLDEN_COLLECTION}


@router.get("/golden-qa/candidates")
def candidate_recommendations(days: int = 7, top_m: int = 10, db=Depends(_db)):
    """批13-C：候选推荐队列（👍👎 纯观测聚合，无自动写路径）。"""
    items = gsvc.list_candidate_recommendations(db, days=days, top_m=top_m)
    return {"ok": True, "data": {"total": len(items), "items": items, "days": days}}


@router.patch("/golden-qa/{golden_id}")
def set_status(golden_id: str, body: GoldenStatus, db=Depends(_db)):
    return gsvc.set_golden_status(db, golden_id, body.enabled)


@router.delete("/golden-qa/{golden_id}")
def delete_golden(golden_id: str, db=Depends(_db)):
    return gsvc.delete_golden(db, golden_id)
