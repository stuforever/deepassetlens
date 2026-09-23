"""DecisionGateMiddleware 单元测试（v3.2 下一步判断）

不依赖 LLM（直接构造 ToolCallRequest + mock handler + 真 scope_checker）：
- 下一步判断解析（标记 + 已知/判断/因此，范围"无"->空）
- 非 execute_sql 无判定单拒绝 / 有判定单放行 / 无判定单拒绝 / 字段不全拒绝 / 工具名不符拒绝 / 一轮多工具拒绝
- 范围校验：声明范围+SQL在范围放行 / 越界拒绝 / 声明"无"跳过放行
- 一次补判：1次失败拒绝 / 2次失败阻断 / 补判后通过放行
- feature flag（reason_gated=False 关闸门）

用 asyncio.run 跑 async，无需 pytest-asyncio 标记/配置。
"""
import asyncio

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.services.decision_gate import (
    DECISION_MARKER,
    REJECT_MARKER,
    DecisionGateMiddleware,
    _parse_decision,
)


def _tc(name: str, args: dict | None = None, tc_id: str = "tc1") -> dict:
    return {"name": name, "args": args or {}, "id": tc_id, "type": "tool_call"}


def _request(tool_name: str, messages, tc_id: str = "tc1", args: dict | None = None,
             scope_names: list | None = None, scope_source: str = "model_declared") -> ToolCallRequest:
    """构造 ToolCallRequest。scope_names 设 state.last_scope.customer_names（可信范围来源）。
    scope_source: "user_input"（不可被模型覆盖）或 "model_declared"（可被覆盖）。"""
    state = {"messages": messages}
    if scope_names is not None:
        state["last_scope"] = {"customer_names": scope_names, "ordered": True,
                               "commitment": "exact_set", "source": scope_source}
    return ToolCallRequest(
        tool_call=_tc(tool_name, args, tc_id),
        tool=None,
        state=state,
        runtime=None,
    )


def _decision(scope: str = "客户001,客户003", known: str = "用户限定客户001/003",
              judge: str = "需查户变关系", tool: str = "execute_sql") -> str:
    s = (
        f"{DECISION_MARKER}\n已知: {known}\n判断: {judge}\n因此: 调用 {tool}。"
    )
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
    """记录中间件派发的 committed/rejected 事件（不调真实 adispatch_custom_event）。"""
    def __init__(self):
        self.events = []

    async def __call__(self, event_name, payload, config):
        self.events.append({"name": event_name, "data": payload})


def _mw(**kwargs):
    """构造 DecisionGateMiddleware，注入 spy dispatcher（单测不依赖 agent 上下文）。"""
    return DecisionGateMiddleware(dispatcher=_DispatchSpy(), **kwargs)


def _run(coro):
    return asyncio.run(coro)


# ---- 解析 ----

class TestParse:
    def test_解析四字段(self):
        d = _parse_decision(_decision())
        assert d["known"] == "用户限定客户001/003"
        assert d["judge"] == "需查户变关系"
        assert d["therefore"] == "调用 execute_sql。"
        assert d["scope"] == ["客户001", "客户003"]

    def test_范围无解析为空(self):
        d = _parse_decision(_decision(scope="无"))
        assert d["scope"] == []

    def test_范围顿号分隔(self):
        d = _parse_decision(_decision(scope="客户001、客户003"))
        assert d["scope"] == ["客户001", "客户003"]

    def test_无标记返回None(self):
        assert _parse_decision("直接查一下") is None
        assert _parse_decision("") is None


# ---- 放行 ----

