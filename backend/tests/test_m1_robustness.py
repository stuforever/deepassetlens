"""M1 健壮性测试（图谱问数融合设计 §三 / 批次总表 M1）。

覆盖：
  1. PatchToolCalls 悬空 tool_calls 恢复——会话中断后同 thread 续问不崩：
     - 历史里未应答的 tool_call（无对应 ToolMessage）被补 ToolMessage("cancelled")
     - 修补后状态幂等（再次跑 before_agent 返回 None，不重复修补）
     - 已应答的调用不触发修补
  2. 显式保守摘要装配——替代 monkey-patch 后：
     - profile excluded_middleware={"SummarizationMiddleware"} 精确丢弃框架自动阈值件
     - 子类 _TupuSummarizationMiddleware 与 SummarizationToolMiddleware 存活
     - 最终栈无重名（langchain factory 去重断言不触发）

运行方式：
    cd backend && python -m pytest tests/test_m1_robustness.py -v
"""
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, ToolMessage

from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.summarization import SummarizationMiddleware, SummarizationToolMiddleware
from deepagents import HarnessProfile
from deepagents._excluded_middleware import _apply_excluded_middleware


class _TupuSummarizationMiddleware(SummarizationMiddleware):
    """与 app/services/tupu_deepagent.py 内的显式摘要子类同构（名不同则存活）。"""


class TestPatchToolCalls:
    def _dangling_state(self):
        """构造中断态：AIMessage 携带 tool_call 但无对应 ToolMessage。"""
        return {
            "messages": [
                HumanMessage("统计用电客户总数"),
                AIMessage(
                    "",
                    tool_calls=[
                        {"name": "execute_sql", "args": {"sql": "SELECT COUNT(*) FROM dim_cst_elec_cons_cust"},
                         "id": "call_1", "type": "tool_call"}
                    ],
                ),
            ]
        }

    def test_悬空调用被补ToolMessage(self):
        """中断态 -> before_agent 返回修补，悬空 id 获得 ToolMessage('cancelled')。"""
        mw = PatchToolCallsMiddleware()
        result = mw.before_agent(self._dangling_state(), runtime=None)
        assert result is not None
        msgs = result["messages"]
        # 全量重建（RemoveMessage 在前）
        assert any(isinstance(m, RemoveMessage) for m in msgs)
        patched = [m for m in msgs if isinstance(m, ToolMessage)]
        assert patched, "悬空 tool_call 应被补 ToolMessage"
        assert any(m.tool_call_id == "call_1" for m in patched)

    def test_修补后幂等复跑不重复(self):
        """修补后的状态再跑 before_agent 应返回 None（无再悬空），续问不崩。"""
        mw = PatchToolCallsMiddleware()
        first = mw.before_agent(self._dangling_state(), runtime=None)
        assert first is not None
        # 模拟消息 reducer 应用修补结果后的状态
        patched_msgs = [m for m in first["messages"] if not isinstance(m, RemoveMessage)]
        second = mw.before_agent({"messages": patched_msgs}, runtime=None)
        assert second is None

    def test_已应答调用不触发修补(self):
        """tool_call 已有对应 ToolMessage 时 before_agent 返回 None。"""
        mw = PatchToolCallsMiddleware()
        state = {
            "messages": [
                HumanMessage("统计用电客户总数"),
                AIMessage("", tool_calls=[{"name": "execute_sql", "args": {"sql": "SELECT 1"}, "id": "call_1", "type": "tool_call"}]),
                ToolMessage(content='{"row_count": 10}', name="execute_sql", tool_call_id="call_1"),
            ]
        }
        assert mw.before_agent(state, runtime=None) is None


class TestExplicitSummarization:
    def test_排除机制丢弃自动件保留显式件(self):
        """excluded_middleware={'SummarizationMiddleware'} 精确丢弃自动件；显式子类与工具件存活。"""
        auto = SummarizationMiddleware.__new__(SummarizationMiddleware)
        mine = _TupuSummarizationMiddleware.__new__(_TupuSummarizationMiddleware)
        tool_mw = SummarizationToolMiddleware.__new__(SummarizationToolMiddleware)
        stack = [auto, mine, tool_mw]
        profile = HarnessProfile(excluded_middleware={"SummarizationMiddleware"})
        out = _apply_excluded_middleware(stack, profile)
        names = [m.name for m in out]
        assert "SummarizationMiddleware" not in names, "框架自动件应被丢弃"
        assert "_TupuSummarizationMiddleware" in names, "显式保守件应存活"
        assert "SummarizationToolMiddleware" in names, "compact_conversation 工具件应存活"

    def test_最终栈无重名(self):
        """等价于 langchain factory 的去重断言：栈内 name 集合大小 == 栈长。"""
        auto = SummarizationMiddleware.__new__(SummarizationMiddleware)
        mine = _TupuSummarizationMiddleware.__new__(_TupuSummarizationMiddleware)
        tool_mw = SummarizationToolMiddleware.__new__(SummarizationToolMiddleware)
        stack = [mine, tool_mw]
        profile = HarnessProfile(excluded_middleware={"SummarizationMiddleware"})
        out = _apply_excluded_middleware(stack, profile)
        names = [m.name for m in out]
        assert len(set(names)) == len(names), f"存在重名中间件: {names}"
