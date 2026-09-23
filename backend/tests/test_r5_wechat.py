# -*- coding: utf-8 -*-
"""R5批⑦（清单安全）契约测试：wechat_push 凭据收敛+webhook 签名强制。

- OAuthRequest 只剩 code（appid/secret/mock 均服务端 env）
- webhook 强制 sha1 签名校验（无 token fail-closed 403；bypass env 显式放行）
变异锚点：凭据回请求体/签名校验删除 → 对应测红。
"""
import hashlib

import pytest
from fastapi import HTTPException

from app.services.sishu_full.api.routers.wechat_push import OAuthRequest, oauth_exchange, wechat_webhook


def test_oauth_request_model_no_credentials():
    assert set(OAuthRequest.model_fields) == {"code"}
    body = OAuthRequest(code="abc", secret="evil", mock_mode=False)  # 多余字段被忽略
    assert body.code == "abc"


@pytest.mark.asyncio
async def test_oauth_mock_from_env(monkeypatch):
    monkeypatch.delenv("WECHAT_MP_MOCK", raising=False)
    out = await oauth_exchange(OAuthRequest(code="abc123"))
    assert out["ok"] is True and out["openid"] == "mock_openid_abc123"


@pytest.mark.asyncio
async def test_oauth_real_mode_requires_server_secret(monkeypatch):
    monkeypatch.setenv("WECHAT_MP_MOCK", "0")
    monkeypatch.delenv("WECHAT_MP_SECRET", raising=False)
    with pytest.raises(HTTPException) as ei:
        await oauth_exchange(OAuthRequest(code="abc"))
    assert ei.value.status_code == 400


def _sig(token, ts, nonce):
    return hashlib.sha1("".join(sorted([token, ts, nonce])).encode()).hexdigest()


@pytest.mark.asyncio
async def test_webhook_fails_closed_without_token(monkeypatch):
    monkeypatch.delenv("WECHAT_MP_TOKEN", raising=False)
    monkeypatch.delenv("TUPU_WECHAT_WEBHOOK_UNVERIFIED", raising=False)
    with pytest.raises(HTTPException) as ei:
        await wechat_webhook({"FromUserName": "spoof"}, signature="x", timestamp="1", nonce="n")
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("WECHAT_MP_TOKEN", "tok")
    monkeypatch.delenv("TUPU_WECHAT_WEBHOOK_UNVERIFIED", raising=False)
    with pytest.raises(HTTPException) as ei:
        await wechat_webhook({"FromUserName": "spoof"}, signature="deadbeef", timestamp="1", nonce="n")
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_webhook_valid_signature_passes(monkeypatch):
    monkeypatch.setenv("WECHAT_MP_TOKEN", "tok")
    monkeypatch.delenv("TUPU_WECHAT_WEBHOOK_UNVERIFIED", raising=False)
    import app.services.sishu_full.services.wechat_push.chat as chatmod
    async def _fake(content, openid="", image_url="", image_bytes=None):
        return ""
    monkeypatch.setattr(chatmod, "handle_mp_message", _fake)
    out = await wechat_webhook({"FromUserName": "o1"}, signature=_sig("tok", "1", "n"),
                               timestamp="1", nonce="n")
    assert out["ok"] is True


@pytest.mark.asyncio
async def test_webhook_bypass_env(monkeypatch):
    monkeypatch.delenv("WECHAT_MP_TOKEN", raising=False)
    monkeypatch.setenv("TUPU_WECHAT_WEBHOOK_UNVERIFIED", "1")
    import app.services.sishu_full.services.wechat_push.chat as chatmod
    async def _fake(content, openid="", image_url="", image_bytes=None):
        return ""
    monkeypatch.setattr(chatmod, "handle_mp_message", _fake)
    out = await wechat_webhook({"FromUserName": "o1"})
    assert out["ok"] is True
