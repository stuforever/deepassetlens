"""M4 G5 反馈观测测试（融合设计 §6.1；批13-C 重定义为纯观测信号）。

覆盖：👍/👎 全部落 KgFeedbackLog 观测表（无任何示例库自动写路径；SQL/question 存证）；
无效 verdict；run_id -> MetricQueryLog 取原问题/执行 SQL 存证。
候选推荐消费见 test_golden_candidates.py（list_candidate_recommendations）。
"""
import uuid

import pytest

from app.core.database import SessionLocal
from app.models.base import KgFeedbackLog, KgVerifiedQaExample, MetricQueryLog


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
    # 清理（只清本测试自建的 user_confirmed 行：sql 打点 cms20_cst_cust，不动生产示例）
    db.query(MetricQueryLog).filter(MetricQueryLog.run_id == rid).delete()
    db.query(KgVerifiedQaExample).filter(
        KgVerifiedQaExample.example_type == "user_confirmed",
        KgVerifiedQaExample.sql.like("%cms20_cst_cust%")).delete(synchronize_session=False)
    db.commit()


class TestM5Feedback:
    def test_点赞无修正_纯观测(self, db, run_row):
        """批13-C 重定义：👍 无修正 -> 纯观测落 KgFeedbackLog（不再入示例库）。"""
        from app.services.feedback_service import process_feedback
        res = process_feedback(db, run_id=run_row, verdict="up")
        assert res["ok"] and res["route"] == "observed"
        row = db.query(KgFeedbackLog).filter(KgFeedbackLog.run_id == run_row,
                                             KgFeedbackLog.verdict == "up").order_by(
            KgFeedbackLog.created_at.desc()).first()
        assert row is not None and row.question == "统计用电客户总数"
        assert "cms20_cst_cust" in (row.sql or "")
        db.query(KgFeedbackLog).filter(KgFeedbackLog.id == row.id).delete(synchronize_session=False)
        db.commit()

    def test_点踩加修正_纯观测存证(self, db, run_row):
        """批13-C 重定义：👎+修正 -> 纯观测记录（SQL 存证；候选推荐队列消费，无自动写路径）。"""
        from app.services.feedback_service import process_feedback
        _fixed = "SELECT COUNT(*) AS total FROM cms20_cst_cust WHERE 1=1"
        res = process_feedback(db, run_id=run_row, verdict="down", corrected_sql=_fixed)
        assert res["ok"] and res["route"] == "observed"
        row = db.query(KgFeedbackLog).filter(KgFeedbackLog.run_id == run_row,
                                             KgFeedbackLog.verdict == "down").order_by(
            KgFeedbackLog.created_at.desc()).first()
        assert row is not None and (row.corrected_sql or "") == _fixed
        db.query(KgFeedbackLog).filter(KgFeedbackLog.id == row.id).delete(synchronize_session=False)
        db.commit()

    def test_点踩无修正_纯观测(self, db, run_row):
        """批13-C 重定义：👎 无修正 -> 同样落观测表（存证 question/sql）。"""
        from app.services.feedback_service import process_feedback
        res = process_feedback(db, run_id=run_row, verdict="down")
        assert res["ok"] and res["route"] == "observed"
        row = db.query(KgFeedbackLog).filter(KgFeedbackLog.run_id == run_row,
                                             KgFeedbackLog.verdict == "down").order_by(
            KgFeedbackLog.created_at.desc()).first()
        assert row is not None
        db.query(KgFeedbackLog).filter(KgFeedbackLog.id == row.id).delete(synchronize_session=False)
        db.commit()

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
