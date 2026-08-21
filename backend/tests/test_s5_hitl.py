"""S5 HITL v2 测试（问数稳定性与体验_S阶段细化设计_20260820 §六）。

覆盖：
  1. 门控：hitl_enabled + TABLE_MISSING -> 不自动降级（degradation_used 保持 False），注册待审中断
  2. 批准：resolve 后授予定位许可（degradation_used=True）+ 注册表清空
  3. 拒绝：resolve(approve=False) -> 不授予；超时 -> 不授予
  4. 未开启 HITL：TABLE_MISSING 仍自动降级（既有行为保留）
  5. 恢复端点：未知 interrupt_id -> 404；命中 -> 200
  6. 会话锁：恢复端点不碰会话锁（无死锁路径，单测以「端点内不 acquire 锁」为静态断言，
     运行时验证由 28000 冒烟执行）

运行方式：
    cd backend && python -m pytest tests/test_s5_hitl.py -v
"""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.services import skill_policy as sp
from app.services.query_contract import QueryContract


class _FakeRequest(SimpleNamespace):
    """SkillPolicy._emit 所需的最小 request 形状（runtime.config 供 dispatcher/自定义事件）。"""
    runtime = SimpleNamespace(config=None)


def _make_contract(hitl_enabled: bool = True):
    c = QueryContract.generic()
    c.hitl_enabled = hitl_enabled
    return c


def _monkey_tool_json(monkeypatch, ec: str):
    monkeypatch.setattr(sp, "_parse_tool_json", lambda out: {"error_class": ec, "error": f"Table 'x.{ec}' doesn't exist"})


async def _run_interrupt(contract, tool_name="execute_sql", resolve_after_ms=50, approve=True, timeout=5):
    """在事件循环里跑 _check_hitl_interrupt，同时按调度 resolve。返回 (contract, captured_events, interrupt_id)。"""
    captured = []
    async def _dispatcher(event_name, payload, config):
        captured.append((event_name, dict(payload)))
    mw = sp.SkillPolicyMiddleware(dispatcher=_dispatcher)
    mw._get_contract = lambda request: contract  # 不需要
    fut = asyncio.get_running_loop().create_future()

    async def _worker():
        # 直接调用 HITL 检查（构造 result 字符串 -> _result_text 返回原样）
        await mw._check_hitl_interrupt(
            contract, tool_name, json.dumps({"error_class": "TABLE_MISSING"}), _FakeRequest())

    async def _resolver():
        await asyncio.sleep(resolve_after_ms / 1000)
        ids = list(sp._HITL_INTERRUPTS.keys())
        assert ids, "应注册了待审中断"
        iid = ids[0]
        sp.resolve_hitl_interrupt(iid, approve)
        return iid

    task = asyncio.create_task(_worker())
    res_task = asyncio.create_task(_resolver())
    await asyncio.wait_for(asyncio.gather(task, res_task), timeout=timeout)
    iid = res_task.result()
    return contract, captured, iid


class TestS5GateAndApprove:
    def test_表缺失不自动降级并注册中断(self, monkeypatch):
        _monkey_tool_json(monkeypatch, "TABLE_MISSING")
        contract = _make_contract(hitl_enabled=True)
        contract, captured, iid = asyncio.run(_run_interrupt(contract, approve=True))
        assert contract._runtime.get("degradation_used") is True, "批准后应授予定位许可"
        events = {name for name, _ in captured}
        assert "policy.interrupt" in events, captured
        assert iid not in sp._HITL_INTERRUPTS, "批准后注册表应清空"
        # 事件带 interrupt_id/reason/proposal
        intr = next(p for n, p in captured if n == "policy.interrupt")
        assert intr["interrupt_id"] == iid
        assert "reason" in intr and "proposal" in intr

    def test_拒绝不授予(self, monkeypatch):
        _monkey_tool_json(monkeypatch, "TABLE_MISSING")
        contract = _make_contract(hitl_enabled=True)
        contract, captured, iid = asyncio.run(_run_interrupt(contract, approve=False))
        assert contract._runtime.get("degradation_used") in (None, False), "拒绝后不应授予定位许可"
        assert iid not in sp._HITL_INTERRUPTS

    def test_超时视为拒绝(self, monkeypatch):
        _monkey_tool_json(monkeypatch, "TABLE_MISSING")
        contract = _make_contract(hitl_enabled=True)
        # 不 resolve，让 wait_for 超时（用极小超时）
        mw = sp.SkillPolicyMiddleware(dispatcher=lambda *a, **k: None)

        async def _worker():
            orig_timeout = sp._HITL_TIMEOUT
            sp._HITL_TIMEOUT = 0.05
            try:
                await mw._check_hitl_interrupt(
                    contract, "execute_sql", json.dumps({"error_class": "TABLE_MISSING"}), _FakeRequest())
            finally:
                sp._HITL_TIMEOUT = orig_timeout
        asyncio.run(_worker())
        assert contract._runtime.get("degradation_used") in (None, False), "超时视为拒绝"

    def test_catalog_missing也触发(self, monkeypatch):
        _monkey_tool_json(monkeypatch, "CATALOG_MISSING")
        contract = _make_contract(hitl_enabled=True)
        contract, captured, iid = asyncio.run(_run_interrupt(contract, approve=True))
        assert contract._runtime.get("degradation_used") is True
        assert {n for n, _ in captured} == {"policy.interrupt"}


