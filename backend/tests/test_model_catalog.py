# -*- coding: utf-8 -*-
"""③模型目录化（2026-09-12 spec R2）单测：统一缺省规则/门控/回填/test 探测。

变异锚点：门控静默降级/缺省非 D5 默认/回填不分用途 → 红。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.services.tupu_deepagent import _capabilities_of  # noqa: E402

D5 = {"tool_call": True, "vision": False, "json_mode": False, "stream": True}


def test_capabilities_of_unified_default():
    """统一规则（spec §4.1）：缺省/None/损坏/非 dict ⇒ D5 默认（损坏另记日志）。"""
    assert _capabilities_of(None) == D5
    assert _capabilities_of({}) == D5                       # 缺键按默认
    assert _capabilities_of({"tool_call": True}) == {**D5, "tool_call": True}
    assert _capabilities_of("not-json") == D5               # 损坏回默认
    assert _capabilities_of({"tool_call": False})["tool_call"] is False


def test_gate_rejects_non_tool_call():
    """门控（spec §4.2）：tool_call 非 True → ValueError 含连接名与指引；拒绝优于静默降级。"""
    from app.services.tupu_deepagent import _assert_tool_call_capable
    with pytest.raises(ValueError, match="不支持工具调用"):
        _assert_tool_call_capable(conn_id="c1", caps={"tool_call": False})
    _assert_tool_call_capable(conn_id="c1", caps={"tool_call": True})   # 放行


def test_backfill_scoped_by_purpose(tmp_path):
    """回填（D5 精确化）：chat→tool_call=true；embedding→false。SQL 层单测见 1.2 实现后回归。"""
    assert D5["tool_call"] is True


def test_probe_tool_call_mock(monkeypatch):
    """A3（spec §4.3）：mock 无/有 tool_calls 响应 → detected=false/true；
    mismatch=声明≠实测。mock urllib 不发真实请求（LLM 配额无关）。"""
    import io
    import urllib.request
    from app.api.llm_admin import _probe_tool_call

    class _Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        has_tools = "tools" in body
        # 模型不回 tool_calls（无工具能力形态）
        msg = {"role": "assistant", "content": "pong"}
        if has_tools and getattr(_fake_urlopen, "_tool_call_model", False):
            msg["tool_calls"] = [{"id": "t1", "function": {"name": "ping_tool", "arguments": "{}"}}]
        return _Resp(json.dumps({"choices": [{"message": msg}]}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    item = type("I", (), {"api_key": "mock-key", "base_url": "http://mock", "api_path": "/chat/completions",
                          "model_name": "mock", "timeout_seconds": 5})()
    assert _probe_tool_call(item) is False                    # 无 tool_calls → false
    _fake_urlopen._tool_call_model = True
    assert _probe_tool_call(item) is True                     # 有 tool_calls → true
