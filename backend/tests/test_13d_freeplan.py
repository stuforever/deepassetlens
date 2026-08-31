# -*- coding: utf-8 -*-
"""批13-D 调度拆分 Step1：freeplan.sse / freeplan.delivery 纯函数测试。

覆盖：sse_frames 字节一致（行为零变化验收）；delivery 各纯函数
（final 提取 / 输出契约 / sql_result 载荷 / confirmed / evidence 置信度三级 /
recommendations / done 载荷键）。
"""
import pytest

from app.api.freeplan.sse import sse_frames, sse_line
from app.api.freeplan import delivery as D


class TestSseFrames:
    def test_字节一致(self):
        frames = list(sse_frames("final", {"answer": "统计结果"}))
        assert frames == ["event: final\n", 'data: {"answer": "统计结果"}\n\n']
        # 与拆分前内联 yield 逐字节相同：两行，event 行无 json，data 行带 \n\n
        assert frames[0].startswith("event: final\n")
        assert frames[1].startswith('data: ')
        assert frames[1].endswith("\n\n")

    def test_default_str兜底(self):
        # done 载荷含非 json 可序列化对象（如 datetime）时 default=str 兜底
        frames = list(sse_frames("done", {"x": 1}, default=str))
        assert frames[0] == "event: done\n"
        assert '"x": 1' in frames[1]

    def test_sse_line_拼接(self):
        assert sse_line("status", {"node": "DeepAgent"}) == (
            "event: status\ndata: {\"node\": \"DeepAgent\"}\n\n")


class TestDelivery:
    def test_extract_final_answer(self):
        class _Msg:
            def __init__(self, cls, content, tool_calls=None):
                self.cls, self.content, self.tool_calls = cls, content, tool_calls
            @property
            def __class__(self):
                class _C:
                    __name__ = self.cls
                return _C()
        msgs = [
            _Msg("AIMessage", "中间汇报", tool_calls=[{"name": "x"}]),
            _Msg("ToolMessage", "工具返回"),
            _Msg("AIMessage", "  最终答案  "),
        ]
        assert D.extract_final_answer_from_state(msgs) == "  最终答案  "
        assert D.extract_final_answer_from_state([]) == ""

    def test_apply_output_contract_无结果不清洗(self):
        # 无 UI 结果（sql_result 为 None / error）时不触发清洗，原样返回
        r = D.apply_output_contract("有结论", None)
        assert r["answer"] == "有结论" and not r["scrubbed"]
        r2 = D.apply_output_contract("有结论", {"error": "fail"})
        assert r2["answer"] == "有结论" and not r2["scrubbed"]

    def test_build_sql_result_payload(self):
        p = D.build_sql_result_payload(
            {"columns": ["a"], "rows": [[1], [2]], "row_count": 2,
             "verification": {"ok": True}},
            "SELECT 1",
        )
        assert p["columns"] == ["a"] and p["rows"] == [[1], [2]]
        assert p["row_count"] == 2 and p["sql"] == "SELECT 1"
        assert p["is_preview"] is False and p["result_available_for_ui"] is True
        assert p["llm_is_preview"] is False  # 2 行不超 10
        # error 结果 -> None
        assert D.build_sql_result_payload({"error": "boom"}, "SELECT 1") is None

    def test_build_confirmed(self):
        c = D.build_confirmed({"l2_name": "配变", "entity_code": "X1",
                               "attributes": ["a"], "assembled_sql": "S"})
        assert c["L2"] == "配变" and c["L2X"] == "X1" and c["assembled_sql"] == "S"

    def test_evidence_置信度三级(self):
        class _Contract:
            def __init__(self, rubric_status, corrections=0, runtime=None):
                self.skill_id = "s"
                self.route_type = "generic"
                self._runtime = dict(runtime or {})
                self._runtime.setdefault("rubric_status", rubric_status)
                self._runtime.setdefault("rubric_iterations", 1)
                self._runtime.setdefault("corrections", corrections)
        # 高：satisfied 且 verification 无 warning
        c = _Contract("satisfied")
        ev = D.build_evidence(c, {"sql_result": {"verification": {"ok": True}}, "sql_executed": True}, "答")
        assert ev["confidence"] == "高" and ev["evidence"]["rubric"]["status"] == "satisfied"
        # 中：无 rubric（scenario）
        c2 = _Contract(None)
        ev2 = D.build_evidence(c2, {"sql_result": {"verification": {}}, "sql_executed": True}, "答")
        assert ev2["confidence"] == "中"
        # 低：corrections>0
        c3 = _Contract("failed", corrections=1)
        ev3 = D.build_evidence(c3, {"sql_result": {}, "sql_executed": True}, "答")
        assert ev3["confidence"] == "低"
        # 低：零执行但答案含数字（S1 b）
        c4 = _Contract(None)
        ev4 = D.build_evidence(c4, {"sql_executed": False}, "结果是 3 个")
        assert ev4["confidence"] == "低" and ev4["evidence"]["missing_data_support"] is True

    def test_build_recommendations(self):
        # 优先 final_delivery.recommendations
        recs = D.build_recommendations({"recommendations": ["A", "B"]}, "正文")
        assert recs == ["A", "B"]
        # 无推荐 -> 默认兜底（非空）
        recs2 = D.build_recommendations(None, "")
        assert recs2 and len(recs2) >= 1

    def test_build_done_payload_键齐全(self):
        p = D.build_done_payload(
            thread_id="t1", confirmed={"L2": "x"}, think_stream=[{"task": "a"}],
            tool_results={"sql_executed": True}, route=None, contract=None,
            final_answer="答", structured=None, structured_degraded=False,
            final_delivery={}, sql_result_data=None, recs=["A"],
            evidence={"route": {}}, confidence="高", timing={"total": 1},
            output_scrubbed=False, output_check_reason="",
        )
        assert p["thread_id"] == "t1" and p["routed_skill"] == "free_plan"
        assert p["completed_tasks"] == ["a"]
        assert p["flags"]["sql_executed"] is True
        assert p["confidence"] == "高" and p["evidence"] == {"route": {}}
        assert p["timing"] == {"total": 1}
        assert p["recommendations"] == [{"label": "A", "shortcut": "A"}]
        # 键集合与拆分前 done 载荷一致
        for k in ("pending_clarification", "route", "contract", "output_contract_check",
                  "think_stream", "final_answer", "final_answer_structured",
                  "response_format_degraded", "final_delivery", "sql_result",
                  "next_step_recommendation", "message_card"):
            assert k in p


