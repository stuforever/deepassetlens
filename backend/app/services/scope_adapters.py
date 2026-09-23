"""scope_adapters.py - 四类数据工具的范围适配器（第一批半 P0）

评审点4：SCOPE_GATED_TOOLS 不能只加工具名，因为四个工具的参数结构不同：
  execute_sql        -> SQL WHERE（scope_checker 已支持）
  execute_doris_sql  -> SQL 或 filters（双载体）
  execute_entity_api -> filters（dict，非 SQL）
  execute_api_sql    -> DuckDB SQL（scope_checker 已支持）

每个 adapter 负责：
  1. 从工具 args 提取"范围载体"（SQL 字符串或 filters dict）
  2. 从载体提取客户名集合（复用 scope_checker 的 sqlglot 解析或 filters 解析）
  3. 与可信范围（Agent state.last_scope.customer_names）交叉校验

可信范围来源：Agent state.last_scope（由 data_intelligence 从用户输入解析写入），
不来自模型自己写的"范围"行（防模型自洽绕过）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.services.scope_checker import ScopeCheck, extract_customer_names, _to_str_set


@dataclass
class ToolArgs:
    """从 tool_call.args 提取的标准化参数。"""
    sql: str = ""
    filters: dict = None
    entity_code: str = ""

    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


def extract_tool_args(tool_call: dict) -> ToolArgs:
    """从 tool_call.args 提取 SQL/filters/entity_code（兼容 dict 和 JSON str）。"""
    args = tool_call.get("args", {}) or {}
    if isinstance(args, str):
        import json
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    return ToolArgs(
        sql=args.get("sql", "") or "",
        filters=args.get("filters", {}) or {},
        entity_code=args.get("entity_code", "") or "",
    )


def extract_customer_names_from_filters(filters: dict) -> set[str]:
    """从 filters dict 提取客户名（兼容 cust_name / customer_name / customer_names 键）。"""
    if not filters:
        return set()
    names = set()
    for key in ("cust_name", "customer_name", "customer_names", "cust_names"):
        val = filters.get(key)
        if val is None:
            continue
        if isinstance(val, (list, tuple, set)):
            for v in val:
                if v:
                    names.add(str(v).strip())
        elif isinstance(val, str):
            # 逗号分隔字符串
            for v in val.replace("，", ",").split(","):
                v = v.strip()
                if v:
                    names.add(v)
    return names


def check_scope_for_tool(tool_name: str, tool_call: dict, trusted_scope: Any) -> ScopeCheck:
    """按工具类型选择 adapter，提取范围载体并与可信范围交叉校验。

    Args:
        tool_name: 工具名（execute_sql / execute_doris_sql / execute_entity_api / execute_api_sql）
        tool_call: request.tool_call，含 args
        trusted_scope: 可信范围（Agent state.last_scope），可为 dict{customer_names: [...]}
                       或 list/set/单字符串；为空则跳过（v1 仅对声明了客户名集合的查询强校验）

    Returns:
        ScopeCheck: ok=True 表示工具范围 ⊆ 可信范围
    """
    # 解析可信范围
    if isinstance(trusted_scope, dict):
        trusted_names = _to_str_set(trusted_scope.get("customer_names") or [])
    else:
        trusted_names = _to_str_set(trusted_scope)

    # 无可信范围则跳过（与 scope_checker v1 策略一致）
    if not trusted_names:
        return ScopeCheck(
            ok=True, extracted=set(), declared=trusted_names,
            reason="无可信客户名范围，跳过(仅对声明集合强校验)",
        )

    args = extract_tool_args(tool_call)

    # 按工具类型提取范围载体
    if tool_name in ("execute_sql", "execute_api_sql"):
        # SQL 型：用 sqlglot 提取 cust_name
        extracted = extract_customer_names(args.sql)
    elif tool_name == "execute_doris_sql":
        # Doris 双载体：R5批㉔——对齐 handler 实际语义（_kg_execute_doris_sql：
        # entity_code 非空时 sql 完全忽略）。原"优先 filters 次选 sql"在两者同给时
        # 可用无关 filters 过闸而真实执行的 sql 漏检（烟雾弹通道）。
        if getattr(args, "entity_code", ""):
            extracted = extract_customer_names_from_filters(args.filters)
        else:
            extracted = extract_customer_names(args.sql) if args.sql else set()
    elif tool_name == "execute_entity_api":
        # 纯 filters 型
        extracted = extract_customer_names_from_filters(args.filters)
    else:
        # 非数据工具，跳过
        return ScopeCheck(ok=True, extracted=set(), declared=trusted_names, reason="非范围校验工具")

    # 交叉校验：extracted ⊆ trusted_names
    if not extracted:
        return ScopeCheck(
            ok=False, extracted=extracted, declared=trusted_names,
            reason=f"可信范围{sorted(trusted_names)}但工具无cust_name过滤(越界风险)",
        )
    extras = extracted - trusted_names
    if extras:
        return ScopeCheck(
            ok=False, extracted=extracted, declared=trusted_names,
            reason=f"工具客户名{sorted(extracted)}超出可信{sorted(trusted_names)}: 越界{sorted(extras)}",
        )
    return ScopeCheck(
        ok=True, extracted=extracted, declared=trusted_names,
        reason=f"工具客户名{sorted(extracted)}⊆可信{sorted(trusted_names)}",
    )
