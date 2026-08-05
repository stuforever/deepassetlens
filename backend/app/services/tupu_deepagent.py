"""
Tupu DeepAgent -- 基于 LangGraph 原生 create_react_agent 的问数流程

架构:
  create_deep_agent(model, tools=[kg_api], system_prompt, state_schema, checkpointer, backend, skills)
    ├─ Tool: kg_api  知识图谱查询工具（10 个 action）
    └─ skills=["/skills/"]  虚拟文件系统挂载 SKILL.md

  ReAct 模式：LLM 自主规划步骤、自主调 kg_api 工具、边推理边输出 token
  checkpointer: AsyncSqliteSaver (持久化，支持多轮上下文继承)
  SSE: astream_events(version="v2") 推送 think/token/trace/sql_result/final/done
"""
from __future__ import annotations

import logging
import os
from typing import Annotated, Any, Dict, List, TypedDict

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

import operator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. State 定义 (DeepAgentState 扩展)
# ---------------------------------------------------------------------------

try:
    from deepagents.graph import DeepAgentState
    _HAS_DEEPAGENTS = True
except ImportError:
    _HAS_DEEPAGENTS = False
    # Fallback: 当 deepagents 未安装时，提供最小化的 State 基类
    # Plan-Execute 路径不需要 DeepAgentState，只需保证模块可导入
    from typing import TypedDict as _TypedDict
    class DeepAgentState(_TypedDict):
        """Fallback State 基类（deepagents 未安装时使用）"""
        messages: NotRequired[list]
        context: NotRequired[dict]


class TupuAgentState(DeepAgentState):
    """tupu 问数流程的 DeepAgent State 扩展"""
    # 业务字段
    confirmed: NotRequired[dict]                              # 已确认项(L1/L2/L2X/attributes/relations/assembled_sql)
    flags: NotRequired[dict]                                  # 5 旗标
    think_history: NotRequired[Annotated[list, operator.add]] # 推理过程(累加)
    pending_clarification: NotRequired[dict]                  # 澄清卡数据
    goal: NotRequired[str]                                    # 目标(sql_assembly / knowledge_only)


# ---------------------------------------------------------------------------
# 2. System Prompt (按技能分段注入, 降低 LLM 认知负担)
# ---------------------------------------------------------------------------

from datetime import datetime

_BASE_ROLE = """你是 tupu 数据智能问答平台的助手，专注于电力行业数据图谱问答。
当前日期：__CURRENT_DATE__
平台版本：0.17.0
"""

_COMMON_RULES = """
## 重要规则
1. 不要用 glob/ls 探索文件系统，直接调 kg_api 工具
2. 不要用 write_file 写中间文件，数据在对话里传递
3. 不要自己编造 SQL，必须先查 JOIN 关系（fetch_join_expr）
4. 拼装 SQL 后必须调 validate_safe_sql 校验，通过后才执行
5. SQL 只允许 SELECT/WITH，必须加 LIMIT
6. 回答用中文，结构清晰
7. **SQL 表名规则（关键）**：
   - search_entities 返回的 entity_code（如 dim_ps_project_def）是逻辑代码，**不能**用作 SQL 表名
   - search_entities 返回的 entity_en_name（如 ProjectDefinition）才是数据库物理表名，**必须**用它写 SQL
   - 例：SELECT * FROM ProjectDefinition LIMIT 10  ✓
   - 例：SELECT * FROM dim_ps_project_def LIMIT 10  ✗（表不存在）
8. **数据真实性规则（关键）**：
   - 答案的 summary 和 row_count 必须基于 execute_sql 实际返回的数据
   - 如果 execute_sql 返回 error 或 0 行，必须如实报告"未查到数据"，**不得编造数据**
   - 禁止在未成功执行 SQL 的情况下输出具体的数据值
"""

_SQL_FLOW_RULES = """
## 问数流程（定位 → 拼 SQL → 校验 → 执行 → 输出）
1. 调 fetch_l1_l2_tree 获取层级树，对比用户问句锁定 L2
2. 调 validate_l2 校验 L2
3. 调 fetch_subgraph 获取子图，锁定实体
   **关键：子图可能含多个实体，必须根据用户问句关键词选择最匹配的实体**
   - 用户问"WBS成本"→ 选 entity_en_name=ProjectCost（不要选 WbsElement）
   - 用户问"WBS预算"→ 选 entity_en_name=ProjectBudget（不要选 WbsElement）
   - 用户问"WBS元素"→ 选 entity_en_name=WbsElement
   - 用户问"项目定义"→ 选 entity_en_name=ProjectDefinition
   - 用户问"网络活动"→ 选 entity_en_name=NetworkActivity
   - 用户问"网络组件"→ 选 entity_en_name=NetworkComponent
   - 用户问"里程碑"→ 选 entity_en_name=Milestone
   - 用户问"状态"→ 选 entity_en_name=PsStatus
4. 调 validate_attributes 校验属性 code
5. 如需跨表：调 fetch_join_expr 查 JOIN 字段
6. 调 get_entity_source_mode(entity_code) 确认数据源模式，按模式选执行工具（铁律：模式锁定后不可切换）：
   - api_integration -> execute_entity_api(entity_code, filters)（多源API联邦SQL，ES等多源自动JOIN，WHERE下推，返回 columns+rows）
   - sql_integration -> execute_doris_sql(entity_code, filters)（Doris 整合 SQL）
   - physical_table -> 拼装 SQL（字段加表名前缀，LIMIT 500）-> validate_safe_sql 校验 -> execute_sql(sql, entity_code) 执行
   【硬规则】source_mode 一经确认，只能用对应工具。execute_doris_sql 返回空结果(row_count=0)或 hint="未查到相关数据"=数据不存在，直接回复"未查到相关数据"，禁止降级到 execute_sql 或 execute_entity_api 重试。不要无限试验其他模式。

## 跨源查询路由（physical_table 多实体场景）
当 SQL 涉及多个 physical_table 实体时：
1. 先对每个实体调 get_entity_source_mode 取 data_source_id + doris_catalog_name
2. data_source_id 全相同（或全空）-> execute_sql(sql, entity_code) 走该源直连
3. data_source_id 不同 -> execute_doris_sql(sql) 走 Doris 联邦，SQL 用 3 段命名 catalog.db.table（catalog=各数据源的 doris_catalog_name）
4. 某实体 data_source_id 非空但 doris_catalog_name 为空 -> 该源未纳管 Doris catalog，无法跨源联邦，如实说明缺哪个源，不要硬编造 catalog 名
7. 输出结构化答案（summary + execution_process + sql + row_count + recommendations）
   - summary：必须基于实际返回的数据内容生成差异化总结。要求：
     a) 引用具体数据值（如具体户号、户名、数量、金额等）
     b) 指出数据特征（如最大值/最小值/分布规律/异常点）
     c) 每次总结的措辞和侧重点应有所不同，避免模板化
     d) 用自然语言表达，像分析师在汇报发现
     e) **必须涵盖所有数据分组/类型**（如 PsStatus 有 NA/NW/WBS/PD 等多种 object_type，summary 必须提到每种类型的代表记录）
   - execution_process：定位了哪个 L2、哪个实体、查了哪些字段
   - sql：执行的 SQL
   - row_count：返回行数
   - recommendations：3-5 个后续问题

## 上下文继承
- 对话历史中已定位同一 L2+实体：跳过步骤 1-4
- 用户换了业务域或实体：重新定位
- 用户加了筛选条件但实体不变：跳过定位，在 SQL 加 WHERE
"""

