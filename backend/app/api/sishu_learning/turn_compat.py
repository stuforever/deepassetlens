# -*- coding: utf-8 -*-
"""v4批6 6.C：mastery_path 的 turn 运行时窄适配（E-62⑤）。

vendor get_turn_runtime_manager() 整栈（turn_runtime 2122 行+context_builder+source_inventory
+pocketbase……）属批8 会话域收编，不随批6 移植。本适配只承接 mastery_path 路由的实际消费面：
  `_cancel_active_learning_turn(book_id)`
    = runtime.store.get_active_turn(session_id=book_id)  → turns 表 status='running' 行
    + runtime.cancel_turn(turn_id)                        → 状态置 'cancelled'
vendor cancel_turn 的进程内任务取消注册表不随本适配（DB 状态转移=其他组件读取的契约面，
先到批8 全栈收编）；读改直连 vendor 同库 chat_history.db（path_service 同一解析点），
批8 换 PG sishu_turns 时本件随迁。
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any

from app.services.sishu.services.path_service import get_path_service


def _db_path():
    return get_path_service().get_chat_history_db().resolve()


class _TurnStore:
    async def get_active_turn(self, session_id: str) -> dict[str, Any] | None:
        try:
            with sqlite3.connect(str(_db_path())) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT id, session_id, status, created_at, updated_at FROM turns "
                    "WHERE session_id = ? AND status = 'running' ORDER BY updated_at DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
        except Exception:
            return None
        if row is None:
            return None
        return {"id": row["id"], "session_id": row["session_id"], "status": row["status"],
                "created_at": row["created_at"], "updated_at": row["updated_at"]}


class _TurnRuntime:
    def __init__(self) -> None:
        self.store = _TurnStore()

    async def cancel_turn(self, turn_id: str) -> bool:
        now = time.time()
        try:
            with sqlite3.connect(str(_db_path())) as conn:
                cur = conn.execute(
                    "UPDATE turns SET status='cancelled', error='', updated_at=?, finished_at=? "
                    "WHERE id=? AND status='running'",
                    (now, now, turn_id),
                )
                conn.commit()
            return cur.rowcount > 0
        except Exception:
            return False


def get_turn_runtime_manager() -> _TurnRuntime:
    return _TurnRuntime()
