"""scope_checker.py - 范围强校验（v3.1 步骤3）

v1 仅对"客户名精确集合"启用严格范围校验（v3.1 共识第2点）。
从 SQL 提取 cust_name 过滤的客户名集合，与判定单声明的结果范围比对：
SQL 查询的客户不得超出声明范围（落实"其他不要检索"，防越界）。

两级范围（v3.1 共识第6点）：
- result_scope: 主查询最终结果的客户集合（最外层 WHERE cust_name ...）
- logical_source_scope: 数据来源的客户集合（CTE/子查询里的 cust_name 过滤，
  即"先锁目标客户/台区再关联配变"的锁客户步骤）
v1 校验 extracted(result+source 并集) ⊆ declared；source 不单独强制（v2 再收紧）。

依赖 sqlglot（已在 deps，DuckDB/Doris 用），无新依赖。
解析失败一律放行（不在此处阻断），交由调用方按"声明了范围却提取为空"判定。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

# v1 仅 cust_name（中文名列）；cust_no/cust_id 不做范围校验（防反复试错，对齐 SKILL.md 三列区别）
_CUSTOMER_NAME_COLS = frozenset({"cust_name"})


@dataclass
class ScopeCheck:
    """范围校验结果。"""

    ok: bool
    extracted: set[str] = field(default_factory=set)  # SQL 提取到的客户名集合
    declared: set[str] = field(default_factory=set)  # 判定单声明的客户名集合
    reason: str = ""

    def __str__(self) -> str:
        return f"ok={self.ok} extracted={sorted(self.extracted)} declared={sorted(self.declared)} {self.reason}"


def extract_customer_names(sql: str) -> set[str]:
    """从 SQL 提取所有 cust_name 过滤的客户名（IN / =，跨 CTE/主查询并集）。

    支持两种 cust_name 过滤写法：
    - `cust_name IN ('客户001','客户003')` —— SKILL.md 文档主推模式
    - `cust_name = '客户001'` —— 单客户场景兼容
    列名带表别名前缀(c.cust_name)自动剥离。解析失败返回空集。
    """
    if not sql or not sql.strip():
        return set()
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:
        return set()
    names: set[str] = set()

    def _under_not(node) -> bool:
        # R5批③：手动上溯——sqlglot 本版 find_ancestor 隔 Paren 即断链（NOT (a=b) 漏判）
        p = node.parent
        while p is not None:
            if isinstance(p, exp.Not):
                return True
            p = p.parent
        return False

    # 1) cust_name IN ('...','...') —— 文档主推模式
    # R5批③（清单安全）：NOT IN（Not(In(...))）是排除集，值不属于提取集合——原 find_all
    # 会命中其内层 In，把排除列表当包含列表（NOT IN ('X') 配 declared={'X'} 判通过=全量绕过）
    for in_expr in tree.find_all(exp.In):
        if _under_not(in_expr):
            continue
        if _col_name(in_expr.this).lower() in _CUSTOMER_NAME_COLS:
            for v in in_expr.expressions:
                if isinstance(v, exp.Literal) and v.is_string:
                    names.add(v.this)
    # 2) cust_name = '...' —— 单客户场景兼容（左右两侧都可能列名；同款排除 NEQ/NOT 包裹）
    for eq in tree.find_all(exp.EQ):
        if _under_not(eq):
            continue
        left_name = _col_name(eq.this).lower()
        right = eq.expression  # = 右侧
        if left_name in _CUSTOMER_NAME_COLS and isinstance(right, exp.Literal) and right.is_string:
            names.add(right.this)
            continue
        right_name = _col_name(right).lower()
        if right_name in _CUSTOMER_NAME_COLS and isinstance(eq.this, exp.Literal) and eq.this.is_string:
            names.add(eq.this.this)
    return names


def check_customer_scope(sql: str, declared) -> ScopeCheck:
    """校验 SQL 的客户名范围是否在声明范围内（v1 严格越界检查）。

    策略：
    - declared 为空 -> 跳过（v1 仅对声明了客户名集合的查询强校验）
    - declared 非空 且 extracted 为空 -> 不通过（声明了客户范围但 SQL 无 cust_name 过滤 = 越界风险）
    - extracted ⊄ declared -> 不通过（SQL 查了声明外的客户 = 越界）
    - extracted ⊆ declared -> 通过（查的是声明子集，结果不越界）

    Args:
        sql: 待校验的 SQL（execute_sql 的 args.sql）。
        declared: 判定单声明的客户名范围，可为 list/set/单字符串。
    """
    declared_set = _to_str_set(declared)
    extracted = extract_customer_names(sql)
    if not declared_set:
        return ScopeCheck(
            ok=True, extracted=extracted, declared=declared_set,
            reason="未声明客户名范围，跳过(v1仅对声明集合强校验)",
        )
    # R5批③（清单安全）：字面子集校验的边界盲区 fail-closed——OR 自由条件（IN ('X') OR 1=1）
    # 与 UNION 无过滤分支可让「提取字面量 ⊆ 声明」成立而实际结果集越界。v1 严格定位下
    # 这类写法不可证明，直接拒绝（合法剧本 SQL 均为单 SELECT + cust_name IN/=，不受影响）。
    try:
        _tree = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:
        _tree = None
    if _tree is not None:
        if _tree.find(exp.Or) is not None:
            return ScopeCheck(
                ok=False, extracted=extracted, declared=declared_set,
                reason="SQL 含 OR 自由条件，字面子集校验不可证明(越界风险，v1 严格拒绝)",
            )
        if _tree.find(exp.Union) is not None:
            return ScopeCheck(
                ok=False, extracted=extracted, declared=declared_set,
                reason="SQL 含 UNION，分支过滤不可证明(越界风险，v1 严格拒绝)",
            )
    if not extracted:
        return ScopeCheck(
            ok=False, extracted=extracted, declared=declared_set,
            reason=f"声明了客户名范围{sorted(declared_set)}但SQL无cust_name过滤(越界风险)",
        )
    extras = extracted - declared_set
    if extras:
        return ScopeCheck(
            ok=False, extracted=extracted, declared=declared_set,
            reason=f"SQL客户名{sorted(extracted)}超出声明{sorted(declared_set)}: 越界{sorted(extras)}",
        )
    return ScopeCheck(
        ok=True, extracted=extracted, declared=declared_set,
        reason=f"SQL客户名{sorted(extracted)}⊆声明{sorted(declared_set)}",
    )


def _col_name(expr) -> str:
    """取列名（去表别名前缀）: c.cust_name -> cust_name。非 Column 返回空。"""
    if isinstance(expr, exp.Column):
        return expr.name or ""
    return ""


def _to_str_set(val) -> set[str]:
    """把任意输入(list/set/单值)转成 str 集合，忽略空串。"""
    if val is None:
        return set()
    if isinstance(val, str):
        return {val} if val.strip() else set()
    out: set[str] = set()
    for v in val:
        if v is not None:
            s = str(v).strip()
            if s:
                out.add(s)
    return out