_KNOWLEDGE_FLOW_RULES = """
## 知识查询流程（不碰 SQL）
- 直接调 kg_api 的搜索/查询 action 获取信息
- 用自然语言组织答案，不要只输出原始 JSON
- 结构：定义/列表 -> 详细说明 -> 相关建议
"""

# 可用技能概要（自主模式时注入，让 LLM 自主 read_file 选技能）
_SKILL_OVERVIEW = """
## 可用技能（5能力包 + 5意图标签 + 场景剧本）
自主判断用户意图：先看是否命中"场景剧本"（业务分析任务，口径固化），命中则按剧本步骤执行；
否则用 read_file 读取最匹配的 /skills/{技能名}/SKILL.md 获取场景提示，按提示调能力包工具。

### 能力包（工具箱，按需挑用，不要求走完）
- locate：定位。锚定业务域L2、实体表、字段
- relate：关系。查实体关联和JOIN字段
- sql-exec：SQL执行。校验并执行SQL
- api取数：多源API联邦SQL(execute_api_sql)，WHERE/JOIN自动下推
- explore：搜索。搜实体/概念/字段

### 意图标签（场景提示词，选一个最匹配的）
- sql-query：SQL数据查询。查数量/统计/排名/趋势/对比/质检/具体字段/跨实体（含5类SQL写法提示）
- explain-concept：概念解释。问概念含义/区别
- explore-graph：浏览结构。问有哪些/包含什么/关系
- find-entity：反查字段。找字段/表位置
- trace-lineage：数据血缘。问数据来源/血缘

### 场景剧本（业务分析任务，命中即按剧本执行，口径固化。优先级高于意图标签）
- distribution-overload（配电重载过载分析）：用户问配电/变压器重载/过载/负载率/96点功率/户变关系/受影响用户时命中。模块化设计，用户可随时只查其中一段。
  口径（硬规则）：配电层面功率=SUM(计量点负荷)GROUP BY变压器+时间点；负载率=配电层面功率/容量×100%；重载=连续≥8点≥80%；过载=连续≥8点≥100%；默认最近30天，用户指定则用用户值；只统计在运变压器。
  关联链路：变压器.voltreg_eqp_id->调压设备.adj_volt_dev_id->dist_sta_id->台区->安装点.inst_id->计量点负荷（正式营配贯通链路，非编号近似）。
  完整剧本：read_file("/skills/scenarios/distribution-overload/SKILL.md")
- project-lifecycle-cost（项目预算与成本对比分析）：用户问"WBS预算/成本/超成本/超支/超预算/预算执行率/全生命周期成本/总成本/LCC"时命中。支持"所有WBS"或"指定项目"。
  口径（硬规则）：超成本(超计划)=actual_cost>planned_cost即variance>0；超预算=actual_cost>total_budget；预算执行率=actual/total_budget×100%；预算与成本分属两数据源，必须用get_entity_source_mode分发：预算走execute_entity_api(ES联邦dim+amt JOIN)，成本走execute_doris_sql(Doris)；JOIN键=wbs_element。各自锁定模式，空结果即停，不降级不重试其他模式。
  步骤：①get_entity_source_mode("dim_ps_wbs_budget")确认api_integration->execute_entity_api取wbs_element+total_budget+available_budget ②get_entity_source_mode("dim_ps_wbs_cost")确认sql_integration->execute_doris_sql取wbs_element+actual_cost+planned_cost+variance ③按wbs_element关联算执行率+余额+超计划标记 ④输出明细表+超成本清单+结论
  完整剧本：read_file("/skills/scenarios/project-lifecycle-cost/SKILL.md")
"""

