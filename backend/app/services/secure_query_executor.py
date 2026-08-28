"""secure_query_executor.py - SQL 执行安全边界（第一批半 P0）

统一拦截所有 SQL 型数据工具（execute_sql / execute_doris_sql / execute_api_sql），
在执行前做 AST 级安全校验。execute_entity_api 走 filters 不走 SQL，由 ScopeAdapter 覆盖。

校验链（不可绕过）：
  SQL -> AST 解析 -> 只读语句校验 -> 表白名单 -> 强制 LIMIT -> 返回 sanitized SQL

设计原则（评审第二批 + YAGNI）：
  - 用已有 sqlglot，不加依赖
  - 只做机械安全校验，不改语义
  - 校验失败返回结构化错误，不自动修复（第一批已删语义改变型修复）
  - 超时/只读账号由调用方在执行层落实，本模块只负责 SQL 层面
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import sqlglot
from sqlglot import exp

# 只允许 SELECT / WITH ... SELECT（只读查询）
_READONLY_STMT_TYPES = frozenset({"Select"})
# 禁止的语句类型（DDL/DML/过程调用）
_FORBIDDEN_STMT_TYPES = frozenset({
    "Insert", "Update", "Delete", "Drop", "Create", "Alter",
    "Truncate", "Merge", "Command", "Unknown",
})
# 禁止的函数名（副作用函数）
_FORBIDDEN_FUNCS = frozenset({
    "sleep", "benchmark", "load_file", "into_outfile", "into_dumpfile",
    "pg_sleep", "dbms_lock", "sys_exec", "sys_eval",
})
# 强制最大 LIMIT（防超大结果集）
DEFAULT_MAX_LIMIT = 500


@dataclass
class SqlCheck:
    """SQL 安全校验结果。"""
    ok: bool
    sql: str = ""           # 校验通过后返回的 SQL（可能加了强制 LIMIT）
    reason: str = ""
    tables: list[str] = None  # SQL 涉及的表名

    def __post_init__(self):
        if self.tables is None:
            self.tables = []


def validate_sql(sql: str, allowed_tables: Optional[set[str]] = None, max_limit: int = DEFAULT_MAX_LIMIT) -> SqlCheck:
    """AST 级 SQL 安全校验。

    Args:
        sql: 待校验 SQL
        allowed_tables: 允许查询的表白名单（物理表名集合）；None 则不校验表名
        max_limit: 强制最大 LIMIT

    Returns:
        SqlCheck: ok=True 时 sql 字段为可安全执行的 SQL；ok=False 时 reason 含失败原因
    """
    if not sql or not sql.strip():
        return SqlCheck(ok=False, reason="SQL 为空")

    # 安全控制中心接线（sql_safety）：开关关闭 -> 跳过机械安全校验，直接放行（管理员显式操作）。
    # 默认开启（fail-closed 基线），关闭仅影响本层校验，其余守卫仍生效。
    from app.services import guard_config as _gc
    if not _gc.guard_enabled("sql_safety"):
        return SqlCheck(ok=True, sql=sql, tables=[])

    # 1. AST 解析
    try:
        # 多语句检测：sqlglot.parse 返回多棵树说明有多语句
        trees = list(sqlglot.parse(sql))
    except Exception as e:
        return SqlCheck(ok=False, reason=f"SQL 解析失败: {e}")

    if len(trees) != 1:
        return SqlCheck(ok=False, reason=f"禁止多语句(检测到 {len(trees)} 条)")
    tree = trees[0]
    if tree is None:
        return SqlCheck(ok=False, reason="SQL 解析为空")

    # 2. 只读语句校验
    stmt_type = type(tree).__name__
    if stmt_type not in _READONLY_STMT_TYPES:
        if stmt_type in _FORBIDDEN_STMT_TYPES:
            return SqlCheck(ok=False, reason=f"禁止 {stmt_type} 语句(仅允许 SELECT/WITH)")
        return SqlCheck(ok=False, reason=f"不支持的语句类型: {stmt_type}")

    # 3. 禁止副作用函数
    for func in tree.find_all(exp.Func):
        # sql_name() 对匿名函数返回 'ANONYMOUS'，需取 func.name（真实函数名如 sleep/benchmark）
        func_name = (func.name or func.sql_name() or "").lower()
        if func_name in _FORBIDDEN_FUNCS:
            return SqlCheck(ok=False, reason=f"禁止函数: {func_name}")

    # 4. 表白名单校验
    tables = _extract_tables(tree)
    if allowed_tables is not None:
        for t in tables:
            # 归一化：取最后一段表名做比对（catalog.db.table -> table）
            t_norm = t.split(".")[-1].strip("`\"'")
            if t_norm and t_norm not in allowed_tables and t not in allowed_tables:
                return SqlCheck(ok=False, reason=f"表「{t}」不在允许查询的白名单内", tables=tables)

    # 5. 强制 LIMIT（无 LIMIT 或 LIMIT 超过上限则改写）
    sanitized = _ensure_limit(tree, max_limit)

    return SqlCheck(ok=True, sql=sanitized, tables=tables)


def _extract_tables(tree) -> list[str]:
    """从 AST 提取所有表名（FROM/JOIN 子句）。"""
    tables = []
    for table_expr in tree.find_all(exp.Table):
        name = table_expr.sql()
        if name:
            tables.append(name)
    return tables


def _ensure_limit(tree, max_limit: int) -> str:
    """确保 SQL 有 LIMIT 且不超过 max_limit。无 LIMIT 则追加。"""
    existing = tree.args.get("limit")
    if existing is not None:
        # 已有 LIMIT，检查值
        try:
            n = int(existing.expression.name)  # type: ignore
            if n > max_limit:
                existing.set("expression", exp.Literal.number(max_limit))
        except Exception:
            pass  # LIMIT 值解析失败（如 LIMIT ?），不动
    else:
        # 无 LIMIT，追加
        tree.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
    return tree.sql()
