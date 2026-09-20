# -*- coding: utf-8 -*-
"""v4批4 4.1：平台 sandbox 客户端 TDD（协议：dt_baseline/v4_sandbox_wire.json 冻结线约）。
mock httpx 层——验证 payload 形状（code_b64/language）与结果映射（success/程序错/超时/连接失败）。"""
import base64
import json

import httpx
import pytest

from app.services.sandbox_client import SandboxClient, SandboxResult


def _fake_transport(responses: list[dict]):
    """伪造 httpx.AsyncClient.post——按序返回 canned JSON 响应，并记录 payload。"""
    calls: list[dict] = []

    class _Resp:
        def __init__(self, data: dict):
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            calls.append({"url": url, "payload": json})
            data = responses.pop(0)
            return _Resp(data)

    import app.services.sandbox_client as mod
    orig = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = _Client
    return calls, lambda: setattr(mod.httpx, "AsyncClient", orig)


@pytest.mark.anyio
async def test_execute_success_wraps_main_and_parses():
    calls, restore = _fake_transport([{"status": "success", "stdout": "4\n", "stderr": "", "exit_code": 0}])
    try:
        client = SandboxClient()
        r = await client.execute("print(4)")
    finally:
        restore()
    assert isinstance(r, SandboxResult)
    assert r.ok is True and r.stdout == "4\n" and r.exit_code == 0
    # payload 形状：code_b64（自动包 main）/language
    payload = calls[0]["payload"]
    assert payload["language"] == "python"
    code = base64.b64decode(payload["code_b64"]).decode("utf-8")
    assert "def main()" in code and "print(4)" in code
    assert calls[0]["url"].endswith("/run")


@pytest.mark.anyio
async def test_execute_program_error_maps_not_ok():
    calls, restore = _fake_transport([{
        "status": "program_error", "stdout": "", "stderr": "Traceback ...",
        "exit_code": 1, "detail": None}])
    try:
        r = await SandboxClient().execute("raise ValueError()")
    finally:
        restore()
    assert r.ok is False
    assert r.exit_code == 1
    assert "Traceback" in r.stderr


@pytest.mark.anyio
async def test_execute_runner_unavailable_maps_not_ok():
    """连接失败→ok=False，error 带 runner unavailable 语义（vendor 同款口径）。"""
    import app.services.sandbox_client as mod

    class _Boom:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            raise httpx.ConnectError("refused")

    orig = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = _Boom
    try:
        r = await SandboxClient().execute("print(1)")
    finally:
        mod.httpx.AsyncClient = orig
    assert r.ok is False
    assert "runner unavailable" in r.error or "refused" in r.error


@pytest.mark.anyio
async def test_execute_timeout_maps_not_ok():
    """超时→ok=False，error 带超时语义。"""
    import app.services.sandbox_client as mod

    class _Timeout:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            raise httpx.ReadTimeout("timed out")

    orig = mod.httpx.AsyncClient
    mod.httpx.AsyncClient = _Timeout
    try:
        r = await SandboxClient(timeout_s=2).execute("while True: pass")
    finally:
        mod.httpx.AsyncClient = orig
    assert r.ok is False
    assert "timeout" in r.error.lower() or "timed out" in r.error.lower()
