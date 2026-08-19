"""M3 自评与验证测试（融合设计 §5）。

覆盖：
  1. DA-2 QueryContract.rubric：generic 默认文案 / scenario None / to_dict 透出
  2. RubricMiddleware 装配源（max_iterations=1 + TUPU_RUBRIC_CONNECTION_ID + on_evaluation）
  3. on_evaluation 回调：contextvar 桥 -> contract._runtime.rubric_status + sink.append
  4. G4 _build_verification：列空值率 >80% 告警 / 干净结果无告警 / 错误结果空
  5. G7 SSE 接线源：rubric/query_verified 事件 + final evidence/confidence

运行方式：
    cd backend && python -m pytest tests/test_m3_verify.py -v
"""
from pathlib import Path

from app.services.query_contract import QueryContract


class TestM3RubricContract:
    def test_generic_默认rubric(self):
        c = QueryContract.generic()
        assert c.rubric is not None
        assert "数字必须来自工具返回结果" in c.rubric
        assert "统计口径" in c.rubric

    def test_scenario_rubric为None(self):
        from app.services.query_contract import QueryContract as QC
        # from_step 场景契约 rubric 保持 None（模板已保证结构，省 grader）
        c = QC(
            run_id="r", skill_id="s", skill_version="1", workflow_step="w",
            allowed_tools=["read_file"], forbidden_tools=[], route_type="scenario",
        )
        assert c.rubric is None

    def test_to_dict含rubric(self):
        c = QueryContract.generic()
        d = c.to_dict()
        assert d["rubric"] == c.rubric


class TestM3RubricAssembly:
    def test_create_tupu_agent装配RubricMiddleware(self):
        p = Path(__file__).resolve().parent.parent / "app" / "services" / "tupu_deepagent.py"
        src = p.read_text(encoding="utf-8")
        assert "RubricMiddleware(model=_rubric_model, max_iterations=1" in src
        assert "TUPU_RUBRIC_CONNECTION_ID" in src
        assert "on_evaluation=_on_rubric_evaluation" in src

    def test_stream注入rubric到调用状态(self):
        p = Path(__file__).resolve().parent.parent / "app" / "api" / "data_intelligence_stream.py"
        src = p.read_text(encoding="utf-8")
        assert 'if _contract is not None and _contract.rubric:' in src
        assert '_inv_state["rubric"] = _contract.rubric' in src
        assert "_RUBRIC_HOOK_CTX.set" in src
        assert "_RUBRIC_HOOK_CTX.reset" in src


class TestM3OnEvaluationCallback:
    def test_回调写契约与sink(self):
        from app.services import tupu_deepagent as td

        class _Sink:
            def __init__(self):
                self.items = []

            def append(self, name, payload):
                self.items.append((name, payload))

        sink = _Sink()
        contract = QueryContract.generic()
        token = td._RUBRIC_HOOK_CTX.set({"sink": sink, "contract": contract})
        try:
            td._on_rubric_evaluation({
                "result": "satisfied", "iteration": 0, "explanation": "数字来自工具返回",
                "grading_run_id": "g1",
            })
        finally:
            td._RUBRIC_HOOK_CTX.reset(token)
        assert contract._runtime["rubric_status"] == "satisfied"
        assert contract._runtime["rubric_iterations"] == 1
        assert sink.items and sink.items[0][0] == "rubric_evaluation_end"
        assert sink.items[0][1]["result"] == "satisfied"

    def test_回调无桥不炸(self):
        from app.services import tupu_deepagent as td
        assert td._RUBRIC_HOOK_CTX.get() is None
        td._on_rubric_evaluation({"result": "failed", "iteration": 0, "explanation": ""})  # 不抛


class TestM3Verification:
    def test_空值率高告警(self):
        from app.services.kg_action_handlers import _build_verification
        r = {
            "columns": ["col_a", "col_b"],
            "rows": [["x", None], ["y", ""], ["z", None]],
            "row_count": 3,
        }
        v = _build_verification(r)
        assert v["row_count"] == 3
        assert v["null_rates"]["col_b"] == 1.0
        assert any("col_b" in w and "空值率" in w for w in v["warnings"])

    def test_干净结果无告警(self):
        from app.services.kg_action_handlers import _build_verification
        r = {"columns": ["a", "b"], "rows": [["1", "2"], ["3", "4"]], "row_count": 2}
        v = _build_verification(r)
        assert v["null_rates"]["a"] == 0.0
        assert v["warnings"] == []

    def test_错误结果空(self):
        from app.services.kg_action_handlers import _build_verification
        assert _build_verification({"error": "x", "error_class": "SYNTAX"}) == {}

    def test_四出口都挂verification(self):
        p = Path(__file__).resolve().parent.parent / "app" / "services" / "kg_action_handlers.py"
        src = p.read_text(encoding="utf-8")
        assert src.count('result["verification"] = _build_verification(result)') >= 3
        assert src.count('res["verification"] = _build_verification(res)') >= 1

    def test_点分表名取末段(self):
        from app.services.kg_action_handlers import _extract_main_table
        assert _extract_main_table("SELECT COUNT(*) FROM internal.test_db.dim_cst_elec_cons_cust") == "dim_cst_elec_cons_cust"
        assert _extract_main_table("SELECT 1 FROM cms20_cst_cust WHERE a=1") == "cms20_cst_cust"


class TestM3G7SSE:
    def test_stream含rubric与query_verified事件(self):
        p = Path(__file__).resolve().parent.parent / "app" / "api" / "data_intelligence_stream.py"
        src = p.read_text(encoding="utf-8")
        assert 'yield f"event: query_verified\\n"' in src
        assert 'yield f"event: rubric\\n"' in src

    def test_final含evidence与confidence(self):
        p = Path(__file__).resolve().parent.parent / "app" / "api" / "data_intelligence_stream.py"
        src = p.read_text(encoding="utf-8")
        assert '"evidence": _evidence' in src
        assert '"confidence": _ev_confidence' in src
        # 置信度三级规则
        assert '_ev_confidence = "中"' in src
        assert '_ev_confidence = "高"' in src
        assert '_ev_confidence = "低"' in src
        assert '"rubric": _ev_rubric, "corrections": _ev_corrections' in src
