"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
import hashlib
import json
import time
from typing import Any
import urllib.parse

import httpx
from loguru import logger
from pydantic import Field

from app.services.sishu_full.partners.bus.events import OutboundMessage
from app.services.sishu_full.partners.bus.queue import MessageBus
from app.services.sishu_full.partners.channels.base import BaseChannel
from app.services.sishu_full.partners.config.schema import DeliveryOverrides

WECHAT_MP_API = "https://api.weixin.qq.com"
ACCESS_TOKEN_TTL = 7200 - 300  # token valid 7200s; refresh 5 min early


class WechatMpConfig(DeliveryOverrides):
    """WeChat Official Account (公众号) channel configuration."""

    enabled: bool = False
    app_id: str = ""            # 公众号 AppID
    app_secret: str = ""        # 公众号 AppSecret
    token: str = ""             # 服务器配置中的 Token（用于回调签名验证）
    # 模板消息 ID（在公众号后台申请）
    review_template_id: str = ""      # 每日复习提醒模板
    weekly_template_id: str = ""      # 每周学情周报模板
    # 允许接收推送的 openid 列表；"*" 表示允许全部
    allow_from: list[str] = Field(default_factory=list)
    # 可选：接收消息的 webhook 路径（本地不配置也可，仅用于主动推送）
    webhook_path: str = ""
    # 模拟模式：没有真实凭据时用 mock 发送（测试用）
    mock_mode: bool = True