class TestPassThrough:
    def test_非execute_sql工具无判定单拒绝(self):
        # v3.3: 理由闸门覆盖全工具, 非 execute_sql 无判定单也拒绝
        mw = _mw()
        spy = _HandlerSpy()
        ai = AIMessage(content="查层级树", tool_calls=[_tc("fetch_l1_l2_tree")])
        result = _run(mw.awrap_tool_call(_request("fetch_l1_l2_tree", [ai]), spy))
        assert spy.called is False
        assert REJECT_MARKER in result.content

    def test_非execute_sql工具有判定单放行(self):
        # v3.3: 非 execute_sql 有完整判定单(工具名匹配)放行, 不做范围校验
        mw = _mw()
        spy = _HandlerSpy()
        decision = f"{DECISION_MARKER}\n已知: 需查层级树\n判断: 先获取L1-L2结构\n因此: 调用 fetch_l1_l2_tree。"
        ai = AIMessage(content=decision, tool_calls=[_tc("fetch_l1_l2_tree")])
        result = _run(mw.awrap_tool_call(_request("fetch_l1_l2_tree", [ai]), spy))
        assert spy.called is True
        assert result.content == "OK"

    def test_execute_sql有判定单且SQL在范围内放行(self):
        mw = _mw()
        spy = _HandlerSpy()
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"
        ai = _ai_decision(sql)
        result = _run(mw.awrap_tool_call(_request("execute_sql", [ai], args={"sql": sql}), spy))
        assert spy.called is True

    def test_execute_sql声明无范围跳过校验放行(self):
        # 范围:无 -> 不做范围校验, 即使 SQL 无 cust_name 过滤也放行(非客户限定查询)
        mw = _mw()
        spy = _HandlerSpy()
        ai = _ai_decision("SELECT * FROM dim_taiz", scope="无")
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT * FROM dim_taiz"}), spy))
        assert spy.called is True


# ---- 拒绝 ----

class TestReject:
    def test_execute_sql无判定单拒绝(self):
        mw = _mw()
        spy = _HandlerSpy()
        ai = AIMessage(content="直接查", tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})])
        result = _run(mw.awrap_tool_call(_request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is False
        assert REJECT_MARKER in result.content
        assert "下一步判断" in result.content  # 提示补写下一步判断

    def test_execute_sql字段不全拒绝(self):
        mw = _mw()
        spy = _HandlerSpy()
        # 缺"判断"行
        content = f"{DECISION_MARKER}\n已知: 用户限定001/003\n因此: 调用 execute_sql。\n范围: 客户001,客户003"
        ai = AIMessage(content=content, tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})])
        result = _run(mw.awrap_tool_call(_request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is False
        assert REJECT_MARKER in result.content
        assert "字段不全" in result.content

    def test_execute_sql因此工具名不符拒绝(self):
        mw = _mw()
        spy = _HandlerSpy()
        # 因此写 search_entities 但实际调 execute_sql
        ai = _ai_decision("SELECT 1", tool="search_entities")
        result = _run(mw.awrap_tool_call(_request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is False
        assert REJECT_MARKER in result.content
        assert "工具名" in result.content

    def test_execute_sql一轮多工具拒绝(self):
        mw = _mw()
        spy = _HandlerSpy()
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"
        # 同一 AIMessage 含 2 个 tool_call
        ai = AIMessage(
            content=_decision(),
            tool_calls=[_tc("execute_sql", {"sql": sql}, "tc1"), _tc("search_entities", {}, "tc2")],
        )
        result = _run(mw.awrap_tool_call(_request("execute_sql", [ai], tc_id="tc1", args={"sql": sql}), spy))
        assert spy.called is False
        assert REJECT_MARKER in result.content
        assert "多个工具" in result.content

    def test_execute_sql越界拒绝第一次补判(self):
        mw = _mw()
        spy = _HandlerSpy()
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户005')"
        ai = _ai_decision(sql)  # 声明 001,003 但 SQL 查了 005
        # v3.6: 可信范围从 state.last_scope 取（不从模型"范围"行取）
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": sql}, scope_names=["客户001", "客户003"]), spy))
        assert spy.called is False
        assert REJECT_MARKER in result.content
        assert "第1次" in result.content
        assert "越界" in result.content

    def test_拒绝消息tool_call_id匹配(self):
        mw = _mw()
        spy = _HandlerSpy()
        ai = AIMessage(content="直接查", tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"}, tc_id="r-99")])
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], tc_id="r-99", args={"sql": "SELECT 1"}), spy))
        assert result.tool_call_id == "r-99"


# ---- 一次补判 + 阻断 ----

class TestRepairAndBlock:
    def test_二次校验失败阻断(self):
        """state 已有1条拒绝 ToolMessage, 当前仍越界 -> 阻断(不放行也不再普通拒绝)。"""
        mw = _mw()
        spy = _HandlerSpy()
        prior_reject = ToolMessage(
            content=f"{REJECT_MARKER}[第1次范围校验失败] 越界...", tool_call_id="tc0"
        )
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户005')"
        ai = _ai_decision(sql, tc_id="tc2")  # 补判后仍越界
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [prior_reject, ai], tc_id="tc2", args={"sql": sql},
                     scope_names=["客户001", "客户003"]), spy))
        assert spy.called is False  # 不放行
        assert "阻断" in result.content

    def test_补判后通过放行(self):
        """state 已有1条拒绝, 当前补判为范围内 SQL -> 放行(再校验通过)。"""
        mw = _mw()
        spy = _HandlerSpy()
        prior_reject = ToolMessage(
            content=f"{REJECT_MARKER}[第1次范围校验失败] 越界...", tool_call_id="tc0"
        )
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"
        ai = _ai_decision(sql, tc_id="tc2")  # 补判后改对
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [prior_reject, ai], tc_id="tc2", args={"sql": sql}), spy))
        assert spy.called is True  # 放行


