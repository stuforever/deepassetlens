# -*- coding: utf-8 -*-
"""⑤补补-3 步骤 2：今日任务 policy（组合逻辑迁 DeepTutor policy 语义，无新状态机）。

due（到期卡，直接复习）+ weak（薄弱点 kp，有母题者出练习）→ 今日任务清单：
[{kind, item_id, title, reason}]——due 在前 weak 在后，各截断合并 ≤limit。
"""
from __future__ import annotations

from typing import Optional

from .learning_dao import mother_questions_by_kps
from .service import due_cards


def today_tasks(user_id: str, limit: int = 10) -> list[dict]:
    """今日任务=N（due 到期 + weak 薄弱点选题组合）。"""
    tasks: list[dict] = []
    for it in due_cards(user_id, limit=limit):
        tasks.append({
            "kind": it.get("kind") or "knowledge_point",
            "item_id": it.get("item_id"),
            "title": it.get("item_id"),
            "reason": "到期复习",
        })
    remain = max(0, limit - len(tasks))
    if remain > 0:
        from .learner_profile import build_learner_profile
        p = build_learner_profile(user_id)
        weak_kps = [w["item_id"] for w in (p.weak_points or [])][:remain]
        if weak_kps:
            mqs = mother_questions_by_kps(weak_kps)
            by_kp: dict[str, list[dict]] = {}
            for m in mqs:
                by_kp.setdefault(m.get("knowledge_point_id"), []).append(m)
            seen: set[str] = set()
            for kp in weak_kps:
                if kp in seen or remain <= 0:
                    continue
                seen.add(kp)
                first = (by_kp.get(kp) or [None])[0]
                if first:
                    tasks.append({
                        "kind": "mother_question",
                        "item_id": first.get("mq_id"),
                        "title": first.get("title") or kp,
                        "reason": f"薄弱点练习（{kp}）",
                    })
                    remain -= 1
    return tasks[:limit]


__all__ = ["today_tasks"]
