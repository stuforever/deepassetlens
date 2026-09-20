# -*- coding: utf-8 -*-
# [sishu port] v4批6 特制件：vendor deeptutor/services/wechat_push/chat.py（1:1 语义，仅 import 改写）。
# 引擎换点（E-62②）：answer_with_orchestrator 的 vendor ChatOrchestrator → 平台引擎
# app.api.dt_agent_orchestrations.dispatch（v4 引擎合一——vendor runtime/orchestrator 不随批6 移植）。
# 会话键 wechat:{openid}、回复裁剪 max_chars、失败降级文案均保持 vendor 语义。
# 本件为特制件（脚本 _v4_port_batch6.py 播种自 scripts/sishu_port_special/）。
"""公众号对话框消息处理 — 命令路由 + AI 答疑（design §4.2 对话框消息）。

把公众号用户在对话框里发的消息变成有用的回复：

  * 发「复习」      → 今日到期复习题清单（母题库 due 驱动）
  * 发「周报」      → 本周学情摘要
  * 发图片（照片）  → OCR 识别题目 → 带题目文本走 AI 答疑
  * 发其他文字      → 平台 chat 引擎答疑（因材施教：注入学情画像）

这是「公众号发照片能答疑」验收项的实现核心：inbound 消息不再只是
丢进 bus 等 partner 消费，而是由本服务直接驱动平台 chat 引擎，
把回复经 WechatMpChannel 客服消息回推给用户。

设计参考：DESIGN_自主学习与记忆融合.md §4.2（对话框消息）§4.3（杀手场景）。
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from app.services.sishu.services.wechat_push.identity import openid_to_profile_openid

# 关键词命令（大小写不敏感，匹配前缀）
_COMMAND_REVIEW = ("复习", "今日复习", "review")
_COMMAND_WEEKLY = ("周报", "学情周报", "weekly", "周报？", "周报?")


def _classify_command(text: str) -> str | None:
    """返回 'review' | 'weekly' | None（普通消息走答疑）。"""
    t = (text or "").strip().lower()
    if not t:
        return None
    for kw in _COMMAND_REVIEW:
        if t == kw or t.startswith(kw):
            return "review"
    for kw in _COMMAND_WEEKLY:
        if t == kw or t.startswith(kw):
            return "weekly"
    return None


def build_review_reply(*, max_items: int = 3) -> str:
    """「复习」命令：列出今日到期的复习题（母题库 FSRS due）。

    没有到期时给出轻松提示；有到期时列出题目标题 + 简要提示。
    """
    try:
        from app.services.sishu.learning.mother_question import MotherQuestionStore

        store = MotherQuestionStore()
        due = store.list_due(max_items=max_items)
    except Exception:  # noqa: BLE001
        logger.warning("build_review_reply: mother store unavailable", exc_info=True)
        due = []

    if not due:
        return (
            "📭 今天没有到期的复习题，可以松口气啦！\n"
            "不过每天复习一点点，掌握度会更稳哦 🌱\n"
            "（发「周报」看看本周学情）"
        )

    lines = ["📚 今日复习清单（FSRS 到期）：", ""]
    for i, m in enumerate(due, 1):
        title = (m.title or "").strip() or (m.question_text or "").strip()[:30]
        lines.append(f"{i}. {title}")
    lines.append("")
    lines.append("答完记得来标注对错，我帮你更新掌握度 ✅")
    return "\n".join(lines)


def build_weekly_reply() -> str:
    """「周报」命令：本周学情摘要（复用周报 payload）。"""
    try:
        from app.services.sishu.services.wechat_push import build_weekly_report_payload

        payload = build_weekly_report_payload()
    except Exception:  # noqa: BLE001
        logger.warning("build_weekly_reply: payload failed", exc_info=True)
        return "📊 周报生成失败，稍后再试～"

    return (
        "📊 本周学情周报\n\n"
        f"· {payload['keyword1']['value']}\n"
        f"· 薄弱点：{payload['keyword2']['value']}\n"
        f"· 进度：{payload['keyword3']['value']}\n\n"
        "查看完整报告：打开公众号菜单「📊 学情」"
    )


def _profile_learning_summary() -> str:
    """拼一段学情画像摘要，供答疑 prompt 注入（因材施教）。"""
    try:
        from app.services.sishu.learning.learner_profile import build_learner_profile

        profile = build_learner_profile()
    except Exception:  # noqa: BLE001
        logger.warning("profile summary unavailable", exc_info=True)
        return ""
    if not profile or not profile.kp_mastery:
        return ""
    weak_names = [
        profile.kp_mastery[k].kp_name
        for k in profile.weak_points
        if k in profile.kp_mastery
    ]
    strong_names = [
        profile.kp_mastery[k].kp_name
        for k in profile.strong_points
        if k in profile.kp_mastery
    ]
    due_names = [
        d.get("kp_name", "") for d in profile.due_reviews[:5] if d.get("kp_name")
    ]
    parts = []
    if strong_names:
        parts.append(f"已掌握：{'、'.join(strong_names[:5])}")
    if weak_names:
        parts.append(f"薄弱点：{'、'.join(weak_names[:5])}（重点辅导这些）")
    if due_names:
        parts.append(f"今日应复习：{'、'.join(due_names)}")
    if parts:
        return "当前学生学习画像：" + "；".join(parts) + "。"
    return ""


async def answer_with_orchestrator(
    question: str,
    *,
    openid: str = "",
    context_hint: str = "",
    max_chars: int = 600,
) -> str:
    """用平台 chat 引擎跑一轮对话，返回最终回复文本。

    *question* 是要问的内容；*context_hint* 是注入的学情上下文；
    回复太长会被裁剪到 max_chars（微信客服消息长度限制宽松，但对话体验
    不宜过长）。

    E-62② 引擎换点：vendor ChatOrchestrator().handle(UnifiedContext) →
    平台 dispatch(req, session_id, turn_id, user_prefix)——result 帧取 answer 文本。
    """
    from types import SimpleNamespace

    from app.api.dt_agent_orchestrations import dispatch

    profile_openid = openid_to_profile_openid(openid)
    # 把用户想问的 + 学情画像注入给模型
    system_context = (
        f"{context_hint}\n"
        if context_hint
        else _profile_learning_summary()
    )
    user_message = f"{system_context}\n用户的问题：{question}".strip()

    session_id = f"wechat:{profile_openid}"
    import uuid as _uuid

    turn_id = _uuid.uuid4().hex
    req = SimpleNamespace(
        skill_code="sishu/chat",
        message=user_message,
        knowledge_bases=[],
        tools=[],
        mode="chat",
    )
    final_text = ""
    errors: list[str] = []
    try:
        async for event in dispatch(req, session_id, turn_id, "admin"):
            etype = event.get("type")
            if etype == "result" and event.get("stage") == "answer":
                final_text = str(event.get("content") or "")
            elif etype == "error" and event.get("content"):
                errors.append(str(event.get("content")))
    except Exception as exc:  # noqa: BLE001
        logger.exception("wechat answer turn crashed")
        errors.append(f"{type(exc).__name__}: {exc}")

    if not final_text.strip():
        return (
            f"抱歉，答疑暂时没跑通（{errors[-1][:120] if errors else '未知错误'}）。"
            "请稍后再试，或换一种问法～"
        )
    final_text = final_text.strip()
    if len(final_text) > max_chars:
        final_text = final_text[: max_chars - 1] + "…"
    return final_text


def ocr_image_bytes(file_bytes: bytes) -> str:
    """OCR 识别图片里的题目文字（复用 image_pipeline）。"""
    from app.services.sishu.learning.image_pipeline import ocr_image

    result = ocr_image(file_bytes)
    text = str(result.get("text") or result.get("ocr_text") or "").strip()
    return text


async def handle_mp_message(
    text: str,
    *,
    openid: str = "",
    image_url: str = "",
    image_bytes: bytes | None = None,
) -> str:
    """公众号对话框消息的统一入口，返回要回推给用户的文本。

    Args:
        text: 用户消息文本（图片消息时可为空或描述）。
        openid: 发送者 openid（用于学情注入 / 会话隔离）。
        image_url: 图片消息的 PicUrl（若有）。
        image_bytes: 图片原始字节（若有，直接 OCR）。
    """
    # 1) 关键词命令优先
    if text:
        cmd = _classify_command(text)
        if cmd == "review":
            return build_review_reply()
        if cmd == "weekly":
            return build_weekly_reply()

    # 2) 图片：OCR 识别 → 带题答疑
    if image_bytes or image_url:
        ocr_text = ""
        if image_bytes:
            try:
                ocr_text = ocr_image_bytes(image_bytes)
            except Exception:  # noqa: BLE001
                logger.warning("wechat image OCR failed", exc_info=True)
                ocr_text = ""
        prompt_parts = []
        if ocr_text:
            prompt_parts.append(f"图片中识别到的题目文字：\n{ocr_text}")
        if text:
            prompt_parts.append(f"用户的补充说明：{text}")
        prompt_parts.append("请识别这道题并给出：1）题目考查的知识点；2）分步解答；3）易错点提醒。")
        return await answer_with_orchestrator("\n".join(prompt_parts), openid=openid)

    # 3) 普通文字：AI 答疑（带学情画像，因材施教）
    if text:
        return await answer_with_orchestrator(text, openid=openid)

    return "你好！我是你的 AI 私教 👋 可以这样用我：\n· 直接问一道题\n· 发「复习」看今日复习清单\n· 发「周报」看本周学情\n· 拍一张题目照片发给我，我来讲解"


__all__ = [
    "_classify_command",
    "answer_with_orchestrator",
    "build_review_reply",
    "build_weekly_reply",
    "handle_mp_message",
    "ocr_image_bytes",
]
