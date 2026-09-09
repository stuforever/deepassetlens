# -*- coding: utf-8 -*-
"""件①：kg_entity_lookup_cache 缓存层（spec 2026-09-09 §三/§五）。

行为契约：缓存是加速件非正确性件——读写失败一律 warning+降级（查返 None/写跳过/
清空不阻断）；失效=实体/元数据写操作全表清空（DELETE，重建代价=下次一次批量查）。
自开短会话：不掺和调用方事务（写端点接线零侵入）。
"""
import json
import logging
import unicodedata
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def normalize_query_key(q: str) -> str:
    """归一化查询键：NFKC → 小写 → 去全部空白（spec 件①）。"""
    return "".join(unicodedata.normalize("NFKC", q or "").lower().split())


def cache_lookup(query: str, query_kind: str) -> Optional[Dict[str, Any]]:
    """命中直返（零向量零重查）并 bump hit_count/last_used_at；异常降级 None+warning。"""
    key = normalize_query_key(query)
    if not key:
        return None
    from app.core.database import SessionLocal
    from sqlalchemy import text
    try:
        with SessionLocal() as db:
            row = db.execute(text(
                "SELECT result_json, hit_count FROM kg_entity_lookup_cache "
                "WHERE query_key = :k AND query_kind = :kind LIMIT 1"
            ), {"k": key, "kind": query_kind}).fetchone()
            if row is None:
                return None
            db.execute(text(
                "UPDATE kg_entity_lookup_cache SET hit_count = hit_count + 1, "
                "last_used_at = NOW() WHERE query_key = :k"
            ), {"k": key})
            db.commit()
            result = row[0]
            if isinstance(result, str):
                # 裸 text 查询绕过 ORM JSON 类型：pymysql 将 JSON 列返回为 str，
                # 须反序列化回「与 search_entities 单查返回同构」的 dict（任务 2 `**cached` 依赖）。
                result = json.loads(result)
            return result
    except Exception as e:
        logger.warning(f"[entity_lookup_cache] 读缓存失败（降级直查）: {e}")
        return None


def cache_store(query: str, query_kind: str, result: Dict[str, Any]) -> None:
    """回写（upsert）；失败仅 warning 不阻断。"""
    key = normalize_query_key(query)
    if not key or result is None:
        return
    from app.core.database import SessionLocal
    from sqlalchemy import text
    try:
        with SessionLocal() as db:
            db.execute(text(
                "INSERT INTO kg_entity_lookup_cache (id, query_key, query_kind, result_json, hit_count) "
                "VALUES (:id, :k, :kind, :r, 1) "
                "ON DUPLICATE KEY UPDATE result_json = :r, updated_at = NOW()"
            ), {"id": str(uuid.uuid4()), "k": key, "kind": query_kind,
                "r": json.dumps(result, ensure_ascii=False)})
            db.commit()
    except Exception as e:
        logger.warning(f"[entity_lookup_cache] 写缓存失败（跳过）: {e}")


def invalidate_entity_lookup_cache() -> None:
    """全表清空（实体/元数据写后触发，engine_health invalidate 同款模式）；失败不阻断写操作。"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    try:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM kg_entity_lookup_cache"))
            db.commit()
    except Exception as e:
        logger.warning(f"[entity_lookup_cache] 失效清空失败: {e}")
