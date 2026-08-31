# -*- coding: utf-8 -*-
"""test_batch10_skeleton.py - 批10：B'-1 clean_aggregate 豁免判定 + 骨架卡接线检查"""
import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.services.tupu_deepagent import _is_clean_aggregate_result


def _state_with_exec(sql_result: dict, tool_name: str = "execute_doris_sql"):
    """构造含一次数据工具调用的 state（AIMessage.tool_calls -> ToolMessage）"""
    return {"messages": [
        HumanMessage(content="查询项目数量"),
        AIMessage(content="", tool_calls=[{"id": "call_1", "name": tool_name, "args": {}, "type": "tool_call"}]),
        ToolMessage(content=json.dumps({"type": "text", "text": json.dumps(sql_result, ensure_ascii=False)},
                                      ensure_ascii=False), tool_call_id="call_1"),
    ]}


_CLEAN = {
    "columns": ["proj_cnt"], "rows": [[3]], "row_count": 1,
    "verification": {"row_count": 1, "null_rates": {"proj_cnt": 0.0}, "warnings": []},
}


class TestCleanAggregate:
    def test_clean_single_value_skips(self):
        """干净单值统计（verification 全绿+单行单列）-> 豁免"""
        assert _is_clean_aggregate_result(_state_with_exec(_CLEAN)) is True

    def test_verification_warning_no_skip(self):
        """引擎校验有告警（空值率>80%）-> 不豁免，回退自评"""
        r = dict(_CLEAN, verification={"row_count": 1, "null_rates": {"proj_cnt": 0.9},
                                       "warnings": ["列 proj_cnt 空值率 90%，可能选错列"]})
        assert _is_clean_aggregate_result(_state_with_exec(r)) is False

    def test_detail_list_no_skip(self):
        """明细清单（多行）-> 非单一聚合型，不豁免"""
        r = {"columns": ["cust_id", "cust_name"], "rows": [["a", "b"], ["c", "d"]], "row_count": 2,
             "verification": {"row_count": 2, "null_rates": {}, "warnings": []}}
        assert _is_clean_aggregate_result(_state_with_exec(r)) is False

    def test_error_no_skip(self):
        """执行报错 -> 不豁免"""
        r = {"error": "Unknown table"}
        assert _is_clean_aggregate_result(_state_with_exec(r)) is False

    def test_non_data_tool_no_skip(self):
        """只有非数据工具（search_entities）-> 无执行依据，不豁免"""
        state = _state_with_exec(_CLEAN, tool_name="search_entities")
        assert _is_clean_aggregate_result(state) is False

    def test_empty_state_no_skip(self):
        assert _is_clean_aggregate_result({"messages": []}) is False


class TestWiring:
    def test_confidence_treats_skip_as_high(self):
        """done 置信度口径：skipped_clean_aggregate 与 satisfied 同档（源码接线检查，批13-D 迁移至 freeplan.delivery）"""
        _base = __import__("os").path.join(
                __import__("os").path.dirname(__file__),
                "..", "app", "api")
        with open(__import__("os").path.join(_base, "freeplan", "delivery.py"), encoding="utf-8") as f:
            dsrc = f.read()
        assert "skipped_clean_aggregate" in dsrc

    def test_middleware_installed(self):
        """装配点使用 _TupuRubricMiddleware 子类"""
        import inspect
        from app.services import tupu_deepagent as td
        src = inspect.getsource(td)
        assert "_TupuRubricMiddleware(model=_rubric_model" in src
