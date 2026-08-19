# -*- coding: utf-8 -*-
"""golden_qa.py - 金标评估集管理 API（融合设计 §6.2 G6）

GET    /api/v1/golden-qa        列表（?enabled_only=true）
POST   /api/v1/golden-qa        新增（缺 digest 时实时执行期望 SQL 计算）
POST   /api/v1/golden-qa/seed   种子灌入（模板 + 历史成功查询；兼灌示例库 G1 冷启动）
PATCH  /api/v1/golden-qa/{id}   启停
DELETE /api/v1/golden-qa/{id}   删除
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
    feed_example: bool = True


class GoldenStatus(BaseModel):
    enabled: bool


@router.get("/golden-qa")
def list_golden(enabled_only: bool = False, db=Depends(_db)):
    return {"ok": True, "data": {"total": len(gsvc.list_golden(db, enabled_only)),
                                 "items": gsvc.list_golden(db, enabled_only)}}


@router.post("/golden-qa")
def add_golden(body: GoldenAdd, db=Depends(_db)):
    res = gsvc.add_golden(db, question=body.question, expected_sql=body.expected_sql,
                          expected_result_digest=body.expected_result_digest,
                          route_type=body.route_type, scenario_tag=body.scenario_tag,
                          feed_example=body.feed_example)
    return res


@router.post("/golden-qa/seed")
def seed_golden(db=Depends(_db)):
    return gsvc.seed_golden(db)


@router.patch("/golden-qa/{golden_id}")
def set_status(golden_id: str, body: GoldenStatus, db=Depends(_db)):
    return gsvc.set_golden_status(db, golden_id, body.enabled)


@router.delete("/golden-qa/{golden_id}")
def delete_golden(golden_id: str, db=Depends(_db)):
    return gsvc.delete_golden(db, golden_id)