def _load_skill_md(skill_name: str) -> str:
    """读取 SKILL.md 文件内容（去掉 frontmatter）。

    与 ReAct 模式共用同一份技能文件，避免双份维护。

    Args:
        skill_name: 技能名（如 "multi-hop-query"）

    Returns:
        SKILL.md 正文（去掉 ---...--- 头），文件不存在返回空字符串
    """
    if not skill_name:
        return ""
    from pathlib import Path as _Path
    skill_md = _Path(__file__).resolve().parent.parent.parent / "data" / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        # 子技能路由降级：distribution-overload-impact -> distribution-overload（共享同一份 SKILL.md）
        for suffix in ("-impact", "-power", "-link", "-verdict"):
            if skill_name.endswith(suffix):
                base = skill_name[:-len(suffix)]
                base_md = _Path(__file__).resolve().parent.parent.parent / "data" / "skills" / base / "SKILL.md"
                if base_md.exists():
                    skill_md = base_md
                    break
        if not skill_md.exists():
            return ""
    content = skill_md.read_text("utf-8")
    # 去掉 YAML frontmatter（---...---）
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            content = content[end + 3:].strip()
    return content


def _build_dynamic_system_prompt(skill_hint: str = "") -> str:
    """构建动态 system_prompt（按技能分段注入）。

    Plan-Execute 和 ReAct 共用此函数，技能知识统一来源 SKILL.md。
    不再走 skill_router 预分类：skill_hint 为空时注入全量技能概要，
    由 LLM 自主 read_file 选技能。

    Args:
        skill_hint: 可选技能名（如 "execute-sql" 续轮执行），为空时走自主模式
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    parts = [_BASE_ROLE.replace("__CURRENT_DATE__", date_str)]

    # 读 SKILL.md 替代 _SKILL_HINTS 字典，与 ReAct 模式共用同一份技能知识
    skill_md_content = _load_skill_md(skill_hint)
    if skill_md_content:
        parts.append(f"\n## 当前技能指南\n{skill_md_content}\n")

    if skill_hint == "execute-sql":
        parts.append("""