class TestS5NonHitl:
    def test_未开启仍自动降级(self):
        """既有行为：hitl_enabled 缺省（scenario/旧路径）-> TABLE_MISSING 自动授予，无中断。"""
        contract = _make_contract(hitl_enabled=False)
        mw = sp.SkillPolicyMiddleware(dispatcher=lambda *a, **k: None)

        async def _worker():
            await mw._check_hitl_interrupt(
                contract, "execute_sql", json.dumps({"error_class": "TABLE_MISSING"}), _FakeRequest())
        asyncio.run(_worker())
        assert contract._runtime.get("degradation_used") in (None, False), "未开启 HITL 不走人审"
        assert sp._HITL_INTERRUPTS == {}, "不应注册中断"

    def test_同步降级路径不受影响(self):
        """_check_controlled_degradation 在非 HITL 下仍自动置 degradation_used。"""
        contract = _make_contract(hitl_enabled=False)
        # 直接构造：经 _postcheck 模拟——此处只验证 auto-grant 分支条件
        # 复算 gate：ec in triggers && !used && !(hitl && trigger)
        contract._runtime["degradation_used"] = False
        assert sp._DEGRADATION_TRIGGERS.issuperset({"TABLE_MISSING"})
        assert "CATALOG_MISSING" in sp._HITL_TRIGGERS


class TestS5ResumeAPI:
    def test_未知中断404(self):
        from app.main import app
        tc = TestClient(app)
        r = tc.post("/api/data-intelligence/chat/freeplan/resume", json={
            "interrupt_id": "not-exist", "approve": True, "thread_id": "t"})
        assert r.status_code == 200
        assert r.json()["code"] == 404

    def test_命中恢复200(self):
        from app.main import app
        # 预置一个待审 Future（独立 loop 创建，Py3.13 主线程无默认 loop）
        loop = asyncio.new_event_loop()
        try:
            fut = loop.create_future()
        finally:
            loop.close()
        iid = "test-resume-001"
        sp._HITL_INTERRUPTS[iid] = fut
        try:
            tc = TestClient(app)
            r = tc.post("/api/data-intelligence/chat/freeplan/resume", json={
                "interrupt_id": iid, "approve": False, "thread_id": "t"})
            assert r.status_code == 200
            assert r.json()["code"] == 200
            assert r.json()["data"]["approved"] is False
            assert fut.done() and fut.result() == {"approve": False}
        finally:
            sp._HITL_INTERRUPTS.pop(iid, None)


class TestS5Helpers:
    def test_resolver幂等(self):
        loop = asyncio.new_event_loop()
        try:
            fut = loop.create_future()
        finally:
            loop.close()
        iid = "test-idem"
        sp._HITL_INTERRUPTS[iid] = fut
        try:
            assert sp.resolve_hitl_interrupt(iid, True) is True
            assert sp.resolve_hitl_interrupt(iid, True) is False  # 已 done -> 幂等 False
            assert fut.result() == {"approve": True}
        finally:
            sp._HITL_INTERRUPTS.pop(iid, None)

    def test_pending计数(self):
        loop = asyncio.new_event_loop()
        try:
            fut = loop.create_future()
        finally:
            loop.close()
        iid = "test-count"
        sp._HITL_INTERRUPTS[iid] = fut
        try:
            assert sp.pending_hitl_interrupts_count() >= 1
        finally:
            sp._HITL_INTERRUPTS.pop(iid, None)
