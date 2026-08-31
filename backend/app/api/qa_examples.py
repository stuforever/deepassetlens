# -*- coding: utf-8 -*-
"""G1 验证示例库管理 API —— 批13-C 已下线（deprecation 壳，留一迭代后整体移除）。

题库移除（最终设计 §批13-C）：示例库退出运行时（契约组装/直通判定/自评豁免已切
金标 tupu_golden_qa），👍👎 改纯观测（KgFeedbackLog + 候选推荐队列），本 API 全部
端点返回 410 Gone。金标管理走 /api/v1/golden-qa（管理页 /golden-qa）。
"""
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_GONE = {
    "code": 410,
    "message": "示例库 API 已下线（批13-C 题库移除）：运行时锚定已切换金标体系，"
               "👍👎 改为纯观测信号（聚合进候选推荐队列）。请使用 /api/v1/golden-qa 管理金标。",
    "data": None,
}


class QaExampleCreate(BaseModel):
    question_raw: str
    sql: Optional[str] = None


class QaExampleSeed(BaseModel):
    items: List[QaExampleCreate]


class QaExampleStatusUpdate(BaseModel):
    status: str  # enabled | disabled | review


@router.get("/qa-examples")
def list_qa_examples():
    return _GONE


@router.post("/qa-examples")
def add_qa_example(body: QaExampleCreate):
    return _GONE


@router.post("/qa-examples/seed")
def seed_qa_examples(body: QaExampleSeed):
    return _GONE


@router.patch("/qa-examples/{example_id}/status")
def set_qa_example_status(example_id: str, body: QaExampleStatusUpdate):
    return _GONE


@router.get("/qa-examples/{example_id}/similar")
def similar_qa_examples(example_id: str):
    return _GONE


@router.delete("/qa-examples/{example_id}")
def delete_qa_example(example_id: str):
    return _GONE
