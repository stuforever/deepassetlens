# -*- coding: utf-8 -*-
r"""切换 v3.0 R0-⑥：vendor sqlite 会话元数据 → PG 一次性迁移（design §2.2 C 组）。

扫描 backend/data 下全部 chat_history.db（per-expert workspace + per-user 隔离目录），
把 sessions 表逐行 upsert 进 PG sishu_session_meta（user_prefix 按文件路径派生）：
  data/experts/<expert>/workspace/data/users/<user>/user/chat_history.db → expert/<user>
  data/experts/<expert>/workspace/data/user/chat_history.db            → expert/anonymous
  其余布局（data/user/chat_history.db 等遗留位置）→ 相对目录路径作前缀
幂等（重复跑=更新）；messages/turns 内容面不迁（会话内容=langgraph checkpointer）。

用法：cd backend && python scripts/migrate_sishu_sessions_to_pg.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


def _user_prefix_of(db_path: Path) -> str:
    rel = db_path.relative_to(BACKEND_ROOT / "data").as_posix()
    head = rel[: -len("/chat_history.db")] if rel.endswith("/chat_history.db") else rel
    if "experts/" in rel and "/workspace/data/user" in rel:
        expert = head.split("experts/", 1)[1].split("/workspace/data/user", 1)[0]
        if "/workspace/data/users/" in rel:
            user = head.split("/workspace/data/users/", 1)[1]
            return f"{expert}/{user}"
        return f"{expert}/anonymous"
    return head  # 遗留/未知布局：相对目录路径即前缀（信息不丢）


def _to_dt(ts: float | None):
    if not ts:
        return None
    try:
        return _dt.datetime.fromtimestamp(float(ts), tz=_dt.timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def migrate(dry_run: bool = False) -> dict:
    from sqlalchemy.orm import Session as _SaSession

    from app.core.database import SessionLocal
    from app.models.base import SishuSessionMeta

    dbs = sorted((BACKEND_ROOT / "data").rglob("chat_history.db"))
    stats = {"scanned_dbs": len(dbs), "upserted": 0, "skipped": 0, "dbs": []}
    for db_path in dbs:
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                rows = conn.execute(
                    "SELECT id, title, created_at, updated_at, compressed_summary,"
                    " preferences_json FROM sessions").fetchall()
            finally:
                conn.close()
        except sqlite3.Error as e:
            stats["dbs"].append({"path": str(db_path), "error": str(e)})
            continue
        prefix = _user_prefix_of(db_path)
        stats["dbs"].append({"path": str(db_path), "user_prefix": prefix, "rows": len(rows)})
        if dry_run or not rows:
            continue
        db: _SaSession = SessionLocal()
        try:
            for sid, title, created, updated, summary, prefs in rows:
                try:
                    prefs_obj = json.loads(prefs) if prefs else {}
                except json.JSONDecodeError:
                    prefs_obj = {}
                obj = db.get(SishuSessionMeta, sid) or SishuSessionMeta(id=sid)
                obj.user_prefix = prefix
                obj.title = title or ""
                obj.compressed_summary = summary or ""
                obj.preferences_json = prefs_obj or {}
                obj.created_at = _to_dt(created)
                obj.updated_at = _to_dt(updated)
                db.add(obj)
                stats["upserted"] += 1
            db.commit()
        finally:
            db.close()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    out = migrate(dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=1))