class WechatMpChannel(BaseChannel):
    """WeChat Official Account channel — template + customer-service push."""

    name = "wechat_mp"
    display_name = "WeChat 公众号"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return WechatMpConfig().model_dump(by_alias=True)

    def __init__(self, config: Any, bus: MessageBus):
        if isinstance(config, dict):
            config = WechatMpConfig.model_validate(config)
        super().__init__(config, bus)
        self.config: WechatMpConfig = config
        self._access_token: str = ""
        self._token_expires_at: float = 0.0
        self._client: httpx.AsyncClient | None = None
        self._running = False
        self._sent_log: list[dict] = []  # mock-mode delivery log for tests

    # ------------------------------------------------------------------
    # Access token
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Return a cached (or freshly fetched) access_token."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        if self.config.mock_mode:
            self._access_token = "mock_access_token"
            self._token_expires_at = time.time() + ACCESS_TOKEN_TTL
            return self._access_token
        assert self._client is not None
        resp = await self._client.get(
            f"{WECHAT_MP_API}/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": self.config.app_id,
                "secret": self.config.app_secret,
            },
        )
        data = resp.json()
        token = data.get("access_token", "")
        if not token:
            raise RuntimeError(f"WeChat access_token failed: {data}")
        self._access_token = token
        self._token_expires_at = time.time() + ACCESS_TOKEN_TTL
        return token

    # ------------------------------------------------------------------
    # Channel lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the channel. For MP, outbound is HTTP-push so there is no
        long-poll loop; we only prepare the HTTP client and (optionally) run
        a lightweight inbound webhook if configured."""
        self._running = True
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15, connect=10),
            follow_redirects=True,
        )
        # Probe token availability so misconfiguration surfaces early.
        try:
            await self._get_access_token()
        except Exception as e:
            if not self.config.mock_mode:
                logger.warning("wechat_mp: access token probe failed: {}", e)
        logger.info("wechat_mp channel started (mock_mode={})", self.config.mock_mode)
        if self.config.webhook_path:
            await self._start_webhook()

    async def stop(self) -> None:
        self._running = False
        if self._client:
            with suppress(Exception):
                await self._client.aclose()
            self._client = None

    async def _start_webhook(self) -> None:
        """Start a small local HTTP server receiving WeChat callback events.

        Production would use a reverse-proxied public URL; here we just bind a
        local endpoint so tests/clients can simulate inbound messages. Real
        inbound handling is implemented in ``handle_inbound_event``.
        """
        from aiohttp import web  # optional dependency

        async def handler(request):
            body = await request.text()
            # WeChat signature verification (GET) / message push (POST)
            if request.method == "GET":
                return web.Response(text=self.config.token)
            try:
                event = json.loads(body) if body else {}
                await self.handle_inbound_event(event)
            except Exception:
                logger.exception("wechat_mp webhook handler error")
            return web.Response(text="success")

        app = web.Application()
        app.router.add_post(self.config.webhook_path, handler)
        app.router.add_get(self.config.webhook_path, handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 8123)
        await site.start()
        self._webhook_site = site
        logger.info("wechat_mp webhook listening on :8123{}", self.config.webhook_path)

    # ------------------------------------------------------------------
    # Inbound
    # ------------------------------------------------------------------

    async def handle_inbound_event(self, event: dict[str, Any]) -> None:
        """Turn a WeChat XML/JSON callback event into a bus inbound message.

        ``event`` shape (JSON) or (XML-parsed dict):
          {FromUserName, MsgType: text/image, Content, MsgId, ...}
        """
        openid = str(event.get("FromUserName") or event.get("FromUserName") or "")
        if not openid or not self.is_allowed(openid):
            return
        msg_type = event.get("MsgType") or event.get("msgtype") or "text"
        content = ""
        media_paths: list[str] = []
        if msg_type == "text":
            content = str(event.get("Content") or event.get("content") or "")
        elif msg_type == "image":
            # image -> we cannot fetch without media API; pass the pic url if present
            url = event.get("PicUrl") or event.get("pic_url") or ""
            content = f"[image] {url}" if url else "[image]"
        if not content:
            return
        await self._handle_message(
            sender_id=openid,
            chat_id=openid,
            content=content,
            media=media_paths or None,
            metadata={"msg_id": event.get("MsgId") or event.get("msg_id")},
        )

    # ------------------------------------------------------------------
    # Outbound: customer-service message
    # ------------------------------------------------------------------

    async def send(self, msg: OutboundMessage) -> None:
        if self.config.mock_mode:
            self._sent_log.append(
                {
                    "kind": "custom",
                    "to_user": msg.chat_id,
                    "content": msg.content,
                    "media": list(msg.media or []),
                    "ts": time.time(),
                }
            )
            logger.info("wechat_mp [mock] custom send -> {}", msg.chat_id)
            return
        token = await self._get_access_token()
        assert self._client is not None
        # Text message
        if not msg.media:
            body = {
                "touser": msg.chat_id,
                "msgtype": "text",
                "text": {"content": msg.content},
            }
        else:
            # First media -> image message; text is appended as a follow-up text
            body = {
                "touser": msg.chat_id,
                "msgtype": "image",
                "image": {"media_id": msg.media[0]},
            }
            await self._custom_send(token, body)
            if msg.content:
                body = {
                    "touser": msg.chat_id,
                    "msgtype": "text",
                    "text": {"content": msg.content},
                }
        await self._custom_send(token, body)

    async def _custom_send(self, token: str, body: dict) -> None:
        assert self._client is not None
        resp = await self._client.post(
            f"{WECHAT_MP_API}/cgi-bin/message/custom/send",
            params={"access_token": token},
            json=body,
        )
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"WeChat custom/send failed: {data}")

    async def send_delta(
        self, chat_id: str, delta: str, metadata: dict[str, Any] | None = None
    ) -> None:
        # MP platform has no native streaming; ignore deltas.
        return

    # ------------------------------------------------------------------
    # Outbound: template message (推送)
    # ------------------------------------------------------------------

    async def send_template(
        self,
        openid: str,
        template_id: str,
        data: dict[str, dict[str, str]],
        *,
        url: str = "",
        miniprogram: dict | None = None,
    ) -> dict:
        """Send a WeChat template message. Returns the API response dict."""
        if self.config.mock_mode:
            self._sent_log.append(
                {
                    "kind": "template",
                    "template_id": template_id,
                    "to_user": openid,
                    "data": data,
                    "ts": time.time(),
                }
            )
            logger.info("wechat_mp [mock] template send -> {}", openid)
            return {"errcode": 0, "errmsg": "mock ok"}
        token = await self._get_access_token()
        body: dict[str, Any] = {
            "touser": openid,
            "template_id": template_id,
            "data": data,
        }
        if url:
            body["url"] = url
        if miniprogram:
            body["miniprogram"] = miniprogram
        assert self._client is not None
        resp = await self._client.post(
            f"{WECHAT_MP_API}/cgi-bin/message/template/send",
            params={"access_token": token},
            json=body,
        )
        result = resp.json()
        if result.get("errcode", 0) != 0:
            logger.warning("wechat_mp template/send failed: {}", result)
        return result

    # ------------------------------------------------------------------
    # Convenience: 每日复习提醒 / 每周学情周报
    # ------------------------------------------------------------------

    async def send_daily_review_reminder(
        self, openid: str, *, kp_names: list[str], due_count: int, study_href: str = ""
    ) -> dict:
        """每日复习提醒（模板消息）。"""
        data = {
            "first": {"value": "早上好！今天有复习任务等你完成 🌱"},
            "keyword1": {"value": "、".join(kp_names[:3]) if kp_names else "暂无到期"},
            "keyword2": {"value": f"{due_count} 项"},
            "keyword3": {"value": "错题巩固 · 遗忘曲线"},
            "remark": {"value": "点开开始 30 秒复习，保持掌握度。"},
        }
        return await self.send_template(
            openid,
            self.config.review_template_id or "review_reminder",
            data,
            url=study_href,
        )

    async def send_weekly_report(
        self,
        openid: str,
        *,
        subject_summary: str,
        weak_points: str,
        progress: str,
        report_href: str = "",
    ) -> dict:
        """每周学情周报（模板消息）。"""
        data = {
            "first": {"value": "本周学习周报已生成 📊"},
            "keyword1": {"value": subject_summary},
            "keyword2": {"value": weak_points},
            "keyword3": {"value": progress},
            "remark": {"value": "查看完整报告，把握下周重点。"},
        }
        return await self.send_template(
            openid,
            self.config.weekly_template_id or "weekly_report",
            data,
            url=report_href,
        )

    # ------------------------------------------------------------------
    # Signature verification helper (公开给 API 层做回调校验)
    # ------------------------------------------------------------------

    @staticmethod
    def verify_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
        """WeChat server-config signature check: sha1(sort(token, ts, nonce))."""
        if not token or not signature:
            return False
        raw = "".join(sorted([token, timestamp, nonce]))
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return digest == signature


__all__ = ["WechatMpChannel", "WechatMpConfig"]
