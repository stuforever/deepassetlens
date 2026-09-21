"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import time

from app.services.sishu_full.services.path_service import get_path_service

logger = logging.getLogger(__name__)

DAILY_CRON = "30 7 * * *"      # 每天 07:30 复习提醒
MISTAKE_CRON = "30 18 * * *"    # 每天 18:30 错题到期提醒
PUSH_CRON = "30 19 * * 3"       # 每周三 19:30 掌握度推进提醒
WEEKLY_CRON = "0 20 * * 0"      # 每周日 20:00 周报
_DAILY_ID = "wechat_daily_review"
_MISTAKE_ID = "wechat_mistake_due"
_PUSH_ID = "wechat_mastery_push"
_WEEKLY_ID = "wechat_weekly_report"


def _settings_path() -> Path:
    return get_path_service().get_settings_dir() / "wechat_push.json"


def load_subscribers() -> list[str]:
    """Openids subscribed to push (from settings/wechat_push.json)."""
    try:
        p = _settings_path()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            subs = data.get("subscribers") or []
            return [s for s in subs if s]
    except Exception:
        logger.warning("wechat_push settings read failed", exc_info=True)
    return []


def set_subscribers(openids: list[str]) -> dict:
    """Persist the subscriber openid list."""
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"subscribers": [s for s in openids if s], "updated_at": time.time()}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


async def _send_to_all(fn, *args, **kwargs) -> list[dict]:
    """Send to every subscriber via *fn*; returns per-openid results.

    *role_filter* (via kwargs ``_role``) restricts which subscribers receive
    the push: 'student' (default for study pushes), 'parent' (weekly report),
    or None (everyone). A per-openid payload can be built by reading
    ``kwargs['_profile_openid']``.
    """
    from app.services.sishu_full.services.wechat_push import get_channel
    from app.services.sishu_full.services.wechat_push.identity import (
        filter_subscribers_by_role,
        openid_to_profile_openid,
    )

    role_filter = kwargs.pop("_role", None)
    openids = load_subscribers()
    if role_filter:
        openids = filter_subscribers_by_role(openids, role_filter)

    results = []
    channel = get_channel()
    await channel.start()
    try:
        for openid in openids:
            try:
                result = await fn(
                    channel,
                    openid,
                    *args,
                    _profile_openid=openid_to_profile_openid(openid),
                    **kwargs,
                )
                results.append({"openid": openid, "ok": True, "result": result})
            except Exception as e:  # noqa: BLE001
                results.append({"openid": openid, "ok": False, "error": str(e)})
    finally:
        await channel.stop()
    return results


async def send_daily_review_to_all() -> list[dict]:
    """发送今日复习提醒给所有订阅者（仅 student 角色）。

    按 openid 的 LearnerProfile 分别构建（多学生场景发各自的内容）。
    """
    from app.services.sishu_full.learning.learner_profile import build_learner_profile
    from app.services.sishu_full.services.wechat_push.identity import openid_to_profile_openid

    async def _send(channel, openid, *, _profile_openid):
        profile = build_learner_profile(user_id=_profile_openid)
        due = profile.due_reviews[:5]
        kp_names = [d.get("kp_name", "") for d in due if d.get("kp_name")]
        weak_names = [
            profile.kp_mastery[k].kp_name
            for k in profile.weak_points
            if k in profile.kp_mastery
        ]
        return await channel.send_daily_review_reminder(
            openid,
            kp_names=kp_names,
            due_count=len(due),
        )

    return await _send_to_all(_send, _role="student")


async def send_weekly_report_to_all() -> list[dict]:
    """发送每周学情周报给订阅的**家长**（设计：周报给家长看）。

    按家长关联的学生（openid_to_profile_openid）分别构建，多学生场景
    各家长收到自己孩子的周报。
    """
    from app.services.sishu_full.learning.learner_profile import build_learner_profile, compute_weekly_delta

    async def _send(channel, openid, *, _profile_openid):
        profile = build_learner_profile(user_id=_profile_openid)
        # 学科摘要
        subjects = {}
        for kp in profile.kp_mastery.values():
            s = subjects.setdefault(kp.subject, {"total": 0, "mastered": 0})
            s["total"] += 1
            if kp.status == "mastered":
                s["mastered"] += 1
        subj_label = {"math": "数学", "chinese": "语文", "english": "英语"}
        summary_parts = [
            f"{subj_label.get(subj, subj)}：掌握{st['mastered']}/{st['total']}"
            for subj, st in subjects.items()
        ]
        subject_summary = "；".join(summary_parts) if summary_parts else "暂无学习数据"

        weak_names = [
            profile.kp_mastery[k].kp_name
            for k in profile.weak_points
            if k in profile.kp_mastery
        ]
        weak_points = "、".join(weak_names[:5]) if weak_names else "暂无明确薄弱点，保持节奏"

        # 本周增量（audit P1-4）
        delta = compute_weekly_delta(profile)
        total_kps = len(profile.kp_mastery)
        mastered = len(profile.strong_points)
        if delta["active_days"] == 0 and total_kps == 0:
            progress = "本周开始建立学情画像"
        else:
            parts = []
            if delta["new_kps"]:
                parts.append(f"本周新学 {delta['new_kps']} 个知识点")
            if delta["mastered_this_week"]:
                parts.append(f"本周掌握 {delta['mastered_this_week']} 个")
            if delta["attempts"]:
                parts.append(f"答题 {delta['attempts']} 次（正确率 {int(delta['correct_rate'] * 100)}%）")
            if delta["review_count"]:
                parts.append(f"复习 {delta['review_count']} 次")
            progress = "、".join(parts) + f"；累计掌握 {mastered}/{total_kps}" if parts else f"累计掌握 {mastered}/{total_kps} 个知识点"
        return await channel.send_weekly_report(
            openid,
            subject_summary=subject_summary,
            weak_points=weak_points,
            progress=progress,
        )

    return await _send_to_all(_send, _role="parent")