class TestPrep:
    """批13-D Step2：freeplan.prep.run_prep（prep 段提取，行为零变化）。"""

    def _mk(self, monkeypatch, route_type="generic"):
        import types
        from unittest.mock import AsyncMock, MagicMock

        # 路由：generic/scenario -> 带 contract 的 route
        class _Contract:
            skill_id = "test_skill"
            workflow_step = "step1"
            allowed_tools = []
            forbid_markdown_detail_table = False
            aggregate_intent = None
            hitl_enabled = False

            def __init__(self):
                self._runtime = {}
                self.route_type = route_type

        class _Route:
            def __init__(self, rt):
                self.route_type = rt
                self.contract = _Contract()
                self.to_dict = lambda: {"route_type": rt}

        _route = _Route(route_type)

        from app.services import skill_router as sr_mod
        monkeypatch.setattr(sr_mod, "route_user_input", lambda q, ctx: _route)

        from app.api import data_intelligence as di_mod
        monkeypatch.setattr(di_mod, "_build_contract_system_message",
                            lambda c, question="", precomputed_bundle=None: "契约消息")

        agent = MagicMock()
        agent.aget_state = AsyncMock(return_value=MagicMock(values={"messages": [], "last_scope": None}))
        agent.aupdate_state = AsyncMock(return_value=None)

        req = types.SimpleNamespace(user_input="查询项目数量", thread_id="t1", llm_connection_id="")
        return agent, req

    async def _run(self, agent, req):
        from app.api.freeplan.prep import run_prep
        timing = {}
        return await run_prep(req=req, agent=agent, memory_thread_id="u:t1", prep_timing=timing), timing

    def test_generic_契约注入(self, monkeypatch):
        import asyncio
        agent, req = self._mk(monkeypatch, "generic")
        prep, timing = asyncio.run(self._run(agent, req))
        assert prep.contract is not None and prep.route.route_type == "generic"
        assert prep.effective_question == "查询项目数量"
        assert len(prep.input_messages) == 2  # SystemMessage + HumanMessage
        assert prep.ctx.get("contract") is prep.contract
        assert "route_ms" in timing and "rewrite_ms" in timing
        # last_skill 写回：generic -> 清空
        agent.aupdate_state.assert_called_once()
        assert agent.aupdate_state.call_args[0][1] == {"last_skill": None, "last_step": None}

    def test_scenario_不改写(self, monkeypatch):
        import asyncio
        agent, req = self._mk(monkeypatch, "scenario")
        prep, timing = asyncio.run(self._run(agent, req))
        assert prep.route.route_type == "scenario"
        # scenario 路径契约注入也走双消息（含 SystemMessage）
        assert len(prep.input_messages) == 2
        # last_skill 写回：scenario -> 记录 skill/step
        assert agent.aupdate_state.call_args[0][1] == {"last_skill": "test_skill", "last_step": "step1"}

    def test_hitl_enabled_generic(self, monkeypatch):
        import asyncio
        agent, req = self._mk(monkeypatch, "generic")
        prep, _ = asyncio.run(self._run(agent, req))
        assert prep.contract.hitl_enabled is True
