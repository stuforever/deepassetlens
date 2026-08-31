"""G1 验证示例库服务（融合设计 §4.1）——批13-C 运行时退役。

**批13-C 题库移除**：运行时契约组装/直通判定/自评豁免已全部切换金标体系
（golden_qa_service.retrieve_golden_bundle / build_golden_payload / bump_golden_hit，
runtime 键 example_hits -> golden_hits）；👍👎 改纯观测（KgFeedbackLog +
候选推荐队列），feedback_service 不再调用本服务；QA API（/api/v1/qa-examples）
已下线为 410 deprecation 壳。本模块保留 CRUD/检索原函数仅供历史数据迁移与
既有测试引用，**运行时路径零引用**；Qdrant tupu_qa_examples 集合退役脚本见
scripts/_retire_qa_examples.py。

历史功能（已不在运行时路径）：
- 语义检索：问题 embedding -> Qdrant 集合 tupu_qa_examples 检索 top-3（阈值 0.75，status=enabled）；
- 注入块：build_examples_block 供 _build_contract_system_message 尾部追加（仅供构造参考，禁止照抄执行）；
- CRUD：新增/列表/启停/删除（DB 行 + Qdrant point 同步）；
- 降级：Qdrant 或向量服务不可用时**静默跳过**（不阻断问答），沿用 qdrant_unavailable 降级模式。
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.base import KgExampleHitLog, KgVerifiedQaExample
from app.services.tupu_qdrant_client import TupuQdrantClient

logger = logging.getLogger(__name__)

QDRANT_COLLECTION_QA_EXAMPLES = "tupu_qa_examples"
_SCORE_THRESHOLD_DEFAULT = 0.75
_MAX_TOP = 3
# 批2-D：实体名核心词后缀剥离（「用电客户主数据」→「用电客户」；子串匹配问题主体词用）
_CORE_SUFFIX_RE = re.compile(r"(主数据|业务数据|资产主数据|台账|（.*?）|\(.*?\)|拉链表|信息表).*$")


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


# 批2-C 前置：计数问法同义归一化（让「统计用电客户数量」以 score=1.0 确定性命中「统计用电客户总数」示例）。
# 仅当问题不含条件/比较词时替换（「数量大于1000」这类带条件问法不归一化，防误直通 COUNT 全量）。
_COUNT_SYNONYM_REPL = {"数量": "总数", "多少个": "总数", "几个": "总数", "数目": "总数", "多少": "总数"}
_CONDITION_WORDS = ("大于", "超过", "以上", "以下", "高于", "低于", "不小于", "大于等于", "小于", "区间", "范围内", "大于", "多于")


def _count_normalize(text: str) -> str:
    """计数问法同义归一化：数量/多少个/几个/数目/多少 -> 总数（无条件词时，防误直通带条件问法）。"""
    t = str(text or "").strip()
    if any(w in t for w in _CONDITION_WORDS):
        return t
    for w, rep in _COUNT_SYNONYM_REPL.items():
        t = t.replace(w, rep)
    return t


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
    precomputed_vec: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """检索 top-N 已验证示例（status=enabled）。两级检索：

      Tier1（确定性保底）：DB 精确匹配 question_raw / question_norm == 问题（弱 embedding 环境下
            保证「同类问题二问」确定性命中，score=1.0）；
      Tier2（语义增强）：问题向量 -> Qdrant tupu_qa_examples 检索（阈值 0.75，按设计），补充不足 top 的部分。

    Qdrant/向量不可用时静默降级为仅 Tier1，不阻断问答。
    批7-E1：precomputed_vec 由 retrieve_context_bundle 传入（一次 embedding 双集合并搜）。
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
        # 批2-C 前置：计数问法同义归一化后的规范形（「统计用电客户数量」→「统计用电客户总数」，
        # 使 Tier1 确定性命中 score=1.0，触发 rubric 直通 + 首选计划，达成锚定≤25s）
        _norm_q_count = _count_normalize(_norm_q) or _norm_q
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
                KgVerifiedQaExample.question_norm.in_([_norm_q, _norm_q_count]),
            ).all()
        if not exact:
            exact = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.status == "enabled",
            ).all()
            exact = [r for r in exact if _norm_question(r.question_raw) in (_norm_q, _norm_q_count)
                     or (r.question_norm or "").strip() in (_norm_q, _norm_q_count)]
        for r in exact[:top]:
            results.append({
                "id": str(r.id), "score": 1.0,
                "question_raw": r.question_raw, "sql": r.sql or "",
                "route_type": r.route_type or "",
                "engine": r.engine or "",
            })
            seen.add(str(r.id))
    except Exception as _e:
        logger.warning(f"[QA示例库] Tier1 检索失败: {_e}")
    if len(results) >= top:
        return results[:top]
    # Tier2：语义检索补充（阈值环境变量化：TUPU_EXAMPLE_SIM_THRESHOLD，默认 0.75）。
    # 批2-C：检索 query 用计数同义归一化（「统计用电客户数量」→「统计用电客户总数」→ Qdrant score≈1.0 命中，
    # 因为同义计数问法在字符层与向量层都查不到原始「总数」示例；有条件词时不归一化）
    _retrieve_q = _count_normalize(question)
    vec = precomputed_vec if precomputed_vec else _embed_question(db, _retrieve_q)
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
            "engine": payload.get("engine", "") or "",
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


