# biz_work_order API (供 n8n 跨 API 编排用)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from ..core.database import SessionLocal

router = APIRouter(prefix="/api/v1/biz_work_order", tags=["biz_work_order"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/list", response_model=Dict[str, Any])
def list_work_orders(limit: int = 100):
    """返回 biz_work_order 表数据 (JSON API)"""
    db = SessionLocal()
    try:
        result = db.execute(text(
            "SELECT work_order_id, cust_id, work_order_type, apply_date, "
            "expect_finish_date, status, apply_capacity_kw, fee, handler, remark "
            "FROM biz_work_order LIMIT :limit"
        ), {"limit": limit})
        rows = []
        for row in result:
            rows.append({
                "work_order_id": row[0],
                "cust_id": row[1],
                "work_order_type": row[2],
                "apply_date": str(row[3]) if row[3] else None,
                "expect_finish_date": str(row[4]) if row[4] else None,
                "status": row[5],
                "apply_capacity_kw": row[6],
                "fee": float(row[7]) if row[7] else None,
                "handler": row[8],
                "remark": row[9],
            })
        return {"count": len(rows), "data": rows, "source": "MySQL tupu"}
    finally:
        db.close()


@router.get("/{cust_id}", response_model=Dict[str, Any])
def get_work_orders_by_cust(cust_id: str):
    """按 cust_id 查工单"""
    db = SessionLocal()
    try:
        result = db.execute(text(
            "SELECT work_order_id, cust_id, work_order_type, apply_date, "
            "expect_finish_date, status, apply_capacity_kw, fee, handler, remark "
            "FROM biz_work_order WHERE cust_id = :cust_id"
        ), {"cust_id": cust_id})
        rows = []
        for row in result:
            rows.append({
                "work_order_id": row[0],
                "cust_id": row[1],
                "work_order_type": row[2],
                "apply_date": str(row[3]) if row[3] else None,
                "expect_finish_date": str(row[4]) if row[4] else None,
                "status": row[5],
                "apply_capacity_kw": row[6],
                "fee": float(row[7]) if row[7] else None,
                "handler": row[8],
                "remark": row[9],
            })
        return {"count": len(rows), "cust_id": cust_id, "data": rows, "source": "MySQL tupu"}
    finally:
        db.close()
