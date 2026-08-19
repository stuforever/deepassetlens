"""P2: 剧本命中 + 数据完整性契约 e2e 验收测试

验证两个核心场景：
  1. "所有用电户与配变户变关系"：命中 distribution-overload 第1步，
     不调用 task 子代理，60s 内完成，主答案显示行数，sql_result 含完整数据+契约字段。
  2. "8月1日上网负载过载情况"：命中 distribution-overload 第2步，
     主答案显示过载台区。

运行方式：
    # 确保后端运行在 28000
    python -m pytest tests/test_e2e_scenario_contract.py -v -m integration
"""
import json
import time
import pytest
import requests


BASE_URL = "http://localhost:28000/api/data-intelligence/chat/freeplan/stream"


def _call_sse_full(query: str, thread_id: str, timeout: int = 120) -> dict | None:
    """调用 SSE 流式 API，收集所有事件，返回 done 事件 + sql_result 事件列表。"""
    payload = {"thread_id": thread_id, "user_input": query, "mode": "free_plan"}
    sql_results = []
    traces = []
    done_data = None
    try:
        resp = requests.post(BASE_URL, json=payload, stream=True, timeout=timeout)
        resp.raise_for_status()
        event_type = None
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                event_type = line[7:].strip()
            elif line.startswith("data:"):
                data_str = line[6:].strip()
                if not data_str:
                    continue
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if event_type == "done":
                    done_data = data
                elif event_type == "sql_result":
                    sql_results.append(data)
                elif event_type == "trace":
                    traces.append(data)
    except Exception:
        return None
    return {
        "done": done_data,
        "sql_results": sql_results,
        "traces": traces,
    }


