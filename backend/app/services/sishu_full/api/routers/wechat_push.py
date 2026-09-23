"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.sishu_full.services.wechat_push import (
    build_daily_review_payload,
    build_weekly_report_payload,
    get_channel,
)
from app.services.sishu_full.services.wechat_push.scheduler import (
    get_push_scheduler,
    load_subscribers,
    set_subscribers,
)
from app.services.sishu_full.services.wechat_push.identity import (
    bind_openid,
    get_binding,
    list_bindings,
    unbind_openid,
    exchange_code_for_openid,
)

router = APIRouter()


class PushRequest(BaseModel):
    openid: str = ""
    max_items: int = 5
    url: str = ""


class SubscribeRequest(BaseModel):
    openid: str
    subscribe: bool = True


class BindRequest(BaseModel):
    openid: str
    role: str = "student"
    display_name: str = ""
    student_openid: str = ""


class OAuthRequest(BaseModel):
    # R5批⑦（清单安全）：appid/secret 是服务端凭据，不再由请求体传入（任何能调用本
    # 接口的人都能拿到或替换它）；mock 与否同样收敛服务端 env。请求体只保留 code。
    code: str


@router.get("/subscribers")
def list_subscribers():
    """列出订阅推送的 openid 列表。"""
    return {"subscribers": load_subscribers()}


@router.post("/subscribe")
def subscribe(body: SubscribeRequest):
    """订阅 / 退订每日复习 + 周报推送。"""
    if not body.openid:
        raise HTTPException(status_code=400, detail="openid required")
    subs = load_subscribers()
    if body.subscribe and body.openid not in subs:
        subs.append(body.openid)
    elif not body.subscribe:
        subs = [s for s in subs if s != body.openid]
    data = set_subscribers(subs)
    return {"ok": True, "subscribers": data["subscribers"]}


@router.post("/oauth/code")
async def oauth_exchange(body: OAuthRequest):
    """微信网页授权：code -> openid（mock 或真实）。appid/secret/mock 均由服务端
    env 决定（WECHAT_MP_APPID / WECHAT_MP_SECRET / WECHAT_MP_MOCK，mock 默认开以
    兼容开发态）。"""
    appid = os.getenv("WECHAT_MP_APPID", "")
    secret = os.getenv("WECHAT_MP_SECRET", "")
    mock_mode = os.getenv("WECHAT_MP_MOCK", "1") == "1"
    try:
        openid = await exchange_code_for_openid(
            body.code, appid=appid, secret=secret, mock_mode=mock_mode
        )
        return {"ok": True, "openid": openid, "binding": get_binding(openid)}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/identity/{openid}")
def identity(openid: str):
    """查询 openid 的身份绑定。"""
    binding = get_binding(openid)
    if not binding:
        raise HTTPException(status_code=404, detail="no binding for openid")
    return {"openid": openid, **binding}


