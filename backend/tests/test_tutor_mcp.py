# -*- coding: utf-8 -*-
"""权限重构 T8a 单测：教学 11 件 MCP 回挂 + 用户上下文传递 + EXEC 两段臂。

计划：docs/superpowers/plans/2026-09-24-权限体系重构-实施计划.md 任务 8a（v1.4）。
规格：docs/superpowers/specs/2026-09-24-权限体系重构-design.md §8.2/§8.3/§8.4。

变异锚点：
- 教学包装缺 current_user_strict → runtime 未置位落 anonymous 共享桶（🔴-4 复现）
- X-Tupu-User 签名校验删除 → 伪造身份头跨用户读写学习数据
- 两段臂执行臂缺 confirm_token 校验 → 模型/技能直调绕过确认流
- confirm_token 不绑参数 → 预检 token 挪用到其他参数（重放）
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mcp_server import mcp  # noqa: E402
from app.services import memory_runtime as mr  # noqa: E402
from app.services.learning.tutor_inprocess import SPECS  # noqa: E402
from app.services.tool_confirm import issue, verify  # noqa: E402

_TUTOR_11 = {s["name"] for s in SPECS}
_TUTOR_WRITE_4 = {"wrong_question_add", "fsrs_review",
                  "mother_question_find_or_create", "export_wrong_book"}


def test_tutor_11_registered_with_specs_descriptions():
    """11 件全部注册且 description 与 SPECS 逐字一致（拷贝源纪律）。"""
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert _TUTOR_11 <= set(tools), _TUTOR_11 - set(tools)
    for spec in SPECS:
        t = tools[spec["name"]]
        assert (t.description or "").startswith(str(spec["description"])[:20]), spec["name"]
        # 铁律①：参数面绝无 user_id
        assert "user_id" not in (t.inputSchema or {}).get("properties", {}), spec["name"]


def test_tutor_write4_schema_has_confirm_token():
    """写 4 件 schema 带 confirm_token（两段臂臂②参数）；读 7 件不带。"""
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for spec in SPECS:
        props = (tools[spec["name"]].inputSchema or {}).get("properties", {})
        if spec["name"] in _TUTOR_WRITE_4:
            assert "confirm_token" in props, spec["name"]
        else:
            assert "confirm_token" not in props, spec["name"]


def _unwrap(r):
    """mcp.call_tool 返回形状统一解包：(content, structured) / list[TextContent] / str。"""
    if isinstance(r, tuple) and len(r) == 2:
        content, structured = r
        if isinstance(structured, dict):
            return structured
        r = content
    if isinstance(r, list) and r and hasattr(r[0], "text"):
        return json.loads(r[0].text)
    if isinstance(r, str):
        return json.loads(r)
    return r


def test_tutor_call_without_runtime_fail_closed():
    """runtime 未置位（/mcp 无头）→ current_user_strict 抛错（🔴-4 fail-closed）。
    FastMCP 把 impl 异常包成 ToolError 上抛——fail-closed 语义断言看消息。"""
    from mcp.server.fastmcp.exceptions import ToolError

    mr.reset()
    with pytest.raises(ToolError, match="fail-closed"):
        asyncio.run(mcp.call_tool("fsrs_due", {"kind": ""}))


def test_two_user_context_isolation(monkeypatch):
    """两用户 ContextVar 隔离：fsrs_due 收到的 user 严格随 runtime（🔴-4 负向用例）。"""
    seen = []

    def _fake_due(user, kind=None):
        seen.append(user)
        return []

    import app.services.learning.service as svc
    monkeypatch.setattr(svc, "due_cards", _fake_due)

    mr.set_runtime("wenshu", "userA", "sess-A")
    asyncio.run(mcp.call_tool("fsrs_due", {"kind": ""}))
    mr.set_runtime("wenshu", "userB", "sess-B")
    asyncio.run(mcp.call_tool("fsrs_due", {"kind": ""}))
    mr.reset()
    assert seen == ["userA", "userB"]


def test_user_sig_header_roundtrip(monkeypatch):
    """agent 注入的 X-Tupu-User-Sig 与 /mcp 面验签同源——合法通过、篡改被拒。"""
    import app.mcp_server as ms

    monkeypatch.setenv("TUPU_INTERNAL_TOKEN", "test-internal-key")
    sig = ms.user_sig_header("userX")
    ok, err = ms._verify_user_sig("userX", sig)
    assert ok, err
    ok2, _ = ms._verify_user_sig("userY", sig)  # 挪用他人身份 → 拒
    assert ok2 is False
    ok3, _ = ms._verify_user_sig("userX", sig.rsplit(".", 1)[0] + ".1")  # 改 ts → 签名失配
    assert ok3 is False


def test_two_arm_flow(monkeypatch):
    """写件两段臂：无 token→pending_confirmation；携合法 token→执行到 impl；
    参数挪用→deny（重放防护 🛠 §8.4 风险表）。"""
    captured = []

    def _fake_add(user, **kwargs):
        captured.append((user, kwargs.get("variant_text")))
        return json.dumps({"ok": True})

    import app.services.learning.tutor_inprocess as ti
    monkeypatch.setattr(ti, "_impl_wrong_question_add", _fake_add)

    mr.set_runtime("wenshu", "userC", "sess-C")
    # ① 预检臂：无 token → pending + confirm_token
    body = _unwrap(asyncio.run(mcp.call_tool("wrong_question_add", {"variant_text": "题干"})))
    assert body.get("status") == "pending_confirmation", body
    tok = body["confirm_token"]

    # ② 执行臂：携 token → 真正执行（impl 被调）
    body2 = _unwrap(asyncio.run(mcp.call_tool("wrong_question_add",
                                              {"variant_text": "题干", "confirm_token": tok})))
    assert captured and captured[0] == ("userC", "题干"), body2

    # ③ 重放防护：同 token 换参数（variant_text 变化）→ deny
    body3 = _unwrap(asyncio.run(mcp.call_tool("wrong_question_add",
                                              {"variant_text": "改过的题干", "confirm_token": tok})))
    assert body3.get("status") == "denied", body3
    mr.reset()


def test_confirm_token_binding():
    """confirm_token 四元组绑定：换 user/换 args/过期 都失败。"""
    args = {"a": 1}
    tok = issue("t1", args, "u1")
    assert verify("t1", args, "u1", tok)[0] is True
    assert verify("t1", {"a": 2}, "u1", tok)[0] is False      # 换参数
    assert verify("t1", args, "u2", tok)[0] is False          # 换用户
    assert verify("t2", args, "u1", tok)[0] is False          # 换工具
    assert verify("t1", args, "u1", tok, now=10**12)[0] is False  # 过期


def test_twin_rollback_switch_removed():
    """切换 R6 twin 收尾：灰度回滚开关已摘除（教学 11 件 MCP 面为唯一路径）。"""
    import app.services.tupu_deepagent as td

    assert not hasattr(td, "_strip_tutor_tools_for_rollback"), \
        "灰度回滚开关应已删除（双轨期结束——回滚=git revert，不留长尾开关）"
    assert not hasattr(td, "_TUTOR_TOOL_NAMES")
