# -*- coding: utf-8 -*-
"""R5批⑬（清单安全）契约测试。

- system：/test/* 三端点 admin 门控（原非管理员可调且回显模型/异常串）
- space_mcp：redirect_uri 不再默认信任 x-forwarded-*（伪造=授权码引到攻击者域）
变异锚点：管理门/转发头信任任一回退 → 对应测红。
（T6批3：原 auth PB first-user 判定用例随 vendor auth 面退役——PB 分支已物理删除。）
"""
import pytest
from fastapi import HTTPException

from app.services.sishu_full.api.routers import system as sysmod
from app.services.sishu_full.api.routers import space_mcp as mcp


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


def test_book_mount_admin_gated():
    """R5批⑭：book 域挂载 _admin（原 _auth——仅凭 book_id 可读/改/删任意书籍）。"""
    import inspect
    from app.services.sishu_full.api import main as mainmod
    src = inspect.getsource(mainmod)
    assert 'book.router, prefix="/api/v1/book", tags=["book"], dependencies=_admin' in src