@router.post("/identity/bind")
def bind(body: BindRequest):
    """绑定 openid 到角色（student / parent）。"""
    if not body.openid:
        raise HTTPException(status_code=400, detail="openid required")
    try:
        entry = bind_openid(
            body.openid,
            role=body.role,
            display_name=body.display_name,
            student_openid=body.student_openid,
        )
        return {"ok": True, "openid": body.openid, "binding": entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/identity/unbind")
def unbind(body: SubscribeRequest):
    """解绑 openid。"""
    ok = unbind_openid(body.openid)
    return {"ok": ok}


@router.get("/identity")
def identity_list():
    """列出所有微信身份绑定。"""
    return {"bindings": list_bindings()}


@router.get("/push/daily")
def preview_daily():
    """预览今日复习提醒的模板数据（不发送）。"""
    return build_daily_review_payload()


@router.post("/push/daily")
async def send_daily(body: PushRequest):
    """发送今日复习提醒（mock 或真实模板消息）。"""
    payload = build_daily_review_payload(max_items=body.max_items)
    if not body.openid:
        return {"payload": payload, "note": "未提供 openid，未发送（预览模式）"}
    channel = get_channel(body.openid)
    await channel.start()
    try:
        result = await channel.send_daily_review_reminder(
            body.openid,
            kp_names=[d["kp_name"] for d in payload["_meta"]["due_reviews"]],
            due_count=len(payload["_meta"]["due_reviews"]),
            study_href=body.url,
        )
        return {"ok": True, "result": result, "payload": payload}
    finally:
        await channel.stop()


@router.get("/push/weekly")
def preview_weekly():
    """预览每周学情周报的模板数据（不发送）。"""
    return build_weekly_report_payload()


@router.post("/push/weekly")
async def send_weekly(body: PushRequest):
    """发送每周学情周报（mock 或真实模板消息）。"""
    payload = build_weekly_report_payload()
    if not body.openid:
        return {"payload": payload, "note": "未提供 openid，未发送（预览模式）"}
    channel = get_channel(body.openid)
    await channel.start()
    try:
        result = await channel.send_weekly_report(
            body.openid,
            subject_summary=payload["keyword1"]["value"],
            weak_points=payload["keyword2"]["value"],
            progress=payload["keyword3"]["value"],
            report_href=body.url,
        )
        return {"ok": True, "result": result, "payload": payload}
    finally:
        await channel.stop()


@router.post("/push/broadcast")
async def broadcast(which: str):
    """向所有订阅者广播推送（daily | mistake | push | weekly）。"""
    if which not in ("daily", "mistake", "push", "weekly"):
        raise HTTPException(
            status_code=400, detail="which must be 'daily' | 'mistake' | 'push' | 'weekly'"
        )
    scheduler = get_push_scheduler()
    results = await scheduler.run_once(which)
    return {"ok": True, "results": results}


@router.post("/push/mistake")
async def send_mistake(body: PushRequest):
    """错题到期提醒：向单个 openid 发送今日到期错题清单。

    未提供 openid 时返回预览（不发送）。
    """
    from app.services.sishu_full.services.wechat_push.chat import build_review_reply

    reply = build_review_reply(max_items=body.max_items)
    if not body.openid:
        return {"reply": reply, "note": "未提供 openid，未发送（预览模式）"}
    channel = get_channel(body.openid)
    await channel.start()
    try:
        from app.services.sishu_full.partners.bus.events import OutboundMessage

        result = await channel.send(
            OutboundMessage(channel="wechat_mp", chat_id=body.openid, content=reply)
        )
        return {"ok": True, "result": result, "reply": reply}
    finally:
        await channel.stop()


@router.post("/push/mastery")
async def send_mastery(body: PushRequest):
    """掌握度推进提醒：向单个 openid 推送「还差薄弱点这关」。

    未提供 openid 时返回预览（不发送）。
    """
    from app.services.sishu_full.services.wechat_push.chat import build_weekly_reply  # noqa: F401  (keep import contract)

    from app.services.sishu_full.learning.learner_profile import build_learner_profile

    profile = build_learner_profile()
    weak_names = [
        profile.kp_mastery[k].kp_name
        for k in profile.weak_points
        if k in profile.kp_mastery
    ]
    if not profile.kp_mastery or not weak_names:
        return {"ok": False, "note": "无薄弱知识点，跳过（正常）"}
    total = len(profile.kp_mastery)
    mastered = len(profile.strong_points)
    pct = int((mastered / total) * 100) if total else 0
    reply = (
        f"🎯 学习推进提醒\n\n"
        f"当前掌握度 {pct}%（{mastered}/{total} 个知识点），"
        f"还差「{weak_names[0]}」这一关。\n\n"
        f"今晚花 10 分钟突破它，下周就轻松多啦 💪"
    )
    if not body.openid:
        return {"reply": reply, "note": "未提供 openid，未发送（预览模式）"}
    channel = get_channel(body.openid)
    await channel.start()
    try:
        from app.services.sishu_full.partners.bus.events import OutboundMessage

        result = await channel.send(
            OutboundMessage(channel="wechat_mp", chat_id=body.openid, content=reply)
        )
        return {"ok": True, "result": result, "reply": reply}
    finally:
        await channel.stop()


@router.post("/scheduler/start")
async def scheduler_start():
    """启动后台定时推送调度器（每天 07:30 / 周日 20:00）。"""
    started = get_push_scheduler().start_if_running_loop()
    return {"ok": True, "running": started}


@router.post("/scheduler/stop")
async def scheduler_stop():
    """停止后台定时推送调度器。"""
    get_push_scheduler().stop()
    return {"ok": True, "running": False}


@router.post("/webhook")
async def wechat_webhook(
    body: dict,
    signature: str = Query(""),
    timestamp: str = Query(""),
    nonce: str = Query(""),
):
    """接收公众号回调事件（用户消息 / 菜单点击）并**回复**。

    事件 -> 消息解析 -> 关键词命令 / 图片 OCR / AI 答疑 -> 客服消息回推。

    R5批⑦（清单安全）：强制签名校验——原注释声称「签名校验由公众号后台 (Token) 或
    反向代理完成」实际无人做，FromUserName 客户端可控=身份/消息伪造+AI 成本消耗。
    token 由 env WECHAT_MP_TOKEN 配置，sha1(sort(token,ts,nonce)) 校验；未配置
    fail-closed 403，开发联调显式设 TUPU_WECHAT_WEBHOOK_UNVERIFIED=1 放行。

    支持的事件字段：
      - ``FromUserName``: 发送者 openid
      - ``MsgType``: text | image
      - ``Content``: 文本内容（text）
      - ``PicUrl`` / ``pic_url``: 图片 URL（image）
      - ``base64_image``: 图片字节的 base64（测试/聚合用）
    """
    if os.getenv("TUPU_WECHAT_WEBHOOK_UNVERIFIED", "") != "1":
        from app.services.sishu_full.partners.channels.wechat_mp import WechatMpChannel

        token = os.getenv("WECHAT_MP_TOKEN", "")
        if not token or not WechatMpChannel.verify_signature(token, signature, timestamp, nonce):
            raise HTTPException(status_code=403, detail="webhook 签名校验失败")

    from app.services.sishu_full.partners.bus.events import OutboundMessage
    from app.services.sishu_full.services.wechat_push.chat import handle_mp_message

    openid = str(body.get("FromUserName") or body.get("from_user") or "")
    msg_type = str(body.get("MsgType") or body.get("msgtype") or "text")
    content = str(body.get("Content") or body.get("content") or "")
    image_url = str(body.get("PicUrl") or body.get("pic_url") or "")
    base64_image = body.get("base64_image") or ""

    image_bytes: bytes | None = None
    if base64_image:
        import base64 as _b64

        try:
            image_bytes = _b64.b64decode(base64_image)
        except Exception:  # noqa: BLE001
            image_bytes = None

    # 生成回复（命令 / 图片 / 答疑）
    reply = await handle_mp_message(
        content,
        openid=openid,
        image_url=image_url,
        image_bytes=image_bytes,
    )

    # 回推给用户（客服消息）
    if reply and openid:
        channel = get_channel(openid)
        await channel.start()
        try:
            result = await channel.send(
                OutboundMessage(channel="wechat_mp", chat_id=openid, content=reply)
            )
        finally:
            await channel.stop()
        return {"ok": True, "reply": reply, "result": result}

    return {"ok": True, "reply": reply, "note": "无 openid，未回推"}


__all__ = ["router"]
