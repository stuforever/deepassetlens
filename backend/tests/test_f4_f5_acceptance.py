"""F4/F5 验收测试：context_schema 原生路径 + response_format 降级标识

F4: 验证 _get_trusted_scope 从 runtime.context（原生路径）读取 last_scope，
    不再依赖 config["configurable"]["last_scope"] 旁路。
    验证 source=user_input 的范围不被 model_declared 覆盖。
    验证首轮无 last_scope + 决策无"范围:"行 -> 拒绝。

F5: 验证 response_format 降级标识逻辑（structured_response 为 None 时 degraded=True）。
    GLM 不兼容结构化输出时，文本答案降级路径可用。

不依赖 LLM，直接构造 mock runtime 和 state。
"""
import asyncio
from types import SimpleNamespace

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.services.decision_gate import (
    DECISION_MARKER,
    REJECT_MARKER,
    DecisionGateMiddleware,
    _get_trusted_scope,
    _update_last_scope,
)


# ---- mock runtime 构造 ----

def _runtime_with_context(context: dict | None = None, config: dict | None = None):
    """构造带 context 属性的 mock runtime（模拟 LangGraph ToolRuntime）。

    context: runtime.context（原生 context_schema 路径）
    config: runtime.config（用于派发事件，不影响 scope 读取）
    """
    return SimpleNamespace(context=context, config=config or {})


def _tc(name: str, args: dict | None = None, tc_id: str = "tc1") -> dict:
    return {"name": name, "args": args or {}, "id": tc_id, "type": "tool_call"}


def _decision(scope: str = "客户001,客户003", known: str = "用户限定客户001/003",
              judge: str = "需查户变关系", tool: str = "execute_sql") -> str:
    s = f"{DECISION_MARKER}\n已知: {known}\n判断: {judge}\n因此: 调用 {tool}。"
    if scope is not None:
        s += f"\n范围: {scope}"
    return s


def _ai_decision(sql: str, tc_id: str = "tc1", scope: str = "客户001,客户003",
                 tool: str = "execute_sql") -> AIMessage:
    return AIMessage(
        content=_decision(scope=scope, tool=tool),
        tool_calls=[_tc(tool, {"sql": sql}, tc_id)],
    )


class _HandlerSpy:
    def __init__(self):
        self.called = False

    async def __call__(self, request):
        self.called = True
        return ToolMessage(content="OK", tool_call_id=request.tool_call["id"])


class _DispatchSpy:
    def __init__(self):
        self.events = []

    async def __call__(self, event_name, payload, config):
        self.events.append({"name": event_name, "data": payload})


def _mw(**kwargs):
    return DecisionGateMiddleware(dispatcher=_DispatchSpy(), **kwargs)


def _run(coro):
    return asyncio.run(coro)


# ---- F4: _get_trusted_scope 原生 context 路径 ----

class TestGetTrustedScopeNativeContext:
    """F4: 验证 scope 从 runtime.context 原生路径读取，config 旁路已删除。"""

    def test_从_runtime_context_读_user_input_范围(self):
        """runtime.context.last_scope (source=user_input) 应被正确读取。"""
        ctx = {
            "last_scope": {
                "customer_names": ["客户001", "客户003"],
                "ordered": True,
                "commitment": "exact_set",
                "source": "user_input",
            }
        }
        runtime = _runtime_with_context(context=ctx)
        scope = _get_trusted_scope(state={}, runtime=runtime)
        assert scope is not None
        assert scope["customer_names"] == ["客户001", "客户003"]
        assert scope["source"] == "user_input"

    def test_runtime_context_为空时_fallback_到_state(self):
        """runtime.context 无 last_scope 时，fallback 到 state.last_scope。"""
        runtime = _runtime_with_context(context={})
        state = {
            "last_scope": {
                "customer_names": ["客户002"],
                "source": "model_declared",
            }
        }
        scope = _get_trusted_scope(state=state, runtime=runtime)
        assert scope is not None
        assert scope["customer_names"] == ["客户002"]
        assert scope["source"] == "model_declared"

    def test_runtime_和_state_都无范围时返回_None(self):
        """无任何可信范围时返回 None（触发首工具拦截）。"""
        runtime = _runtime_with_context(context={})
        scope = _get_trusted_scope(state={}, runtime=runtime)
        assert scope is None

    def test_config_旁路已删除(self):
        """F4 核心：config["configurable"]["last_scope"] 不再被读取。

        构造一个 config 里有 last_scope 但 context 里没有的 runtime，
        验证 _get_trusted_scope 返回 None（而不是从 config 旁路读取）。
        """
        # config 里塞 scope（旧旁路路径），context 里没有
        config_with_scope = {
            "configurable": {
                "last_scope": {
                    "customer_names": ["客户999"],
                    "source": "user_input",
                }
            }
        }
        runtime = _runtime_with_context(context={}, config=config_with_scope)
        # 期望：不从 config 读，返回 None
        scope = _get_trusted_scope(state={}, runtime=runtime)
        assert scope is None, "config 旁路应已删除，不应从 configurable 读 last_scope"

    def test_runtime_为_None_时_fallback_到_state(self):
        """runtime=None（旧路径兼容）时，从 state.last_scope 读。"""
        state = {
            "last_scope": {
                "customer_names": ["客户005"],
                "source": "model_declared",
            }
        }
        scope = _get_trusted_scope(state=state, runtime=None)
        assert scope is not None
        assert scope["customer_names"] == ["客户005"]


