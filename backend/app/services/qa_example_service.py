"""G1 验证示例库服务（融合设计 §4.1）。

- 语义检索：问题 embedding -> Qdrant 集合 tupu_qa_examples 检索 top-3（阈值 0.75，status=enabled）；
- 注入块：build_examples_block 供 _build_contract_system_message 尾部追加（仅供构造参考，禁止照抄执行）；
- CRUD：新增/列表/启停/删除（DB 行 + Qdrant point 同步）；
- 降级：Qdrant 或向量服务不可用时**静默跳过**（不阻断问答），沿用 qdrant_unavailable 降级模式。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.base import KgExampleHitLog, KgVerifiedQaExample
from app.services.tupu_qdrant_client import TupuQdrantClient

logger = logging.getLogger(__name__)

QDRANT_COLLECTION_QA_EXAMPLES = "tupu_qa_examples"
_SCORE_THRESHOLD_DEFAULT = 0.75
_MAX_TOP = 3


def _score_threshold() -> float:
    """相似度阈值（S4：TUPU_EXAMPLE_SIM_THRESHOLD 环境变量化，默认 0.75；每次读取支持运行时调整）。"""
    try:
        return float(os.getenv("TUPU_EXAMPLE_SIM_THRESHOLD", str(_SCORE_THRESHOLD_DEFAULT)))
    except Exception:
        return _SCORE_THRESHOLD_DEFAULT


def _norm_question(text: Any) -> str:
    """规范化问题（复用标准语义词条管线的 normalize_text）：NFKC + 去空白/标点 + 小写。"""
    try:
        from app.services.query_entity_utils import normalize_text
        return normalize_text(text)
    except Exception:
        return str(text or "").strip()


def _safe_client() -> Optional[TupuQdrantClient]:
    """健康检查通过的 Qdrant client；不可用返回 None（不抛）。"""
    try:
        from app.services.tupu_qdrant_client import is_qdrant_backend_enabled
        if not is_qdrant_backend_enabled():
            return None
        client = TupuQdrantClient()
        if not client.healthcheck():
            return None
        return client
    except Exception as _e:
        logger.warning(f"[QA示例库] Qdrant 不可用（跳过向量操作）: {_e}")
        return None


def _embed_question(db: Session, question: str) -> List[float]:
    """问题向量化；失败返回 []（调用方据此静默跳过检索）。"""
    try:
        from app.services.semantic_retrieval import embed_texts
        vecs = embed_texts(db, [question])
        if vecs and vecs[0]:
            return [float(x) for x in vecs[0]]
    except Exception as _e:
        logger.warning(f"[QA示例库] 向量化失败（跳过 Qdrant 检索）: {_e}")
    return []


def search_qa_examples(
    db: Session,
    question: str,
    top: int = _MAX_TOP,
    score_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """检索 top-N 已验证示例（status=enabled）。两级检索：

      Tier1（确定性保底）：DB 精确匹配 question_raw / question_norm == 问题（弱 embedding 环境下
            保证「同类问题二问」确定性命中，score=1.0）；
      Tier2（语义增强）：问题向量 -> Qdrant tupu_qa_examples 检索（阈值 0.75，按设计），补充不足 top 的部分。

    Qdrant/向量不可用时静默降级为仅 Tier1，不阻断问答。
    """
    question = (question or "").strip()
    if not question:
        return []
    results: List[Dict[str, Any]] = []
    seen: set = set()
    # Tier1：DB 精确/归一化匹配（sim=1.0 优先，防向量抖动——S4b 直通增强）
    #   匹配面：question_raw == 原文 | question_norm == 原文/规范化输入 | 规范化(question_raw) == 规范化输入
    #   （normalize_text 去空白/标点/大小写后比较，容忍「统计用电客户总数。」vs「统计用电客户总数」这类抖动）
    try:
        _norm_q = _norm_question(question)
        exact = db.query(KgVerifiedQaExample).filter(
            KgVerifiedQaExample.status == "enabled",
            KgVerifiedQaExample.question_raw == question,
        ).all()
        if not exact:
            exact = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.status == "enabled",
                KgVerifiedQaExample.question_norm == question,
            ).all()
        if not exact:
            exact = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.status == "enabled",
                KgVerifiedQaExample.question_norm == _norm_q,
            ).all()
        if not exact:
            exact = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.status == "enabled",
            ).all()
            exact = [r for r in exact if _norm_question(r.question_raw) == _norm_q]
        for r in exact[:top]:
            results.append({
                "id": str(r.id), "score": 1.0,
                "question_raw": r.question_raw, "sql": r.sql or "",
                "route_type": r.route_type or "",
            })
            seen.add(str(r.id))
    except Exception as _e:
        logger.warning(f"[QA示例库] Tier1 检索失败: {_e}")
    if len(results) >= top:
        return results[:top]
    # Tier2：语义检索补充（阈值环境变量化：TUPU_EXAMPLE_SIM_THRESHOLD，默认 0.75）
    vec = _embed_question(db, question)
    if not vec:
        return results
    client = _safe_client()
    if client is None:
        return results
    try:
        hits = client.search_points(
            QDRANT_COLLECTION_QA_EXAMPLES, vec,
            top=max(top * 3, 10), score_threshold=score_threshold if score_threshold is not None else _score_threshold(),
        )
    except Exception as _e:
        logger.warning(f"[QA示例库] Qdrant 检索失败（降级为仅 Tier1）: {_e}")
        return results
    for h in hits:
        payload = h.get("payload") or {}
        if payload.get("status", "enabled") != "enabled":
            continue
        pid = str(h.get("id"))
        if pid in seen:
            continue
        results.append({
            "id": pid,
            "score": h.get("score"),
            "question_raw": payload.get("question_raw", ""),
            "sql": payload.get("sql", ""),
            "route_type": payload.get("route_type", ""),
        })
        seen.add(pid)
        if len(results) >= top:
            break
    return results[:top]


def build_examples_payload(db: Session, question: str, top: int = _MAX_TOP) -> Dict[str, Any]:
    """构造注入负载：{block: str, hits: [{id, score, question_raw, sql, route_type}]}。
    无命中/降级时 block 为空串、hits 为空列表（不阻断问答）。"""
    hits = search_qa_examples(db, question, top=top)
    if not hits:
        return {"block": "", "hits": []}
    lines = ["\n参考示例（历史已验证查询，仅供构造 SQL 参考，禁止照抄执行）："]
    for i, ex in enumerate(hits, 1):
        lines.append(f"[示例{i}] 问题：{ex['question_raw']}")
        if ex.get("sql"):
            lines.append(f"        SQL：{ex['sql']}")
    return {"block": "\n".join(lines), "hits": hits}


def build_examples_block(db: Session, question: str, top: int = _MAX_TOP) -> str:
    """构造参考示例块（注入 SystemMessage 尾部）。无命中/降级返回空串。"""
    return build_examples_payload(db, question, top=top)["block"]


# ---------------------------------------------------------------------------
# CRUD（DB 行 + Qdrant point 同步）
# ---------------------------------------------------------------------------

def _upsert_qdrant(client: TupuQdrantClient, example_id: str, question_raw: str,
                   sql: str, route_type: str, status: str) -> None:
    """把示例向量 upsert 进 tupu_qa_examples（集合缺失则按配置维度创建）。失败仅告警不阻断。"""
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            vec = _embed_question(db, question_raw)
        finally:
            db.close()
        if not vec:
            logger.warning(f"[QA示例库] 示例 {example_id} 向量化失败，跳过 Qdrant upsert")
            return
        # 集合维度 = 实际向量长度（配置默认可能与真实 encoder 输出不一致，以 len(vec) 为准）
        _dim = len(vec)
        try:
            client.ensure_collection(QDRANT_COLLECTION_QA_EXAMPLES, _dim)
        except Exception as _ce:
            # 维度不匹配：仅当集合为空时重建（本库冷启动阶段允许），否则告警跳过
            try:
                if client.count_points(QDRANT_COLLECTION_QA_EXAMPLES) == 0:
                    client.ensure_collection(QDRANT_COLLECTION_QA_EXAMPLES, _dim, recreate=True)
                else:
                    logger.warning(f"[QA示例库] 集合维度不匹配且非空，跳过 upsert: {_ce}")
                    return
            except Exception:
                logger.warning(f"[QA示例库] 集合创建失败（跳过 upsert）: {_ce}")
                return
        client.upsert_points(QDRANT_COLLECTION_QA_EXAMPLES, [{
            "id": example_id,
            "vector": vec,
            "payload": {"question_raw": question_raw, "sql": sql or "",
                        "route_type": route_type or "", "status": status or "enabled"},
        }])
    except Exception as _e:
        logger.warning(f"[QA示例库] Qdrant upsert 失败（DB 已写入，向量暂缺）: {_e}")


def add_qa_example(
    db: Session,
    *,
    question_raw: str,
    sql: Optional[str] = None,
    entity_codes: Optional[List[str]] = None,
    route_type: str = "generic",
    engine: Optional[str] = None,
    example_type: str = "manual",
    question_norm: Optional[str] = None,
    status: str = "enabled",
) -> Dict[str, Any]:
    """新增示例（DB 行 + Qdrant point）。返回 {id, ok}。

    status: enabled | review（G5 反馈 👎+修正 SQL 进审核队列用 review）。
    """
    question_raw = (question_raw or "").strip()
    if not question_raw:
        return {"ok": False, "error": "question_raw 必填"}
    row = KgVerifiedQaExample(
        question_norm=(question_norm or question_raw)[:500],
        question_raw=question_raw[:500],
        sql=sql or None,
        entity_codes=entity_codes or [],
        route_type=route_type or "generic",
        engine=engine,
        example_type=example_type or "manual",
        status=status or "enabled",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    client = _safe_client()
    if client is not None:
        _upsert_qdrant(client, str(row.id), question_raw, sql or "", route_type, status or "enabled")
    return {"ok": True, "id": str(row.id)}


def list_qa_examples(
    db: Session,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> Dict[str, Any]:
    q = db.query(KgVerifiedQaExample)
    if status:
        q = q.filter(KgVerifiedQaExample.status == status)
    if keyword:
        q = q.filter(KgVerifiedQaExample.question_raw.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(KgVerifiedQaExample.created_at.desc()) \
            .offset(max(page - 1, 0) * size).limit(size).all()
    # S4a：30 天命中 = 近 30 天命中事件行数（一次分组聚合，按当前页示例 id）
    _cutoff = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    _page_ids = [str(r.id) for r in rows]
    _hit30: Dict[str, int] = {}
    if _page_ids:
        try:
            from sqlalchemy import func
            for _eid, _cnt in db.query(
                KgExampleHitLog.example_id, func.count(KgExampleHitLog.id),
            ).filter(
                KgExampleHitLog.example_id.in_(_page_ids),
                KgExampleHitLog.created_at >= _cutoff,
            ).group_by(KgExampleHitLog.example_id).all():
                _hit30[_eid] = int(_cnt)
        except Exception as _e:
            logger.warning(f"[QA示例库] 30 天命中统计失败（忽略）: {_e}")
    return {
        "total": total,
        "items": [{
            "id": str(r.id),
            "question_raw": r.question_raw,
            "question_norm": r.question_norm,
            "sql": r.sql,
            "entity_codes": r.entity_codes or [],
            "route_type": r.route_type,
            "engine": r.engine,
            "example_type": r.example_type,
            "status": r.status,
            "hit_count": r.hit_count,
            "hit_count_30d": _hit30.get(str(r.id), 0),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows],
    }


def find_similar_examples(db: Session, example_id: str, top: int = 5) -> List[Dict[str, Any]]:
    """S4a：Drawer 内 top-N 相似问题预览（带相似度）。

    以该示例的 question_raw 为查询向量检索 tupu_qa_examples（排除自身），
    返回 [{id, question_raw, score}]；Qdrant/向量不可用或示例不存在时返回 []（不抛）。
    """
    row = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == example_id).first()
    if not row:
        return []
    vec = _embed_question(db, row.question_raw)
    if not vec:
        return []
    client = _safe_client()
    if client is None:
        return []
    try:
        hits = client.search_points(
            QDRANT_COLLECTION_QA_EXAMPLES, vec,
            top=max(top * 2, 10), score_threshold=_score_threshold(),
        )
    except Exception as _e:
        logger.warning(f"[QA示例库] 相似检索失败（忽略）: {_e}")
        return []
    out: List[Dict[str, Any]] = []
    for h in hits:
        pid = str(h.get("id"))
        if pid == str(example_id):
            continue  # 排除自身
        payload = h.get("payload") or {}
        out.append({
            "id": pid,
            "question_raw": payload.get("question_raw", ""),
            "score": h.get("score"),
        })
        if len(out) >= top:
            break
    return out


def set_qa_example_status(db: Session, example_id: str, status: str) -> Dict[str, Any]:
    """启停示例（status=enabled/disabled）。同步更新 Qdrant payload.status。"""
    if status not in ("enabled", "disabled", "review"):
        return {"ok": False, "error": f"非法 status: {status}"}
    row = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == example_id).first()
    if not row:
        return {"ok": False, "error": f"示例不存在: {example_id}"}
    row.status = status
    db.commit()
    client = _safe_client()
    if client is not None:
        _upsert_qdrant(client, str(row.id), row.question_raw, row.sql or "", row.route_type or "", status)
    return {"ok": True, "id": str(row.id), "status": status}


def delete_qa_example(db: Session, example_id: str) -> Dict[str, Any]:
    """删除示例（DB 行 + Qdrant point + 命中事件行）。"""
    row = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == example_id).first()
    if not row:
        return {"ok": False, "error": f"示例不存在: {example_id}"}
    db.delete(row)
    db.query(KgExampleHitLog).filter(KgExampleHitLog.example_id == example_id).delete()
    db.commit()
    client = _safe_client()
    if client is not None:
        try:
            client.delete_points(QDRANT_COLLECTION_QA_EXAMPLES, [example_id])
        except Exception as _e:
            logger.warning(f"[QA示例库] Qdrant 删除点失败: {_e}")
    return {"ok": True, "id": example_id}


def bump_hit_count(db: Session, example_ids: List[str]) -> None:
    """命中计数（示例被注入后调用，容错）。

    S4a：除累计 hit_count + last_used_at 外，同步写 KgExampleHitLog 命中事件行
    （「30 天命中」统计源）。批量一次提交；失败静默不阻断问答。
    入参去重后处理（命中事件与累计计数保持一致；生产 hits 本已去重）。
    """
    _ids = list(dict.fromkeys(example_ids))
    if not _ids:
        return
    try:
        now = datetime.now(timezone.utc)
        rows = db.query(KgVerifiedQaExample).filter(
            KgVerifiedQaExample.id.in_(_ids)).all()
        for r in rows:
            r.hit_count = (r.hit_count or 0) + 1
            r.last_used_at = now
        for _eid in _ids:
            db.add(KgExampleHitLog(example_id=_eid))
        db.commit()
    except Exception as _e:
        logger.warning(f"[QA示例库] hit_count 更新失败（忽略）: {_e}")
