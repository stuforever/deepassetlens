# -*- coding: utf-8 -*-
"""engine_accelerator.py - 预聚合加速器（P5）

把高频聚合物化到 Doris internal 表（INSERT OVERWRITE / CREATE TABLE AS 刷新），
对同形单值聚合 SQL 做平台层拦截（模型不自行改写，平台拦截），命中返回并标注
「数据截至 HH:MM（预聚合，TTL N 分钟）」。

- try_serve(sql)         单值聚合拦截：SELECT COUNT(*) FROM src -> 预聚合表服务
- refresh_accelerator    刷新目标表（表不存在则 CREATE TABLE AS；存在则 INSERT OVERWRITE）
- refresh_due_all        按 refresh_minutes 到期批量刷新（TaskWorker 周期调用）
- list/create/update/delete  CRUD
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import sqlglot
from sqlglot import exp

from app.core.database import SessionLocal
from app.models.base import EngineAccelerator

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #

def _row_to_dict(acc: EngineAccelerator) -> Dict[str, Any]:
    return {
        "id": acc.id, "name": acc.name, "description": acc.description,
        "source_tables": acc.source_tables or [],
        "agg_expr": acc.agg_expr, "agg_col": acc.agg_col,
        "target_catalog": acc.target_catalog, "target_db": acc.target_db,
        "target_table": acc.target_table,
        "refresh_sql": acc.refresh_sql, "refresh_minutes": acc.refresh_minutes,
        "staleness_note": acc.staleness_note, "enabled": acc.enabled,
        "last_refresh_at": acc.last_refresh_at.isoformat() if acc.last_refresh_at else None,
        "last_status": acc.last_status, "last_error": acc.last_error,
        "created_at": acc.created_at.isoformat() if acc.created_at else None,
    }


def list_accelerators(enabled_only: bool = False) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = db.query(EngineAccelerator)
        if enabled_only:
            q = q.filter(EngineAccelerator.enabled.is_(True))
        return [_row_to_dict(a) for a in q.order_by(EngineAccelerator.created_at).all()]
    finally:
        db.close()


def create_accelerator(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        acc = EngineAccelerator(
            name=payload["name"],
            description=payload.get("description"),
            source_tables=list(payload.get("source_tables") or []),
            agg_expr=payload.get("agg_expr"),
            agg_col=payload.get("agg_col"),
            target_catalog=payload.get("target_catalog") or "internal",
            target_db=payload.get("target_db") or "test_db",
            target_table=payload["target_table"],
            refresh_sql=payload["refresh_sql"],
            refresh_minutes=int(payload.get("refresh_minutes") or 60),
            staleness_note=bool(payload.get("staleness_note", True)),
            enabled=bool(payload.get("enabled", True)),
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        return _row_to_dict(acc)
    finally:
        db.close()


def update_accelerator(acc_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        acc = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_id).first()
        if not acc:
            return None
        for k in ("name", "description", "agg_expr", "agg_col", "target_catalog", "target_db",
                  "target_table", "refresh_sql", "refresh_minutes", "staleness_note", "enabled"):
            if k in payload:
                setattr(acc, k, payload[k])
        if "source_tables" in payload:
            acc.source_tables = list(payload["source_tables"] or [])
        db.commit()
        db.refresh(acc)
        return _row_to_dict(acc)
    finally:
        db.close()


def delete_accelerator(acc_id: str) -> bool:
    db = SessionLocal()
    try:
        acc = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_id).first()
        if not acc:
            return False
        db.delete(acc)
        db.commit()
        return True
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 新鲜度
# --------------------------------------------------------------------------- #

def _is_fresh(acc: EngineAccelerator, now: Optional[datetime] = None) -> bool:
    if not acc.last_refresh_at:
        return False
    now = now or datetime.now()
    try:
        import pytz
        from datetime import timezone
        # 兼容 aware/naive 混用
        last = acc.last_refresh_at
        n = now
        if last.tzinfo is None and n.tzinfo is not None:
            last = last.replace(tzinfo=n.tzinfo)
        elif last.tzinfo is not None and n.tzinfo is None:
            n = n.replace(tzinfo=last.tzinfo)
        age_minutes = (n - last).total_seconds() / 60.0
        return age_minutes <= int(acc.refresh_minutes or 60)
    except Exception:
        return True


def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    try:
        return dt.strftime("%H:%M")
    except Exception:
        return str(dt)


# --------------------------------------------------------------------------- #
# 单值聚合拦截
# --------------------------------------------------------------------------- #

def _norm_agg(expr) -> Optional[str]:
    try:
        return expr.sql(dialect="duckdb").upper().strip()
    except Exception:
        return None


def try_serve(sql: str) -> Optional[Dict[str, Any]]:
    """单值聚合加速器拦截。

    SELECT COUNT(*)[/SUM(col)/AVG/MIN/MAX] FROM <src> 且无 WHERE/GROUP BY/JOIN：
    命中新鲜启用的加速器 -> 用预聚合表服务（Doris 亚秒返回），结果附
    accelerator / data_as_of / accelerated 标注。否则返回 None（走原执行路径）。
    """
    try:
        ast = sqlglot.parse_one(sql)
    except Exception:
        return None
    if not isinstance(ast, exp.Select):
        return None
    if ast.args.get("where") or ast.args.get("joins") or ast.args.get("group") or ast.args.get("limit"):
        return None
    froms = list(ast.find_all(exp.From))
    if len(froms) != 1:
        return None
    src = froms[0].this
    if not isinstance(src, exp.Table):
        return None
    src_name = src.name
    exprs = list(ast.expressions)
    if len(exprs) != 1:
        return None
    sel = exprs[0]
    alias = None
    if isinstance(sel, exp.Alias):
        alias = sel.alias
        sel = sel.this
    agg_str = _norm_agg(sel)
    if not agg_str or not isinstance(sel, (exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max)):
        return None

    db = SessionLocal()
    try:
        acc = db.query(EngineAccelerator).filter(
            EngineAccelerator.enabled.is_(True),
            EngineAccelerator.agg_expr.isnot(None),
        ).all()
        hit = None
        for a in acc:
            if agg_str == str(a.agg_expr).upper().strip() and src_name in (a.source_tables or []):
                hit = a
                break
        if not hit or not _is_fresh(hit):
            return None
        if not hit.agg_col:
            return None
        target_sql = f"SELECT `{hit.agg_col}` AS `{alias or 'n'}` FROM `{hit.target_db}`.`{hit.target_table}`"
    finally:
        db.close()

    from app.services import doris_engine
    res = doris_engine.execute_sql(target_sql)
    if res.get("error"):
        return None
    res["accelerated"] = True
    res["accelerator"] = {
        "name": hit.name,
        "target_table": f"{hit.target_db}.{hit.target_table}",
        "agg_expr": hit.agg_expr,
        "staleness_note": hit.staleness_note,
    }
    res["data_as_of"] = _fmt_dt(hit.last_refresh_at)
    res["data_snapshot_at"] = res["data_as_of"]
    return res


# --------------------------------------------------------------------------- #
# 刷新
# --------------------------------------------------------------------------- #

def refresh_accelerator(acc_id: str) -> Dict[str, Any]:
    """刷新加速器目标表：存在 -> INSERT OVERWRITE；不存在 -> CREATE TABLE AS。"""
    db = SessionLocal()
    try:
        acc = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_id).first()
        if not acc:
            return {"ok": False, "error": "加速器不存在"}
        from app.services import doris_engine
        conn = doris_engine.get_conn()
        try:
            cur = conn.cursor()
            select_sql = (acc.refresh_sql or "").strip().rstrip(";")
            db_name = acc.target_db
            tbl = acc.target_table
            try:
                cur.execute(f"INSERT OVERWRITE TABLE `{db_name}`.`{tbl}` {select_sql}")
            except Exception as e:
                # 目标表尚不存在 -> CREATE TABLE AS（幂等）；单 BE 集群需显式 replication_num=1
                logger.info(f"[Accelerator] {tbl} 不存在，改用 CREATE TABLE AS: {str(e)[:80]}")
                cur.execute(f"DROP TABLE IF EXISTS `{db_name}`.`{tbl}`")
                cur.execute(f'CREATE TABLE `{db_name}`.`{tbl}` PROPERTIES("replication_num"="1") AS {select_sql}')
            try:
                conn.commit()
            except Exception:
                pass
            acc.last_status = "ok"
            acc.last_error = None
            acc.last_refresh_at = datetime.now()
            db.commit()
            db.refresh(acc)
            return {"ok": True, "accelerator": _row_to_dict(acc)}
        finally:
            conn.close()
    except Exception as e:
        try:
            acc = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_id).first()
            if acc:
                acc.last_status = "error"
                acc.last_error = str(e)
                db.commit()
        except Exception:
            pass
        logger.error(f"[Accelerator] 刷新失败: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


def refresh_due_all() -> Dict[str, Any]:
    """按 refresh_minutes 到期批量刷新（TaskWorker 周期调用，best-effort）。"""
    db = SessionLocal()
    try:
        accs = db.query(EngineAccelerator).filter(EngineAccelerator.enabled.is_(True)).all()
    finally:
        db.close()
    refreshed, errors = [], []
    for acc in accs:
        if not _is_fresh(acc):
            r = refresh_accelerator(acc.id)
            (refreshed if r.get("ok") else errors).append(acc.id)
    return {"refreshed": refreshed, "errors": errors}


def register_refresh_job(manager) -> None:
    """TaskWorker 周期任务：每 5 分钟检查到期加速器。"""
    try:
        manager.register_periodic(300, refresh_due_all)
        logger.info("[Accelerator] 周期刷新任务已注册（300s）")
    except Exception as e:
        logger.error(f"[Accelerator] 周期任务注册失败: {e}")
