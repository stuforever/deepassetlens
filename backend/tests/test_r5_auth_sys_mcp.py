# -*- coding: utf-8 -*-
"""R5批⑬（清单安全）契约测试。

- auth：PB 模式 first-user 判定改查 PB（原查本地库恒 True=闸门失效）；查询失败 fail-closed
- system：/test/* 三端点 admin 门控（原非管理员可调且回显模型/异常串）
- space_mcp：redirect_uri 不再默认信任 x-forwarded-*（伪造=授权码引到攻击者域）
变异锚点：pb 判定/管理门/转发头信任任一回退 → 对应测红。
"""
import pytest
from fastapi import HTTPException

from app.services.sishu_full.services import auth as authsvc
from app.services.sishu_full.api.routers import system as sysmod
from app.services.sishu_full.api.routers import space_mcp as mcp


class _PB:
    def __init__(self, items):
        self._items = items

    def collection(self, name):
        class _C:
            def __init__(self, items):
                self._items = items
            def get_list(self, page=1, per_page=1):
                class _R:
                    pass
                r = _R()
                r.items = self._items
                return r
        return _C(self._items)


def test_pb_is_first_user(monkeypatch):
    monkeypatch.setattr("app.services.sishu_full.services.pocketbase_client.get_pb_client",
                        lambda: _PB([]))
    assert authsvc.pb_is_first_user() is True
    monkeypatch.setattr("app.services.sishu_full.services.pocketbase_client.get_pb_client",
                        lambda: _PB(["u1"]))
    assert authsvc.pb_is_first_user() is False
    def _boom():
        raise RuntimeError("pb down")
    monkeypatch.setattr("app.services.sishu_full.services.pocketbase_client.get_pb_client",
                        _boom)
    assert authsvc.pb_is_first_user() is False  # fail-closed


class _U:
    def __init__(self, admin):
        self.is_admin = admin


@pytest.mark.asyncio
async def test_system_test_endpoints_admin_gated(monkeypatch):
    monkeypatch.setattr(sysmod, "get_current_user", lambda: _U(False))
    for fn in (sysmod.test_llm_connection, sysmod.test_embeddings_connection,
               sysmod.test_search_connection):
        with pytest.raises(HTTPException) as ei:
            await fn()
        assert ei.value.status_code == 403


class _Req:
    def __init__(self, headers, scheme="https"):
        self.headers = headers
        self.url = type("U", (), {"scheme": scheme})()


def test_request_origin_no_proxy_trust(monkeypatch):
    monkeypatch.delenv("TUPU_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("TUPU_TRUST_PROXY", raising=False)
    req = _Req({"x-forwarded-host": "evil.example", "x-forwarded-proto": "http",
                "host": "real.example"})
    assert mcp._request_origin(req) == "https://real.example"


def test_request_origin_env_base_wins(monkeypatch):
    monkeypatch.setenv("TUPU_PUBLIC_BASE_URL", "https://sishu.example/")
    assert mcp._request_origin(_Req({})) == "https://sishu.example"


def test_request_origin_trust_proxy_optin(monkeypatch):
    monkeypatch.delenv("TUPU_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("TUPU_TRUST_PROXY", "1")
    req = _Req({"x-forwarded-host": "proxy.example", "x-forwarded-proto": "https"})
    assert mcp._request_origin(req) == "https://proxy.example"
