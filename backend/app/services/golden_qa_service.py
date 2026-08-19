# -*- coding: utf-8 -*-
"""golden_qa_service.py - 金标评估集服务（融合设计 §6.2 G6）

- KgGoldenQaSet：question -> expected_sql -> expected_result_digest（row_count + 首行 sha1）
- compute_result_digest：由真实执行结果计算 digest（比结果不比 SQL 文本）
- seed_golden：种子灌入（落地页示例问题 + 历史成功查询抽样），并兼以 example_type=golden
  灌入示例库（G1 冷启动即有数据）
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import KgGoldenQaSet, KgVerifiedQaExample, MetricQueryLog

logger = logging.getLogger(__name__)

# 种子最大容量（设计目标 50-100，以可执行真实查询为准，随历史增长）
SEED_MAX = 60

# 种子模板（落地页示例问题 + distribution-overload 场景 + 本会话已验证可复现的统计类问题）
# SQL 走真实引擎执行计算 digest；引擎按表归属：internal./test_db. -> doris internal，pg_tupu. -> doris 联邦，其余 -> physical
# 重要：agent 对「用电客户」经 search_entities 解析到 pg_tupu.public.dim_cst_elec_cons_cust（3 行 mock，
# 列 cust_id/cust_name/voltage_name/ctrt_cap/run_cap/impt_lv_name/bus_srv_addr_name）——种子期望 SQL 须与该
# 规范表一致，否则 eval 必然错（比结果不比 SQL，但表不一致 = 不同答案）。
SEED_TEMPLATES: List[Dict[str, str]] = [
    # 用电客户统计类（agent 规范表 pg_tupu.public.dim_cst_elec_cons_cust，源表 COUNT=3；
    # 注意：裸 COUNT(*) 会被预聚合加速器拦截返回陈旧值 10，故期望 SQL 用 WHERE cust_id IS NOT NULL
    # 绕过加速器取源真实值 3——加速器陈旧问题已记发布清单）
    {"question": "统计一下当前有多少用电客户", "expected_sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE cust_id IS NOT NULL",
     "route_type": "generic", "scenario_tag": "statistics"},
    {"question": "用电客户总数是多少", "expected_sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE cust_id IS NOT NULL",
     "route_type": "generic", "scenario_tag": "statistics"},
    {"question": "统计用电客户总数", "expected_sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE cust_id IS NOT NULL",
     "route_type": "generic", "scenario_tag": "statistics"},
    # 明细/清单类（与 agent 实际执行同形，保证同结果）
    {"question": "列出用电客户清单", "expected_sql": "SELECT cust_id, cust_name, voltage_name, ctrt_cap, run_cap, impt_lv_name, bus_srv_addr_name FROM pg_tupu.public.dim_cst_elec_cons_cust LIMIT 500",
     "route_type": "generic", "scenario_tag": "statistics"},
    # 分布负载场景（distribution-overload：电压等级分布——agent 须产出 GROUP BY 才通过）
    {"question": "各电压等级的用电客户分布是怎样的", "expected_sql": "SELECT voltage_name AS dim, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name ORDER BY cnt DESC",
     "route_type": "generic", "scenario_tag": "distribution-overload"},
]


def _uuid_str() -> str:
    return uuid.uuid4().hex


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
            from app.services.doris_engine import execute_sql as d_exec
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


def _feed_example_library(db: Session, question: str, sql: str, route_type: str) -> None:
    """金标兼以 example_type=golden 灌入示例库（G1 冷启动即有数据；已存在同问题不重复）。"""
    try:
        from app.services.qa_example_service import add_qa_example
    except Exception as e:
        logger.warning(f"[Golden] 示例库导入失败: {e}")
        return
    exists = db.query(KgVerifiedQaExample).filter(
        or_(KgVerifiedQaExample.question_raw == question,
            KgVerifiedQaExample.question_norm == question)).first()
    if exists:
        return
    try:
        add_qa_example(db, question_raw=question, sql=sql,
                       route_type=route_type, example_type="golden")
    except Exception as e:
        logger.warning(f"[Golden] 示例库写入失败: {e}")


def list_golden(db: Session, enabled_only: bool = False) -> List[Dict[str, Any]]:
    q = db.query(KgGoldenQaSet)
    if enabled_only:
        q = q.filter(KgGoldenQaSet.enabled == True)  # noqa: E712
    items = q.order_by(KgGoldenQaSet.created_at).all()
    return [{
        "id": g.id, "question": g.question, "expected_sql": g.expected_sql,
        "expected_result_digest": g.expected_result_digest, "route_type": g.route_type,
        "scenario_tag": g.scenario_tag, "enabled": g.enabled,
        "created_at": str(g.created_at) if g.created_at else None,
    } for g in items]


def add_golden(db: Session, *, question: str, expected_sql: str,
               expected_result_digest: Optional[Dict[str, Any]] = None,
               route_type: str = "generic", scenario_tag: Optional[str] = None,
               feed_example: bool = True) -> Dict[str, Any]:
    """新增金标。expected_result_digest 缺省时实时执行期望 SQL 计算（失败则拒绝入库）。"""
    question = (question or "").strip()
    if not question or not expected_sql:
        return {"ok": False, "error": "question/expected_sql 必填"}
    digest = expected_result_digest or _exec_for_digest(expected_sql)
    if not digest:
        return {"ok": False, "error": "期望 SQL 执行失败，无法计算 digest（请人工提供 expected_result_digest）"}
    row = KgGoldenQaSet(
        id=_uuid_str(), question=question[:500], expected_sql=expected_sql,
        expected_result_digest=digest, route_type=route_type, scenario_tag=scenario_tag,
        enabled=True,
    )
    db.add(row)
    db.commit()
    if feed_example:
        _feed_example_library(db, question, expected_sql, route_type)
    return {"ok": True, "id": row.id, "expected_result_digest": digest}


def set_golden_status(db: Session, golden_id: str, enabled: bool) -> Dict[str, Any]:
    row = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.id == golden_id).first()
    if not row:
        return {"ok": False, "error": "金标不存在"}
    row.enabled = bool(enabled)
    db.commit()
    return {"ok": True, "id": row.id, "enabled": row.enabled}


def delete_golden(db: Session, golden_id: str) -> Dict[str, Any]:
    row = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.id == golden_id).first()
    if not row:
        return {"ok": False, "error": "金标不存在"}
    db.delete(row)
    db.commit()
    return {"ok": True, "id": golden_id}


def seed_golden(db: Session, *, max_count: int = SEED_MAX) -> Dict[str, Any]:
    """种子：模板 + 历史成功 MetricQueryLog 抽样 -> 执行算 digest -> 入库 + 灌示例库。

    返回 {seeded, skipped, total}；幂等（同问题已存在跳过）。
    """
    existing_q = {g.question for g in db.query(KgGoldenQaSet).all()}
    seeded, skipped = 0, 0
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
        db.add(KgGoldenQaSet(
            id=_uuid_str(), question=q[:500], expected_sql=t["expected_sql"],
            expected_result_digest=digest, route_type=t.get("route_type", "generic"),
            scenario_tag=t.get("scenario_tag")))
        _feed_example_library(db, q, t["expected_sql"], t.get("route_type", "generic"))
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
        db.add(KgGoldenQaSet(
            id=_uuid_str(), question=q[:500], expected_sql=h.executed_sql,
            expected_result_digest=digest, route_type="generic",
            scenario_tag="historical"))
        _feed_example_library(db, q, h.executed_sql, "generic")
        existing_q.add(q)
        seeded += 1
    db.commit()
    total = db.query(KgGoldenQaSet).count()
    return {"ok": True, "seeded": seeded, "skipped": skipped, "total": total}