## 执行确认流程
用户确认执行上一轮的 SQL。直接调 kg_api(action="execute_sql") 执行，不要重新定位。
执行后输出结果总结。
""")
    elif skill_hint:
        # 指定了技能：
        # - 场景剧本(scenarios/*)自带步骤+口径，不注入通用 SQL 流程(其 locate->validate_safe_sql->execute_sql
        #   会与剧本的 get_entity_source_mode->execute_entity_api/execute_doris_sql 冲突，导致回退到 execute_sql)
        # - 其它技能(locate/sql-query 等)注入两套流程规则，LLM 按技能类型自主选用
        if not skill_hint.startswith("scenarios/"):
            parts.append(_SQL_FLOW_RULES)
            parts.append(_KNOWLEDGE_FLOW_RULES)
    else:
        # 自主模式：注入全量技能概要 + 两套流程规则，LLM 自主 read_file 选技能
        parts.append(_SKILL_OVERVIEW)
        parts.append(_SQL_FLOW_RULES)
        parts.append(_KNOWLEDGE_FLOW_RULES)

    parts.append(_COMMON_RULES)
    return "\n".join(parts)



# ---------------------------------------------------------------------------
# 3. Tools (6 个技能 + 1 个思考工具)
# ---------------------------------------------------------------------------

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# 结构化最终答案 schema（response_format 用）
class TupuFinalAnswer(BaseModel):
    """tupu 数据查询的最终结构化答案。"""
    summary: str = Field(description="一句话总结查询结果")
    execution_process: str = Field(description="执行过程描述：定位了哪个实体、查了哪些属性、SQL 逻辑")
    sql: str = Field(default="", description="查询用的 SQL 语句")
    row_count: int = Field(default=0, description="查询返回的数据行数（未执行填 0）")
    recommendations: list[str] = Field(default_factory=list, description="3-5 个推荐的后续问题")


# ---------------------------------------------------------------------------
# SQL 自动修复辅助函数（execute_sql action 用）
# ---------------------------------------------------------------------------

def _remove_column_from_select(sql: str, bad_col: str) -> str:
    """从 SELECT 语句中移除指定列（处理 Unknown column 错误）。

    处理形式：t0.col / col / `col` / t0.`col` / col AS alias
    只处理 SELECT 和 FROM 之间的字段列表，保留其他部分（WHERE/ORDER BY/LIMIT 等）
    """
    import re as _re
    if not sql or not bad_col:
        return sql
    m = _re.match(r'(\s*SELECT\s+)(.*?)(\s+FROM\s+.*)', sql, _re.IGNORECASE | _re.DOTALL)
    if not m:
        return sql
    prefix, col_list, suffix = m.group(1), m.group(2), m.group(3)
    parts = []
    depth = 0
    current = ""
    for ch in col_list:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())

    bad_col_lower = bad_col.lower()
    filtered = []
    for part in parts:
        check_part = part.strip()
        if _re.search(r'\s+AS\s+', check_part, _re.IGNORECASE):
            check_part = _re.split(r'\s+AS\s+', check_part, flags=_re.IGNORECASE)[0].strip()
        check_part = check_part.split(".")[-1].strip("`").strip()
        if bad_col_lower in check_part.lower() or bad_col_lower in part.lower():
            continue
        filtered.append(part)

    if not filtered:
        return sql
    new_col_list = ", ".join(filtered)
    return prefix + new_col_list + suffix


def _fix_aggregate_unknown_column(sql: str, bad_col: str) -> str:
    """修复聚合函数内的 Unknown column 错误。

    场景：LLM 生成 COUNT(elec_cons_cust_id)，但字段在物理表不存在。
    把含坏列的聚合函数整体替换为 COUNT(*)。
    """
    import re as _re
    if not sql or not bad_col:
        return sql
    pattern = _re.compile(
        r'(COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT)\s*\(\s*(?:DISTINCT\s+)?'
        r'[^()]*\b' + _re.escape(bad_col) + r'\b[^()]*?\s*\)',
        _re.IGNORECASE
    )
    new_sql, n = pattern.subn('COUNT(*)', sql)
    return new_sql if n > 0 else sql


def dispatch_kg_action(action: str, body: dict) -> dict:
    """kg_api 业务逻辑分发（@tool 和 MCP tool 共用，单一逻辑源）。action/参数见 kg_api docstring。"""
    from datetime import datetime as _dt
    _ts = _dt.now().strftime("%H:%M:%S")

    # 同进程直接调函数（避免 HTTP 自调自死锁）
    if action == "fetch_l1_l2_tree":
        from app.services.skill_injections import build_fetch_l1_l2_tree
        fn = build_fetch_l1_l2_tree()
        if not fn:
            return {"l1_list": [], "error": "查询函数不可用", "log": f"[{_ts}] 获取L1-L2树失败：查询函数不可用"}
        res = fn()
        l1_list = res.get("l1_list", []) if isinstance(res, dict) else []
        l2_count = sum(len((l1.get("l2_list") or l1.get("children") or [])) for l1 in l1_list)
        res["log"] = f"[{_ts}] 获取L1-L2层级树：共 {len(l1_list)} 个行业域(L1)，{l2_count} 个小类(L2)"
        return res

    elif action == "validate_l2":
        from app.api.kg_api import validate_l2, ValidateL2Request
        res = validate_l2(ValidateL2Request(**body))
        l2_name = (res or {}).get("l2_name", "") or body.get("l2_name", "")
        l2_id = (res or {}).get("l2_id", "")
        valid = (res or {}).get("valid", False)
        if valid:
            res["log"] = f"[{_ts}] 校验L2「{l2_name}」成功，锁定 L2_id={str(l2_id)[:8]}..."
        else:
            cands = (res or {}).get("candidates", []) or []
            cand_names = "、".join([str(c.get("name", "") if isinstance(c, dict) else c) for c in cands[:5]])
            res["log"] = f"[{_ts}] 校验L2「{l2_name}」未精确命中，候选：{cand_names or '无'}"
        return res

    elif action == "fetch_subgraph":
        from app.services.skill_injections import build_fetch_subgraph_by_l2
        fn = build_fetch_subgraph_by_l2()
        if not fn:
            return {"l2x_entities": [], "error": "查询函数不可用", "log": f"[{_ts}] 获取子图失败：查询函数不可用"}
        res = fn(body.get("l2_id", ""))
        ents = (res or {}).get("l2x_entities", []) if isinstance(res, dict) else []
        ent_names = "、".join([str(e.get("entity_name", "") if isinstance(e, dict) else e) for e in ents[:6]])
        res["log"] = f"[{_ts}] 获取L2子图：该小类下共 {len(ents)} 个实体（{ent_names}{'...' if len(ents) > 6 else ''}）"
        return res

    elif action == "validate_attributes":
        from app.api.kg_api import validate_attributes, ValidateAttrsRequest
        res = validate_attributes(ValidateAttrsRequest(**body))
        entity_code = (res or {}).get("entity_code", "") or body.get("entity_code", "")
        attrs = (res or {}).get("attributes", []) if isinstance(res, dict) else []
        attr_names = "、".join([str(a.get("attribute_name", "") if isinstance(a, dict) else a) for a in attrs[:8]])
        res["log"] = f"[{_ts}] 校验实体「{entity_code}」属性成功：命中 {len(attrs)} 个属性（{attr_names}{'...' if len(attrs) > 8 else ''}）"
        return res

    elif action == "fetch_join_expr":
        from app.services.skill_runnable import _build_fetch_join_expr_fn
        fn = _build_fetch_join_expr_fn()
        src = body.get("source_entity", "")
        tgt = body.get("target_entity", "")
        if fn:
            join_on = fn(src, tgt)
        else:
            join_on = ""
        if not join_on:
            join_on = f"{src}.cust_id = {tgt}.cust_id"
        return {"join_on": join_on, "source_entity": src, "target_entity": tgt,
                "log": f"[{_ts}] 查询关联关系：{src} ⋈ {tgt}，JOIN ON {join_on}"}

    elif action == "validate_safe_sql":
        from app.api.kg_api import validate_safe_sql, ValidateSafeSqlRequest
        res = validate_safe_sql(ValidateSafeSqlRequest(**body))
        safe = (res or {}).get("safe", False)
        sql_preview = (body.get("sql", "") or "")[:60].replace("\n", " ")
        if safe:
            res["log"] = f"[{_ts}] SQL安全校验通过：{sql_preview}..."
        else:
            reason = (res or {}).get("reason", "") or (res or {}).get("error", "")
            res["log"] = f"[{_ts}] SQL安全校验未通过：{reason or '未知原因'}"
        return res

    elif action == "execute_sql":
        # 硬守卫：若带 entity_code，校验 source_mode 必须为 physical_table；并取 per-entity 数据源
        entity_code_exec = body.get("entity_code", "")
        data_source_id = None
        if entity_code_exec:
            from app.models.base import Entity
            from app.core.database import SessionLocal
            _db_guard = SessionLocal()
            try:
                _ent = _db_guard.query(Entity).filter(Entity.entity_code == entity_code_exec).first()
                if _ent:
                    if _ent.source_mode and _ent.source_mode != "physical_table":
                        _hint_tool = "execute_entity_api" if _ent.source_mode == "api_integration" else "execute_doris_sql"
                        return {"error": f"模式锁：实体 {entity_code_exec} source_mode={_ent.source_mode}，禁止 execute_sql，请用 {_hint_tool}",
                                "log": f"[{_ts}] 模式守卫拦截：{entity_code_exec} 非 physical_table，不降级不重试"}
                    data_source_id = str(_ent.data_source_id) if _ent.data_source_id else None
            finally:
                _db_guard.close()
        from app.services.sql_executor import build_execute_query_fn
        import re as _re_exec
        exec_fn = build_execute_query_fn(data_source_id=data_source_id)
        if not exec_fn:
            return {"error": "执行函数不可用", "log": f"[{_ts}] SQL执行失败：执行函数不可用"}
        sql_text = body.get("sql", "")
        if not sql_text or "{{" in sql_text:
            return {"error": f"SQL 含未解析占位符或为空: {sql_text[:60]}",
                    "log": f"[{_ts}] SQL执行失败：SQL 含未解析占位符或为空"}

        # 自动修复 "Unknown column" 错误（从 plan_execute 合并而来）
        # 1. 聚合函数内的坏列：COUNT(bad_col) -> COUNT(*)
        # 2. SELECT 字段列表中的坏列：移除该字段
        max_repair = 30
        current_sql = sql_text
        repair_count = 0
        res = None
        fallback_used = False
        while True:
            try:
                res = exec_fn(current_sql)
            except Exception as e:
                err_msg = str(e)
                m = _re_exec.search(r"Unknown column '([^']+)'", err_msg)
                if m and repair_count < max_repair:
                    bad_col = m.group(1)
                    new_sql = _fix_aggregate_unknown_column(current_sql, bad_col)
                    if new_sql == current_sql:
                        new_sql = _remove_column_from_select(current_sql, bad_col)
                    if new_sql != current_sql:
                        current_sql = new_sql
                        repair_count += 1
                        continue
                _err = str(e)
                _hint = ""
                if "doesn't exist" in _err or "1146" in _err:
                    import re as _re1146
                    _tm = _re1146.search(r"Table '[^']*?\.([^']+)'", _err)
                    _tn = _tm.group(1) if _tm else "该表"
                    _hint = f" | 提示：表「{_tn}」不存在于数据库，请用 kg_api(action=list_tables, params='{{}}') 查真实表名，或用 search_entities 重新定位"
                res = {"error": f"SQL执行异常: {e}{_hint}", "log": f"[{_ts}] SQL执行异常：{e}{_hint}"}
                break
            if isinstance(res, dict):
                if res.get("error"):
                    err_msg = str(res.get("error", ""))
                    m = _re_exec.search(r"Unknown column '([^']+)'", err_msg)
                    if m and repair_count < max_repair:
                        bad_col = m.group(1)
                        new_sql = _fix_aggregate_unknown_column(current_sql, bad_col)
                        if new_sql == current_sql:
                            new_sql = _remove_column_from_select(current_sql, bad_col)
                        if new_sql != current_sql:
                            current_sql = new_sql
                            repair_count += 1
                            continue
                    if not fallback_used and repair_count >= max_repair:
                        fallback_used = True
                        tbl_m = _re_exec.search(r'FROM\s+(\S+)', current_sql, _re_exec.IGNORECASE)
                        lim_m = _re_exec.search(r'LIMIT\s+(\d+)', current_sql, _re_exec.IGNORECASE)
                        if tbl_m:
                            tbl = tbl_m.group(1).rstrip(';')
                            lim = lim_m.group(1) if lim_m else "100"
                            current_sql = f"SELECT * FROM {tbl} LIMIT {lim}"
                            repair_count += 1
                            continue
                    _hint2 = ""
                    if "doesn't exist" in err_msg or "1146" in err_msg:
                        import re as _re1146b
                        _tm2 = _re1146b.search(r"Table '[^']*?\.([^']+)'", err_msg)
                        _tn2 = _tm2.group(1) if _tm2 else "该表"
                        _hint2 = f" | 提示：表「{_tn2}」不存在，请用 kg_api(action=list_tables) 查真实表名"
                    res["error"] = str(res.get("error", err_msg)) + _hint2
                    res["log"] = f"[{_ts}] SQL执行失败：{err_msg}{_hint2}"
                else:
                    row_cnt = res.get("row_count", 0)
                    cols = res.get("columns", []) or []
                    repair_note = f"（自动修复 {repair_count} 次后成功）" if repair_count > 0 else ""
                    res["log"] = f"[{_ts}] SQL执行成功{repair_note}：返回 {row_cnt} 行数据，字段（{', '.join(cols[:6])}{'...' if len(cols) > 6 else ''}）"
                    res["sql"] = current_sql
            break
        return res

    elif action == "search_concepts":
        # 搜概念定义（explain-concept 技能用）
        from app.core.database import SessionLocal
        from sqlalchemy import text
        keyword = (body.get("keyword") or "").strip()
        db = SessionLocal()
        try:
            if keyword:
                rows = db.execute(text(
                    "SELECT id, name, level, description FROM kg_concepts "
                    "WHERE name LIKE :kw OR description LIKE :kw ORDER BY level, sort_order LIMIT 20"
                ), {"kw": f"%{keyword}%"}).fetchall()
            else:
                rows = db.execute(text(
                    "SELECT id, name, level, description FROM kg_concepts ORDER BY level, sort_order LIMIT 20"
                )).fetchall()
            concepts = [
                {"id": str(r[0]), "name": r[1] or "", "level": r[2], "description": r[3] or ""}
                for r in rows
            ]
            kw = keyword or "(全部)"
            return {"concepts": concepts,
                    "log": f"[{_ts}] 搜概念「{kw}」：命中 {len(concepts)} 条定义"}
        finally:
            db.close()

    elif action == "search_entities":
        # 搜实体/字段（find-entity 技能用）
        from app.core.database import SessionLocal
        from sqlalchemy import text
        import json as _json2
        keyword = (body.get("keyword") or "").strip()
        entity_code = (body.get("entity_code") or "").strip()
        db = SessionLocal()
        try:
            if entity_code:
                # 查指定实体的属性列表（数据字典）
                row = db.execute(text(
                    "SELECT entity_code, entity_name, entity_en_name, description, properties_schema "
                    "FROM kg_entities WHERE entity_code = :code LIMIT 1"
                ), {"code": entity_code}).fetchone()
                if not row:
                    return {"entity_code": entity_code, "attributes": [], "error": "实体不存在"}
                props = row[4]
                if isinstance(props, str):
                    try: props = _json2.loads(props)
                    except Exception: props = []
                attrs = []
                if isinstance(props, list):
                    for p in props:
                        if isinstance(p, dict):
                            attrs.append({
                                "attribute_code": str(p.get("code") or p.get("attribute_code") or ""),
                                "attribute_name": str(p.get("name") or p.get("attribute_name") or ""),
                            })
                return {"entity_code": row[0], "entity_name": row[1] or "", "entity_en_name": row[2] or "",
                        "description": row[3] or "", "attributes": attrs,
                        "log": f"[{_ts}] 查实体「{entity_code}」数据字典：共 {len(attrs)} 个属性（物理表名: {row[2] or '未知'}）"}
            elif keyword:
                # 按关键词搜实体名/实体描述/属性名（含物理表名 entity_en_name）
                rows = db.execute(text(
                    "SELECT entity_code, entity_name, entity_en_name, description FROM kg_entities "
                    "WHERE entity_code LIKE :kw OR entity_name LIKE :kw OR description LIKE :kw "
                    "OR entity_en_name LIKE :kw "
                    "ORDER BY sort_order LIMIT 20"
                ), {"kw": f"%{keyword}%"}).fetchall()
                # 再搜源字段表（kg_source_field_imports）
                field_rows = db.execute(text(
                    "SELECT DISTINCT table_en, table_cn, field_en, field_cn "
                    "FROM kg_source_field_imports "
                    "WHERE field_cn LIKE :kw OR field_en LIKE :kw OR table_cn LIKE :kw "
                    "LIMIT 20"
                ), {"kw": f"%{keyword}%"}).fetchall()
                return {
                    "entities": [
                        {"entity_code": r[0], "entity_name": r[1] or "", "entity_en_name": r[2] or "", "description": r[3] or ""}
                        for r in rows
                    ],
                    "fields": [
                        {"table_en": r[0], "table_cn": r[1] or "", "field_en": r[2], "field_cn": r[3] or ""}
                        for r in field_rows
                    ],
                    "log": f"[{_ts}] 搜实体/字段「{keyword}」：命中 {len(rows)} 个实体、{len(field_rows)} 个源字段",
                }
            else:
                rows = db.execute(text(
                    "SELECT entity_code, entity_name, entity_en_name FROM kg_entities ORDER BY sort_order LIMIT 50"
                )).fetchall()
                return {"entities": [{"entity_code": r[0], "entity_name": r[1] or "", "entity_en_name": r[2] or ""} for r in rows],
                        "log": f"[{_ts}] 列出全部实体：共 {len(rows)} 个"}
        finally:
            db.close()

    elif action == "get_entity_relations":
        # 查实体关联关系（explore-graph / multi-hop 技能用，含物理表名）
        from app.core.database import SessionLocal
        from sqlalchemy import text
        entity_code = (body.get("entity_code") or "").strip()
        db = SessionLocal()
        try:
            if entity_code:
                rows = db.execute(text(
                    "SELECT e1.entity_code as src, e1.entity_en_name as src_table, "
                    "e2.entity_code as tgt, e2.entity_en_name as tgt_table, "
                    "r.relation_name, r.join_expr, r.source_field_name, r.target_field_name, "
                    "r.cardinality, r.direction "
                    "FROM kg_entity_relations r "
                    "JOIN kg_entities e1 ON r.source_entity_id = e1.id "
                    "JOIN kg_entities e2 ON r.target_entity_id = e2.id "
                    "WHERE e1.entity_code = :code OR e2.entity_code = :code"
                ), {"code": entity_code}).fetchall()
            else:
                rows = db.execute(text(
                    "SELECT e1.entity_code as src, e1.entity_en_name as src_table, "
                    "e2.entity_code as tgt, e2.entity_en_name as tgt_table, "
                    "r.relation_name, r.join_expr, r.source_field_name, r.target_field_name, "
                    "r.cardinality, r.direction "
                    "FROM kg_entity_relations r "
                    "JOIN kg_entities e1 ON r.source_entity_id = e1.id "
                    "JOIN kg_entities e2 ON r.target_entity_id = e2.id "
                    "LIMIT 50"
                )).fetchall()
            relations = [
                {"source": r[0], "source_table": r[1] or "", "target": r[2], "target_table": r[3] or "",
                 "relation_name": r[4] or "", "join_expr": r[5] or "", "source_field": r[6] or "",
                 "target_field": r[7] or "", "cardinality": r[8] or "", "direction": r[9] or ""}
                for r in rows
            ]
            ent_label = entity_code or "(全部)"
            return {"relations": relations,
                    "log": f"[{_ts}] 查实体关联「{ent_label}」：共 {len(relations)} 条关系"}
        finally:
            db.close()

    elif action == "list_tables":
        # 列出知识图谱实体对应的物理表名（entity_en_name），过滤掉非业务表
        from app.core.database import SessionLocal
        from sqlalchemy import text
        keyword = (body.get("keyword") or "").strip()
        db = SessionLocal()
        try:
            # 只返回 kg_entities 中定义的 entity_en_name（物理表名），避免 LLM 用错表
            if keyword:
                rows = db.execute(text(
                    "SELECT DISTINCT entity_en_name, entity_name, entity_code FROM kg_entities "
                    "WHERE entity_en_name IS NOT NULL AND entity_en_name != '' "
                    "AND (entity_en_name LIKE :kw OR entity_name LIKE :kw OR entity_code LIKE :kw) "
                    "ORDER BY entity_en_name LIMIT 50"
                ), {"kw": f"%{keyword}%"}).fetchall()
            else:
                rows = db.execute(text(
                    "SELECT DISTINCT entity_en_name, entity_name, entity_code FROM kg_entities "
                    "WHERE entity_en_name IS NOT NULL AND entity_en_name != '' "
                    "ORDER BY entity_en_name LIMIT 100"
                )).fetchall()
            tables = [{"table_name": r[0], "entity_name": r[1] or "", "entity_code": r[2] or ""} for r in rows]
            kw_label = f"含「{keyword}」" if keyword else "(全部)"
            return {"tables": tables, "count": len(tables),
                    "log": f"[{_ts}] 列出知识图谱物理表{kw_label}：共 {len(tables)} 张表"}
        finally:
            db.close()

    elif action == "get_entity_source_mode":
        # NL2API 路由：查询实体的数据源模式（sql_integration/api_integration/physical_table）
        from app.api.kg_api import get_entity_source_mode
        entity_code = body.get("entity_code", "")
        res = get_entity_source_mode(entity_code)
        source_mode = res.get("source_mode", "physical_table")
        res["log"] = f"[{_ts}] 实体「{entity_code}」数据源模式={source_mode}"
        return res

    elif action == "execute_api_sql":
        # 多源API联邦SQL：DuckDB 执行，WHERE/JOIN 自动下推到 API 参数
        from app.services.duckdb_engine import execute_sql as _exec_api_sql, load_endpoints_from_db
        from app.core.database import SessionLocal
        sql_text = body.get("sql", "").strip()
        if not sql_text:
            return {"error": "缺少 sql 参数", "log": f"[{_ts}] API联邦查询失败：缺少sql"}
        db = SessionLocal()
        try:
            endpoints = load_endpoints_from_db(db)
            if not endpoints:
                return {"error": "尚未配置任何API端点", "log": f"[{_ts}] API联邦查询失败：无端点"}
            result = _exec_api_sql(sql_text, endpoints)
            pushed = result.get("pushed_down", {})
            result["log"] = f"[{_ts}] API联邦SQL执行成功：返回 {result.get('row_count', 0)} 行，下推表 {list(pushed.keys())}"
            return result
        except Exception as e:
            return {"error": f"API联邦查询异常: {e}", "log": f"[{_ts}] API联邦查询异常：{e}"}
        finally:
            db.close()

    elif action == "execute_entity_api":
        # 对象API执行：取EntityApiMapping，build_sql_with_filters拼接+下推，duckdb_engine执行
        from app.models.base import Entity, EntityApiMapping
        from app.services.duckdb_engine import execute_sql as _exec_api_sql, load_endpoints_from_db, build_sql_with_filters
        from app.core.database import SessionLocal
        entity_code = body.get("entity_code", "")
        filters = body.get("filters", {}) or {}
        if not entity_code:
            return {"error": "缺少 entity_code", "log": f"[{_ts}] 对象API执行失败：缺少entity_code"}
        db = SessionLocal()
        try:
            ent = db.query(Entity).filter(Entity.entity_code == entity_code).first()
            if not ent:
                return {"error": f"对象不存在: {entity_code}", "log": f"[{_ts}] 对象不存在：{entity_code}"}
            # 硬守卫：source_mode 必须为 api_integration
            if ent.source_mode and ent.source_mode != "api_integration":
                _hint_tool = "execute_sql" if ent.source_mode == "physical_table" else "execute_doris_sql"
                return {"error": f"模式锁：实体 {entity_code} source_mode={ent.source_mode}，禁止 execute_entity_api，请用 {_hint_tool}",
                        "log": f"[{_ts}] 模式守卫拦截：{entity_code} 非 api_integration，不降级不重试"}
            m = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == ent.id).first()
            if not m:
                return {"error": f"对象未配置API映射: {entity_code}", "log": f"[{_ts}] 对象未配置API映射：{entity_code}"}
            sql = build_sql_with_filters(m.pseudo_sql, filters)
            endpoints = load_endpoints_from_db(db)
            if not endpoints:
                return {"error": "尚未配置任何API端点", "log": f"[{_ts}] 无API端点"}
            result = _exec_api_sql(sql, endpoints)
            pushed = result.get("pushed_down", {})
            result["log"] = f"[{_ts}] 对象「{entity_code}」API执行成功：返回 {result.get('row_count', 0)} 行，下推 {list(pushed.keys())}"
            return result
        except Exception as e:
            return {"error": f"对象API执行异常: {e}", "log": f"[{_ts}] 对象API执行异常：{e}"}
        finally:
            db.close()

    elif action == "execute_doris_sql":
        # Doris 整合执行：sql_integration 场景。entity_code 优先（自动加载 integration_sql + filters 下推），
        # 仅当未给 entity_code 时才用调用方自建 sql（agent 可能猜错 catalog/表路径）
        from app.services.doris_engine import execute_sql as _doris_exec, build_sql_with_filters
        entity_code = body.get("entity_code", "")
        filters = body.get("filters", {}) or {}
        sql_text = ""
        doris_catalog = None  # entity_code 模式下取实体配置的 catalog，执行前 SWITCH（对齐 REST 路径）
        if entity_code:
            from app.models.base import Entity
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                ent = db.query(Entity).filter(Entity.entity_code == entity_code).first()
                if not ent:
                    return {"error": f"对象不存在: {entity_code}", "log": f"[{_ts}] Doris执行失败：对象不存在 {entity_code}"}
                # 硬守卫：entity_code 模式时 source_mode 必须为 sql_integration
                if ent.source_mode and ent.source_mode != "sql_integration":
                    _hint_tool = "execute_sql" if ent.source_mode == "physical_table" else "execute_entity_api"
                    return {"error": f"模式锁：实体 {entity_code} source_mode={ent.source_mode}，禁止 execute_doris_sql，请用 {_hint_tool}",
                            "log": f"[{_ts}] 模式守卫拦截：{entity_code} 非 sql_integration，不降级不重试"}
                sql_text = (ent.integration_sql or "").strip()
                if not sql_text:
                    return {"error": f"对象未配置 integration_sql: {entity_code}", "log": f"[{_ts}] Doris执行失败：{entity_code} 无 integration_sql"}
                doris_catalog = ent.doris_catalog or None
            finally:
                db.close()
            sql_text = build_sql_with_filters(sql_text, filters)
        else:
            sql_text = body.get("sql", "").strip()
        if not sql_text:
            return {"error": "缺少 sql 或 entity_code 参数", "log": f"[{_ts}] Doris查询失败：缺少sql/entity_code"}
        try:
            result = _doris_exec(sql_text, catalog=doris_catalog)
            _rc = result.get("row_count", 0)
            if _rc == 0:
                result["hint"] = "未查到相关数据"
                result["log"] = f"[{_ts}] Doris「{entity_code or 'inline'}」SQL执行成功：返回 0 行，已停止，不降级不重试"
            else:
                result["log"] = f"[{_ts}] Doris「{entity_code or 'inline'}」SQL执行成功：返回 {_rc} 行，filters={list(filters.keys())}"
            return result
        except Exception as e:
            return {"error": f"Doris查询异常: {e}", "log": f"[{_ts}] Doris查询异常：{e}"}

    return {"error": f"未知 action: {action}"}


@tool
def kg_api(action: str, params: str) -> dict:
    """调用知识图谱 API 查询数据。查 L1-L2 树/子图/JOIN/校验/执行 SQL/搜概念/搜实体/查关系 都用此工具。

    Args:
        action: API 动作（15个）：fetch_l1_l2_tree/validate_l2/fetch_subgraph/validate_attributes/fetch_join_expr/validate_safe_sql/execute_sql/search_concepts/search_entities/get_entity_relations/list_tables/get_entity_source_mode/execute_api_sql/execute_entity_api/execute_doris_sql
        params: JSON 格式参数字符串，如 '{"l2_id":"xxx"}'，无参数传 '{}'

    Returns:
        dict: 查询结果 JSON
    """
    import json as _json
    try:
        body = _json.loads(params) if params and params.strip() else {}
    except Exception:
        body = {}
    return dispatch_kg_action(action, body)



# ---------------------------------------------------------------------------
# 4. Agent 工厂函数
# ---------------------------------------------------------------------------


async def create_tupu_agent(checkpointer=None):
    """创建 tupu DeepAgent（业务工具走 MCP，与 deepagent 解耦）

    业务工具（fetch_l1_l2_tree 等 16 个）通过 MCP client 从 MCP server 加载，
    不再用进程内 @tool。框架工具（read_file/write_todos/ls）由 deepagents 中间件自动注入。

    Args:
        checkpointer: LangGraph checkpointer（AsyncSqliteSaver/PostgresSaver/MemorySaver）

    Returns:
        CompiledStateGraph (DeepAgent)
    """
    from deepagents import create_deep_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient

    from app.services.llm_client import get_chat_model
    # streaming=True 让 on_chat_model_stream 产出 token 事件，避免长时间无反馈（对齐数据问答修复）
    model = get_chat_model(temperature=0.0, streaming=True)

    # MCP client 加载业务工具（16 个 tool，走 SSE，与 deepagent 解耦）
    mcp_client = MultiServerMCPClient({
        "tupu-kg": {"url": "http://127.0.0.1:28000/mcp/sse", "transport": "sse"}
    })
    mcp_tools = await mcp_client.get_tools()

    from deepagents.backends import StateBackend
    from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
    backend = StateBackend()
    # 排除框架自动注入的文件系统/shell 工具，避免 LLM 绕业务链路瞎翻文件致死循环
    # 保留 read_file（读 /skills/SKILL.md 剧本必需）、write_todos（任务规划）、ls（看剧本目录）
    excluded_mw = _ToolExclusionMiddleware(excluded=frozenset({
        "grep",          # 搜文件内容，业务问答无用，曾导致 LLM 翻配置找库名绕死循环
        "glob",          # 列文件，同上
        "write_file",    # 写文件，业务问答无用
        "edit_file",     # 改文件，业务问答无用
        "execute",       # 执行 shell 命令，危险且无用
    }))

    agent = create_deep_agent(
        model=model,
        tools=mcp_tools,
        system_prompt=_build_dynamic_system_prompt(),
        state_schema=TupuAgentState,
        checkpointer=checkpointer,
        backend=backend,
        skills=["/skills/"],
        middleware=[excluded_mw],
    )

    return agent


def build_skill_system_message(skill_name: str = "") -> str:
    """构建技能级 system 指令（按请求注入到 messages 中）。

    skill_name 为空时走自主模式（注入全量技能概要，LLM 自主选技能）；
    传入技能名时注入对应 SKILL.md 指南。
    """
    return _build_dynamic_system_prompt(skill_hint=skill_name)


# ---------------------------------------------------------------------------
# 5. 全局 Agent 实例（单例，带 checkpointer）
# ---------------------------------------------------------------------------

_GLOBAL_AGENT = None
_GLOBAL_CHECKPOINTER = None

_CHECKPOINT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "deepagent_checkpoints.db"
)


async def get_tupu_agent():
    """获取 tupu DeepAgent 单例（自由规划问答用，ReAct 模式）"""
    global _GLOBAL_AGENT, _GLOBAL_CHECKPOINTER
    if _GLOBAL_AGENT is None:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        import aiosqlite
        os.makedirs(os.path.dirname(_CHECKPOINT_DB), exist_ok=True)
        _GLOBAL_CHECKPOINTER = AsyncSqliteSaver(aiosqlite.connect(_CHECKPOINT_DB))
        _GLOBAL_AGENT = await create_tupu_agent(checkpointer=_GLOBAL_CHECKPOINTER)
        logger.info(f"[DeepAgent] tupu ReAct agent 已创建, checkpoint={_CHECKPOINT_DB}")
    return _GLOBAL_AGENT