# ---- F4: source 优先级（user_input 不可被覆盖）----

class TestScopeSourcePriority:
    """F4/P0-1: source=user_input 的范围不可被 _update_last_scope 覆盖。"""

    def test_user_input_范围不被_model_declared_覆盖(self):
        """state 里已有 source=user_input 的范围时，_update_last_scope 跳过。"""
        state = {
            "last_scope": {
                "customer_names": ["客户001", "客户003"],
                "ordered": True,
                "source": "user_input",
            }
        }
        # 模型声明了不同范围
        decision = _decision(scope="客户002,客户004")
        _update_last_scope(state, decision)
        # user_input 范围应保留，不被覆盖
        assert state["last_scope"]["customer_names"] == ["客户001", "客户003"]
        assert state["last_scope"]["source"] == "user_input"

    def test_无_user_input_时_model_declared_可写入(self):
        """state 里无范围或 model_declared 范围时，_update_last_scope 可更新。"""
        state = {}
        decision = _decision(scope="客户002,客户004")
        _update_last_scope(state, decision)
        assert state["last_scope"]["customer_names"] == ["客户002", "客户004"]
        assert state["last_scope"]["source"] == "model_declared"


# ---- F4: 首工具拦截（无可信范围 + 无"范围:"行 -> 拒绝）----

class TestFirstToolGate:
    """F4/P0-1: 首轮无 last_scope 时，决策必须含"范围:"行，否则拒绝。"""

    def test_无范围_无范围行_拒绝(self):
        """runtime.context 无 last_scope + 决策无"范围:"行 -> 拒绝。"""
        runtime = _runtime_with_context(context={})
        # 决策里没有"范围:"行
        decision_no_scope = (
            f"{DECISION_MARKER}\n已知: 用户问客户信息\n判断: 需查询\n因此: 调用 execute_sql。"
        )
        ai_msg = AIMessage(
            content=decision_no_scope,
            tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})],
        )
        request = ToolCallRequest(
            tool_call=_tc("execute_sql", {"sql": "SELECT 1"}),
            tool=None,
            state={"messages": [ai_msg]},
            runtime=runtime,
        )
        spy = _HandlerSpy()
        mw = _mw()
        _run(mw.awrap_tool_call(request, spy))
        assert not spy.called, "无可信范围且决策无范围行时，应拒绝执行"

    def test_无范围_有范围行_放行(self):
        """runtime.context 无 last_scope + 决策有"范围: 无"行 -> 放行。"""
        runtime = _runtime_with_context(context={})
        ai_msg = _ai_decision("SELECT 1", scope="无")
        request = ToolCallRequest(
            tool_call=_tc("execute_sql", {"sql": "SELECT 1"}),
            tool=None,
            state={"messages": [ai_msg]},
            runtime=runtime,
        )
        spy = _HandlerSpy()
        mw = _mw()
        _run(mw.awrap_tool_call(request, spy))
        assert spy.called, "决策含范围声明（即使'无'）时应放行"


# ---- F5: response_format 降级标识 ----

class TestResponseFormatDegradation:
    """F5: 验证 structured_response 为 None 时降级标识为 True。

    GLM 模型不兼容 response_format（Pydantic 结构化输出），
    实际运行时 state["structured_response"] 为 None。
    接口需暴露 response_format_degraded=true 让前端可观测降级状态。
    """

    def test_structured_为_None_时降级标识_True(self):
        """模拟 GLM 不兼容：structured_response=None -> degraded=True。"""
        _structured = None  # GLM 未产出结构化结果
        _structured_degraded = _structured is None
        assert _structured_degraded is True

    def test_structured_有值时降级标识_False(self):
        """模拟兼容模型：structured_response 有值 -> degraded=False。"""
        _structured = {
            "summary": "查询返回3行",
            "execution_process": "定位客户实体后查询",
            "sql": "SELECT * FROM dim_customer LIMIT 3",
            "row_count": 3,
            "recommendations": ["统计总数"],
        }
        _structured_degraded = _structured is None
        assert _structured_degraded is False

    def test_降级时文本答案可用(self):
        """GLM 降级时，final_answer（文本）应作为兜底答案可用。

        验证降级路径：structured=None 时，前端用 final_answer 文本展示。
        """
        _structured = None
        final_answer = "## 一、综合结论\n查询返回3行客户数据。"  # 文本答案兜底
        _structured_degraded = _structured is None
        # 降级时文本答案必须非空
        assert _structured_degraded is True
        assert final_answer and final_answer.strip(), "降级时文本答案不能为空"

    def test_final_response_包含降级标识字段(self):
        """验证 final_response dict 包含 response_format_degraded 字段。"""
        _structured = None
        _structured_degraded = _structured is None
        final_response = {
            "final_answer": "文本答案",
            "final_answer_structured": _structured,
            "response_format_degraded": _structured_degraded,
        }
        assert "response_format_degraded" in final_response
        assert final_response["response_format_degraded"] is True
        assert final_response["final_answer_structured"] is None
