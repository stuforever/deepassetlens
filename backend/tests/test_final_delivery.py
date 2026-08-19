"""统一最终交付协议单元测试（最终结果交付任务书 §7）。

覆盖 A-E 确定性降级策略与禁止行为：
  1. 有结构化结果时，采用结构化结果（row_count 用工具真实结果校正）
  2. 有最终文本、无结构化结果时，保留文本并标记兼容降级
  3. 无最终文本、有 101 行结果时，不调用模型，仍生成可交付结果
  4. 空结果输出"未查询到符合当前条件的数据"
  5. 错误结果输出安全错误提示（不泄露原始堆栈全文）
  6. 前三行均"正常"时，不允许生成"所有记录均正常"（禁止 rows[:3] 推断全量结论）
  7. is_preview=true 且 result_available_for_ui=true 时，不得产生分页重查/子代理建议

运行方式：
    cd backend && python -m pytest tests/test_final_delivery.py -v
"""
from app.api.data_intelligence import _build_final_delivery


def _sql_result(row_count=101, ncols=3, rows=None, error=None):
    cols = [f"col{i}" for i in range(ncols)]
    if rows is None:
        rows = [[f"v{r}_{c}" for c in range(ncols)] for r in range(row_count)]
    data = {"columns": cols, "rows": rows, "row_count": row_count, "sql": "SELECT 1"}
    if error:
        data["error"] = error
    return data


class TestFinalDelivery:
    def test_有结构化结果时采用结构化(self):
        """A: structured_response 存在 -> 直接采用，row_count 覆盖为工具真实结果。"""
        structured = {
            "answer_type": "overload_analysis",
            "title": "上网负载过载分析",
            "summary": ["8月1日上网负载过载 2 台。"],
            "findings": [{"label": "过载台区", "value": "2台", "level": "error"}],
            "warnings": [],
            "recommendations": ["查看过载台区明细"],
            "row_count": 999,  # 模型编造值，应被工具真实结果覆盖
            "result_available_for_ui": False,
        }
        result = _build_final_delivery(
            user_input="8月1日上网负载过载情况",
            final_answer="",
            structured=structured,
            sql_result=_sql_result(row_count=2),
        )
        assert result["degraded"] is False
        d = result["final_delivery"]
        assert d["answer_type"] == "overload_analysis"
        assert d["findings"][0]["value"] == "2台"
        assert d["title"] == "上网负载过载分析"
        # row_count 必须来自工具真实结果，覆盖模型编造值
        assert d["row_count"] == 2
        assert d["result_available_for_ui"] is True

    def test_结构化结果为Pydantic实例时同样采用(self):
        """A: structured 为 FinalDelivery Pydantic 实例时也走结构化分支。"""
        from app.services.tupu_deepagent import FinalDelivery
        fd = FinalDelivery(
            answer_type="data_list",
            title="查询结果",
            summary=["结构化摘要"],
            row_count=5,
        )
        result = _build_final_delivery(
            user_input="测试问题",
            final_answer="",
            structured=fd,
            sql_result=_sql_result(row_count=5),
        )
        assert result["degraded"] is False
        assert result["final_delivery"]["summary"] == ["结构化摘要"]
        assert result["final_delivery"]["row_count"] == 5

    def test_有最终文本无结构化保留文本并标记降级(self):
        """B: 有最终文本、无结构化 -> 保留文本，标记 response_format_degraded。"""
        result = _build_final_delivery(
            user_input="查客户联系电话",
            final_answer="客户001 的联系电话是 13800138000。",
            structured=None,
            sql_result=_sql_result(row_count=3),
        )
        assert result["degraded"] is True
        assert result["final_answer"] == "客户001 的联系电话是 13800138000。"
        d = result["final_delivery"]
        assert d["row_count"] == 3
        assert d["result_available_for_ui"] is True

    def test_无最终文本有101行结果不调用模型仍可交付(self):
        """C: 无最终文本 + 101 行真实结果 -> 纯 Python 确定性交付（不调用模型）。"""
        result = _build_final_delivery(
            user_input="所有用电户与配变户变关系",
            final_answer="",
            structured=None,
            sql_result=_sql_result(row_count=101),
        )
        assert result["degraded"] is True
        assert "共返回 101 条" in result["final_answer"]
        # 确定性兜底文案明确指向前端查询结果表，不诱导双表
        assert "完整明细见下方查询结果表" in result["final_answer"]
        d = result["final_delivery"]
        assert d["row_count"] == 101
        assert d["result_available_for_ui"] is True
        assert any("101" in s for s in d["summary"])
        assert any("完整明细见下方查询结果表" in s for s in d["summary"])
        # 确定性交付不含 L2/主表/SQL/执行过程等内部过程内容
        assert "L2" not in result["final_answer"]
        assert "SELECT" not in result["final_answer"]
        # 不出现"以下为明细/预览样例"等可能诱导双表的措辞
        assert "预览样例" not in result["final_answer"]
        assert "以下为明细" not in result["final_answer"]

    def test_空结果输出未查询到(self):
        """D: 工具返回空数据 -> 输出"未查询到符合当前条件的数据"。"""
        result = _build_final_delivery(
            user_input="查某台区负载",
            final_answer="",
            structured=None,
            sql_result=_sql_result(row_count=0, rows=[]),
        )
        assert "未查询到符合当前条件的数据" in result["final_answer"]
        assert result["final_delivery"]["answer_type"] == "empty"
        assert result["final_delivery"]["result_available_for_ui"] is False

    def test_错误结果输出安全错误提示(self):
        """E: 执行错误 -> 安全错误摘要，不泄露原始堆栈全文。"""
        result = _build_final_delivery(
            user_input="查负载",
            final_answer="",
            structured=None,
            sql_result=None,
            sql_error="SQL执行异常: Table 'tupu.xxx' doesn't exist\n  详细堆栈traceback行",
        )
        assert "查询未完成" in result["final_answer"]
        assert result["final_delivery"]["answer_type"] == "error"
        # 安全错误摘要只取首行压缩，不含堆栈全文
        assert "详细堆栈traceback行" not in result["final_delivery"]["summary"][0]
        assert "查询未完成" in result["final_delivery"]["summary"][0]

    def test_前三行均正常不允许生成所有记录均正常(self):
        """禁止根据 rows[:3] 推断全量业务结论。"""
        rows = [["正常", "正常", "正常"]] * 101
        result = _build_final_delivery(
            user_input="所有客户运行状态",
            final_answer="",
            structured=None,
            sql_result=_sql_result(row_count=101, rows=rows),
        )
        assert "所有记录均正常" not in result["final_answer"]
        assert "所有客户都正常" not in result["final_answer"]
        # 确定性交付只报数量与字段，不检查行内容、不做全量业务推断
        assert "正常" not in result["final_answer"]

    def test_预览契约下不产生分页重查或子代理建议(self):
        """is_preview=true 且 result_available_for_ui=true 时，不得产生分页/子代理建议。"""
        result = _build_final_delivery(
            user_input="所有用电户与配变户变关系",
            final_answer="",
            structured=None,
            sql_result=_sql_result(row_count=101),
        )
        # 不出现"分页重查/分段查询/task 子代理"建议
        assert "分页重查" not in result["final_answer"]
        assert "分段查询" not in result["final_answer"]
        assert "子代理" not in result["final_answer"]
        assert "task" not in result["final_answer"].lower()
        # 推荐问题也不建议分页/子代理
        for r in result["final_delivery"]["recommendations"]:
            assert "分页" not in r
            assert "task" not in r.lower()
