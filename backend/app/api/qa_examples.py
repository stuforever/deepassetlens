"""G1 验证示例库管理 API（融合设计 §4.1，管理页 /qa-examples 后端）。

- GET    /api/v1/qa-examples               列表（status/keyword 过滤 + 分页）
- POST   /api/v1/qa-examples               新增（DB 行 + Qdrant point 同步）
- PATCH  /api/v1/qa-examples/{id}/status   启停（enabled/disabled/review）
- DELETE /api/v1/qa-examples/{id}          删除（DB 行 + Qdrant point 同步）
- POST   /api/v1/qa-examples/seed          冷启动种子（example_type=golden 批量灌入，M4 金标复用）
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services import qa_example_service

router = APIRouter()


class QaExampleCreate(BaseModel):
    question_raw: str
    sql: Optional[str] = None
    entity_codes: List[str] = []
    route_type: str = "generic"
    engine: Optional[str] = None
    example_type: str = "manual"


class QaExampleSeed(BaseModel):
    items: List[QaExampleCreate]


class QaExampleStatusUpdate(BaseModel):
    status: str  # enabled | disabled | review


@router.get("/qa-examples")
def list_qa_examples(
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
):
    return {"code": 200, "data": qa_example_service.list_qa_examples(
        db, status=status, keyword=keyword, page=page, size=min(size, 100))}


@router.post("/qa-examples")
def create_qa_example(body: QaExampleCreate, db: Session = Depends(get_db)):
    r = qa_example_service.add_qa_example(
        db,
        question_raw=body.question_raw,
        sql=body.sql,
        entity_codes=body.entity_codes,
        route_type=body.route_type,
        engine=body.engine,
        example_type=body.example_type,
    )
    if not r.get("ok"):
        return {"code": 400, "message": r.get("error", "新增失败")}
    return {"code": 200, "data": r}


@router.post("/qa-examples/seed")
def seed_qa_examples(body: QaExampleSeed, db: Session = Depends(get_db)):
    """冷启动种子：批量灌入示例（example_type=golden 兼 M4 金标灌入），失败条目跳过。"""
    ok = []
    failed = []
    for item in body.items:
        r = qa_example_service.add_qa_example(
            db,
            question_raw=item.question_raw,
            sql=item.sql,
            entity_codes=item.entity_codes,
            route_type=item.route_type,
            engine=item.engine,
            example_type="golden" if item.example_type == "golden" else item.example_type,
        )
        (ok if r.get("ok") else failed).append(r.get("id") or r.get("error"))
    return {"code": 200, "data": {"ok": len(ok), "failed": len(failed), "ids": ok}}


@router.patch("/qa-examples/{example_id}/status")
def update_qa_example_status(example_id: str, body: QaExampleStatusUpdate, db: Session = Depends(get_db)):
    r = qa_example_service.set_qa_example_status(db, example_id, body.status)
    if not r.get("ok"):
        return {"code": 404, "message": r.get("error", "操作失败")}
    return {"code": 200, "data": r}


@router.get("/qa-examples/{example_id}/similar")
def similar_qa_examples(example_id: str, top: int = 5, db: Session = Depends(get_db)):
    """S4a：Drawer 内 top-N 相似问题预览（带相似度）。"""
    return {"code": 200, "data": {"items": qa_example_service.find_similar_examples(db, example_id, top=min(top, 10))}}


@router.delete("/qa-examples/{example_id}")
def delete_qa_example(example_id: str, db: Session = Depends(get_db)):
    r = qa_example_service.delete_qa_example(db, example_id)
    if not r.get("ok"):
        return {"code": 404, "message": r.get("error", "删除失败")}
    return {"code": 200, "data": r}
