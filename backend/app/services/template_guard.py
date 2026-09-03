"""template_guard.py - SQL 模板校验（受控 Skill 问答平台 v2，设计 §6.2）

v1 不做"任意 SQL 全自动语义判定"，只做受控场景模板校验：
- 只允许 SELECT（无 DDL/DML/UNION 绕过）；
- 表集合 ⊆ 模板允许表集合；
- 无未知子查询（FROM 只出自模板已用表）；
- 模板参数只替换白名单变量；
- 客户范围一致性由既有 scope_checker 负责（此处不重复实现）。
依赖 sqlglot（已在 deps，DuckDB/Doris 均用），不新增包。
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

# 白名单模板参数（SKILL.md 约定：/* {{param}} */ 注入位）
_ALLOWED_PARAMS = frozenset({"customer_scope", "date_filter"})
_TEMPLATE_PARAM_RE = re.compile(r"/\*\s*\{\{\s*(\w+)\s*\}\}\s*\*/")

# 模板校验分级（P0-2 强牢笼：评审建议 scenario_strict / extensible / generic）
TEMPLATE_MODE_STRICT = "scenario_strict"          # 结构指纹不一致直接拒绝（模板派生 SQL 强制执行）
TEMPLATE_MODE_EXTENSIBLE = "scenario_extensible"  # 允许同表结构变化，但记结构漂移审计（默认）
TEMPLATE_MODE_GENERIC = "generic"                 # 通用 SQL 安全校验（不强制模板结构）


@dataclass
class TemplateCheck:
    ok: bool
    reason: str = ""
    tables: Set[str] = field(default_factory=set)
    template_id: str = ""
    fingerprint: str = ""
    structure_match: bool = False            # 批4 指纹比对：候选与模板结构骨架一致
    candidate_fingerprint: str = ""          # 候选结构指纹
    template_fingerprint: str = ""           # 模板结构指纹


def load_template(absolute_path: str | Path) -> str:
    """读取已批准模板文件内容。"""
    p = Path(absolute_path)
    return p.read_text("utf-8")


def render_template(template_sql: str, params: Dict[str, str]) -> str:
    """按参数白名单渲染模板：/* {{customer_scope}} */ -> 实际值。

    未知参数名直接忽略（不替换），不抛错（保持模板原样 -> 之后校验会发现缺失）。
    """
    out = template_sql

    def _rep(m: re.Match):
        name = m.group(1)
        if name in _ALLOWED_PARAMS and name in params:
            return str(params[name])
        return m.group(0)

    return _TEMPLATE_PARAM_RE.sub(_rep, out)


def fingerprint(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------
# 批4 模板指纹精确比对（设计 §1.2/§6.1：模板哈希 + 参数注入点校验）
# ----------------------------------------------------------------------
def _strip_comments(sql: str) -> str:
    """剥离 SQL 注释（`--` 行注释 / `/* */` 块注释），保留字符串字面量内的内容。

    注：sqlglot 30.x 的 `parse_one(comments=False)` 不被支持（会抛 TypeError），
    批4 的"去注释"此前一直静默回退到 rough_normalize（注释仍残留、污染结构指纹）。
    这里用扫描器在规范化前真正剥离注释，避免注释文本（如【动态】示例 SQL）进入骨架。
    """
    if not sql:
        return sql
    out = []
    i, n = 0, len(sql)
    in_str: Optional[str] = None
    while i < n:
        ch = sql[i]
        if in_str:
            out.append(ch)
            if ch == in_str:
                if i + 1 < n and sql[i + 1] == in_str:  # 转义引号 '' / ""
                    out.append(sql[i + 1])
                    i += 2
                    continue
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            out.append(ch)
            i += 1
            continue
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            while i < n and sql[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def canonicalize_sql(sql: str, dialect: str = "postgres") -> str:
    """把 SQL 规范化为"结构骨架"：字面量（数值/字符串/布尔）统一替换为 ?，其余结构保留。

    目的：候选 SQL 若由模板派生（仅替换参数），其骨架应与模板骨架一致 ——
    结构指纹比对可发现"同表但结构漂移"（如擅自改 JOIN、加 GROUP BY 等）。
    注释（含【动态】声明片段、中文说明）在规范化前被剥离，不进入骨架。
    """
    text = _strip_comments(sql or "")
    try:
        tree = sqlglot.parse_one(text, dialect=dialect)
    except Exception:
        return _rough_normalize(text)
    try:
        for node in tree.walk():
            if isinstance(node, (exp.Literal, exp.Boolean, exp.Null, exp.Interval)):
                node.replace(exp.Literal.string("?"))
        return tree.sql(dialect=dialect).strip().lower()
    except Exception:
        return _rough_normalize(text)


def _rough_normalize(sql: str) -> str:
    """解析失败兜底：引号/数值字面量替换 + 空白归一（不因解析失败放弃指纹）。"""
    s = re.sub(r"'[^']*'", "'?'", sql)
    s = re.sub(r"\b\d+(\.\d+)?\b", "?", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def structural_fingerprint(sql: str, dialect: str = "postgres") -> str:
    """结构骨架指纹（sha256[:16]）。"""
    return hashlib.sha256(canonicalize_sql(sql, dialect).encode("utf-8")).hexdigest()[:16]


def has_unrendered_params(sql: str) -> bool:
    """候选 SQL 是否残留未渲染的模板参数占位（/* {{param}} */）—— 提示模板参数未注入。"""
    return bool(_TEMPLATE_PARAM_RE.search(sql or ""))


def extract_tables(sql: str, dialect: str = "postgres") -> Set[str]:
    """用 sqlglot 提取 SQL 引用的全部表名（去 schema/catalog 前缀，统一小写）。"""
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return set()
    tables: Set[str] = set()
    for tbl in tree.find_all(exp.Table):
        if tbl.name:
            tables.add(tbl.name.lower())
    return tables


def _contains_union(sql: str, dialect: str = "postgres") -> bool:
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return "union" in sql.lower()
    return any(isinstance(n, exp.Union) for n in tree.find_all(exp.Union))


def _is_select_only(sql: str, dialect: str = "postgres") -> bool:
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return False
    if isinstance(tree, (exp.Select, exp.Subquery)):
        return True
    # UNION ALL 合法（模板自身用于合并两段查询），要求两侧都是 SELECT
    if isinstance(tree, exp.Union):
        left, right = tree.this, tree.expression
        return isinstance(left, (exp.Select, exp.Subquery)) and isinstance(right, (exp.Select, exp.Subquery))
    return False


def _dynamic_fragments(template_sql: str) -> List[str]:
    """提取模板 `-- 【动态】...: <SQL片段>` 声明式扩展点（scenario_strict 允许的唯一 AST 变化）。

    示例：`-- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')`
    -> 片段 `AND c.cust_name IN ('客户001','客户003')`。
    """
    frags = []
    for m in re.finditer(r"--\s*【动态】[^：:]*[：:]\s*(.+)", template_sql or ""):
        frag = m.group(1).strip()
        if frag and not frag.startswith("--"):
            frags.append(frag)
    return frags


def _conjunct_canonical(text: str, dialect: str = "postgres") -> str:
    """把 WHERE 连接项/片段规范化为可比对骨架（去字面量 + 空白归一 + 去前导 and/or）。"""
    t = text.strip()
    # 去掉行尾分号与注释
    t = re.sub(r";\s*$", "", t)
    t = re.split(r"--.*$", t, flags=re.MULTILINE)[0].strip()
    norm = _rough_normalize(t)
    # 片段形如 `AND c.cust_name IN (...)`，与解析出的连接项（无前导 and）对齐
    norm = re.sub(r"^\s*(and|or)\s+", "", norm)
    # sqlglot 的 IN 列表生成 `(?, ?)`，模板片段为 `(?,?)` -> 统一去逗号后空格
    norm = re.sub(r",\s+", ",", norm)
    return norm


def _split_conjuncts(node) -> list:
    """把 WHERE 表达式按顶层 AND 分裂为连接项列表（叶子）。"""
    if isinstance(node, exp.And):
        return _split_conjuncts(node.left) + _split_conjuncts(node.right)
    return [node]


def _all_where_conjuncts(sql: str, dialect: str = "postgres") -> Set[str]:
    """遍历整棵 AST 的所有 WHERE（每个 SELECT/CTE/UNION 分支），收集全部连接项骨架。

    评审 P0-2（二轮）：必须用 `find_all(exp.Where)` 而非 `find(exp.Where)` ——
    `find()` 只取第一个 WHERE，改第二个分支/GROUP BY/JOIN 会漏检。
    """
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return set()
    conjs: Set[str] = set()
    for wh in tree.find_all(exp.Where):
        if wh.this is None:
            continue
        conjs |= {_conjunct_canonical(n.sql(dialect=dialect), dialect) for n in _split_conjuncts(wh.this)}
    return conjs


def _prune_conjunct(node, remove: Set[str], dialect: str) -> Optional[exp.Expression]:
    """从 AND 树中摘除规范化后属于 remove 的叶子；空树返回 None。"""
    if node is None:
        return None
    if isinstance(node, exp.And):
        left = _prune_conjunct(node.left, remove, dialect)
        right = _prune_conjunct(node.right, remove, dialect)
        if left is None:
            return right
        if right is None:
            return left
        node.set("left", left)
        node.set("right", right)
        return node
    if _conjunct_canonical(node.sql(dialect=dialect), dialect) in remove:
        return None
    return node


def _prune_where_conjuncts(tree, remove: Set[str], dialect: str) -> None:
    """从整棵 AST 的所有 WHERE 摘除匹配 remove 的连接项（原地修改 AST）。"""
    for wh in list(tree.find_all(exp.Where)):
        pruned = _prune_conjunct(wh.this, remove, dialect)
        if pruned is None:
            wh.pop()  # 整个 WHERE 被摘空 -> 删除该 WHERE 节点
        else:
            wh.set("this", pruned)


def _strict_derived_from_template(candidate_sql: str, template_sql: str,
                                  dialect: str = "postgres") -> bool:
    """scenario_strict 判定：候选是否严格由模板派生（评审 P0-2 二轮强约束）。

    只允许模板声明的【动态】插槽在**对应位置**出现白名单谓词；其余整棵 AST
    （每个 UNION 分支、CTE、JOIN、GROUP BY、SELECT 列）必须与模板完全一致。

    判定三步：
      1) 完整结构指纹相等 -> 派生（字面量差异已被规范化容忍）；
      2) 模板全部 WHERE 连接项 ⊆ 候选（未删改模板既有条件），候选多出的连接项
         ⊆ 模板【动态】声明片段（规范化后）—— 防"在第一个 WHERE 加合法动态 +
         在其他分支改结构"的组合绕过（多出项必须在声明插槽内）；
      3) 从候选 AST 中**摘除**全部动态连接项后，剩余全文结构指纹必须与模板一致
         —— 这一步覆盖 CTE/UNION 分支/JOIN/GROUP BY/SELECT 列的逐节点比较。
    """
    if structural_fingerprint(candidate_sql, dialect) == structural_fingerprint(template_sql, dialect):
        return True
    t_conjs = _all_where_conjuncts(template_sql, dialect)
    c_conjs = _all_where_conjuncts(candidate_sql, dialect)
    dynamic = {_conjunct_canonical(f, dialect) for f in _dynamic_fragments(template_sql)}
    if not dynamic or not t_conjs or not (t_conjs <= c_conjs):
        return False
    extra = c_conjs - t_conjs
    if not extra or not (extra <= dynamic):
        return False
    # 摘除候选的"多出"动态连接项后，全文结构必须与模板逐节点一致。
    # 模板直接取原始文本（canonicalize 已 comments=False 丢弃模板内联注释，即动态插槽声明），
    # 候选则取摘除动态连接项后的序列化全文 —— 二者指纹相等 = 除插槽外整棵 AST 一致。
    try:
        # 候选先剥离注释再解析，避免内联注释随 .sql() 序列化残留（与模板指纹不可比）
        ctree = sqlglot.parse_one(_strip_comments(candidate_sql), dialect=dialect)
        _prune_where_conjuncts(ctree, extra, dialect)
        base_cand = ctree.sql(dialect=dialect)
        return structural_fingerprint(base_cand, dialect) == structural_fingerprint(template_sql, dialect)
    except Exception:
        return False


def validate_against_template(
    candidate_sql: str,
    template_sql: str,
    template_id: str,
    *,
    dialect: str = "postgres",
    allowed_extra_tables: Optional[Set[str]] = None,
    mode: str = TEMPLATE_MODE_EXTENSIBLE,
) -> TemplateCheck:
    """校验候选 SQL 是否符合已批准模板（SELECT-only + 表集合 ⊆ 模板表 + 无 UNION 绕过）。

    P0-2 强约束分级：
      - scenario_strict：结构指纹不一致（同表但骨架不同）→ 拒绝（模板派生 SQL 强制执行）；
      - scenario_extensible：允许同表结构变化（记结构漂移审计），表集合/未渲染参数仍硬校验；
      - generic：允许结构变化，走通用 SQL 安全校验（表集合仍是闸门）。
    未渲染参数占位（/* {{param}} */）在任何模式下都拒绝（参数注入点校验）。

    UNION 处理：模板自身合法使用 UNION ALL（如户变关系模板合并用电户/发电户两段），
    因此不对 UNION 一刀切拒绝；防绕过靠表集合校验（UNION 引入模板外表必然被表集合检查拦截）。
    """
    candidate = (candidate_sql or "").strip()
    if not candidate:
        return TemplateCheck(ok=False, reason="候选 SQL 为空", template_id=template_id)
    if not _is_select_only(candidate, dialect):
        return TemplateCheck(ok=False, reason="只允许 SELECT 语句（发现 DDL/DML/其他语句）", template_id=template_id)
    # P0-2 未渲染参数占位：任何模式一律拒绝
    if has_unrendered_params(candidate):
        return TemplateCheck(
            ok=False, reason="SQL 残留未渲染的模板参数占位（/* {{param}} */），禁止原样提交",
            template_id=template_id)

    cand_tables = extract_tables(candidate, dialect)
    tmpl_tables = extract_tables(template_sql, dialect)
    allowed = set(tmpl_tables) | set(allowed_extra_tables or ())
    extras = cand_tables - allowed
    has_union = _contains_union(candidate, dialect)
    if extras:
        return TemplateCheck(
            ok=False,
            reason=f"SQL 表集合超出模板允许范围: 额外表 {sorted(extras)}（模板允许 {sorted(allowed) or '空'}）",
            tables=cand_tables, template_id=template_id,
        )
    # P0-2 结构指纹比对（严格模式为硬闸门；extensible/generic 记漂移审计）
    cand_fp = structural_fingerprint(candidate, dialect)
    tmpl_fp = structural_fingerprint(template_sql, dialect)
    structure_match = cand_fp == tmpl_fp and bool(cand_fp)
    note = ""
    if has_union:
        note = "（含 UNION，但表集合在模板范围内，合法合并）"
    if not structure_match:
        fp_note = f"；结构指纹与模板不一致（模板={tmpl_fp} 候选={cand_fp}，同表但结构漂移）"
        if mode == TEMPLATE_MODE_STRICT:
            # P0-2 strict：允许模板派生的唯一变化 = 声明式【动态】扩展点；其余结构漂移一律拒绝
            if _strict_derived_from_template(candidate, template_sql, dialect):
                structure_match = True
            else:
                return TemplateCheck(
                    ok=False,
                    reason=f"SQL 未通过模板严格校验（scenario_strict）：结构指纹与模板不一致{fp_note}",
                    tables=cand_tables, template_id=template_id,
                    structure_match=False,
                    candidate_fingerprint=cand_fp, template_fingerprint=tmpl_fp,
                )
        note += fp_note
    return TemplateCheck(
        ok=True,
        reason=f"SQL 通过模板校验({mode}): 表集合 ⊆ 模板表({sorted(cand_tables)})，SELECT-only{note}",
        tables=cand_tables,
        template_id=template_id,
        fingerprint=fingerprint(candidate),
        structure_match=structure_match,
        candidate_fingerprint=cand_fp,
        template_fingerprint=tmpl_fp,
    )


def template_id_components(template_id: str) -> tuple[str, str]:
    """把 "skill:path/to/template.sql" 拆成 (skill_id, rel_path)。"""
    if ":" in template_id:
        skill, _, rel = template_id.partition(":")
        return skill, rel
    return "", template_id


def resolve_entity_aliases(text: str, aliases: Dict[str, str]) -> str:
    """把模板/参考文件中的 ⟦业务中文名⟧ 替换为物理表名（SKILL.md x_tupu.entity_aliases）。

    aliases 是唯一来源（SKILL.md 声明）；未覆盖的 ⟦引用⟧ 保持原样（由精确 entity_name 解析兜底）。
    """
    if "⟦" not in text or not aliases:
        return text
    out = text
    for ref, table in aliases.items():
        marker = f"⟦{ref}⟧"
        if marker in out:
            out = out.replace(marker, table)
    return out


# ---------------------------------------------------------------------------
# 批13-AB2：精确 entity_name 解析（自 tupu_deepagent.py 搬迁，函数体一字不改）。
# 归属说明：这是「模板/技能文件装配时」的确定性翻译（skill_policy._resolve_step_templates
# 模板表集合比对、_load_skill_md 系统提示词构建共用，0 模型轮次成本），与已退役的
# SkillEntityResolverMiddleware（read_file 运行时翻译站，批13-AB2 删除）无关。
# 运行时模型读技能文件看到 ⟦⟧ 原文 -> 按 AGENTS.md 纪律主动 search_entities 翻译 ->
# 漏网写进 SQL 由模板守卫硬拒（双层安全网，见设计 §2.2）。
# ---------------------------------------------------------------------------
_ENTITY_REF_RE = __import__('re').compile(r'⟦([^⟧]+)⟧')


def _resolve_entity_refs(text: str) -> str:
    """将文本中的 ⟦实体中文名⟧ 替换为元数据中的物理表名（entity_en_name）。
    找不到的保留原文，不阻断。"""
    if '⟦' not in text:
        return text
    names = set(_ENTITY_REF_RE.findall(text))
    if not names:
        return text
    # 一次批量查元数据
    from app.core.database import SessionLocal
    from app.models.base import Entity
    db = SessionLocal()
    try:
        ents = db.query(Entity.entity_name, Entity.entity_en_name).filter(Entity.entity_name.in_(names)).all()
        mapping = {name: en_name for name, en_name in ents if en_name}
    finally:
        db.close()
    if not mapping:
        return text
    # 逐个替换
    def _replacer(m):
        cn = m.group(1)
        return mapping.get(cn, m.group(0))  # 找不到保留原文
    return _ENTITY_REF_RE.sub(_replacer, text)
