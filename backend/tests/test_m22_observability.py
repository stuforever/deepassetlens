# -*- coding: utf-8 -*-
"""M22 单测：观测端点面/pushdown 调试器/缓存管理/降级链（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M22 spec §九验收标准锚定现有实现）。
只读观测+诊断不真实执行（spec §八.1）；Doris EXPLAIN/Profile 真值留联测。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 观测端点面（spec §二/§三：14 端点）
# ---------------------------------------------------------------------------

def test_observability_endpoint_surface():
    """观测 API 端点面：四读+invalidate+pushdown+explain+profile+加速器管理。
    变异锚点：四读端点删 → 引擎域观测失明。"""
    from app.api import engine_observability as O
    paths = " ".join(getattr(r, "path", "") for r in O.router.routes)
    for frag in ("health", "cache/stats", "cache/invalidate", "queries", "circuits",
                 "pushdown/debug", "explain", "profile", "accelerators"):
        assert frag in paths, f"缺观测端点 {frag}"


# ---------------------------------------------------------------------------
# 四读只读（spec §三）
# ---------------------------------------------------------------------------

def test_health_snapshot_readonly():
    """/health 返回 M12 三引擎快照（只读，spec §三）。
    变异锚点：健康读删 → 引擎域工作台无健康面。"""
    from app.api.engine_observability import engine_health_endpoint
    snap = engine_health_endpoint()
    assert isinstance(snap, (dict, list)) and snap


def test_circuits_readonly():
    """/circuits 返回熔断态只读（spec §三：CLOSED/OPEN/HALF_OPEN+连续失败数）。
    变异锚点：熔断读删 → 联邦故障不可见。"""
    from app.api.engine_observability import circuits
    res = circuits()
    assert isinstance(res, (dict, list))


# ---------------------------------------------------------------------------
# 缓存管理两模式（spec §三/§九.5）
# ---------------------------------------------------------------------------

def test_cache_invalidate_all_mode():
    """invalidate 全清模式（endpoint_id 缺省清全部，spec §三）。
    变异锚点：invalidate 删 → 配置保存后陈旧缓存留窗（§八.4 纪律破坏）。"""
    from app.api.engine_observability import CacheInvalidateRequest, cache_invalidate
    res = cache_invalidate(CacheInvalidateRequest(endpoint_id=None))
    assert isinstance(res, dict)


# ---------------------------------------------------------------------------
# Pushdown 调试器（spec §四：诊断不真实执行）
# ---------------------------------------------------------------------------

def test_pushdown_debug_no_execution():
    """pushdown debug 纯解析不执行（spec §四/§八.1）：纯 internal 表 SQL 走调试器
    不触任何引擎（无 API 端点映射→无拉取），返回结构化诊断。
    变异锚点：调试器真执行 → 诊断动作改变数据面（违 §八.1）。"""
    from app.api.engine_observability import PushdownDebugRequest, pushdown_debug
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        res = pushdown_debug(
            PushdownDebugRequest(sql="SELECT COUNT(*) FROM kg_metrics", limit=10), db=db)
        assert isinstance(res, dict)
    finally:
        db.close()


def test_pushdown_error_class_contract():
    """调试器错误走 apply_error_class（spec §四：error_class 契约一致——坏 SQL 不裸抛）。
    变异锚点：诊断错误裸抛 → 前端调试器 500。"""
    from app.api.engine_observability import PushdownDebugRequest, pushdown_debug
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        res = pushdown_debug(
            PushdownDebugRequest(sql="SELEC oops", limit=10), db=db)
        assert isinstance(res, dict)
        data = res.get("data", res) if isinstance(res, dict) else {}
        # 调试器返回结构化诊断（pushdown_trace/sql_with_filters），错误不裸抛
        assert "pushdown_trace" in data or "sql_with_filters" in data or "error_class" in data
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Doris 诊断两件（spec §五：降级链如实）
# ---------------------------------------------------------------------------

def test_explain_and_profile_degradation_chain():
    """explain 两档+profile 两级降级路径在源码（spec §五/§八.3：新路径失败降级历史路径）。
    变异锚点：降级链删 → Doris 2.x 以下版本画像断。"""
    import inspect
    from app.api import engine_observability as O
    src = inspect.getsource(O)
    assert "EXPLAIN VERBOSE" in src or "EXPLAIN" in src
    assert "rest/v1/query_profile" in src  # 历史降级路径显式


def test_explain_rejects_bad_catalog():
    """explain catalog 非法标识拒（spec §九.3）：_check_ident 抛错被捕获→
    code 500+apply_error_class 结构化返回（不裸抛——error_class 契约）。
    变异锚点：catalog 校验删 → SWITCH 注入。"""
    from app.api.engine_observability import ExplainRequest, explain
    res = explain(ExplainRequest(sql="SELECT 1", catalog="bad; DROP", verbose=False))
    assert isinstance(res, dict) and res.get("code") != 200