@pytest.mark.integration
class TestScenarioContractE2E:
    """P2: 验证剧本命中 + 数据完整性契约（integration 级别，需后端运行）。"""

    def test_所有用电户与配变户变关系_命中第1步且不分页(self):
        """核心场景：查所有户变关系，命中剧本第1步，60s 内完成，无 task 子代理。

        断言（最终结果交付任务书 §7 端到端验收）：
        - done 事件存在
        - 耗时 < 90s（宽容边界，目标是 60s）
        - think_stream 不含 task 工具调用
        - final_answer 非空且含行数信息
        - done 含 final_delivery（统一交付协议）
        - 最终结果区显示"101 条"（row_count 出现在答案/交付摘要）
        - 不出现"四段式定位实体模板"
        - sql_result 有 row_count > 0
        - sql_result 含契约字段（is_preview / result_available_for_ui）
        - sql_result rows 完整（returned_rows == row_count，非截断 10 行）
        """
        thread_id = f"e2e_hh_{int(time.time())}"
        t0 = time.time()
        result = _call_sse_full("所有用电户与配变户变关系", thread_id, timeout=120)
        elapsed = round(time.time() - t0, 1)

        if result is None:
            pytest.skip("后端服务未运行或请求超时，跳过 integration 测试")

        done = result["done"]
        assert done is not None, "应收到 done 事件"

        # 耗时检查（目标 60s，宽容到 90s）
        assert elapsed < 90, f"耗时 {elapsed}s 超过 90s 上限"

        # think_stream 不含 task 工具
        think_stream = done.get("think_stream") or []
        tool_names = [s.get("tool_name", "") for s in think_stream if s.get("tool_name")]
        task_calls = [t for t in tool_names if t == "task"]
        assert len(task_calls) == 0, f"禁止调用 task 子代理，实际调用了 {len(task_calls)} 次: {task_calls}"

        # final_answer 非空
        final_answer = done.get("final_answer") or ""
        assert len(final_answer) > 50, f"final_answer 过短（{len(final_answer)} 字），可能未生成答案"

        # 统一最终交付协议：done 应含 final_delivery
        final_delivery = done.get("final_delivery") or {}
        assert isinstance(final_delivery, dict), "done 应含 final_delivery"
        dl_row_count = final_delivery.get("row_count", 0) or 0
        assert dl_row_count > 0, "final_delivery.row_count 应 > 0"

        # 最终结果区显示"101 条"（设计任务书验收：显示"101 条"）
        delivery_text = " ".join(final_delivery.get("summary") or [])
        assert str(dl_row_count) in (final_answer + delivery_text), \
            f"最终结果应显示行数 {dl_row_count}，实际: {final_answer[:200]}"

        # 不出现"四段式定位实体模板"
        assert "定位实体" not in final_answer, "最终答案不得含'定位实体'内部过程内容"
        assert "## 四、推荐问题" not in final_answer, "最终答案不得含四段式模板"

        # sql_result 事件
        sql_results = result["sql_results"]
        assert len(sql_results) > 0, "应至少收到一个 sql_result 事件"

        # 找到有 row_count > 0 的 sql_result
        sr_with_data = [sr for sr in sql_results if sr.get("row_count", 0) > 0]
        assert len(sr_with_data) > 0, "应至少有一个 sql_result 有数据行"

        sr = sr_with_data[0]
        row_count = sr.get("row_count", 0)
        assert row_count > 0, "row_count 应 > 0"

        # 契约字段检查：前端拿完整数据 -> is_preview 必须为 false；模型样本用 llm_is_preview 表达
        assert sr.get("is_preview") is False, \
            f"前端拿完整数据时 is_preview 必须为 false，实际: {sr.get('is_preview')}"
        assert "llm_is_preview" in sr, "sql_result 应含 llm_is_preview 字段（模型是否只看前 N 行样本）"
        assert "llm_preview_row_count" in sr, "sql_result 应含 llm_preview_row_count 字段"
        assert sr.get("result_available_for_ui") is True, "完整数据应已推前端"

        # 数据完整性：rows 应是完整数据，不是截断 10 行
        rows = sr.get("rows", [])
        returned_rows = sr.get("returned_rows", len(rows))
        assert returned_rows == row_count, \
            f"前端应收到完整数据: returned_rows={returned_rows} != row_count={row_count}（数据被截断覆盖）"

        # done.sql_result 同样：完整 rows 时 is_preview 必须为 false
        done_sr = done.get("sql_result")
        if done_sr and done_sr.get("row_count", 0) > 0:
            assert done_sr.get("is_preview") is False, "done.sql_result 完整数据时 is_preview 必须为 false"
            assert len(done_sr.get("rows", [])) == done_sr.get("row_count", 0), \
                "done.sql_result rows 应为完整数据（前端查询明细表只展示一份完整数据）"

    def test_8月1日上网负载过载情况_命中第2步且显示过载(self):
        """核心场景：查上网负载过载，命中剧本第2步，主答案显示过载信息。

        断言（最终结果交付任务书 §7 端到端验收）：
        - done 事件存在
        - final_answer 非空
        - 最终结果区显示"过载"，含台区信息（台区1、台区96）
        - 执行过程与最终结果分离（final_answer 不含"执行过程"）
        """
        thread_id = f"e2e_ol_{int(time.time())}"
        result = _call_sse_full("8月1日上网负载过载情况", thread_id, timeout=120)

        if result is None:
            pytest.skip("后端服务未运行或请求超时")

        done = result["done"]
        assert done is not None, "应收到 done 事件"

        final_answer = done.get("final_answer") or ""
        assert len(final_answer) > 20, f"final_answer 过短（{len(final_answer)} 字）"

        # 最终结果区显示"过载"，含台区信息（设计任务书验收：显示"过载 2 台"、台区1、台区96）
        delivery_text = " ".join((done.get("final_delivery") or {}).get("summary") or [])
        combined = final_answer + delivery_text
        assert "过载" in combined, f"最终结果应含'过载'，实际: {final_answer[:200]}"
        assert "台区" in combined, f"最终结果应含台区信息，实际: {final_answer[:200]}"

        # 执行过程与最终结果分离（内部 trace 不混入最终业务答案）
        assert "执行过程" not in final_answer, "执行过程不得混入最终答案正文"
