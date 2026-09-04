# -*- coding: utf-8 -*-
"""golden_qa_service.py - 金标锚定体系（融合设计 §6.2 G6；批13-C 升级为运行时唯一锚定源）

核心变化（批13-C 题库移除落地）：
- 运行时契约组装不再查示例库（qa_example_service 退役）：build_golden_payload /
  retrieve_golden_bundle 直查金标（Tier1 精确 + Tier2 Qdrant tupu_golden_qa）；
- 金标向量化：增删改/种子同步 upsert Qdrant tupu_golden_qa 集合；
- 字段核对：engine 列（直通/锁引擎依据；NULL 按前缀推断回填，见 init_db._ensure_golden_columns）；
- 命中统计：hit_count + last_hit_at（bump_golden_hit，管理页可见）；
- 候选推荐：KgFeedbackLog（👍👎 纯观测表）近 N 天按问题聚合且金标无覆盖 TopM；
- 金标不再以 example_type=golden 灌示例库（_feed_example_library 移除）。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import KgGoldenQaSet, KgFeedbackLog, MetricQueryLog

logger = logging.getLogger(__name__)

# 种子最大容量（设计目标 50-100，以可执行真实查询为准，随历史增长）
SEED_MAX = 60

# 批13-C：金标向量集合（与退役的 tupu_qa_examples 独立；增删改同步）
GOLDEN_COLLECTION = "tupu_golden_qa"
_SCORE_THRESHOLD_DEFAULT = 0.75
_MAX_TOP = 3
# 批2-D：实体名核心词后缀剥离（「用电客户主数据」→「用电客户」；子串匹配问题主体词用）——
# 实体提示与示例库无关，随 retrieve_golden_bundle 一并保留（从 qa_example_service 搬迁）
_CORE_SUFFIX_RE = re.compile(r"(主数据|业务数据|资产主数据|台账|（.*?）|\(.*?\)|拉链表|信息表).*$")

# 批2-C：计数问法同义归一化（「统计用电客户数量」→「统计用电客户总数」确定性命中金标 score=1.0）
_COUNT_SYNONYM_REPL = {"数量": "总数", "多少个": "总数", "几个": "总数", "数目": "总数", "多少": "总数"}
_CONDITION_WORDS = ("大于", "超过", "以上", "以下", "高于", "低于", "不小于", "大于等于", "小于", "区间", "范围内", "多于")


def _score_threshold() -> float:
    try:
        return float(os.getenv("TUPU_GOLDEN_SIM_THRESHOLD", str(_SCORE_THRESHOLD_DEFAULT)))
    except Exception:
        return _SCORE_THRESHOLD_DEFAULT


def _norm_question(text: Any) -> str:
    """规范化问题（复用标准语义词条管线的 normalize_text）：NFKC + 去空白/标点 + 小写。"""
    try:
        from app.services.query_entity_utils import normalize_text
        return normalize_text(text)
    except Exception:
        return str(text or "").strip()


def _count_normalize(text: str) -> str:
    """计数问法同义归一化：数量/多少个/几个/数目/多少 -> 总数（无条件词时，防误直通带条件问法）。"""
    t = str(text or "").strip()
    if any(w in t for w in _CONDITION_WORDS):
        return t
    for w, rep in _COUNT_SYNONYM_REPL.items():
        t = t.replace(w, rep)
    return t


def _infer_engine(sql: str) -> str:
    """按 SQL 前缀推断引擎（与 golden digest 执行路由同口径）：Doris 联邦目录 -> doris，其余 physical。"""
    s = str(sql or "")
    return "doris" if any(k in s for k in ("internal.", "test_db.", "pg_tupu.")) else "physical"


def _uuid_str() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# digest / seed（eval 与冷启动）
# ---------------------------------------------------------------------------

def compute_result_digest(rows: List[Any], row_count: int) -> Dict[str, Any]:
    """由真实结果计算 digest：{row_count, first_row_hash, first_row}。

    比结果不比 SQL 文本（同结果不同写法算对）；first_row 存实值供 eval 标量宽松比对
    （COUNT 类期望单值，agent 以明细行数作答同属正确答案）。
    """
    first = None
    if rows:
        first = rows[0]
        try:
            json.dumps(first)
        except Exception:
            first = str(first)
    h = hashlib.sha1(json.dumps(first, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:16] if first is not None else ""
    return {"row_count": int(row_count or 0), "first_row_hash": h, "first_row": first}


def _exec_for_digest(sql: str) -> Optional[Dict[str, Any]]:
    """执行期望 SQL 计算 digest；失败返回 None（不灌坏种子）。

    引擎路由与 agent 一致：Doris 3 段名（internal./test_db./pg_tupu. 联邦目录）走 doris_engine，
    其余走 physical（PG）。关键：agent 对「用电客户」经 Doris pg_tupu 目录查 3 行 mock，
    physical 直连 PG 的 tupu 库同名表有 10 行——路由错则种子 digest 与 agent 实际结果不一致。
    """
    try:
        if any(k in sql for k in ("internal.", "test_db.", "pg_tupu.")):
            from app.services.doris_engine import execute_doris_query as d_exec
            res = d_exec(sql, catalog=None)
        else:
            from app.services.sql_executor import build_execute_query_fn
            res = build_execute_query_fn()(sql)
    except Exception as e:
        logger.warning(f"[Golden] 种子 SQL 执行失败: {e}")
        return None
    if not isinstance(res, dict) or res.get("error"):
        return None
    rows = res.get("rows") or []
    return compute_result_digest(rows, res.get("row_count") or len(rows))


# 种子模板（落地页示例问题 + distribution-overload 场景 + 本会话已验证可复现的统计类问题）
SEED_TEMPLATES: List[Dict[str, str]] = [
    {"question": "统计一下当前有多少用电客户", "expected_sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE cust_id IS NOT NULL",
     "route_type": "generic", "scenario_tag": "statistics"},
    {"question": "用电客户总数是多少", "expected_sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE cust_id IS NOT NULL",
     "route_type": "generic", "scenario_tag": "statistics"},
    {"question": "统计用电客户总数", "expected_sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE cust_id IS NOT NULL",
     "route_type": "generic", "scenario_tag": "statistics"},
    {"question": "列出用电客户清单", "expected_sql": "SELECT cust_id, cust_name, voltage_name, ctrt_cap, run_cap, impt_lv_name, bus_srv_addr_name FROM pg_tupu.public.dim_cst_elec_cons_cust LIMIT 500",
     "route_type": "generic", "scenario_tag": "statistics"},
    {"question": "各电压等级的用电客户分布是怎样的", "expected_sql": "SELECT voltage_name AS dim, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name ORDER BY cnt DESC",
     "route_type": "generic", "scenario_tag": "distribution-overload"},
]


def list_golden(db: Session, enabled_only: bool = False) -> List[Dict[str, Any]]:
    q = db.query(KgGoldenQaSet)
    if enabled_only:
        q = q.filter(KgGoldenQaSet.enabled == True)  # noqa: E712
    items = q.order_by(KgGoldenQaSet.created_at).all()
    return [{
        "id": g.id, "question": g.question, "expected_sql": g.expected_sql,
        "expected_result_digest": g.expected_result_digest, "route_type": g.route_type,
        "scenario_tag": g.scenario_tag, "enabled": g.enabled,
        "engine": g.engine, "hit_count": g.hit_count or 0, "last_hit_at": str(g.last_hit_at) if g.last_hit_at else None,
        "created_at": str(g.created_at) if g.created_at else None,
    } for g in items]


def add_golden(db: Session, *, question: str, expected_sql: str,
               expected_result_digest: Optional[Dict[str, Any]] = None,
               route_type: str = "generic", scenario_tag: Optional[str] = None,
               engine: Optional[str] = None) -> Dict[str, Any]:
    """新增金标（批13-C：同步 Qdrant tupu_golden_qa；不再灌示例库）。"""
    question = (question or "").strip()
    if not question or not expected_sql:
        return {"ok": False, "error": "question/expected_sql 必填"}
    digest = expected_result_digest or _exec_for_digest(expected_sql)
    if not digest:
        return {"ok": False, "error": "期望 SQL 执行失败，无法计算 digest（请人工提供 expected_result_digest）"}
    row = KgGoldenQaSet(
        id=_uuid_str(), question=question[:500], expected_sql=expected_sql,
        expected_result_digest=digest, route_type=route_type, scenario_tag=scenario_tag,
        engine=engine or _infer_engine(expected_sql), enabled=True,
    )
    db.add(row)
    db.commit()
    _sync_golden_qdrant(row.id, question, expected_sql, row.engine, True)
    return {"ok": True, "id": row.id, "expected_result_digest": digest}


def set_golden_status(db: Session, golden_id: str, enabled: bool) -> Dict[str, Any]:
    row = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.id == golden_id).first()
    if not row:
        return {"ok": False, "error": "金标不存在"}
    row.enabled = bool(enabled)
    db.commit()
    _sync_golden_qdrant(row.id, row.question, row.expected_sql or "", row.engine, row.enabled)
    return {"ok": True, "id": row.id, "enabled": row.enabled}


def delete_golden(db: Session, golden_id: str) -> Dict[str, Any]:
    row = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.id == golden_id).first()
    if not row:
        return {"ok": False, "error": "金标不存在"}
    db.delete(row)
    db.commit()
    _delete_golden_qdrant(golden_id)
    return {"ok": True, "id": golden_id}


def seed_golden(db: Session, *, max_count: int = SEED_MAX) -> Dict[str, Any]:
    """种子：模板 + 历史成功 MetricQueryLog 抽样 -> 执行算 digest -> 入库 + Qdrant 同步。

    返回 {seeded, skipped, total}；幂等（同问题已存在跳过）。批13-C：不再灌示例库。
    """
    existing_q = {g.question for g in db.query(KgGoldenQaSet).all()}
    seeded, skipped = 0, 0
    _new_rows: List[KgGoldenQaSet] = []
    # 1) 模板种子
    for t in SEED_TEMPLATES:
        if seeded >= max_count:
            break
        q = t["question"]
        if q in existing_q:
            skipped += 1
            continue
        digest = _exec_for_digest(t["expected_sql"])
        if not digest:
            skipped += 1
            continue
        row = KgGoldenQaSet(
            id=_uuid_str(), question=q[:500], expected_sql=t["expected_sql"],
            expected_result_digest=digest, route_type=t.get("route_type", "generic"),
            scenario_tag=t.get("scenario_tag"), engine=_infer_engine(t["expected_sql"]))
        db.add(row)
        _new_rows.append(row)
        existing_q.add(q)
        seeded += 1
    # 2) 历史成功查询抽样（MetricQueryLog 有 user_query + executed_sql 且已成功）
    hist = db.query(MetricQueryLog).filter(
        MetricQueryLog.query_status == "success",
        MetricQueryLog.user_query.isnot(None),
        MetricQueryLog.executed_sql.isnot(None),
    ).order_by(MetricQueryLog.created_at.desc()).limit(60).all()
    for h in hist:
        if seeded >= max_count:
            break
        q = (h.user_query or "").strip()
        if not q or q in existing_q or len(q) > 200:
            skipped += 1
            continue
        digest = _exec_for_digest(h.executed_sql)
        if not digest:
            skipped += 1
            continue
        row = KgGoldenQaSet(
            id=_uuid_str(), question=q[:500], expected_sql=h.executed_sql,
            expected_result_digest=digest, route_type="generic",
            scenario_tag="historical", engine=_infer_engine(h.executed_sql))
        db.add(row)
        _new_rows.append(row)
        existing_q.add(q)
        seeded += 1
    db.commit()
    # 批13-C：新种子同步向量（commit 后执行，避免事务内网络调用拖长锁）
    for row in _new_rows:
        _sync_golden_qdrant(row.id, row.question, row.expected_sql or "", row.engine, True)
    total = db.query(KgGoldenQaSet).count()
    return {"ok": True, "seeded": seeded, "skipped": skipped, "total": total}


# ---------------------------------------------------------------------------
# 批13-C：Qdrant tupu_golden_qa 同步（增删改/种子）
# ---------------------------------------------------------------------------

def _safe_client():
    """健康检查通过的 Qdrant client；不可用返回 None（不抛）。"""
    try:
        from app.services.tupu_qdrant_client import is_qdrant_backend_enabled, TupuQdrantClient
        if not is_qdrant_backend_enabled():
            return None
        client = TupuQdrantClient()
        if not client.healthcheck():
            return None
        return client
    except Exception as _e:
        logger.warning(f"[Golden] Qdrant 不可用（跳过向量操作）: {_e}")
        return None


def _embed_question(db: Session, question: str) -> List[float]:
    """问题向量化；失败返回 []（调用方据此静默跳过检索/同步）。"""
    try:
        from app.services.semantic_retrieval import embed_texts
        vecs = embed_texts(db, [question])
        if vecs and vecs[0]:
            return [float(x) for x in vecs[0]]
    except Exception as _e:
        logger.warning(f"[Golden] 向量化失败: {_e}")
    return []


def _sync_golden_qdrant(golden_id: str, question: str, sql: str,
                        engine: Optional[str], enabled: bool) -> None:
    """金标向量 upsert 进 tupu_golden_qa（集合缺失则按实际维度创建）。失败仅告警不阻断。"""
    client = _safe_client()
    if client is None:
        return
    try:
        from app.core.database import SessionLocal
        _db = SessionLocal()
        try:
            vec = _embed_question(_db, question)
        finally:
            _db.close()
        if not vec:
            logger.warning(f"[Golden] 金标 {golden_id} 向量化失败，跳过 Qdrant upsert")
            return
        _dim = len(vec)
        try:
            client.ensure_collection(GOLDEN_COLLECTION, _dim)
        except Exception as _ce:
            try:
                if client.count_points(GOLDEN_COLLECTION) == 0:
                    client.ensure_collection(GOLDEN_COLLECTION, _dim, recreate=True)
                else:
                    logger.warning(f"[Golden] 集合维度不匹配且非空，跳过 upsert: {_ce}")
                    return
            except Exception:
                logger.warning(f"[Golden] 集合创建失败（跳过 upsert）: {_ce}")
                return
        client.upsert_points(GOLDEN_COLLECTION, [{
            "id": golden_id,
            "vector": vec,
            "payload": {"question_raw": question, "sql": sql or "",
                        "engine": engine or "", "enabled": bool(enabled)},
        }])
    except Exception as _e:
        logger.warning(f"[Golden] Qdrant upsert 失败（DB 已写入，向量暂缺）: {_e}")


def _delete_golden_qdrant(golden_id: str) -> None:
    client = _safe_client()
    if client is None:
        return
    try:
        client.delete_points(GOLDEN_COLLECTION, [golden_id])
    except Exception as _e:
        logger.warning(f"[Golden] Qdrant 删除点失败: {_e}")


# ---------------------------------------------------------------------------
# 批13-C：运行时锚定检索（契约组装切源：example_hits -> golden_hits）
# ---------------------------------------------------------------------------

def search_golden_qa(db: Session, question: str, top: int = _MAX_TOP,
                     precomputed_vec: Optional[List[float]] = None) -> List[Dict[str, Any]]:
    """检索金标 top-N（enabled 且 expected_sql 非空）。两级检索：

      Tier1（确定性保底）：DB 全量金标（≤百行级）Python 规范化比对——question_norm ==
            规范化输入（含计数同义归一化口径），score=1.0（弱 embedding 环境下保证
            「同类问题二问」确定性命中）；
      Tier2（语义增强）：问题向量 -> Qdrant tupu_golden_qa 检索（阈值默认 0.75）。
    Qdrant/向量不可用时静默降级为仅 Tier1，不阻断问答。
    """
    question = (question or "").strip()
    if not question:
        return []
    results: List[Dict[str, Any]] = []
    seen: set = set()
    # Tier1：规范化精确匹配（含计数归一口径）
    try:
        _norm_q = _norm_question(question)
        _norm_q_count = _count_normalize(_norm_q) or _norm_q
        rows = db.query(KgGoldenQaSet).filter(
            KgGoldenQaSet.enabled == True,  # noqa: E712
            KgGoldenQaSet.expected_sql.isnot(None),
        ).all()
        exact = [r for r in rows
                 if _norm_question(r.question) in (_norm_q, _norm_q_count)]
        for r in exact[:top]:
            results.append({
                "id": str(r.id), "score": 1.0,
                "question_raw": r.question, "sql": r.expected_sql or "",
                "route_type": r.route_type or "",
                "engine": (r.engine or "") or _infer_engine(r.expected_sql or ""),
            })
            seen.add(str(r.id))
    except Exception as _e:
        logger.warning(f"[Golden] Tier1 检索失败: {_e}")
    if len(results) >= top:
        return results[:top]
    # Tier2：语义检索补充（检索 query 用计数同义归一化口径，与示例库时代一致）
    _retrieve_q = _count_normalize(question)
    vec = precomputed_vec if precomputed_vec else _embed_question(db, _retrieve_q)
    if not vec:
        return results
    client = _safe_client()
    if client is None:
        return results
    try:
        hits = client.search_points(
            GOLDEN_COLLECTION, vec,
            top=max(top * 3, 10), score_threshold=_score_threshold(),
        )
    except Exception as _e:
        logger.warning(f"[Golden] Qdrant 检索失败（降级为仅 Tier1）: {_e}")
        return results
    for h in hits:
        payload = h.get("payload") or {}
        if not payload.get("enabled", True):
            continue
        pid = str(h.get("id"))
        if pid in seen:
            continue
        # payload enabled 快照可能与 DB 漂移（启用态变更先落 DB）；以 DB 为准复核
        try:
            row = db.query(KgGoldenQaSet).filter(
                KgGoldenQaSet.id == pid,
                KgGoldenQaSet.enabled == True,  # noqa: E712
            ).first()
        except Exception:
            row = None
        if row is None:
            continue
        results.append({
            "id": pid,
            "score": h.get("score"),
            "question_raw": payload.get("question_raw") or row.question,
            "sql": payload.get("sql") or row.expected_sql or "",
            "route_type": row.route_type or "",
            "engine": (row.engine or "") or _infer_engine(row.expected_sql or ""),
        })
        seen.add(pid)
        if len(results) >= top:
            break
    return results[:top]


def build_golden_payload(db: Session, question: str, top: int = _MAX_TOP,
                         precomputed_vec: Optional[List[float]] = None) -> Dict[str, Any]:
    """构造金标锚定负载：{block: str, hits: [{id, score, question_raw, sql, engine}]}。

    无命中/降级时 block 为空串、hits 为空列表（不阻断问答）。形状与旧
    build_examples_payload 一致（调用方只换函数名与 runtime 键）。
    """
    hits = search_golden_qa(db, question, top=top, precomputed_vec=precomputed_vec)
    if not hits:
        return {"block": "", "hits": []}
    lines = ["\n金标锚定（已验证查询，仅供构造参考，禁止照抄执行）："]
    for i, ex in enumerate(hits, 1):
        lines.append(f"[金标{i}] 问题：{ex['question_raw']}")
        if ex.get("sql"):
            lines.append(f"        SQL：{ex['sql']}")
    return {"block": "\n".join(lines), "hits": hits}


# ---------------------------------------------------------------------------
# 检索单调用化 + 短窗缓存（沿用批7-E1/E2 设计；实体提示一并保留）
# ---------------------------------------------------------------------------

_BUNDLE_TTL_SECONDS = float(os.getenv("TUPU_BUNDLE_CACHE_TTL", "60"))
_BUNDLE_CACHE_SIZE = max(1, int(os.getenv("TUPU_BUNDLE_CACHE_SIZE", "128")))
_bundle_cache: "OrderedDict[str, tuple]" = OrderedDict()


def clear_bundle_cache() -> None:
    """清空短窗缓存（管理/测试用）。"""
    _bundle_cache.clear()


def build_entity_hint_block(db: Session, question: str, top: int = 3,
                            precomputed_vec: Optional[List[float]] = None) -> str:
    """批2-D 实体预解析：候选实体注入契约消息（省 search_entities 定位轮）。

    两步：1) 子串扫描（可靠，实体集合点量小全量 scroll 一次 <100ms）；
    2) 无子串命中退回向量检索 top-N（尽力而为）。Qdrant 不可用静默跳过，不阻断问答。
    """
    q = (question or "").strip()
    if not q:
        return ""
    _picked: List[tuple] = []
    # 1) 子串扫描
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
    # 2) 无子串命中：退回向量检索（弱）——批13-G 件2：相似度阈值过滤（防低相似错挂，
    #    对齐 13-H 混合检索 0.6 阈值；13-M 错挂事故教训：宁缺勿错，无高相似候选则不预解析）
    if not _picked:
        try:
            from app.services.entity_attr_vector_service import search_entity_vectors
            _hits = search_entity_vectors(q, top_k=top * 3, db=db, vec=precomputed_vec)
        except Exception as _e2:
            logger.warning(f"[实体预解析] 向量检索失败（跳过）: {_e2}")
            _hits = []
        _picked = [(h.get("name") or "", h.get("code") or "", float(h.get("score") or 0))
                   for h in _hits if float(h.get("score") or 0) >= 0.6][:top]
    if not _picked:
        return ""
    lines = [
        "\n实体预解析（已定位主体实体，直接 batch_entity_source_mode 确认源模式后执行查询）：",
        "无需 fetch_l1_l2_tree / validate_l2 / fetch_subgraph 定位（问题主体实体已预解析）：",
    ]
    for _nm, _cd, _sc in _picked:
        lines.append(f"- {_nm}（{_cd}）")
    return "\n".join(lines)


def retrieve_golden_bundle(db: Session, question: str, top_golden: int = _MAX_TOP,
                           top_entities: int = 3) -> Dict[str, Any]:
    """批13-C 检索单入口（替代 qa_example_service.retrieve_context_bundle）：
    一次 embedding -> 并搜 tupu_golden_qa（Tier2）与实体集合（实体提示退回路径），
    返回 {golden_block, golden_hits, entity_hint_block}。

    - 短窗缓存（E2 沿用）：同规范化问题 TTL 内直接返回缓存 bundle，0 远程调用；
    - 降级语义不变：Qdrant/向量不可用静默跳过（不阻断问答）；
    - 调用方（契约组装/批9 直通判定/自评豁免）共享同一份 golden_hits。
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
    # 单次 embedding：计数同义归一化后的查询文本（与金标 Tier2 检索口径一致）
    vec = _embed_question(db, _count_normalize(question))
    payload = build_golden_payload(db, question, top=top_golden, precomputed_vec=vec)
    entity_hint = build_entity_hint_block(db, question, top=top_entities, precomputed_vec=vec)
    bundle = {
        "golden_block": payload["block"],
        "golden_hits": payload["hits"],
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


def bump_golden_hit(db: Session, golden_ids: List[str]) -> None:
    """金标命中计数（注入/直通后调用，容错）：hit_count+1 + last_hit_at。"""
    _ids = list(dict.fromkeys(golden_ids))
    if not _ids:
        return
    try:
        now = datetime.now(timezone.utc)
        rows = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.id.in_(_ids)).all()
        for r in rows:
            r.hit_count = (r.hit_count or 0) + 1
            r.last_hit_at = now
        db.commit()
    except Exception as _e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning(f"[Golden] hit_count 更新失败（忽略）: {_e}")


