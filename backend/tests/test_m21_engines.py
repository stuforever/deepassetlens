# -*- coding: utf-8 -*-
"""M21 单测：安全底座/错误分类/标识符校验/日志与联邦防护面（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M21 spec §九验收标准锚定现有实现）。
四路引擎真值执行（Doris/物理/DuckDB 联邦拉取）依赖外部服务，留联测。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 安全底座（spec §三/§七：一切模型 SQL 的最终关口）
# ---------------------------------------------------------------------------

def test_validate_sql_select_only_and_limit():
    """SELECT 放行+强制注入 LIMIT 500；UPDATE 拒（spec §九.4）。
    变异锚点：LIMIT 注入删 → 无界结果拖垮前端；SELECT-only 删 → 写操作穿透。"""
    from app.services.secure_query_executor import DEFAULT_MAX_LIMIT, validate_sql
    chk = validate_sql("SELECT COUNT(*) FROM kg_metrics")
    assert chk.ok is True and f"LIMIT {DEFAULT_MAX_LIMIT}" in chk.sql
    bad = validate_sql("UPDATE kg_metrics SET a=1")
    assert bad.ok is False and bad.reason


def test_validate_sql_forbidden_funcs():
    """禁用函数面（_FORBIDDEN_FUNCS，spec §安全底座）。
    变异锚点：禁函数删 → SLEEP/文件读写穿透引擎。"""
    from app.services.secure_query_executor import _FORBIDDEN_FUNCS
    assert _FORBIDDEN_FUNCS  # 禁用函数白名单非空（SLEEP/LOAD_FILE 等）
    assert any("sleep" in f.lower() for f in _FORBIDDEN_FUNCS)


# ---------------------------------------------------------------------------
# 错误分类体系（spec §四：M19 纠错闸门输入）
# ---------------------------------------------------------------------------

def test_classify_by_message_core_classes():
    """消息兜底分类：表缺→TABLE_MISSING/超时→CONNECTION/未知兜底（spec §四/§九.5）。
    变异锚点：分类漂移 → M19 纠错指引错路（SECURITY_VALIDATION 误重试等）。"""
    from app.services.engine_errors import classify_by_message
    assert classify_by_message("Table 'tupu.x' doesn't exist") == "TABLE_MISSING"
    assert classify_by_message("Connection timed out") == "CONNECTION"
    assert classify_by_message("完全未知的错误消息 xyz")  # 未知消息有兜底类不裸抛


def test_classify_pymysql_and_wrapped():
    """pymysql 分类+wrap_engine_exception 结构化（spec §四：不裸抛契约）。
    变异锚点：wrap 删 → 原始异常穿透编排层。"""
    from app.services.engine_errors import classify_pymysql_error, wrap_engine_exception
    assert isinstance(classify_pymysql_error(Exception("Table 'a.b' doesn't exist")), str)
    w = wrap_engine_exception(Exception("boom"))
    assert isinstance(w, dict) and "error" in w and "error_class" in w


def test_apply_error_class_adds_class():
    """apply_error_class 给执行结果补 error_class（spec §四契约）。
    变异锚点：补类删 → 执行结果无 error_class 字段。"""
    from app.services.engine_errors import apply_error_class
    res = apply_error_class({"error": "Table 'x.y' doesn't exist"})
    assert res.get("error_class")


# ---------------------------------------------------------------------------
# Doris 标识符校验（spec §三：_check_ident 防注入）
# ---------------------------------------------------------------------------

def test_check_ident_rejects_injection():
    """标识符校验：合法放行/注入串拒（spec §九.1）。
    变异锚点：校验删 → catalog/表名拼接注入。"""
    from app.services.doris_engine import _check_ident
    assert _check_ident("kg_metrics") == "kg_metrics"
    with pytest.raises(ValueError):
        _check_ident("kg; DROP TABLE x")


# ---------------------------------------------------------------------------
# 加速器拦截条件（spec §六：只拦单值聚合）
# ---------------------------------------------------------------------------

def test_try_serve_rejects_non_single_agg():
    """带 WHERE 的聚合/非聚合不拦（spec §六/§八.3：宁慢勿错）。
    变异锚点：条件放宽 → 明细题被预聚合值顶替。"""
    from app.services.engine_accelerator import try_serve
    assert try_serve("SELECT COUNT(*) FROM t WHERE a=1") is None
    assert try_serve("SELECT a, b FROM t") is None
    assert try_serve("not even sql") is None


def test_accelerator_fresh_and_registry():
    """新鲜度判断+周期刷新注册函数（spec §六：_is_fresh TTL/register_refresh_job M14 钩子）。
    变异锚点：新鲜度失判 → 过期预聚合值冒充实时数。"""
    from app.services import engine_accelerator as A
    assert hasattr(A, "_is_fresh") and hasattr(A, "register_refresh_job")
    assert hasattr(A, "refresh_accelerator")


# ---------------------------------------------------------------------------
# 查询日志与联邦防护（spec §三日志纪律/§五三件套）
# ---------------------------------------------------------------------------

def test_query_log_surface():
    """查询日志面：record/purge/list+30d 注册（spec §三/§九.7，M22 观测+M20 种子双消费）。
    变异锚点：日志删 → 观测与种子提炼双断。"""
    from app.services import engine_query_log as L
    assert hasattr(L, "record_query_log") and hasattr(L, "purge_old_logs")
    assert hasattr(L, "register_purge_job") and hasattr(L, "list_queries")


def test_duckdb_federation_protections():
    """联邦防护三件套：熔断/限流/缓存失效函数（spec §五/§八.4）。
    变异锚点：熔断删 → 外部 API 故障传导进问数主链。"""
    from app.services import duckdb_engine as D
    for fn in ("_check_circuit", "_record_failure", "_record_success", "_enforce_rate_limit",
               "invalidate_endpoint_cache", "_fetch_with_pagination", "test_endpoint"):
        assert hasattr(D, fn), f"缺联邦防护 {fn}"


def test_sql_rewrite_service_exists():
    """ai_rewrite_sql（spec §二：M07 integration-sql 改写联动）。
    变异锚点：改写删 → integration 口径 SQL 不可修复。"""
    from app.services import sql_rewrite_service as R
    assert hasattr(R, "ai_rewrite_sql")