# ---- feature flag ----

class TestConfig:
    def test_关闸门放行(self):
        # reason_gated=False: 完全关闸门, 无判定单也放行
        mw = _mw(reason_gated=False)
        spy = _HandlerSpy()
        ai = AIMessage(content="直接查", tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})])
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is True


# ---- 事件派发（v3.4 候选判断实时流）----

class TestDispatch:
    def test_通过时派发committed(self):
        """闸门通过时必须派发 decision_committed 事件（含完整正文）。"""
        mw = _mw()
        spy = _HandlerSpy()
        ai = _ai_decision("SELECT * FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')")
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT * FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"}), spy))
        assert spy.called is True  # handler 被调用
        # spy dispatcher 收到 committed 事件
        events = mw._dispatcher.events
        assert len(events) == 1
        assert events[0]["name"] == "decision_committed"
        assert events[0]["data"]["tool_name"] == "execute_sql"
        assert DECISION_MARKER in events[0]["data"]["content"]  # 完整判断正文

    def test_拒绝时派发rejected(self):
        """闸门拒绝时必须派发 decision_rejected 事件（含审计字段），且不调 handler。"""
        mw = _mw()
        spy = _HandlerSpy()
        # 无判定单的 AIMessage -> 拒绝
        ai = AIMessage(content="直接查", tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})])
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is False  # handler 未调用
        assert REJECT_MARKER in result.content  # 拒绝消息
        # spy dispatcher 收到 rejected 事件
        events = mw._dispatcher.events
        assert len(events) == 1
        assert events[0]["name"] == "decision_rejected"
        assert events[0]["data"]["tool_name"] == "execute_sql"
        assert events[0]["data"]["candidate_content"] == "直接查"
        assert events[0]["data"]["attempt"] == 1
        assert "reason" in events[0]["data"]

    def test_标记不在开头被拒绝(self):
        """标记不在第一个非空白位置 -> 拒绝（与前端前缀状态机统一标准）。"""
        mw = _mw()
        spy = _HandlerSpy()
        # 标记在中间，不是开头
        content = f"先说点别的\n{DECISION_MARKER}\n已知: x\n判断: y\n因此: 调用 execute_sql。"
        ai = AIMessage(content=content, tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})])
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is False  # 拒绝
        assert REJECT_MARKER in result.content


# ---- P0-1：可信范围链路修复 ----

class TestScopeGateFirstCall:
    """P0-1：首轮无 last_scope 时，数据工具必须声明范围（"范围:"行），不能裸奔执行。"""

    def test_首轮无scope且有范围行放行(self):
        """无 last_scope + 决策含"范围: 无"行 -> 放行（合法声明无客户限定）。"""
        mw = _mw()
        spy = _HandlerSpy()
        ai = _ai_decision("SELECT * FROM cms20_cst_cust", scope="无")
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT * FROM cms20_cst_cust"}), spy))
        assert spy.called is True

    def test_首轮无scope且无范围行拒绝(self):
        """无 last_scope + 决策缺"范围:"行 -> 拒绝（防首轮无范围裸奔）。"""
        mw = _mw()
        spy = _HandlerSpy()
        # 构造无范围行的决策
        content = f"{DECISION_MARKER}\n已知: 查全部\n判断: 需查\n因此: 调用 execute_sql。"
        ai = AIMessage(content=content, tool_calls=[_tc("execute_sql", {"sql": "SELECT 1"})])
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": "SELECT 1"}), spy))
        assert spy.called is False
        assert "范围" in result.content
        assert REJECT_MARKER in result.content

    def test_有scope_user_input不校验范围行存在(self):
        """有 last_scope(source=user_input) 时，即使决策无"范围:"行也放行（范围已由用户输入确定）。"""
        mw = _mw()
        spy = _HandlerSpy()
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"
        # 决策无范围行，但 state 有 user_input scope
        content = f"{DECISION_MARKER}\n已知: 用户限定001/003\n判断: 需查\n因此: 调用 execute_sql。"
        ai = AIMessage(content=content, tool_calls=[_tc("execute_sql", {"sql": sql})])
        result = _run(mw.awrap_tool_call(
            _request("execute_sql", [ai], args={"sql": sql},
                     scope_names=["客户001", "客户003"], scope_source="user_input"), spy))
        assert spy.called is True