# ---------------------------------------------------------------------------
# 批13-C：候选推荐队列（👍👎 纯观测聚合）
# ---------------------------------------------------------------------------

def list_candidate_recommendations(db: Session, days: int = 7, top_m: int = 10) -> List[Dict[str, Any]]:
    """近 N 天高频反馈且无金标覆盖的问题 TopM（管理页「候选推荐」页签）。

    聚合口径（Python 端，观测表量小）：按规范化问题分组 -> {question 展示串, up_count,
    down_count, total, last_seen, latest_sql 存证}；排序：up 多者优先、其次 total；
    过滤：已有金标覆盖（规范化/计数归一化相等）的问题不重复推荐。
    """
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = db.query(KgFeedbackLog).filter(KgFeedbackLog.created_at >= since).all()
    except Exception as _e:
        logger.warning(f"[Golden] 候选推荐查询失败: {_e}")
        return []
    grouped: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        q = (r.question or "").strip()
        if not q:
            continue
        k = _count_normalize(_norm_question(q)) or _norm_question(q)
        g = grouped.setdefault(k, {
            "question": q, "up_count": 0, "down_count": 0, "total": 0,
            "last_seen": None, "latest_sql": "",
        })
        if (r.verdict or "").lower() == "up":
            g["up_count"] += 1
        elif (r.verdict or "").lower() == "down":
            g["down_count"] += 1
        g["total"] += 1
        _ts = r.created_at
        if _ts and (g["last_seen"] is None or _ts > g["last_seen"]):
            g["last_seen"] = _ts
        sql = (r.corrected_sql or r.sql or "").strip()
        if sql:
            g["latest_sql"] = sql
    if not grouped:
        return []
    # 排除已有金标覆盖（规范化相等）
    covered: set = set()
    try:
        for g_row in db.query(KgGoldenQaSet.question).all():
            _nq = _norm_question(g_row[0])
            covered.add(_nq)
            covered.add(_count_normalize(_nq))
    except Exception as _e2:
        logger.warning(f"[Golden] 候选推荐金标覆盖过滤失败（不过滤）: {_e2}")
    out = [g for k, g in grouped.items() if k not in covered]
    out.sort(key=lambda g: (g["up_count"], g["total"]), reverse=True)
    for g in out:
        if g["last_seen"] is not None:
            g["last_seen"] = str(g["last_seen"])
    return out[:top_m]


def record_feedback(db: Session, *, run_id: Optional[str], verdict: str,
                    question: str = "", sql: str = "",
                    corrected_sql: str = "", comment: str = "") -> Dict[str, Any]:
    """批13-C：反馈落观测表（唯一写路径；不再写示例库）。"""
    try:
        row = KgFeedbackLog(
            id=_uuid_str(), run_id=(run_id or "")[:64] or None,
            verdict=(verdict or "").strip().lower(),
            question=(question or "")[:500], sql=sql or "",
            corrected_sql=corrected_sql or "", comment=comment or "")
        db.add(row)
        db.commit()
        return {"ok": True, "id": row.id}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning(f"[Feedback] 观测记录失败: {e}")
        return {"ok": False, "error": str(e)}
