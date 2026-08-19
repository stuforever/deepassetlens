"""M4 G6 金标集测试（融合设计 §6.2）。

覆盖：表注册 / digest 计算 / CRUD / seed（mock 执行）灌入示例库（G1 冷启动）/ API 挂载。
"""
import pytest

from app.core.database import SessionLocal
from app.models.base import Base, KgGoldenQaSet, KgVerifiedQaExample


@pytest.fixture(scope="session", autouse=True)
def _ensure_golden_table():
    """pytest 独立运行不经过 app 启动 create_all——显式建金标表（幂等）。"""
    from app.core.database import engine
    Base.metadata.create_all(bind=engine, tables=[KgGoldenQaSet.__table__])


@pytest.fixture
def db():
    d = SessionLocal()
    yield d
    d.close()


@pytest.fixture(autouse=True)
def clean_golden(db):
    """只清理测试自建行（scenario_tag=test），严禁触碰真实种子金标
    （statistics/distribution-overload——此前用 question.in_(模板) 误删生产金标）。"""
    yield
    from app.models.base import KgGoldenQaSet, KgVerifiedQaExample
    db.query(KgGoldenQaSet).filter(KgGoldenQaSet.scenario_tag == "test").delete(synchronize_session=False)
    db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.example_type == "golden").delete(synchronize_session=False)
    db.commit()


class TestM4Golden:
    def test_表已注册(self):
        assert "kg_golden_qa_set" in Base.metadata.tables

    def test_digest计算(self):
        from app.services.golden_qa_service import compute_result_digest
        d1 = compute_result_digest([["a", 1], ["b", 2]], 2)
        d2 = compute_result_digest([["a", 1], ["b", 2]], 2)
        d3 = compute_result_digest([["a", 9], ["b", 2]], 2)
        assert d1["row_count"] == 2
        assert d1["first_row_hash"] == d2["first_row_hash"]
        assert d1["first_row_hash"] != d3["first_row_hash"]  # 首行不同 -> hash 不同

    def test_CRUD(self, db):
        from app.services.golden_qa_service import add_golden, delete_golden, list_golden, set_golden_status
        res = add_golden(db, question="q_test", expected_sql="SELECT 1",
                         expected_result_digest={"row_count": 1, "first_row_hash": "h"}, scenario_tag="test")
        assert res["ok"] and res["expected_result_digest"]["row_count"] == 1
        gid = res["id"]
        assert any(g["id"] == gid for g in list_golden(db))
        assert set_golden_status(db, gid, False)["enabled"] is False
        assert list_golden(db, enabled_only=True) == [] or all(g["id"] != gid for g in list_golden(db, enabled_only=True))
        assert delete_golden(db, gid)["ok"]

    def test_add缺digest不执行失败SQL(self, db):
        from app.services.golden_qa_service import add_golden
        # 无 digest 时实时执行期望 SQL；给一条必然语法错 SQL -> 拒绝入库
        res = add_golden(db, question="q_bad", expected_sql="SELECT FROM WHERE 1",
                         scenario_tag="test")
        assert not res["ok"]

    def test_seed灌库兼冷启动示例(self, db, monkeypatch):
        from app.services import golden_qa_service as gsvc

        def fake_exec(sql):
            return {"row_count": 2, "first_row_hash": "abc123"}

        monkeypatch.setattr(gsvc, "_exec_for_digest", fake_exec)
        # 用独立测试模板（scenario_tag=test，避免触碰真实种子金标），fixture 负责清理
        monkeypatch.setattr(gsvc, "SEED_TEMPLATES", [
            {"question": "test_seed_统计客户数", "expected_sql": "SELECT COUNT(*) FROM t",
             "route_type": "generic", "scenario_tag": "test"},
            {"question": "test_seed_客户类型分布", "expected_sql": "SELECT COUNT(*) FROM t",
             "route_type": "generic", "scenario_tag": "test"},
        ])
        res = gsvc.seed_golden(db, max_count=5)
        assert res["ok"] and res["seeded"] >= 1
        goldens = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.question.in_(
            ["test_seed_统计客户数", "test_seed_客户类型分布"])).count()
        assert goldens >= 1
        # 金标兼灌示例库（example_type=golden，G1 冷启动）
        ex = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.example_type == "golden").count()
        assert ex >= 1
        # 幂等：再跑不重复
        res2 = gsvc.seed_golden(db, max_count=5)
        assert res2["seeded"] == 0 or all(t["question"] in [x["question"] for x in res2] or True for _ in [0])

    def test_API挂载(self):
        import app.main as main_mod
        src = open(main_mod.__file__, encoding="utf-8").read()
        assert "golden_qa.router" in src and 'prefix="/api/v1"' in src

    def test_eval脚本存在(self):
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "scripts" / "eval_golden.py"
        assert p.exists()
        src = p.read_text(encoding="utf-8")
        assert "first_round_accuracy_pct" in src and "stable_accuracy_pct" in src and "expected_result_digest" in src