class TestScopeSourcePriority:
    """P0-1：source=user_input 的范围不可被 _update_last_scope 覆盖。"""

    def test_user_input_scope不被模型声明覆盖(self):
        """state 已有 user_input scope + 模型声明不同范围 -> last_scope 不变。"""
        from app.services.decision_gate import _update_last_scope, _get_trusted_scope
        state = {"last_scope": {
            "customer_names": ["客户001", "客户003"], "ordered": True,
            "commitment": "exact_set", "source": "user_input",
        }}
        # 模型声明了不同范围
        _update_last_scope(state, f"{DECISION_MARKER}\n已知: 换范围\n判断: 新声明\n因此: 查询\n范围: 客户005,客户006\n")
        _after = _get_trusted_scope(state)
        assert _after["customer_names"] == ["客户001", "客户003"]  # 未被覆盖
        assert _after["source"] == "user_input"

    def test_model_declared_scope可被新声明覆盖(self):
        """state 有 model_declared scope + 模型声明新范围 -> 覆盖。"""
        from app.services.decision_gate import _update_last_scope, _get_trusted_scope
        state = {"last_scope": {
            "customer_names": ["客户001"], "ordered": True,
            "commitment": "exact_set", "source": "model_declared",
        }}
        _update_last_scope(state, f"{DECISION_MARKER}\n已知: 换范围\n判断: 新声明\n因此: 查询\n范围: 客户003,客户005\n")
        _after = _get_trusted_scope(state)
        assert _after["customer_names"] == ["客户003", "客户005"]  # 被覆盖
        assert _after["source"] == "model_declared"

    def test_user_input_scope不被范围无清空(self):
        """state 有 user_input scope + 模型写"范围: 无" -> 不清空（用户指定的不能被模型清掉）。"""
        from app.services.decision_gate import _update_last_scope, _get_trusted_scope
        state = {"last_scope": {
            "customer_names": ["客户001"], "ordered": True,
            "commitment": "exact_set", "source": "user_input",
        }}
        _update_last_scope(state, f"{DECISION_MARKER}\n已知: 换范围\n判断: 清空\n因此: 查询\n范围: 无\n")
        _after = _get_trusted_scope(state)
        assert _after is not None
        assert _after["customer_names"] == ["客户001"]


class TestScopeWordingAlignment:
    """提示词与闸门口径一致（防"仅 execute_sql"旧口径漂移复发）：

    闸门 SCOPE_GATED_TOOLS=4 取数工具首轮都要"范围:"行；提示词/拒绝模板必须同口径，
    否则 LLM 按提示词不写范围行 -> 被闸门拒绝 -> 补判重发，白费一轮（2026-08-29 黄色问题）。
    """

    def test_系统提示词口径覆盖四工具(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "app" / "services"
               / "tupu_deepagent.py").read_text(encoding="utf-8")
        assert "execute_doris_sql / execute_entity_api / execute_api_sql" in src
        assert "四个工具都要写" in src
        assert "调用 execute_sql 时，" not in src  # 旧口径已移除

    def test_拒绝模板口径覆盖四工具(self):
        from app.services.decision_gate import _reject_no_decision
        msg = _reject_no_decision(1, "execute_entity_api")
        assert "execute_doris_sql/execute_entity_api/execute_api_sql" in msg
        assert "仅 execute_sql 需写" not in msg

    def test_闸门工具集与提示词工具集一致(self):
        from app.services.decision_gate import SCOPE_GATED_TOOLS
        assert SCOPE_GATED_TOOLS == frozenset(
            {"execute_sql", "execute_doris_sql", "execute_entity_api", "execute_api_sql"})

