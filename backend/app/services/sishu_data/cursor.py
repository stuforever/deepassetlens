# -*- coding: utf-8 -*-
"""v4批2 2.3：协议 E v2 迁移基建——游标表 + 幂等骨架 + 资产 sha256 双账。
批6-14 迁移脚本族消费：get_cursor/set_cursor 断点续传；bump 游标；hash 清单落
dt_baseline/v4_asset_hashes.json（bytea 类 size+sha256 全量，行数对账对空壳行不设防）。"""
import hashlib
import json
from pathlib import Path

from sqlalchemy import text

from .pg import engine

_BASELINE = Path(__file__).resolve().parents[3] / "scripts" / "dt_baseline"


def get_cursor(domain: str) -> dict:
    """读游标（无记录→零值起点）。"""
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT last_id, rows_done FROM sishu_migration_cursor WHERE domain=:d"),
            {"d": domain}).fetchone()
    return {"last_id": row[0] if row else None,
            "rows_done": row[1] if row else 0}


def set_cursor(domain: str, last_id, rows_done: int) -> None:
    """推进游标（upsert；迁移脚本每批处理完调用一次）。"""
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_migration_cursor (domain, last_id, rows_done, updated_at)
            VALUES (:d, :l, :r, now())
            ON CONFLICT (domain) DO UPDATE SET
              last_id = EXCLUDED.last_id,
              rows_done = EXCLUDED.rows_done,
              updated_at = now()"""), {"d": domain, "l": str(last_id) if last_id is not None else None,
                                       "r": rows_done})


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append_asset_hashes(domain: str, entries: list[dict]) -> None:
    """追加资产哈希清单（协议 E v2 双账）：[{key, mime, size, sha256}]。
    落 dt_baseline/v4_asset_hashes.json（domain 分节累积，重跑幂等去重）。"""
    _BASELINE.mkdir(parents=True, exist_ok=True)
    f = _BASELINE / "v4_asset_hashes.json"
    doc = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    sect = doc.setdefault(domain, {})
    for e in entries:
        sect[e["key"]] = {"mime": e.get("mime"), "size": e.get("size"), "sha256": e.get("sha256")}
    f.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def row_count(engine_or_conn, table: str) -> int:
    sql = text(f"SELECT COUNT(*) FROM {table}")
    with engine.connect() as c:
        return c.execute(sql).scalar()
