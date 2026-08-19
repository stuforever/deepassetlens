"""M4 G5 反馈闭环测试（融合设计 §6.1）。

覆盖：👍 无修正 -> user_confirmed 直接入库；👎+修正 -> review 审核队列；👎 无修正 -> 仅记录；
无效 verdict；run_id -> MetricQueryLog 取原问题/执行 SQL 存证。
"""
import uuid

import pytest

from app.core.database import SessionLocal
from app.models.base import KgVerifiedQaExample, MetricQueryLog


@pytest.fixture
def db():
    d = SessionLocal()
    yield d
    d.close()


@pytest.fixture
def run_row(db):
    rid = f"run_{uuid.uuid4().hex[:10]}"
    row = MetricQueryLog(run_id=rid, user_query="统计用电客户总数",
                         executed_sql="SELECT COUNT(*) AS total FROM cms20_cst_cust",
                         query_status="success")
    db.add(row)
    db.commit()
    yield rid
    # 清理
    db.query(MetricQueryLog).filter(MetricQueryLog.run_id == rid).delete()
    db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.example_type == "user_confirmed").delete()
    db.commit()


class TestM5Feedback:
    def test_点赞无修正_直接入库(self, db, run_row):
        from app.services.feedback_service import process_feedback
        res = process_feedback(db, run_id=run_row, verdict="up")
        assert res["ok"] and res["route"] == "created"
        row = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == res["example_id"]).first()
        assert row is not None and row.example_type == "user_confirmed" and row.status == "enabled"
        assert row.question_raw == "统计用电客户总数"
        assert "cms20_cst_cust" in (row.sql or "")

    def test_点踩加修正_进审核(self, db, run_row):
        from app.services.feedback_service import process_feedback
        res = process_feedback(db, run_id=run_row, verdict="down",
                               corrected_sql="SELECT COUNT(*) AS total FROM cms20_cst_cust WHERE 1=1")
        assert res["ok"] and res["route"] == "review"
        row = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == res["example_id"]).first()
        assert row is not None and row.status == "review"

    def test_点踩无修正_仅记录(self, db, run_row):
        from app.services.feedback_service import process_feedback
        res = process_feedback(db, run_id=run_row, verdict="down")
        assert res["ok"] and res["route"] == "noop"

    def test_无效verdict(self, db, run_row):
        from app.services.feedback_service import process_feedback
        res = process_feedback(db, run_id=run_row, verdict="sideways")
        assert not res["ok"] and res["route"] == "noop"

    def test_API挂载(self):
        import app.main as main_mod
        src = open(main_mod.__file__, encoding="utf-8").read()
        assert "feedback.router" in src and 'prefix="/api/v1"' in src
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "app" / "api" / "feedback.py"
        src2 = p.read_text(encoding="utf-8")
        assert "data-intelligence/feedback" in src2