async def send_mistake_due_to_all(max_items: int = 3) -> list[dict]:
    """错题到期提醒（design §4.2 定时推送）：母题库有到期错题时提醒（仅 student）。

    复用 WechatMpChannel 客服消息（文本）发送，避免依赖额外模板 ID；
    无到期错题时跳过（返回空结果，不打扰）。
    """
    from app.services.sishu_full.learning.mother_question import MotherQuestionStore
    from app.services.sishu_full.services.wechat_push.chat import build_review_reply

    async def _send(channel, openid, *, _profile_openid):
        # 无到期错题时跳过
        try:
            store = MotherQuestionStore()
            due = store.list_due(max_items=max_items)
        except Exception:  # noqa: BLE001
            logger.warning("send_mistake_due_to_all: mother store unavailable", exc_info=True)
            due = []
        if not due:
            return {"skipped": True}
        reply = build_review_reply(max_items=max_items)
        from app.services.sishu_full.partners.bus.events import OutboundMessage

        return await channel.send(
            OutboundMessage(channel="wechat_mp", chat_id=openid, content=reply)
        )

    return await _send_to_all(_send, _role="student")


async def send_mastery_push_to_all() -> list[dict]:
    """掌握度推进提醒（design §4.3 周三晚场景，仅 student）。

    当存在薄弱知识点时推送：「掌握度 X%，还差『薄弱点』这关，今晚搞定？」
    无薄弱点时跳过（不打扰）。
    """
    from app.services.sishu_full.learning.learner_profile import build_learner_profile

    async def _send(channel, openid, *, _profile_openid):
        profile = build_learner_profile(user_id=_profile_openid)
        if not profile or not profile.kp_mastery:
            return {"skipped": True}
        weak_names = [
            profile.kp_mastery[k].kp_name
            for k in profile.weak_points
            if k in profile.kp_mastery
        ]
        if not weak_names:
            return {"skipped": True}
        total = len(profile.kp_mastery)
        mastered = len(profile.strong_points)
        pct = int((mastered / total) * 100) if total else 0
        first_weak = weak_names[0]
        reply = (
            f"🎯 学习推进提醒\n\n"
            f"当前掌握度 {pct}%（{mastered}/{total} 个知识点），"
            f"还差「{first_weak}」这一关。\n\n"
            f"今晚花 10 分钟突破它，下周就轻松多啦 💪\n"
            f"（打开公众号菜单「📚 学习」开始）"
        )
        from app.services.sishu_full.partners.bus.events import OutboundMessage

        return await channel.send(
            OutboundMessage(channel="wechat_mp", chat_id=openid, content=reply)
        )

    return await _send_to_all(_send, _role="student")


# --------------------------------------------------------------------------- #
# 调度器                                                                    #
# --------------------------------------------------------------------------- #


class WechatPushScheduler:
    """Minimal cron-style asyncio scheduler for the two push slots."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_daily: str = ""
        self._last_mistake: str = ""
        self._last_push: str = ""
        self._last_weekly: str = ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "wechat_push scheduler started (daily=%s mistake=%s push=%s weekly=%s)",
            DAILY_CRON,
            MISTAKE_CRON,
            PUSH_CRON,
            WEEKLY_CRON,
        )

    def start_if_running_loop(self) -> bool:
        """Start only when an event loop is running (FastAPI lifespan / async route).

        Returns True when started; False when no loop is available (e.g. a sync
        route worker) so callers can fall back to the loop-free path.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return False
        self.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                # 每天 07:30 复习提醒
                if now.hour == 7 and now.minute >= 30 and self._last_daily != today:
                    self._last_daily = today
                    await send_daily_review_to_all()
                # 每天 18:30 错题到期提醒
                if now.hour == 18 and now.minute >= 30 and self._last_mistake != today:
                    self._last_mistake = today
                    await send_mistake_due_to_all()
                # 每周三 19:30 掌握度推进提醒
                if now.weekday() == 2 and now.hour == 19 and now.minute >= 30 and self._last_push != today:
                    self._last_push = today
                    await send_mastery_push_to_all()
                # 每周日 20:00 周报
                if now.weekday() == 6 and now.hour == 20 and self._last_weekly != today:
                    self._last_weekly = today
                    await send_weekly_report_to_all()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.warning("wechat_push scheduler iteration error", exc_info=True)
            await asyncio.sleep(60)

    async def run_once(self, which: str) -> list[dict]:
        """Manually trigger one push (for tests / API / cron fallback).

        Supported: daily | mistake | push | weekly.
        """
        if which == "daily":
            return await send_daily_review_to_all()
        if which == "mistake":
            return await send_mistake_due_to_all()
        if which == "push":
            return await send_mastery_push_to_all()
        if which == "weekly":
            return await send_weekly_report_to_all()
        raise ValueError(f"unknown push target {which!r}")


_scheduler: WechatPushScheduler | None = None


def get_push_scheduler() -> WechatPushScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = WechatPushScheduler()
    return _scheduler


__all__ = [
    "DAILY_CRON",
    "MISTAKE_CRON",
    "PUSH_CRON",
    "WEEKLY_CRON",
    "WechatPushScheduler",
    "get_push_scheduler",
    "load_subscribers",
    "send_daily_review_to_all",
    "send_mastery_push_to_all",
    "send_mistake_due_to_all",
    "send_weekly_report_to_all",
    "set_subscribers",
]