def build_entity_hint_block(db: Session, question: str, top: int = 3,
                            precomputed_vec: Optional[List[float]] = None) -> str:
    """批2-D 实体预解析：候选实体注入契约消息（省 search_entities 定位轮）。

    两步：
    1. 子串扫描（可靠）：实体名核心词（去「主数据/业务数据/（拉链表）」等后缀）在问题中出现即强相关
       ——完整问题句 embedding 与实体名的向量相似度普遍偏低（如「统计用电客户数量」vs「用电客户主数据」
       仅 0.25 甚至不出现在 top-50），子串匹配比向量更能定位「用电客户」这类主体词；
    2. 无子串命中退回向量检索 top-N（尽力而为）。
    Qdrant 不可用静默跳过（同示例降级语义），不阻断问答。
    注入格式：
      候选实体（语义检索 top-3，仅供参考，执行前仍按引擎规则确认源模式）：
      - 用电客户主数据（dim_cst_elec_cons_cust，评分 1.00）
    """
    q = (question or "").strip()
    if not q:
        return ""
    _picked: List[tuple] = []
    # 1) 子串扫描：实体集合点量小（~125），全量 scroll 一次 <100ms，远低于模型一次决策轮
    try:
        from app.services.entity_attr_vector_service import ENTITY_COLLECTION
        from app.services.tupu_qdrant_client import TupuQdrantClient
        _client = TupuQdrantClient()
        for p in list(_client.scroll_points(ENTITY_COLLECTION, limit=300)):
            _pl = p.get("payload") or {}
            _nm = _pl.get("entity_name") or ""
            _core = _CORE_SUFFIX_RE.sub("", _nm).strip()
            if _core and _core in q:
                _picked.append((_nm, _pl.get("entity_code") or "", 1.0))
            if len(_picked) >= top:
                break
    except Exception as _e:
        logger.warning(f"[实体预解析] 子串扫描失败（跳过）: {_e}")
    # 2) 无子串命中：退回向量检索（弱）；批7-E1 复用单入口预计算向量，避免二次 embedding
    if not _picked:
        try:
            from app.services.entity_attr_vector_service import search_entity_vectors
            _hits = search_entity_vectors(q, top_k=top * 3, db=db, vec=precomputed_vec)
        except Exception as _e2:
            logger.warning(f"[实体预解析] 向量检索失败（跳过）: {_e2}")
            _hits = []
        _picked = [(h.get("name") or "", h.get("code") or "", float(h.get("score") or 0)) for h in _hits[:top]]
    if not _picked:
        return ""
    lines = [
        "\n实体预解析（已定位主体实体，直接 batch_entity_source_mode 确认源模式后执行查询）：",
        "无需 fetch_l1_l2_tree / validate_l2 / fetch_subgraph 定位（问题主体实体已预解析）：",
    ]
    for _nm, _cd, _sc in _picked:
        lines.append(f"- {_nm}（{_cd}）")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 批7：检索单调用化 + 短窗缓存（问三）
# ---------------------------------------------------------------------------

# E2 短窗缓存：LRU {question_norm: (monotonic_ts, bundle)}，TTL=60s size=128——
# 重复提问/纠错重试免远程检索（embedding + Qdrant 双写开销各免一次）。
_BUNDLE_TTL_SECONDS = float(os.getenv("TUPU_BUNDLE_CACHE_TTL", "60"))
_BUNDLE_CACHE_SIZE = max(1, int(os.getenv("TUPU_BUNDLE_CACHE_SIZE", "128")))
try:
    from collections import OrderedDict as _OrderedDict
    _bundle_cache: "_OrderedDict[str, tuple]" = _OrderedDict()
except Exception:  # pragma: no cover
    _bundle_cache = {}


def clear_bundle_cache() -> None:
    """清空短窗缓存（管理/测试用）。"""
    _bundle_cache.clear()


def retrieve_context_bundle(db: Session, question: str, top_examples: int = _MAX_TOP,
                            top_entities: int = 3) -> Dict[str, Any]:
    """批7-E1 检索单入口：一次 embedding -> 并搜 tupu_qa_examples（示例 Tier2）与
    实体集合（实体提示向量退回路径），返回 {examples_block, example_hits, entity_hint_block}。

    - 短窗缓存（E2）：同规范化问题 TTL 内直接返回缓存 bundle，0 远程调用；
    - 降级与既有单函数一致：Qdrant/向量不可用静默跳过（不阻断问答）；
    - 调用方（_build_contract_system_message / 批9 直通判定）共享同一份命中结果。
    """
    key = _norm_question(question)
    now = datetime.now(timezone.utc).timestamp()
    if key:
        _hit = _bundle_cache.get(key)
        if _hit is not None:
            _ts, _bundle = _hit
            if now - _ts <= _BUNDLE_TTL_SECONDS:
                try:
                    _bundle_cache.move_to_end(key)
                except Exception:
                    pass
                return _bundle
            _bundle_cache.pop(key, None)
    # 单次 embedding：用计数同义归一化后的查询文本（与示例 Tier2 检索口径一致；
    # 实体提示为尽力而为的弱信号，复用同一向量即可）
    vec = _embed_question(db, _count_normalize(question))
    hits = search_qa_examples(db, question, top=top_examples, precomputed_vec=vec)
    block_lines: List[str] = []
    if hits:
        block_lines = ["\n参考示例（历史已验证查询，仅供构造 SQL 参考，禁止照抄执行）："]
        for i, ex in enumerate(hits, 1):
            block_lines.append(f"[示例{i}] 问题：{ex['question_raw']}")
            if ex.get("sql"):
                block_lines.append(f"        SQL：{ex['sql']}")
    entity_hint = build_entity_hint_block(db, question, top=top_entities, precomputed_vec=vec)
    bundle = {
        "examples_block": "\n".join(block_lines),
        "example_hits": hits,
        "entity_hint_block": entity_hint,
    }
    if key:
        try:
            _bundle_cache[key] = (now, bundle)
            _bundle_cache.move_to_end(key)
            while len(_bundle_cache) > _BUNDLE_CACHE_SIZE:
                _bundle_cache.popitem(last=False)
        except Exception:
            pass
    return bundle




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
