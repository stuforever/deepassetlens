"""
Tupu DeepAgent -- 基于 LangGraph 原生 create_react_agent 的问数流程

架构:
  create_deep_agent(model, tools=mcp_tools, system_prompt, state_schema, checkpointer, backend, skills)
    ├─ 业务工具：16 个单一职责 MCP 工具（app/mcp_server.py，走 SSE /mcp/sse，不再用进程内 @tool）
    ├─ 框架工具：read_file / write_todos / ls（deepagents 中间件自动注入）
    └─ skills=["/skills/"]  虚拟文件系统挂载 SKILL.md

  ReAct 模式：LLM 自主规划步骤、自主调 MCP 工具、边推理边输出 token
  checkpointer: AsyncSqliteSaver (持久化，支持多轮上下文继承)
  SSE: astream_events(version="v2") 推送 think/token/trace/sql_result/final/done
"""
from __future__ import annotations

import logging
import os
import asyncio
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, TypedDict

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

import operator
from functools import lru_cache

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
    # v3.5 结构化会话上下文：跨轮继承客户范围，不依赖 LLM 指代消解概率
    last_scope: NotRequired[dict]                             # {customer_names: [...], ordered: bool, commitment: str, source_turn_id: str}
    # 评审 P1-5 受控上下文跨轮：确定性代码在路由成功后写回 checkpoint，供下轮"连续上下文优先"
    last_skill: NotRequired[str]                              # 本轮命中场景 skill_id（generic 时为 None）
    last_step: NotRequired[str]                               # 本轮命中步骤 id


def _tool_registry_frozen():
    from app.services.permission_vocab import TOOL_REGISTRY
    return TOOL_REGISTRY


TOOL_REGISTRY_FROZEN = _tool_registry_frozen()


class TupuAgentContext(TypedDict):
    """F4: DeepAgent 原生运行时上下文（不进 checkpoint，不混入消息历史）。

    通过 config["configurable"]["last_scope"] 传递（astream_events 不支持 context 参数），
    DecisionGateMiddleware 从 runtime.config 读取。
    """
    last_scope: NotRequired[dict]  # 用户指定的可信范围（source=user_input）
    user_sub: NotRequired[str]     # 当前用户 OIDC sub
    session_id: NotRequired[str]   # 会话 ID
    # 评审 P2（二轮）：受控执行契约也经 runtime.context 注入（SkillPolicyMiddleware 唯一执行边界）。
    # 用 Any 声明避免 QueryContract 循环导入；运行时 Policy 读取 runtime.context["contract"]。
    contract: NotRequired[Any]     # QueryContract（skill_policy 依赖）


# ---------------------------------------------------------------------------
# 2. System Prompt (按技能分段注入, 降低 LLM 认知负担)
# ---------------------------------------------------------------------------

from datetime import datetime
from langchain.agents.middleware.types import AgentMiddleware

_BASE_ROLE = """你是 tupu 数据智能问答平台的助手，专注于电力行业数据图谱问答。
当前日期：__CURRENT_DATE__
平台版本：0.17.0
"""

_SOURCE_MODE_DISPATCH_RULES = """
## 数据源模式路由（取数前必查，铁律）
执行取数前，调一次 `batch_entity_source_mode(entity_codes)` 批量查询 SQL 涉及的**所有表**的数据源模式，按返回的 `recommended_tool` 选执行工具。**只调一次批量接口**，不要逐表查询：
- `recommended_tool=execute_sql`（全部 physical_table）-> `execute_sql(sql, entity_code)`（传主表 entity_code）
- `recommended_tool=execute_entity_api`（任一 api_integration）-> `execute_entity_api(entity_code, filters)`（多源API联邦，覆盖面最广）
- `recommended_tool=execute_doris_sql`（任一 sql_integration，无 api_integration）-> `execute_doris_sql(entity_code, filters)`（Doris 联邦）
【硬规则】recommended_tool 一经确认，只能用对应工具。返回空结果(row_count=0)=数据不存在，直接回复"未查到相关数据"，禁止降级到其他工具重试。
"""

_COMMON_RULES = """
## 重要规则
1. 不要用 glob/ls 探索文件系统，直接用只读工具定位业务域与表（fetch_l1_l2_tree / search_entities / list_tables / get_entity_relations）
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
**前提：仅当未命中场景剧本时执行本流程。若已 read_file 读取 `scenarios/*` 剧本，直接按剧本步骤执行（剧本已含表结构、关联键、SQL 模板），跳过下面步骤 1-5 的定位/搜实体（fetch_l1_l2_tree/validate_l2/fetch_subgraph/validate_attributes/fetch_join_expr），仅在剧本 SQL 基础上按用户过滤条件加 WHERE。**
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
   **枚举列取样（G3）**：拼 WHERE/GROUP BY 前，对分类/状态/类型/枚举类列先调 sample_column_values(entity_code, column) 查真实枚举值+频次，禁止凭经验猜测（如「状态」值域），按 TOP 值选择过滤口径。
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
7. 输出最终结论（结论 + 关键发现 + 建议）
   - 当工具返回 result_available_for_ui=true（完整数据已推前端查询结果表）时：
     **禁止在最终回答里输出原始查询明细、前 N 行预览、或与结果表同字段的 Markdown 表格**。
     只写：结论（2-3 句）、关键发现（具体数据特征/异常点）、风险或限制（如有）、后续建议，
     并明确写一句”完整明细见下方查询结果表”。
   - 结论必须基于实际返回的数据内容生成差异化总结。要求：
     a) 引用具体数据值（如具体户号、户名、数量、金额等）
     b) 指出数据特征（如最大值/最小值/分布规律/异常点）
     c) 每次总结的措辞和侧重点应有所不同，避免模板化
     d) 用自然语言表达，像分析师在汇报发现
     e) **必须涵盖所有数据分组/类型**（如 PsStatus 有 NA/NW/WBS/PD 等多种 object_type，summary 必须提到每种类型的代表记录）
     f) **样本≠全量（硬规则）**：只能对 row_count 下全量结论（如”共 101 条”）；对行内字段（如”单路供电””状态正常””10kV”）只能说”样本显示”（如”样本显示均为单路供电”）。要输出”全部正常 / 全部单路供电 / 所有 X 均 Y”类全量结论，必须由 SQL 显式聚合统计（COUNT/GROUP BY）提供证据后再下。
   - recommendations：3-5 个后续问题
   【禁止】最终回答里**不得**出现”执行过程””命中场景剧本””关联链路””判定逻辑””row_count””SQL 语句”等内部 trace，也不得复述明细数据或制作明细表格——这些已通过执行过程区与查询结果表实时展示给用户，重复输出会污染答案。

## 上下文继承
- 对话历史中已定位同一 L2+实体：跳过步骤 1-4
- 用户换了业务域或实体：重新定位
- 用户加了筛选条件但实体不变：跳过定位，在 SQL 加 WHERE
"""

# v3.2 下一步判断闸门 feature flag：批13-W W-4a 起改配置化——
# 装配期调 capability_config.get_decision_gate_config()（TUPU_DECISION_GATE=1 环境变量保留为
# 启动兜底；未设时以管理页 decision_gate.enabled 为准，默认关=代码基准）。
# 本模块级常量仅保留为 env 兜底快照（供导入方兼容读取），装配判断以函数内动态读为准。
_DECISION_GATE_ENABLED = os.getenv("TUPU_DECISION_GATE", "") == "1"

# 下一步判断：模型每次调用工具前，须在同一条 AIMessage 的 content 里写明"为什么执行这一步"，
# 再带工具调用。后端把这段 content 原样作为 decision.committed 推给前端，按 tool_call_id 绑定到该步，
# 默认可见（不藏折叠区）。不再展示 reasoning_content、不后端拼接"准备调用 XX"假理由。
_DECISION_GATE_RULES = """
## 下一步判断（每次工具调用前必写，同轮 content）
**每次调用工具前，必须在同一轮回复的 content 里先写"下一步判断"，再带工具调用。一条回复只调用一个工具。**
格式（严格遵守，字段名不可改）：
【下一步判断】
已知: <列出已获得的具体信息：用户要求 + 前序步骤的真实结果（数据/结论），不要笼统说"已有信息">
判断: <两段式：① 已知信息是否充分支撑用户问题？如不充分，具体缺什么；② 本步要补什么信息、为什么用这个工具>
因此: 调用 <本轮工具名>。

规则：
- "下一步判断"与工具调用必须在**同一轮**（同一条 AIMessage 的 content + tool_calls）。
- **一条回复只调用一个工具**：不得在同一轮发起多个 tool_call；需要多步时分多轮顺序调用。
- "因此"行写的工具名必须与实际调用的工具名一致。
- **"判断"必须评估信息充分性**：如果前序结果不足以回答用户问题，先说明缺什么，再调用工具补齐；不得在信息不足时直接给出结论。判断要有逻辑链：已知→缺什么→本步补什么→为什么用这个工具。
- **所有工具调用**（搜索实体/校验L2/读技能/校验SQL/execute_sql 等）都被闸门校验：没写"下一步判断"、格式不全、"因此"工具名不符、或一轮多工具，都会被拒绝（原工具不执行），须按拒绝提示补判后重发（补判会生成新的工具调用）。
- 调用**取数工具（execute_sql / execute_doris_sql / execute_entity_api / execute_api_sql）时**，"下一步判断"后必须额外写一行范围（四个工具都要写，缺"范围:"行会被闸门拒绝、原工具不执行，白白多一轮）：
  范围: <客户名精确集合，逗号分隔，如 客户001,客户003；无客户限定写 无>
  其中 execute_sql 的 SQL `cust_name IN (...)` 必须是该范围的子集，不得查声明外的客户（防"其他不要检索"越界）；其余取数工具仅作显式声明——非客户域查询直接写 无。无客户限定写 无（闸门跳过范围校验）。范围越界会被拒绝，补判后仍越界则阻断，不再重试 execute_sql，基于已有信息回答或说明无法完成。
"""

_DATA_COMPLETENESS_RULES = """
## 数据完整性规则（硬规则，违反即错误）
工具返回数据时，content 开头会有【数据已完整获取】指令，JSON 含结构化契约字段：
- row_count：完整结果数（不是预览行数）
- returned_rows：前端实际拿到的行数（result_available_for_ui=true 时=row_count，完整数据）
- is_preview：**前端接收的数据是否被截断**；result_available_for_ui=true 时前端拿到完整数据，is_preview=false
- llm_is_preview：true=你（模型）只拿到前 llm_preview_row_count 行分析样本，false=全量给了你
- llm_preview_row_count：你的分析样本行数（默认 10）
- result_available_for_ui：true=完整数据已推前端查询结果表展示

【展示边界：明细只由前端查询结果表展示一次】
- 前 10 行仅是你的**分析样本**，不是面向用户的展示数据：不得把该样本复述为"明细如下"，不得用该样本制作预览表格。
- result_available_for_ui=true 时，最终回答只写结论、关键发现、风险/限制、后续建议，并明确写"完整明细见下方查询结果表"；禁止输出与结果表同字段的 Markdown 明细表。

1. **llm_is_preview=true 且 result_available_for_ui=true**：数据已完整获取，只是给你的分析样本截断了。row_count 就是全部数量。禁止分页重查、禁止分段查询（如按台区 020-029、030-039 逐段查）、禁止调用 task 子代理。直接基于 row_count 和样本写结论。
2. **row_count >= 500 且 _limit_reached=true**：可能还有更多数据。可提示用户缩小范围，但不要无限分页重查。
3. **"所有"/"全部"类查询**（如"所有用电户与配变户变关系"）：一次查询拿到结果即完成，row_count 就是全部数量。禁止把"所有"拆成多段分别查询。
4. **样本行数≠数据不完整**：llm_preview_row_count=10 只是你的分析样本，完整数据已推前端查询结果表。LLM 只需引用 row_count 和样本特征写结论，不需要把明细行重新搬运成表格。
5. **task 子代理仅限定位类委派（批13-Z 规格）**：task 只用于 SKILL.md 声明 allow_subagents 的场景按 capability_policies.subagents 规格做定位类只读委派（当前仅 entity_locator 窄集）；禁止用 task 做分块查询/全量数据查询（把"所有"拆段查）——那是违规不是委派。
6. **场景剧本第1步最小终止规则**：户变关系查询只要 SQL 返回 row_count > 0，即立即基于结果生成最终答案。除非用户明确要求"按台区分组统计""导出全量""计算负载率"，否则只执行第1步即终止，禁止为"展示完整结果"反复分页或启动子代理。
7. **样本≠全量（分析结论边界）**：只能对 row_count 下全量结论（如"共 101 条"）。对行内字段（单路供电/状态正常/10kV 等）只能说"样本显示"，如"样本显示均为单路供电"。要输出"全部正常 / 全部单路供电 / 所有 X 均 Y"类全量结论，必须由 SQL 显式聚合统计（COUNT/GROUP BY）提供证据后再下。
"""

_KNOWLEDGE_FLOW_RULES = """
## 知识查询流程（不碰 SQL）
- 直接调只读元数据工具（fetch_l1_l2_tree / search_concepts / search_entities / get_entity_relations / list_tables）获取信息
- 用自然语言组织答案，不要只输出原始 JSON
- 结构：定义/列表 -> 详细说明 -> 相关建议
"""

# 可用技能概要：不再维护静态 _SKILL_OVERVIEW（双维护漂移）。
# 改由 SkillCatalog 实时扫描 SKILL.md frontmatter 生成（设计 §3.3，SKILL.md 是唯一业务来源）。
# 完整口径、SQL 细节、关联链路留在 SKILL.md；这里只生成简短索引。


def _get_model_identifier(model) -> str:
    """提取模型标识（等价 deepagents._models.get_model_identifier，仅依赖 langchain 公开属性）。

    Provider 对字段名不统一：有的用 model_name，有的用 model。取其一。
    不再从框架私有模块 import（升级稳定性）；行为与原私有 helper 一致。
    """
    try:
        v = getattr(model, "model_name", None)
        if v:
            return str(v)
    except Exception:
        pass
    try:
        v = getattr(model, "model", None)
        if v:
            return str(v)
    except Exception:
        pass
    return None


def _get_model_provider(model) -> str:
    """提取模型厂商（等价 deepagents._models.get_model_provider，仅依赖 langchain 公开 API）。

    用 BaseChatModel._get_ls_params() 的 ls_provider 字段（langchain 公开字段，
    各主流 provider 覆盖为硬编码值如 "deepseek"/"anthropic"）。
    """
    try:
        ls_params = model._get_ls_params()
        if isinstance(ls_params, dict):
            p = ls_params.get("ls_provider")
            if isinstance(p, str) and p:
                return p
    except Exception:
        pass
    return None


def _load_skill_md(skill_name: str) -> str:
    """读取 SKILL.md 文件内容（去掉 frontmatter），并解析 ⟦实体中文名⟧ -> 物理表名。

    批13-G 件1：加 @lru_cache（模块加载解析缓存）；
    路径查找扩展 scenarios/ 子目录（场景剧本 distribution-overload 等在
    data/skills/scenarios/ 下，此前只查平铺目录，场景剧本永远读空）。

    批15 件1（2026-09-06）：拆两层改指纹键缓存——外层只做路径解析+stat 指纹，
    内层 _load_skill_md_cached 键=(resolved_path, mtime_ns, size)。文件变→指纹变→
    新缓存条目（改 SKILL.md 不重启下次请求生效，兑现 13-Y「改剧本=下次请求重装配」
    的文本缓存侧）；文件不变→同条目同一字符串对象（test_13g `is` 同一性保持绿，
    13-I C1 前缀缓存逐字节一致契约保住）；键用 resolved_path 后子技能降级五个名字
    共享一条缓存。信号族对齐 _compute_files_hash（mtime+size 触发 Agent 全量重装配），
    粒度严格更细（st_mtime_ns 100ns vs 秒级）。签名零变化（生产调用点/单测零改动）。

    SKILL.md 中用 ⟦中文名⟧ 引用实体（如 ⟦用电户⟧），运行时自动从元数据解析为物理表名（如 cms20_elec_cons_cust）。
    这样 SKILL.md 不含硬编码表名，表名变更只需改元数据。

    Args:
        skill_name: 技能名（如 "multi-hop-query"）

    Returns:
        SKILL.md 正文（去掉 ---...--- 头），文件不存在返回空字符串
    """
    if not skill_name:
        return ""
    from pathlib import Path as _Path
    _skills_dir = _Path(__file__).resolve().parent.parent.parent / "data" / "skills"
    skill_md = _skills_dir / "scenarios" / skill_name / "SKILL.md"
    if not skill_md.exists():
        skill_md = _skills_dir / skill_name / "SKILL.md"
    if not skill_md.exists():
        # 子技能路由降级：distribution-overload-impact -> distribution-overload（共享同一份 SKILL.md）
        for suffix in ("-impact", "-power", "-link", "-verdict"):
            if skill_name.endswith(suffix):
                base = skill_name[:-len(suffix)]
                skill_md = _skills_dir / "scenarios" / base / "SKILL.md"
                if not skill_md.exists():
                    skill_md = _skills_dir / base / "SKILL.md"
                if skill_md.exists():
                    break
        if not skill_md.exists():
            return ""
    st = skill_md.stat()
    return _load_skill_md_cached(str(skill_md), st.st_mtime_ns, st.st_size)


@lru_cache(maxsize=32)
def _load_skill_md_cached(path: str, mtime_ns: int, size: int) -> str:
    """读文件+去 frontmatter+⟦⟧解析，键=(路径, mtime_ns, size)——批15 件1 指纹键（见外层 docstring）。"""
    content = Path(path).read_text("utf-8")
    # 去掉 YAML frontmatter（---...---）
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            content = content[end + 3:].strip()
    # 解析 ⟦实体中文名⟧ -> 物理表名（entity_en_name）（批13-AB2：解析器已搬迁 template_guard）
    from app.services.template_guard import _resolve_entity_refs
    content = _resolve_entity_refs(content)
    return content


# 批13-AB2：占位符站转技能——SkillEntityResolverMiddleware（read_file 运行时 ⟦⟧ 翻译站）已删除。
# _resolve_entity_refs/_ENTITY_REF_RE 搬迁至 template_guard.py（模板装配/系统提示词构建的
# 装配时翻译继续可用，与运行时站无关）；运行时模型按 AGENTS.md §五纪律主动 search_entities
# 翻译，漏网 ⟦⟧ SQL 由模板守卫硬拒（双层安全网，见设计 §2.2）。

# 批13-AB4 数据摘要站一件三拆——DataSummaryMiddleware（data_result 自定义事件 + ToolMessage
# 截断的运行时站）已删除：四查询工具出口在 mcp_server._with_result_ref 统一「全量存
# query_result_store + 返回模型摘要视图(带 result_ref/_directive)」，SSE 路由层 on_tool_end
# 按 result_ref 取全量派发前端。_SUMMARY_THRESHOLD(10) 随迁 mcp_server.py 模块常量。

# 四取数工具名单（13-AB4 后不再用于摘要拦截，仅 clean_aggregate 免评豁免逻辑使用）
_DATA_QUERY_TOOLS = frozenset({
    "execute_doris_sql",    # Doris 联邦
    "execute_sql",          # 物理直连
    "execute_entity_api",   # DuckDB API 联邦（单对象）
    "execute_api_sql",      # DuckDB API 联邦（多源SQL）
})

# 批13-AB3：skill_prompt 模式的自检段（评分站 mode 化）——注入动态系统提示词。
# 与 AGENTS.md §六常驻纪律同文等效（belt+suspenders）：middleware 模式由独立 grader 评分不注入。
RUBRIC_SELF_CHECK_PROMPT = """
## 交付前自检（不合格自行重写后再交）
1. 每个数值可追溯到某次工具返回（row_count/聚合值），禁止编造或心算；
2. 表名与 search_entities/list_tables 返回的物理表名完全一致；
3. 结论与数据口径一致（实体表、时间范围、过滤条件已注明）；
4. 样本结论与全量结论区分（「全部X/所有Y均Z」必须由 row_count 或 SQL 聚合提供证据）。
"""


def _rubric_effective_mode() -> str:
    """批13-AB3：rubric 生效模式（模块级统一口径，提示词构建与装配区共用）。

    返回 "disabled"（TUPU_RUBRIC_DISABLED=1 或能力关）/ "middleware" / "skill_prompt"（缺省）。
    配置读崩 fail-open 用 skill_prompt（自检段常驻无害，与 AGENTS.md §六 belt+suspenders 等效）。
    """
    import os as _os_rm
    if _os_rm.getenv("TUPU_RUBRIC_DISABLED", "") == "1":
        return "disabled"
    try:
        from app.services.capability_config import get_policy
        _p = get_policy("rubric") or {}
        if not _p.get("enabled"):
            return "disabled"
        return (_p.get("params") or {}).get("mode", "skill_prompt")
    except Exception:
        return "skill_prompt"


# 批13-Y：Backend 官方服务器模式迁移——/skills/ 与 /memory/ 从 FilesystemBackend
# （窄化使用+五层缓解的记录偏离）迁移至 StoreBackend（官方 Web 服务器推荐组合）。
# 技能/纪律树在装配时种子进独立 InMemoryStore（_files_store），运行时 Agent 文件路径
# 结构性零磁盘——目录穿越攻击类别整体消失。permissions 三规则保留为冗余保险带。
# 实施调和：设计原文「种子与运行时同库（create_deep_agent store）」；实际用独立
# _files_store 显式传参——消除 filesystem_tools 开+store 关的能力组合耦合，且文件种子柜
# 与用户偏好库 namespace 本就不同（语义不变）。新鲜度：files_hash 并入缓存键，
# 文件增删改 -> hash 变 -> 下次请求重装配+重种子（进行中会话用旧种子，低频运维可接受）。
_SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "skills"
_MEMORY_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "memory"
_FILES_NS_SKILLS = ("tupu", "skills")
_FILES_NS_MEMORY = ("tupu", "memory")


def _mem_inject_list(card) -> list:
    """记忆插槽②批1：memory 注入列表一处收口——归一形状（{slots, legacy_paths}）+
    legacy 手册优先+注入槽按 order（memory_slots.injection_list）。
    wenshu（slots=[]）→ legacy 路径列表 = ①现状逐字节等值。"""
    from app.services.memory_slots import injection_list, normalize_memory_field
    return injection_list(normalize_memory_field((card or {}).get("memory")))


def _memory_permission_rules(card: dict) -> list:
    """agent_edit 槽级放行（spec §八）：allow read skills 根（①卡）+ allow read 逐 RAW_MD
    槽（edit_file 要先读）+ allow write 仅 writer=agent_edit 槽（逐槽精确到文件）+
    deny 基座垫底。wenshu slots=[] → 序列=现状三条逐字节等值（A2）。槽外任何路径
    （未声明 md、/skills/、树外）落回 deny。"""
    from app.services.memory_slots import normalize_memory_field
    rules = [{"op": "read", "paths": [f"{p}**" for p in (card.get("skills") or ["/skills/"])],
              "mode": "allow"}]
    _mem = normalize_memory_field(card.get("memory"))
    _agent_edit = [s for s in _mem["slots"]
                   if s.get("type") == "RAW_MD" and s.get("writer") == "agent_edit"]
    if _agent_edit:
        rules.append({"op": "read", "paths": [s["path"] for s in _agent_edit], "mode": "allow"})
        rules.append({"op": "write", "paths": [s["path"] for s in _agent_edit], "mode": "allow"})
    rules.append({"op": "read", "paths": ["/**"], "mode": "deny"})
    rules.append({"op": "write", "paths": ["/**"], "mode": "deny"})
    return rules


def _agent_edit_slot_rels(card: Dict[str, Any] | None) -> frozenset:
    """卡 RAW_MD(writer=agent_edit) 槽路径 → 相对基准集合（剥 /memory/ 前缀）。

    归一基准与 SkillPolicy._is_agent_edit_slot_target 一致（实证 #11：一侧 strip("/") 保留
    memory 段会导致例外永不命中）。空集=无槽卡（wenshu）。"""
    try:
        from app.services.memory_slots import normalize_memory_field
        out = []
        for s in normalize_memory_field((card or {}).get("memory")).get("slots") or []:
            if s.get("type") != "RAW_MD" or s.get("writer") != "agent_edit" or not s.get("path"):
                continue
            p = str(s["path"]).strip()
            out.append(p[len("/memory/"):] if p.startswith("/memory/") else p.strip("/"))
        return frozenset(out)
    except Exception:
        return frozenset()


def _card_has_agent_edit_slots(card: Dict[str, Any] | None) -> bool:
    """卡是否有 RAW_MD(writer=agent_edit) 槽（装配追加记忆槽写入件的判据；无槽=False）。"""
    return bool(_agent_edit_slot_rels(card))


def _build_memory_edit_tools(mtb):
    """②批补验（spec §五三重防线·第三层）：agent_edit 槽卡的自定义记忆槽写入件。

    built-in write_file/edit_file 被 HarnessProfile excluded 物理剔除（register 对同 key
    是 excluded **并集**语义——provider:model 全专家共享 key，先装配的无槽卡永久并回两件，
    减法无效），且 `_ToolExclusionMiddleware` 在链路最后**按工具名**剥离（含 tools 传入的
    自定义件）——故自定义件必须**换名**（write_memory_slot/edit_memory_slot，非剥离名单内）。
    行为=MemoryTreeBackend.write/edit 直通（_writable 槽白名单+手册只读+备份+台账全保留），
    本件零自制策略（如实上屏，不吞错不伪造成功）。无槽卡不构造=零变化（现状等值）。"""
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    class _WriteArgs(BaseModel):
        file_path: str = Field(description="记忆槽文件路径，如 /memory/偏好.md")
        content: str = Field(description="要写入的完整文件内容")

    class _EditArgs(BaseModel):
        file_path: str = Field(description="记忆槽文件路径，如 /memory/偏好.md")
        old_string: str = Field(description="要替换的原文片段（精确匹配）")
        new_string: str = Field(description="替换后的新片段")
        replace_all: bool = Field(default=False, description="是否替换全部出现")

    def _w(file_path: str, content: str) -> str:
        r = mtb.write(file_path, content)
        if getattr(r, "error", None):
            return f"写入失败: {r.error}"
        return f"写入成功: {getattr(r, 'path', '') or file_path}"

    def _e(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        r = mtb.edit(file_path, old_string, new_string, replace_all)
        if getattr(r, "error", None):
            return f"编辑失败: {r.error}"
        return f"编辑成功: {getattr(r, 'path', '') or file_path}"

    return [
        StructuredTool.from_function(
            func=_w, name="write_memory_slot", args_schema=_WriteArgs,
            description=("写入用户记忆槽文件（仅限专家卡声明的 agent_edit 槽，如 /memory/偏好.md）。"
                         "用户要求记住偏好/画像等长期信息时调用。")),
        StructuredTool.from_function(
            func=_e, name="edit_memory_slot", args_schema=_EditArgs,
            description="编辑用户记忆槽文件（仅限 agent_edit 槽）。old_string 需与文件原文精确匹配。"),
    ]


def _compute_files_hash(card=None, user: str | None = None) -> str:
    """技能树+纪律树新鲜度指纹：逐文件 相对路径+mtime+size 有序拼接 sha256（前16位）。

    ②修正（spec §五）：memory 侧=手册（legacy_paths 物理落点）+read=注入 槽文件（per-user
    经 ContextVar 解析），trace/*.jsonl 与 backup/ 排除——L1 每回合追加，进哈希=每问重建
    Agent（缓存报废）。注入是装配时快照：L2/L3 固化后 f 变→下一装配注入新摘要（明示非缺陷）。
    skills 侧行为原样（①）。装配区与 get_tupu_agent 缓存键共用。
    """
    import hashlib as _hl
    from app.services.memory_slots import normalize_memory_field, injection_list
    h = _hl.sha256()
    # skills 侧（原样，①行为）
    for root, prefix in ((_SKILLS_ROOT, "skills"),):
        try:
            files = sorted(p for p in root.rglob("*") if p.is_file())
        except Exception:
            files = []
        for p in files:
            try:
                st = p.stat(); rel = p.relative_to(root).as_posix()
                h.update(f"{prefix}/{rel}|{int(st.st_mtime)}|{st.st_size};".encode("utf-8"))
            except OSError:
                continue
    if card is not None:
        if user is None:                                 # 调用方不传→ContextVar（endpoint 已前置 set）
            from app.services.memory_runtime import current as _cur
            user = _cur()["user"]
        _user = user or "anonymous"
        from app.services.expert_paths import memory_expert_root, memory_user_root
        eroot = memory_expert_root(card.get("expert_id") or "wenshu")
        uref = memory_user_root(card.get("expert_id") or "wenshu", _user)
        for vp in injection_list(normalize_memory_field(card.get("memory"))):
            rel = vp[len("/memory/"):]
            for root in (eroot, uref):                 # 双根（手册在专家根，槽在用户根）
                p = root / rel
                if p.is_file():
                    st = p.stat()
                    h.update(f"memory/{rel}|{int(st.st_mtime)}|{st.st_size};".encode("utf-8"))
                    break
    else:                                               # ①兼容路径：全 memory 根（搬迁后=手册树）
        try:
            files = sorted(p for p in _MEMORY_ROOT.rglob("*")
                           if p.is_file() and "trace" not in p.parts and "backup" not in p.parts)
        except Exception:
            files = []
        for p in files:
            try:
                st = p.stat(); rel = p.relative_to(_MEMORY_ROOT).as_posix()
                h.update(f"memory/{rel}|{int(st.st_mtime)}|{st.st_size};".encode("utf-8"))
            except OSError:
                continue
    return h.hexdigest()[:16]


def _seed_files(store, ns: tuple, root: Path) -> int:
    """装配时把磁盘树种子进 store（key=/相对路径，value={"content": text}）。

    key 带前导斜杠：CompositeBackend 路由 /skills/xxx 后传给子 backend 的路径保留前导 /，
    StoreBackend 不做归一化（实测 /scenarios/.. 找不到 scenarios/.. 的 key），故种子 key
    必须同形（FilesystemBackend 时代由其内部虚拟根归一化兜住，迁移后由种子 key 对齐）。
    先清场（PutOp value=None 批量删）再种——防删除文件后旧 key 残留（InMemoryStore 无 TTL）。
    返回种子文件数。value 形态按 StoreBackend._convert_store_item_to_file_data 约定
    （store_item.value["content"] 为 str）。"""
    from langgraph.store.base import PutOp as _PutOp
    old_keys = [i.key for i in store.search(ns)]
    if old_keys:
        store.batch([_PutOp(ns, k, None) for k in old_keys])
    n = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if "__pycache__" in p.parts or p.suffix == ".pyc":
            continue  # 防御：字节码缓存不入种子（非技能内容，且非 UTF-8 会炸 read_text）
        rel = p.relative_to(root).as_posix()
        store.put(ns, f"/{rel}", {"content": p.read_text("utf-8")})
        n += 1
    return n


def _build_dynamic_system_prompt(skill_hint: str = "", base: str = None,
                                 expert_card: bool = False) -> str:
    """构建动态 system_prompt（按技能分段注入）。

    Plan-Execute 和 ReAct 共用此函数，技能知识统一来源 SKILL.md。
    不再走 skill_router 预分类：skill_hint 为空时注入全量技能概要，
    由 LLM 自主 read_file 选技能。

    Args:
        skill_hint: 可选技能名（如 "execute-sql" 续轮执行），为空时走自主模式
        base: 专家地基①（spec §五）：提示词基座，缺省 _BASE_ROLE（等值现状）；
              专家卡给定时用卡声明的静态基座逐字节替换（A2 对拍强约束）
        expert_card: ⑤R E1——非 wenshu 专家卡为 True：只保留卡基座（+日期），
              不注入 wenshu 工作流规则块（技能概要/SQL 流程/决策门/数据完整性/
              通用规则均为数据探查域纪律；教学代理按原仓语义=自身人设+卡面工具纪律）
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    if expert_card:
        return (base if base is not None else _BASE_ROLE).replace("__CURRENT_DATE__", date_str)
    parts = [(base if base is not None else _BASE_ROLE).replace("__CURRENT_DATE__", date_str)]

    # 读 SKILL.md 替代 _SKILL_HINTS 字典，与 ReAct 模式共用同一份技能知识
    skill_md_content = _load_skill_md(skill_hint)
    if skill_md_content:
        parts.append(f"\n## 当前技能指南\n{skill_md_content}\n")

    if skill_hint == "execute-sql":
        parts.append("""
## 执行确认流程
用户确认执行上一轮的 SQL。直接调 execute_sql 工具执行，不要重新定位。
执行后输出结果总结。
""")
    elif skill_hint:
        # 指定了技能：
        # - 场景剧本(scenarios/*)自带步骤+口径，不注入通用 SQL 流程(其 locate->validate_safe_sql->execute_sql
        #   会与剧本的 get_entity_source_mode->execute_entity_api/execute_doris_sql 冲突，导致回退到 execute_sql)
        # - 但 source_mode 路由规则是通用的，场景剧本也必须按实体配置选工具，不跳过
        # - 其它技能(locate/sql-query 等)注入两套流程规则，LLM 按技能类型自主选用
        if not skill_hint.startswith("scenarios/"):
            parts.append(_SQL_FLOW_RULES)
            parts.append(_KNOWLEDGE_FLOW_RULES)
        else:
            parts.append(_SOURCE_MODE_DISPATCH_RULES)
    else:
        # 自主模式：注入由 SkillCatalog 实时生成的技能概要 + 两套流程规则，LLM 自主 read_file 选技能
        from app.services.skill_catalog import build_skills_overview
        parts.append(build_skills_overview())
        parts.append(_SQL_FLOW_RULES)
        parts.append(_KNOWLEDGE_FLOW_RULES)

    # 批13-W W-4a：决策门提示词注入切配置源（与装配侧同函数同缓存——PATCH 后 version+1 重建
    # Agent 保一致；TTL 5s 窗口内旧 Agent+新提示词的短暂不一致与其余能力开关同性质，登记接受）
    try:
        from app.services.capability_config import get_decision_gate_config as _gdc
        if _gdc()["enabled"]:
            parts.append(_DECISION_GATE_RULES)
    except Exception:
        if _DECISION_GATE_ENABLED:
            parts.append(_DECISION_GATE_RULES)
    parts.append(_DATA_COMPLETENESS_RULES)
    # 批13-AB3：评分 mode=skill_prompt 时，自检段进动态系统提示词（middleware 模式由
    # _TupuRubricMiddleware 评分，不重复注入；rubric 关闭/禁用也不注入）。
    if _rubric_effective_mode() == "skill_prompt":
        parts.append(RUBRIC_SELF_CHECK_PROMPT)
    parts.append(_COMMON_RULES)
    return "\n".join(parts)



# ---------------------------------------------------------------------------
# 3. Tools
# ---------------------------------------------------------------------------

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


# 统一最终交付协议（response_format 用；GLM 不兼容时由 data_intelligence 确定性降级构造）
class FinalFinding(BaseModel):
    """关键发现（指标卡）：label + value + 级别。"""
    label: str
    value: str
    level: Literal["info", "success", "warning", "error"] = "info"


class FinalDelivery(BaseModel):
    """DeepAgent 最终交付对象（替换粗糙的 TupuFinalAnswer）。

    约束（最终结果交付任务书）：
    - 不存完整 rows / SQL / 执行过程（表格数据继续走 sql_result SSE / done 字段）
    - row_count 必须来自工具真实返回，禁止模型编造
    - answer_type 供前端选择展示形态；后端按 A-E 优先级确定性降级构造
    """
    answer_type: Literal[
        "relationship_list",
        "overload_analysis",
        "data_list",
        "aggregation",
        "knowledge",
        "empty",
        "error",
    ] = "data_list"
    title: str
    summary: list[str] = Field(default_factory=list)
    findings: list[FinalFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    row_count: int = 0
    result_available_for_ui: bool = False


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



# 业务逻辑单一源（MCP server 的 16 个工具与内部调度共用；deepagent 不再用进程内 @tool）
# P0 整改：统一 kg_api 已拆为 16 个单一职责 MCP 工具（app/mcp_server.py），此处不再保留 kg_api 死代码。
from .kg_action_handlers import dispatch_kg_action


# ---------------------------------------------------------------------------
# M3（融合设计 §5.1）：RubricMiddleware on_evaluation 钩子 + 每请求桥接
# rubric 评估事件经 runtime.stream_writer 走 stream_mode="custom"，astream_events 收不到，
# 故以 on_evaluation 回调为可靠通道：治理双落 + contextvar 桥到当前请求的 run_event_sink/契约。
# ---------------------------------------------------------------------------
import contextvars as _cvars

_RUBRIC_HOOK_CTX: _cvars.ContextVar = _cvars.ContextVar("tupu_rubric_hook", default=None)


def _on_rubric_evaluation(evaluation: dict) -> None:
    """M3 DA-2：grader 每次评估回调 -> 治理 + 当前请求 sink/契约（SSE 可见）。

    回调内异常只记不抛（框架对 on_evaluation 异常同样抑制）。
    批3-F：记录单次 grader 耗时进 _runtime["rubric_ms"]（分段计时外露）。
    """
    try:
        from app.services import skill_governance as _gov
        _gov.get_governance().record_policy(
            "rubric.evaluation", "_rubric_", "_rubric_",
            f"result={evaluation.get('result')} iter={evaluation.get('iteration', 0)}")
    except Exception:
        pass
    try:
        bridge = _RUBRIC_HOOK_CTX.get()
        if not bridge:
            return
        sink = bridge.get("sink")
        if sink is not None:
            sink.append("rubric_evaluation_end", {
                "result": evaluation.get("result"),
                "iteration": evaluation.get("iteration"),
                "explanation": (evaluation.get("explanation") or "")[:500],
                "grading_run_id": evaluation.get("grading_run_id"),
            })
        contract = bridge.get("contract")
        if contract is not None:
            contract._runtime["rubric_status"] = evaluation.get("result")
            contract._runtime["rubric_iterations"] = int(evaluation.get("iteration", 0) or 0) + 1
            contract._runtime["rubric_explanation"] = (evaluation.get("explanation") or "")[:500]
            # 批3-F：grader 端到端耗时（ms）——RubricMiddleware 传 evaluation["elapsed_ms"]（若无则 0）
            _el = evaluation.get("elapsed_ms") or 0
            if _el:
                contract._runtime["rubric_ms"] = int(_el)
    except Exception:
        pass


def _is_clean_aggregate_result(state) -> bool:
    """批10-B'-1：执行轨迹是否为「干净的单值聚合结果」。

    设计（交付体验演进 §四 B'-1）：同时满足才免评——
      1. 最后一条数据查询工具成功（无 error）；
      2. 引擎校验全绿（verification.warnings 为空）；
      3. 单一聚合型结果（row_count=1 且单行单列标量，非明细清单）。
    数字直接来自工具返回已被 SkillPolicy/守卫锁定，grader 边际价值≈0。
    解析失败一律返回 False（回退自评，宁可多评不可放过）。
    """
    import json as _json_ca
    messages = state.get("messages") or []
    # tool_call_id -> 工具名（AIMessage.tool_calls）
    _name_by_tcid = {}
    for m in messages:
        for tc in (getattr(m, "tool_calls", None) or []):
            if isinstance(tc, dict) and tc.get("id"):
                _name_by_tcid[tc["id"]] = tc.get("name", "")
    # 倒序找最后一条数据工具的 ToolMessage
    last_content = None
    for m in reversed(messages):
        tcid = getattr(m, "tool_call_id", None)
        if tcid and _name_by_tcid.get(tcid) in _DATA_QUERY_TOOLS:
            last_content = getattr(m, "content", None)
            break
    if last_content is None:
        return False
    # content 解包（LangChain blocks / MCP 包装），与 mcp_server._with_result_ref 输出同构
    if isinstance(last_content, list):
        for b in last_content:
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
                last_content = b["text"]
                break
    if not isinstance(last_content, str):
        return False
    try:
        parsed = _json_ca.loads(last_content)
        if isinstance(parsed, dict) and isinstance(parsed.get("text"), str):
            parsed = _json_ca.loads(parsed["text"])
    except Exception:
        return False
    if not isinstance(parsed, dict) or parsed.get("error"):
        return False
    verification = parsed.get("verification") or {}
    if verification and (verification.get("warnings") or []):
        return False  # 引擎校验有告警 -> 不豁免
    rows = parsed.get("rows") or []
    row_count = parsed.get("row_count")
    # 单一聚合型：恰好 1 行 × 1 列标量（COUNT/SUM 等聚合输出形态）
    return (row_count == 1 and len(rows) == 1
            and isinstance(rows[0], (list, tuple)) and len(rows[0]) == 1)


from deepagents.middleware.rubric import RubricMiddleware  # 批10②：模块级（_TupuRubricMiddleware 继承基类）


class _TupuRubricMiddleware(RubricMiddleware):
    """批10② B'-1：clean_aggregate 豁免 + 桥接登记。

    示例锚定豁免（query_contract.apply_rubric_tier，Agent 前）之外的第二条规则，
    在 grader 发起前（after_agent）基于执行轨迹判定：
      verification 全绿 + 单值聚合结果 -> 跳过本轮自评（省 10~40s 关键路径阻塞）。
    治理：governance 记 rubric.evaluation_skipped="clean_aggregate"；
    contract._runtime["rubric_status"]="skipped_clean_aggregate" 供 done 置信度口径使用。
    （模块级显式 import：create_tupu_agent 内的同名 import 为函数局部，不供本类继承用）
    """

    def _try_clean_aggregate_skip(self, state) -> bool:
        """批10-B'-1：命中 clean_aggregate 豁免则登记治理+桥接并返回 True（跳过 grader）。"""
        if not _is_clean_aggregate_result(state):
            return False
        try:
            from app.services.skill_governance import get_governance
            get_governance().record_policy(
                "rubric.evaluation_skipped", "clean_aggregate", "clean_aggregate",
                "批10-B'-1：verification 全绿+单值聚合结果，免评直出")
        except Exception:
            pass
        bridge = _RUBRIC_HOOK_CTX.get()
        if bridge is not None:
            contract = bridge.get("contract")
            if contract is not None:
                contract._runtime["rubric_status"] = "skipped_clean_aggregate"
            sink = bridge.get("sink")
            if sink is not None:
                sink.append("rubric_evaluation_end", {
                    "result": "skipped_clean_aggregate", "iteration": 0,
                    "explanation": "校验全绿的单值统计结果，免评直出",
                })
        return True

    def after_agent(self, state, runtime):  # noqa: D102（框架签名；sync 图路径）
        try:
            if self._try_clean_aggregate_skip(state):
                return None  # 不发起 grader 轮，图自然结束
        except Exception as e:
            logger.warning(f"[RubricTier] clean_aggregate 判定异常（回退自评）: {e}")
        return super().after_agent(state, runtime)

    async def aafter_agent(self, state, runtime):  # noqa: D102（框架签名）
        # 关键：基类 aafter_agent 是独立实现（不委托 sync after_agent），astream_events
        # 异步图分发的是本方法——只覆写 after_agent 会被完全绕过（批10② 实测教训）。
        try:
            if self._try_clean_aggregate_skip(state):
                return None  # 不发起 grader 轮，图自然结束
        except Exception as e:
            logger.warning(f"[RubricTier] clean_aggregate 判定异常（回退自评）: {e}")
        return await super().aafter_agent(state, runtime)


# 4. Agent 工厂函数
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Agent 装配（批13-Q：能力开关中心条件化装配）
# ---------------------------------------------------------------------------

# F5/批13-Q：结构化最终交付 schema（final 扁平结构，规避嵌套 schema 与 GLM/DeepSeek 的不兼容）
_FINAL_RESPONSE_FORMAT = {
    "title": "FinalAnswer",
    "description": "最终交付结构：面向用户的最终答案文本。",
    "type": "object",
    "properties": {
        "final_answer": {"type": "string", "description": "面向用户的最终答案（含结论/表格引用/建议）"},
    },
    "required": ["final_answer"],
    "additionalProperties": False,
}

# 装配清单（批13-Q 探针读）：{version, agent_key, items: {capability_id: bool(装配态)}}
_ASSEMBLY_MANIFEST: dict = {"version": 0, "agent_key": "", "items": {}}
# fail-safe 快照：最近一次成功装配的 caps（新配置装配失败时回退此版本）
# 专家地基①：扩展含卡快照——回退路径连卡一起回退（spec §十）。
# 批6 E3 修正：改按 expert 分桶——跨专家回退=串卡（echo 会拿到 wenshu 的卡），隔离破坏。
_LAST_GOOD_ASSEMBLY: dict = {}  # {expert_id: {"caps":…, "caps_version":…, "card":…}}


def _narrow_mcp_tools(mcp_tools, card_tools):
    """专家地基①（spec §五）：按卡窄化工具面；空交集拒装配（fail-closed）。"""
    keep = [t for t in mcp_tools if getattr(t, "name", "") in set(card_tools or [])]
    if not keep:
        raise ValueError("专家卡 tools 与 MCP 注册表交集为空，拒装配（fail-closed）")
    return keep


def _assembly_cache_key(connection_id, gver, cver, fhash, expert_id, card_version, role_id=None) -> str:
    """专家地基①（spec §五）：4→6 因子——#e{expert}@{版本}（身份@版本，两专家各自 Agent）。
    B2（v4§四）：role_id 真值追加 #r 因子（切角色=重建，不命中旧提示词实例）；
    None 时键逐字节不变——role_id「None=现状等价」的硬保证。"""
    key = f"{connection_id or '__default__'}#g{gver}#c{cver}#f{fhash}#e{expert_id}@{card_version}"
    if role_id:
        key += f"#r{role_id}"
    return key


async def _build_agent(checkpointer, connection_id: str, caps: dict, card: dict = None, role_id: str = None, user=None):
    """按能力开关条件装配 DeepAgent（批13-Q 4.1）。失败抛异常，由 create_tupu_agent 包装器 fail-safe。
    专家地基①（2026-09-12 spec §五）：card=专家配置卡——提示词基座/工具面/路径/权限四类按卡参数化，
    能力开关检查逻辑零改动（卡=装配参数，链=平台）。
    B2（v4§四）：role_id 真值时卡上注入角色风格段（wenshu 预置 3 卡；基座保留=工作流契约不动）。"""
    if role_id:
        from app.services.wenshu_roles import apply_role
        card = apply_role((card or {}).get("expert_id") or "wenshu", role_id, card or {})
    from deepagents import create_deep_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient

    from app.services.llm_client import get_chat_model
    # streaming=True 让 on_chat_model_stream 产出 token 事件，避免长时间无反馈（对齐数据问答修复）
    # v3.6: 按 connection_id 选模型（让前端选模型真正生效）
    # S1d: 问数场景温度固化 0.1（要稳不要浪；rubric 判定模型保持 0.0 不变）
    # 注：batch 路由修复（sql_integration->execute_doris_sql）后 0.1 不再引发计数题回归（早前 0/3 为引擎锁死锁所致）
    model = get_chat_model(temperature=0.1, streaming=True, connection_id=connection_id)

    # MCP client 加载业务工具（16 个 tool，走 SSE，与 deepagent 解耦）
    # P3-a: MCP server 端 Bearer-only（R1批废 X-Internal-Service 兜底）。批⑥：摘除
    # 死头发送——X-Internal-Service 已无服务端消费方，仅余噪音
    import os as _os
    _internal_token = _os.getenv("TUPU_INTERNAL_TOKEN", "")
    _mcp_headers = {}
    if _internal_token:
        _mcp_headers["Authorization"] = f"Bearer {_internal_token}"
    mcp_client = MultiServerMCPClient({
        "tupu-kg": {"url": "http://127.0.0.1:28000/mcp/sse", "transport": "sse", "headers": _mcp_headers}
    })
    mcp_tools = await mcp_client.get_tools()
    # 批5-C2：工具顺序固化——MCP list_tools 返回序可能抖动，打碎 DeepSeek 服务端前缀缓存；
    # 装配时按工具名排序一次，保证同场景 system prompt 中工具清单逐字节一致。
    try:
        mcp_tools = sorted(mcp_tools, key=lambda t: getattr(t, "name", "") or "")
    except Exception as _tse:
        logger.warning(f"[批5-C2] 工具排序失败（保持原序）: {_tse}")
    # 专家地基①：按卡窄化工具面（批5-C2 序保留；空交集拒装配 fail-closed，spec §五）
    # ⑤R E1：W-1 运维排除分层——原实现把 get_tool_exclusions()（含「教学 11 件默认排除于
    # 问数面」的 W-1 运维态）喂进 HarnessProfile（按 model 共享键、并集合并）→ 教学卡工具面
    # 被共享键连带剥离（E1 实测：模型只见 8 件框架工具）。分层修正：
    #   a) HarnessProfile 只喂安全红线 5 件（普适物理排除，model 级）；
    #   b) W-1 运维排除（问数面白名单）在窄化后对 wenshu 卡生效（问数面语义原样）；
    #   c) 非 wenshu 专家卡=卡面即授权（tools 声明即授权面，不被 W-1 连带）。
    #   wenshu agent 工具面逐件等值（窄化∩card.tools 后再减 excluded16=原两级减法结果）。
    _is_expert_card = bool(card and (card.get("expert_id") or "wenshu") != "wenshu")
    # 引擎批1（2026-09-16）：教学族专家卡（tutor）工具面=vendor 引擎族声明（fsrs/mastery/
    # wrong_question 等 11 件）——该族已随先行版从 MCP 注册表摘除（⑤R R1），批3/4 由本件
    # 编排（dt_agent_orchestrations）承接，非 MCP 面。专家卡 MCP 交集为空不再 fail-closed：
    # 降级空 MCP 面装配（LLM 裸循环+下块 read_file 补挂=可对话可读技能/记忆文件）；
    # wenshu 卡维持原 fail-closed（问数面零感知）。台账登记。
    try:
        mcp_tools = _narrow_mcp_tools(mcp_tools, (card or {}).get("tools"))
    except ValueError:
        if not _is_expert_card:
            raise
        logger.warning("[引擎批1] 专家卡 MCP 交集为空（教学族声明面）——降级空 MCP 面装配，教学工具由编排承接")
        mcp_tools = []
    if not _is_expert_card:
        try:
            _w1_excl = frozenset(_cc.get_tool_exclusions()["excluded"]) if _cc is not None else frozenset()
        except Exception:
            _w1_excl = frozenset()
        mcp_tools = [t for t in mcp_tools if getattr(t, "name", "") not in _w1_excl]
    if _is_expert_card:
        _all_mcp = await mcp_client.get_tools()
        _rf = [t for t in _all_mcp if getattr(t, "name", "") == "read_file"]
        if _rf and "read_file" not in {getattr(t, "name", "") for t in mcp_tools}:
            mcp_tools = mcp_tools + _rf
    # 权限重构T5（design §6.2 装载点）：用户维度过滤——专家白名单（上）∩ 用户/角色
    # 权限（本步），fail-closed。ENABLE_AUTH=0 / admin 原样全量（缓存键无 #u 因子，
    # 开发态零变化）。非注册表面（read_file 等框架工具）按 🛠R14 面外声明放行。
    _t5_allowed_names = None
    if user is not None and not getattr(user, "is_anonymous", False):
        try:
            from app.core.database import SessionLocal as _SL
            from app.services.tool_gate import filter_tools_for_user as _ftfu
            _dbu = _SL()
            try:
                _allowed = _ftfu(_dbu, user, [getattr(t, "name", "") for t in mcp_tools])
            finally:
                _dbu.close()
            _before = len(mcp_tools)
            mcp_tools = [t for t in mcp_tools
                         if getattr(t, "name", "") not in TOOL_REGISTRY_FROZEN
                         or getattr(t, "name", "") in _allowed]
            _t5_allowed_names = _allowed
            logger.info(f"[T5] 工具面用户过滤: {user.sub} {_before}->{len(mcp_tools)} 件")
        except Exception as _tg_err:
            logger.warning(f"[T5] 工具面过滤异常（fail-open 兜底放行——装配方非执法点）: {_tg_err}")
    # ⑤R R1（批12）：教学九件进程内 twin 随先行版教学面退役移除——
    # 先行版 MCP 教学工具族已从 mcp_server 注册表摘除（twin 覆盖层失锚），
    # 教学能力由 vendor 复刻件（deeptutor learning 原生工具+路由族）承接。

    def _cap(cid: str) -> dict:
        return caps.get(cid) or {}

    def _on(cid: str) -> bool:
        return bool((_cap(cid) or {}).get("enabled"))

    from deepagents.backends import StateBackend, CompositeBackend, StoreBackend

    # 批13-Y：Backend 官方服务器模式——/skills/ 与 /memory/ 路由到 StoreBackend（官方 Web 服务器
    # 推荐组合），技能/纪律树装配时种子进独立 _files_store，运行时零磁盘访问（目录穿越类别消失）。
    # 默认 StateBackend：路由表外路径=会话草稿纸（驱逐历史等），语义不变。
    # 批13-Q：filesystem_tools 关闭 -> 退化 StateBackend（无文件路由，文件工具不可用面收窄）。
    from langgraph.store.memory import InMemoryStore as _InMemStore
    _files_store = _InMemStore()
    if _on("filesystem_tools"):
        # 专家地基①：种子/路由按卡声明路径派生（wenshu 卡→data/skills+data/memory 两根，等值现状）
        from app.services.expert_paths import skills_roots, memory_roots
        _s_roots, _m_roots = skills_roots(card or {}), memory_roots(card or {})
        _n_seeded = 0
        for _r in _s_roots:
            _n_seeded += _seed_files(_files_store, _FILES_NS_SKILLS, _r)
        for _r in _m_roots:
            _n_seeded += _seed_files(_files_store, _FILES_NS_MEMORY, _r)
        _routes = {f"/{_p}/": StoreBackend(store=_files_store, namespace=lambda _rt, _ns=_FILES_NS_SKILLS: _ns)
                   for _p in [seg for s in ((card or {}).get("skills") or []) for seg in [str(s).strip("/")] if seg]}
        _routes = {f"/{_p}/": StoreBackend(store=_files_store, namespace=lambda _rt, _ns=_FILES_NS_SKILLS: _ns)
                   for _p in [seg for s in ((card or {}).get("skills") or []) for seg in [str(s).strip("/")] if seg]}
        # 记忆插槽②批2：/memory/ 换心脏——StoreBackend(种子式)→MemoryTreeBackend(物理树持久化，
        # 双根读/单根写/备份/台账)。每 Agent 独立实例（装配期构造，实例零共享状态；读写落点
        # 每次调用经 memory_runtime ContextVar 解析——「同装配、不同人」）。/skills/ 原封不动。
        from app.services.memory_tree_backend import MemoryTreeBackend as _MTB, ensure_dirs as _ensure_dirs
        _routes.update({"/memory/": _MTB(str((card or {}).get("expert_id") or "wenshu"), card or {})})
        _memory_backend = _routes["/memory/"]
        _ensure_dirs(str((card or {}).get("expert_id") or "wenshu"), card or {})  # 骨架+RAW_MD 预创建（不阻装配）
        backend = CompositeBackend(default=StateBackend(), routes=_routes)
        logger.info(f"[13-Y] StoreBackend 路由已装配（种子 {_n_seeded} 个文件，files_hash={_compute_files_hash(card)}）——运行时零磁盘")
    else:
        _n_seeded = 0
        _memory_backend = None
        backend = StateBackend()
        logger.warning("[Capability] filesystem_tools 已关闭：backend 退化为 StateBackend（文件路由不可用）")
    # ②批补验（spec §五三重防线·第三层）：agent_edit 槽卡追加自定义记忆槽写入件
    # （同名替代被 excluded 的 built-in 件；additive 通道不受 union 语义影响）。
    if _memory_backend is not None and _card_has_agent_edit_slots(card):
        try:
            mcp_tools = mcp_tools + _build_memory_edit_tools(_memory_backend)
            logger.info("[MemoryEdit] agent_edit 槽卡：自定义 write_file/edit_file 已挂 tools（放行面=槽白名单）")
        except Exception as _me:
            logger.warning(f"[MemoryEdit] 记忆槽写入件构造失败（不阻装配）: {_me}")
    # 权限规则（按序匹配，首条命中生效，无命中默认允许）：
    #   1. 允许读 /skills/**（技能文件）
    #   2. 拒绝读 /**（兜底封堵：/skills/../../、/etc/passwd、.env 等全部 deny）
    #   3. 拒绝写 /**（业务问答不写文件）
    # 批13-Q：permissions 关闭 -> 不装配权限规则（backend 路由仍限制根目录，virtual_mode 防穿越仍在）。
    # 记忆插槽②批4：规则生成收口 _memory_permission_rules（卡驱动——逐 RAW_MD agent_edit 槽
    # 精确放行 read/write，deny 垫底；wenshu slots=[] → 三条序列逐字节等值①现状，单测锁死）。
    permissions = None
    if _on("permissions"):
        from deepagents.middleware.filesystem import FilesystemPermission
        permissions = [
            FilesystemPermission(operations=[r["op"]], paths=r["paths"], mode=r["mode"])
            for r in _memory_permission_rules(card or {})
        ]
    else:
        logger.warning("[Capability] permissions 已关闭：文件工具无 allow/deny 规则（管理员显式操作）")
    # v3.6: 用公开 HarnessProfile 替换私有 _ToolExclusionMiddleware（评审点5：消除下划线私有依赖）
    # P1-2: 从 model 对象提取真实 identifier 注册，不硬编码模型名（防大小写/变体不匹配）
    # register 是增量合并，幂等安全；create_deep_agent 内部按 model 自动匹配此 profile。
    # 批13-J 收尾（问题一修复）：不再 from deepagents._models import get_model_identifier/get_model_provider
    # （框架私有小门，升级可能改名/挪位）；改用 langchain 公开属性自写等价（model_name/model + _get_ls_params()["ls_provider"]）。
    from deepagents import HarnessProfile, register_harness_profile
    # X-2 审计锚点（2026-08-24 审查）：当前主力模型（DeepSeek-V4-Flash/GLM-5.3-Flash，OpenAI 兼容接入）
    # 未观测到需要 system_prompt_suffix 行为适配的问题；已知 GLM 与 response_format 不兼容
    # 由 data_intelligence 确定性降级路径兜底。将来发现模型行为偏差时，适配（并行工具调用后缀/
    # 工具格式纠正/工具描述改写，见《装配层配置化设计》X-3 登记表）加在本注册处，不加不预支。
    _model_id = _get_model_identifier(model)
    _model_provider = _get_model_provider(model)
    # 批13-W W-1：工具白名单打勾制（黑名单版语义反转）——get_tool_exclusions() 内部已改白名单
    # 换算（excluded = 红线 5 件 ∪ (勾选域 18 件 - allowed)），本侧接口形状不变零改动；
    # fail-safe：读崩 -> 红线 5 件（安全可用态，语义登记见设计 §五.3）。
    _cc = None
    try:
        from app.services import capability_config as _cc
        # ⑤R E1 分层：HarnessProfile（model 级共享键）只喂安全红线 5 件——W-1 运维排除
        # 已折进 wenshu 卡窄化（见 _narrow 后减法）。原实现把运维态喂进共享键会把
        # 非 wenshu 卡声明的工具连带剥离（并集合并，先装配者定态）。
        _excluded = frozenset(_cc.W1_REDLINE_EXCLUSIONS)
    except Exception:
        _excluded = frozenset({"grep", "glob", "write_file", "edit_file", "execute"})
    # ②批补验注记（spec §五三重防线）：write_file/edit_file 的物理挂回**不走 excluded 减法**——
    # deepagents register_harness_profile 对同 key 是 excluded **并集**语义（provider:model 全
    # 专家共享同一 key，先装配的无槽卡会永久并回两件），减法无效。改为：built-in 两件保持排除
    # （无同名冲突），卡有 agent_edit 槽时在 tools 追加**自定义记忆槽写入件**（additive，见下
    # _build_memory_edit_tools）——放行面=槽白名单，三层防线仍完整。
    # 批13-AB1：排除栏条件化——从「常态杀默认摘要件」变为「能力开关关闭时的执行器」。
    # 开关开：官方工厂件 .name="SummarizationMiddleware" 与框架自动件同名 -> graph.py 拼接机
    #         原地替换（我们的件顶掉自动件），排除栏必须为空，否则把工厂件也排除了；
    # 开关关：排除栏把框架自动摘要件撤掉、我们也不装配——两种状态全栈都只有一个摘要件。
    _mw_excl = frozenset({"SummarizationMiddleware"}) if not _on("summarization") else frozenset()
    _registered_keys = []
    if _model_provider and _model_id and ":" not in _model_id:
        _key = f"{_model_provider}:{_model_id}"
        register_harness_profile(_key, HarnessProfile(excluded_tools=_excluded, excluded_middleware=_mw_excl))
        _registered_keys.append(_key)
        # 同时注册大小写变体（防 DB 存 DeepSeek-V4-Flash 但模型返回 deepseek-v4-flash）
        _key_lower = f"{_model_provider}:{_model_id.lower()}"
        if _key_lower != _key:
            register_harness_profile(_key_lower, HarnessProfile(excluded_tools=_excluded, excluded_middleware=_mw_excl))
            _registered_keys.append(_key_lower)
    elif _model_id:
        # fallback: 只有 identifier（含冒号或无 provider）
        register_harness_profile(_model_id, HarnessProfile(excluded_tools=_excluded, excluded_middleware=_mw_excl))
        _registered_keys.append(_model_id)
    logger.info(f"[HarnessProfile] 已注册 {len(_registered_keys)} 个 key: {_registered_keys}："
                f"W-1 白名单换算排除 {len(_excluded)} 件"
                f"{' + SummarizationMiddleware(开关关)' if _mw_excl else ''}")

    # v3.2 下一步判断闸门（feature flag）：TUPU_DECISION_GATE=1 时装配，
    # 工具调用前强校验同轮"下一步判断"(已知/判断/因此)+真实工具名+一轮单工具；
    # execute_sql 额外校验客户名范围。默认关(.env 已设 1，验收默认启用)。
    middleware_list = []  # v3.6: excluded_mw 已由 HarnessProfile(excluded_tools=...) 替代
    # M1（融合设计 §三）：悬空 tool_calls 修复——会话中断后同 thread 续问时，
    # 把历史里未应答的 tool_call 补 ToolMessage("cancelled")，避免复跑报错。
    # 该中间件由框架 create_deep_agent 自动追加（graph.py:802，位于用户 middleware 之前，
    # 先于 SkillPolicy 闸门）；不在此显式装配——langchain factory 对同名中间件有去重断言
    # （len({m.name}) != len(middleware) 抛 AssertionError），显式会与自动件冲突。
    # 受控执行契约硬校验（设计 §6）：最外层闸门——先于 DecisionGate 拦截越权/禁用工
    # 具/模板外 SQL/引擎切换/结果后再查；契约由 data_intelligence 路由后经 context 注入。
    # P0-1 fail-closed：装配失败必须阻止 Agent 创建（不允许降级成只有 DecisionGate 的自由 Agent）。
    from app.services.skill_policy import SkillPolicyMiddleware
    # ②批补验（spec §五三重防线第二层）：agent_edit 槽路径**装配期快照**注入——
    # 运行时读 ContextVar 不可行（langgraph 同步工具在 executor 线程，ContextVars 不跨线程）。
    from app.services.memory_slots import normalize_memory_field as _nmf_sp
    _agent_edit_paths = _agent_edit_slot_rels(card)
    # 权限重构T5（design §6.2 派发点）：用户身份+专家工具面+装配期允许清单注入——
    # awrap_tool_call 前置复核（check_tool_call），拒绝返回结构化 tool_error + 审计落痕。
    middleware_list.insert(0, SkillPolicyMiddleware(
        agent_edit_paths=_agent_edit_paths,
        user=user,
        expert_tools=(card or {}).get("tools"),
        allowed_tools=_t5_allowed_names if user is not None else None,
    ))
    logger.info("[SkillPolicy] 受控执行契约中间件已装配（最外层闸门，技能/步骤/模板/引擎/终止硬校验）")
    # 记忆插槽②（spec §六）：L1 轨迹——洋葱最外层（SkillPolicy 之前；守卫拒绝也记）。
    # wenshu slots=[] → 不装配（no-op）；manifest 记 memory_trace: active|inactive。
    from app.services.memory_slots import normalize_memory_field
    _l1 = [s for s in normalize_memory_field((card or {}).get("memory")).get("slots") or []
           if s.get("type") == "L1_TRACE"]
    if _l1:
        from app.services.memory_trace import MemoryTraceMiddleware
        middleware_list.insert(0, MemoryTraceMiddleware(card))
        logger.info(f"[L1] 记忆轨迹中间件已装配（最外层，surfaces={[s.get('surface') for s in _l1]}）")
    # 批13-AB2：SkillEntityResolverMiddleware（read_file 运行时 ⟦⟧ 翻译站）已删除——
    # 模型按 AGENTS.md §五纪律主动 search_entities 翻译，漏网 SQL 由模板守卫硬拒。
    # 批13-AB4：DataSummaryMiddleware（数据摘要运行时站）已删除——
    # 摘要逻辑下沉 mcp_server._with_result_ref（工具端截断）+ SSE 路由层 result_ref 派发。
    # 批13-W W-4a/W-4b：决策门装卸与范围工具集配置化——env 兜底 or 管理页开关；scope_tools 入 params
    _dg_cfg = _cc.get_decision_gate_config() if _cc is not None else {
        "enabled": os.getenv("TUPU_DECISION_GATE", "") == "1",
        "scope_tools": ["execute_sql", "execute_doris_sql", "execute_entity_api", "execute_api_sql"]}
    if _dg_cfg["enabled"] and not bool(card and (card.get("expert_id") or "wenshu") != "wenshu"):
        from app.services.decision_gate import DecisionGateMiddleware
        middleware_list.append(DecisionGateMiddleware(scope_gated=frozenset(_dg_cfg["scope_tools"])))
        logger.info(f"[DecisionGate] 下一步判断闸门已装配（env={_dg_cfg.get('env_fallback') or '未设'}/管理页）："
                    f"全工具理由校验 + 范围强校验 {sorted(_dg_cfg['scope_tools'])}")
    elif bool(card and (card.get("expert_id") or "wenshu") != "wenshu"):
        logger.info("[DecisionGate] ⑤R E1：非 wenshu 专家卡不装判断闸门（原仓教学代理无此协议）")
    else:
        logger.warning("[DecisionGate] 下一步判断闸门未装配（env 未设=1 且管理页开关关）")

    # M1（批13-AB1 摘要回退官方默认）：官方工厂 create_summarization_middleware 双件套，
    # 替代自研保守阈值摘要件（30k/10/15 + 批5-C3 观测钩子——
    # 摘要历史触发 0 次，无账可记，钩子随之退役）。
    # 同名替换机制：工厂实例 .name="SummarizationMiddleware"（框架公开别名），与框架自动追加的
    # 默认阈值件同名 -> graph.py 拼接机原地替换（我们的工厂件顶掉自动件），全程不需要排除栏。
    # 风险登记（复盘条件，见《摘要官方化回退与站点技能化详细实施设计》§1.3）：
    # 170k(无 profile 固定默认) > DeepSeek 真实窗口 -> 主动压缩可能永不触发；
    # 保护=官方 ContextOverflowError 应急路（超限拒绝->压缩->重试）。复盘触发：
    # ①日志出现超限重试 ②会话普遍>100k token ③13-G 数据显示长会话常态化——
    # 届时为模型补 profile(max_input_tokens) 使工厂自适应 85%，不再自定义阈值。
    from deepagents.middleware.summarization import (
        create_summarization_middleware,
        SummarizationToolMiddleware,
    )
    if _on("summarization"):
        _summ_mw = create_summarization_middleware(model, backend)   # 官方工厂(默认参数,无 profile: 170k/6/20-20)
        middleware_list.append(_summ_mw)                              # .name 与框架自动件同名 -> 原地替换
        middleware_list.append(SummarizationToolMiddleware(_summ_mw))  # 官方手动压缩件(compact_conversation)
        logger.info("[Summarization] 官方默认摘要件已装配(工厂默认阈值)+compact_conversation 工具")
    else:
        logger.warning("[Capability] summarization 已关闭：不装配自动摘要件（长会话可能触达上下文上限）")

    # M3（批13-AB3 评分站 mode 化）：能力项 rubric.params.mode 二选一——
    #   "middleware"：独立评分模型路径（_TupuRubricMiddleware，max_iterations=1，grader 温度 0.0
    #     可用 TUPU_RUBRIC_CONNECTION_ID 指轻量连接；on_evaluation 走治理+sink）——原路径保留可切回；
    #   "skill_prompt"（默认，用户定调）：不装配评分站，自检段 RUBRIC_SELF_CHECK_PROMPT 注入动态
    #     系统提示词（_build_dynamic_system_prompt 同条件判断），同模型自评；代价登记见设计 §3.4。
    # TUPU_RUBRIC_DISABLED=1 时两模式都不激活（§6.2 eval 开/关对比度量净收益）。
    # rubric_status 口径：skill_prompt 模式下 _runtime["rubric_status"] 不写（无 grader/无豁免），
    # 前端按「未评」展示，与 TUPU_RUBRIC_DISABLED=1 既有语义对齐——前端零改动。
    from deepagents.middleware.rubric import RubricMiddleware
    import os as _os3
    _rubric_mode = _rubric_effective_mode()  # 批13-AB3：模块级统一口径（disabled/middleware/skill_prompt）
    if _rubric_mode != "disabled":
        if _rubric_mode == "middleware":
            _rubric_conn = _os3.getenv("TUPU_RUBRIC_CONNECTION_ID", "") or connection_id
            _rubric_model = get_chat_model(temperature=0.0, streaming=True, connection_id=_rubric_conn)
            _rubric_mw = _TupuRubricMiddleware(model=_rubric_model, max_iterations=1,
                                               on_evaluation=_on_rubric_evaluation)
            middleware_list.append(_rubric_mw)
            logger.info(f"[Rubric] 自评闸门已装配（max_iterations=1，grader conn='{_rubric_conn}'，含批10-B'-1 clean_aggregate 豁免）"
                        f" 实例类={type(_rubric_mw).__name__} 覆写生效={type(_rubric_mw).after_agent is not RubricMiddleware.after_agent}")
        else:
            logger.info("[Rubric] skill_prompt 模式：自检段注入系统提示词（middleware 路径保留可切回）")
    else:
        logger.warning("[Rubric] 跳过自评闸门装配（TUPU_RUBRIC_DISABLED=1 或 capability rubric 已关闭）")

    # F5/批13-Q: response_format（统一最终交付协议）按能力开关装配（final 扁平 schema）。
    # 结构化降级仍由 data_intelligence 的 A-E 确定性降级策略兜底（structured_degraded 标识）。
    _response_format = _FINAL_RESPONSE_FORMAT if _on("response_format") else None
    if _response_format is not None:
        logger.info("[Capability] response_format 已装配（final 扁平 schema，结构化最终交付）")

    # 批13-Q：store（长期记忆库，运行时类能力）——InMemoryStore 注入，支持跨会话命名空间偏好存取。
    _store = None
    if _on("store"):
        from langgraph.store.memory import InMemoryStore
        _store = InMemoryStore()
        logger.info("[Capability] store 已装配（InMemoryStore，跨会话偏好存取）")

    # 批13-Q：subagents 受限启用（四护栏）——护栏2/3 在 build_subagent_specs：
    # 子代理显式携带守卫链（SkillPolicyMiddleware 复用父实例，契约经 context 共享传导）；
    # 规格工具集窄化到全局白名单子集，空交集拒装配 + spec_invalid 事件。
    _subagents = None
    if _on("subagents"):
        from app.services.subagent_specs import build_subagent_specs
        _skill_policy_mw = next((m for m in middleware_list if type(m).__name__ == "SkillPolicyMiddleware"), None)
        _subagents = build_subagent_specs(_cap("subagents"), model,
                                          guard_middlewares=[_skill_policy_mw] if _skill_policy_mw else None,
                                          parent_tools=mcp_tools)
        if _subagents:
            logger.info(f"[Capability] subagents 已装配（{len(_subagents)} 个规格：{[s['name'] for s in _subagents]}）")
        else:
            logger.warning("[Capability] subagents 开启但全部规格被护栏拒绝（回退串行定位）")

    # 批13-Q：debug 能力 -> create_deep_agent(debug=True)（框架图执行详细日志，开发排障用）。
    _debug = _on("debug")

    agent = create_deep_agent(
            model=model,
            tools=mcp_tools,
            system_prompt=_build_dynamic_system_prompt(
                base=(card or {}).get("system_prompt"),
                # ⑤R E1：非 wenshu 专家卡=纯净卡基座（无 wenshu 工作流规则块）
                expert_card=bool(card and (card.get("expert_id") or "wenshu") != "wenshu"),
            ),
            state_schema=TupuAgentState,
            context_schema=TupuAgentContext,  # F4: 原生运行时上下文（不进 checkpoint）
            response_format=_response_format,  # F5/批13-Q: 结构化最终答案（按能力开关装配）
            checkpointer=checkpointer,
            backend=backend,
            permissions=permissions,  # 批13-Q: 按能力开关装配（None=无规则约束）
            skills=(card or {}).get("skills") if _on("skills") else None,  # 批13-Q+专家地基①: 按卡装配
            memory=_mem_inject_list(card or {}) if _on("memory") else None,  # M2/批13-Q+①按卡+②注入列表（legacy 优先+槽按 order）
            subagents=_subagents,  # 批13-Q: subagents 受限启用（四护栏）
            store=_store,  # 批13-Q: 长期记忆库
            debug=_debug,  # 批13-Q: 调试模式
            middleware=middleware_list,
        )

    # 批13-Q：装配清单落盘（探针读；patch_tool_calls/message_eviction 为框架自动件，恒装=True）
    try:
        from app.services.capability_config import get_version as _cap_version
        _cap_ids = ["skills", "filesystem_tools", "memory", "summarization", "rubric",
                    "patch_tool_calls", "message_eviction", "response_format", "store",
                    "subagents", "permissions", "debug", "approval_track"]
        manifest_items = {}
        for _cid in _cap_ids:
            manifest_items[_cid] = _on(_cid)
        manifest_items["patch_tool_calls_frame"] = True   # 框架自动件恒装（graph.py L674/759/844）
        manifest_items["message_eviction_frame"] = True   # 框架自动件恒装
        manifest_items["subagent_specs"] = [s["name"] for s in (_subagents or [])]
        manifest_items["response_format_installed"] = _response_format is not None
        manifest_items["store_installed"] = _store is not None
        # 批13-AB1：摘要装配模式（探针断言用）——"official_factory"=官方工厂双件套同名替换
        manifest_items["summarization_mode"] = "official_factory" if _on("summarization") else "disabled"
        # 批13-AB4：数据摘要模式（探针断言用）——"tool_ref"=工具端暂存+SSE result_ref 派发
        manifest_items["data_summary_mode"] = "tool_ref"
        # 批13-AB3：评分模式（探针断言用）——skill_prompt=自检段进提示词 / middleware=独立评分站
        manifest_items["rubric_mode"] = _rubric_mode
        # 批13-Y：backend 模式与种子状态（探针断言用）
        manifest_items["backend_mode"] = "store" if _on("filesystem_tools") else "state_only"
        manifest_items["files_hash"] = _compute_files_hash(card)
        manifest_items["seeded_files"] = _n_seeded
        # 专家地基①（2026-09-12 spec §五）：manifest +2 项——A1 等值判据允许且仅允许的新增项
        manifest_items["expert_id"] = (card or {}).get("expert_id")
        manifest_items["card_version"] = (card or {}).get("version")
        # 记忆插槽②（spec §六）：L1 轨迹装配探针——wenshu slots=[] → "inactive"（②对账判据）
        manifest_items["memory_trace"] = "active" if _l1 else "inactive"
        # 批13-W W-1：装配清单记白名单换算后的排除清单（双向探针断言：勾了的在 Agent 工具表、
        # 没勾的不在——换算结果即「没勾的」，红线 5 件恒在）
        try:
            from app.services import capability_config as _cc2
            # ⑤R E1 分层：探针记本卡实装排除=W-1 运维排除（仅 wenshu 卡承载）∪ 红线 5
            _w1_applied = frozenset() if _is_expert_card else frozenset(_cc2.get_tool_exclusions()["excluded"])
            manifest_items["tool_availability_installed"] = sorted(
                _w1_applied | set(_cc2.W1_REDLINE_EXCLUSIONS))
        except Exception:
            manifest_items["tool_availability_installed"] = sorted(
                {"grep", "glob", "write_file", "edit_file", "execute"})
        # 批13-W W-4：决策门装卸探针 + 参数一致性探针（params 声明==栈内实例 scope_gated）
        # ⑤R E1：非 wenshu 专家卡不装闸门——探针记实装态（与 middleware_list 一致）
        _dg_installed = bool(_dg_cfg["enabled"]) and not _is_expert_card
        manifest_items["decision_gate_installed"] = _dg_installed
        manifest_items["scope_gated_installed"] = sorted(_dg_cfg["scope_tools"]) if _dg_installed else []
        _ASSEMBLY_MANIFEST.clear()
        _ASSEMBLY_MANIFEST.update({
            "version": _cap_version(), "agent_key": connection_id or "__default__",
            "items": manifest_items,
        })
    except Exception as _mfe:
        logger.warning(f"[Capability] 装配清单写入失败（不影响运行）: {_mfe}")

    return agent


async def create_tupu_agent(checkpointer=None, connection_id: str = "", expert_id: str = "wenshu", role_id: str = None):
    """创建 tupu DeepAgent（业务工具走 MCP）——批13-Q fail-safe 包装器。

    按能力开关（capability_config）条件装配；新配置装配失败自动回退上一可用版本
    （fallback 事件+告警，配置写坏不至于全瘫）；回退也失败则 fail-closed 阻止创建（P0-1）。
    专家地基①（2026-09-12 spec §五/§十）：读专家卡传入装配；回退路径连卡快照一起回退；
    仍败 raise + expert_events 落 assembly_failed（行为契约）。
    """
    from app.services import capability_config
    from app.services import expert_config as _ec
    try:
        card, _src = _ec.get_card(expert_id, with_source=True)
    except KeyError as _ke:
        raise RuntimeError(f"未知专家: {expert_id}") from _ke
    caps = {p["capability_id"]: p for p in capability_config.get_policies()}
    _last = _LAST_GOOD_ASSEMBLY.get(expert_id) or {}  # 批6 E3：按专家取回退快照（不跨专家串卡）
    try:
        agent = await _build_agent(checkpointer=checkpointer, connection_id=connection_id, caps=caps, card=card, role_id=role_id, user=user)
        _LAST_GOOD_ASSEMBLY[expert_id] = {"caps": caps,
                                          "caps_version": capability_config.get_version(),
                                          "card": card}
        return agent
    except Exception as e:
        if _last.get("caps"):
            logger.error(f"[Capability] 专家 {expert_id} 新配置装配失败，fail-safe 回退其上一可用版本: {e}")
            try:
                capability_config.record_event(
                    "assembly", "fallback",
                    detail={"expert_id": expert_id, "reason": str(e)[:300],
                            "failed_version": capability_config.get_version(),
                            "fallback_version": _last.get("caps_version")},
                    updated_by="assembly", _sync=True)
                return await _build_agent(checkpointer=checkpointer, connection_id=connection_id,
                                          caps=_last["caps"],
                                          card=_last.get("card"), role_id=role_id, user=user)
            except Exception as e2:
                logger.error(f"[Capability] 回退装配也失败（fail-closed 阻止创建）: {e2}")
                try:
                    _ec.record_event(expert_id, "assembly_failed",
                                     detail={"reason": str(e2)[:300]}, updated_by="assembly")
                except Exception:
                    pass
                raise
        try:
            _ec.record_event(expert_id, "assembly_failed", detail={"reason": str(e)[:300]}, updated_by="assembly")
        except Exception:
            pass
        raise


def build_skill_system_message(skill_name: str = "") -> str:
    """构建技能级 system 指令（按请求注入到 messages 中）。

    skill_name 为空时走自主模式（注入全量技能概要，LLM 自主选技能）；
    传入技能名时注入对应 SKILL.md 指南。
    """
    return _build_dynamic_system_prompt(skill_hint=skill_name)


# ---------------------------------------------------------------------------
# 5. 全局 Agent 实例（单例，带 checkpointer）
# ---------------------------------------------------------------------------

_GLOBAL_AGENTS: dict[str, Any] = {}  # v3.6: 按 connection_id 缓存 Agent（让前端选模型生效）
_GLOBAL_CHECKPOINTER = None
_AGENT_INIT_LOCK = asyncio.Lock()  # 防止多个请求并发首次初始化 Agent

_CHECKPOINT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "deepagent_checkpoints.db"
)


def _migrate_checkpoint_thread_ids(db_path: str = None) -> int:
    """专家地基①（spec §九步骤 4）：checkpoint 两段→三段键迁移。

    对库内全部含 thread_id 列的表执行（实测=checkpoints+writes，langgraph 双表）；
    检测谓词=恰含一个冒号；变换=第一个冒号后插入 'wenshu:'（首冒号插入法——
    严禁整串拼接）；幂等（三段键两冒号不满足谓词自然跳过）；
    try/except：失败记日志返 0，不允许打死平台（lifespan 启动期调用，服务就绪前完成）。
    """
    import sqlite3
    _path = db_path or _CHECKPOINT_DB
    _total = 0
    try:
        con = sqlite3.connect(_path)
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            for t in tables:
                cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
                if "thread_id" not in cols:
                    continue
                cur = con.execute(
                    f"UPDATE {t} SET thread_id = "
                    f"substr(thread_id, 1, instr(thread_id, ':')) || 'wenshu:' || "
                    f"substr(thread_id, instr(thread_id, ':') + 1) "
                    f"WHERE thread_id LIKE '%:%' AND thread_id NOT LIKE '%:%:%'")
                _total += cur.rowcount
            con.commit()
        finally:
            con.close()
        if _total:
            logger.info(f"[专家地基] checkpoint 三段键迁移完成：{_total} 行（双表合计）")
    except Exception as e:
        logger.warning(f"[专家地基] checkpoint 迁移失败（旧键失联但服务活，幂等可重跑）: {e}")
        return 0
    return _total


def _evict_old_agents(current_key: str) -> None:
    """批13-Q：LRU 保留最近 2 个 capability 版本的 Agent 实例，更旧版本回收。
    专家地基①（spec §五）：改按 expert 分组——`#e{expert}@{版本}` 段取专家身份，
    组内按版本排，各组保留最近 2 版（防专家互相挤占）；无 #e 段的旧键归 __default__ 组。

    在跑请求持有的旧实例引用不受 dict 回收影响（Python 引用计数）。
    """
    import re as _re
    try:
        groups: dict = {}
        for k in list(_GLOBAL_AGENTS.keys()):
            m_e = _re.search(r"#e([A-Za-z0-9_-]+)@(\d+)", k)
            if m_e:
                eid, ver = m_e.group(1), int(m_e.group(2))
            else:
                m_c = _re.search(r"#c(\d+)", k)
                eid, ver = "__default__", (int(m_c.group(1)) if m_c else 0)
            groups.setdefault(eid, []).append((ver, k))
        for _eid, entries in groups.items():
            versions = sorted({v for v, _ in entries}, reverse=True)
            keep_versions = set(versions[:2])
            for v, k in entries:
                if v not in keep_versions and k != current_key:
                    _GLOBAL_AGENTS.pop(k, None)
                    logger.info(f"[DeepAgent] LRU 回收旧版本 Agent[{_eid}]: {k}")
    except Exception as e:
        logger.warning(f"[DeepAgent] LRU 回收失败（不影响运行）: {e}")


def _capabilities_of(raw) -> dict:
    """统一规则（spec §4.1）：缺省/NULL/损坏 ⇒ D5 默认；缺键补默认。"""
    d5 = {"tool_call": True, "vision": False, "json_mode": False, "stream": True}
    try:
        caps = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(caps, dict):
            raise ValueError("非对象")
        return {**d5, **{k: caps[k] for k in d5 if k in caps}}
    except Exception as e:
        logger.warning(f"[模型目录化] capabilities 损坏或缺省，按 D5 默认处理: {e}")
        return d5


def _assert_tool_call_capable(conn_id, caps) -> None:
    """门控（spec §4.2）：拒绝优于静默降级——Agent 全链依赖工具调用。"""
    if _capabilities_of(caps).get("tool_call") is not True:
        raise ValueError(f"连接 {conn_id} 的模型不支持工具调用，无法装配 Agent——"
                         f"请在 LLM 配置页改用支持工具调用的连接")


async def get_tupu_agent(connection_id: str = "", expert_id: str = "wenshu", role_id: str = None, user=None):
    """获取 tupu DeepAgent（按 connection_id + capability 版本缓存，让前端选模型/能力开关真正生效）。

    v3.6: 按 connection_id 缓存不同模型的 Agent 实例（空串用默认模型）。
    批13-Q: 缓存键并入能力版本号（<conn>#g{guard}#c{caps}）——PATCH 能力开关后 version+1 ->
    新键建新实例；旧实例 LRU 保留最近 2 个版本（在跑请求不断）；重建写 capability_events(rebuild)。
    专家地基①（2026-09-12 spec §五）：缓存键 4→6 因子（+#e{expert}@{card_version}）；
    装配按卡分发；files_hash 按卡路径；LRU 按专家分组。
    懒加载 + 初始化锁：首次真实请求时才创建。
    """
    global _GLOBAL_CHECKPOINTER
    # 审批轨（approval_track，批13-V）+ 能力开关中心（批13-Q）版本号并入缓存键：
    # 任一守卫/能力 PATCH 后版本+1，下一个请求按新配置重建 Agent。
    try:
        from app.services import guard_config as _gc
        _gver = _gc.get_version()
    except Exception:
        _gver = 0
    try:
        from app.services import capability_config as _cc
        _cver = _cc.get_version()
    except Exception:
        _cver = 0
    # 专家地基①：读专家卡（版本进缓存键 #e 因子；卡读取失败 wenshu 兜底/其他专家如实上屏——get_card 语义）
    from app.services import expert_config as _ec
    card = _ec.get_card(expert_id)
    _ecard_ver = card.get("version") or 1
    # 批13-Y：files_hash 并入缓存键——技能/纪律树任何增删改 -> hash 变 -> 缓存未命中 ->
    # 重装配+重种子（下次请求生效；进行中会话用旧种子，低频运维可接受，设计 §五.1）。
    # 专家地基①：按卡路径派生根集合（wenshu 等值现状两根）。
    try:
        _fhash = _compute_files_hash(card)
    except Exception:
        _fhash = "err"
    # ③模型目录化（spec §4.2）：装配前能力门控——连接解析后、缓存键计算前（坏连接不进缓存）。
    # 含①卡默认连接同校验：connection_id 空串→get_llm_connection_by_id 直接 None→跳过门控
    # （走 get_chat_model 默认连接解析，其能力位由配置页维护为 tool_call=true）。
    if connection_id:
        try:
            from app.services.llm_client import get_llm_connection_by_id
            _conn = get_llm_connection_by_id(connection_id, "chat")
            if _conn is not None:
                _assert_tool_call_capable(_conn.id, _conn.capabilities)
        except ValueError:
            raise
        except Exception as _gate_err:
            logger.warning(f"[模型目录化] 门控预检异常（放行交由装配兜底）: {_gate_err}")
    # 权限重构T5：auth=1 且非匿名时缓存键加 #u 因子（按用户装配工具面）；
    # ENABLE_AUTH=0 / 匿名 admin → 键不变（开发态零影响）。
    _t5_user = user if (user is not None and not getattr(user, "is_anonymous", False)) else None
    _cache_key = _assembly_cache_key(connection_id, _gver, _cver, _fhash, expert_id, _ecard_ver, role_id=role_id)
    if _t5_user is not None:
        _cache_key += f"#u{_t5_user.sub}"
    if _cache_key not in _GLOBAL_AGENTS:
        async with _AGENT_INIT_LOCK:
            if _cache_key not in _GLOBAL_AGENTS:
                if _GLOBAL_CHECKPOINTER is None:
                    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
                    import aiosqlite
                    os.makedirs(os.path.dirname(_CHECKPOINT_DB), exist_ok=True)
                    _GLOBAL_CHECKPOINTER = AsyncSqliteSaver(aiosqlite.connect(_CHECKPOINT_DB))
                # 批13-Q：已有旧版本实例在缓存 -> 本次为能力/守卫版本失配重建 -> 写 rebuild 事件
                if _GLOBAL_AGENTS:
                    try:
                        from app.services import capability_config as _cc
                        _cc.record_event("assembly", "rebuild",
                                         detail={"new_key": _cache_key, "caps_version": _cver,
                                                 "old_keys": list(_GLOBAL_AGENTS.keys())[:4]},
                                         updated_by="assembly")
                    except Exception:
                        pass
                agent = await create_tupu_agent(
                    checkpointer=_GLOBAL_CHECKPOINTER,
                    connection_id=connection_id or None,
                    expert_id=expert_id,
                    role_id=role_id,
                )
                _GLOBAL_AGENTS[_cache_key] = agent
                _evict_old_agents(_cache_key)
                # 专家地基①（D2）：专家维度 rebuild 落账——新键装配=该专家按新版本重建
                try:
                    _ec.record_event(expert_id, "rebuild",
                                     detail={"new_key": _cache_key, "card_version": _ecard_ver},
                                     updated_by="assembly")
                except Exception:
                    pass
                logger.info(f"[DeepAgent] tupu ReAct agent 已创建 (key={_cache_key}), checkpoint={_CHECKPOINT_DB}")
    return _GLOBAL_AGENTS[_cache_key]


async def close_tupu_agent():
    """关闭全局 Agent 的 checkpointer 连接（FastAPI shutdown 阶段调用）。
    MCP 连接无需手动关闭（langchain-mcp-adapters 每次工具调用新建 session）。
    """
    global _GLOBAL_CHECKPOINTER
    if _GLOBAL_CHECKPOINTER is not None:
        try:
            # AsyncSqliteSaver 底层是 aiosqlite.Connection，支持 close
            _conn = getattr(_GLOBAL_CHECKPOINTER, "conn", None)
            if _conn is not None:
                await _conn.close()
            logger.info("[DeepAgent] checkpointer SQLite 连接已关闭")
        except Exception as e:
            logger.warning(f"[DeepAgent] 关闭 checkpointer 失败: {e}")
        finally:
            _GLOBAL_CHECKPOINTER = None


async def reset_tupu_agent():
    """重置全部缓存 Agent（aiosqlite 连接断开后重建用）。

    aiosqlite 的 Connection 内部线程关闭后不能重启（RuntimeError: threads can
    only be started once）。一旦 checkpointer 连接断开，所有后续请求都会失败。
    调用此函数清空所有 connection_id 缓存的 Agent，下次请求时自动用新连接重建。
    """
    global _GLOBAL_CHECKPOINTER
    async with _AGENT_INIT_LOCK:
        if _GLOBAL_CHECKPOINTER is not None:
            try:
                _conn = getattr(_GLOBAL_CHECKPOINTER, "conn", None)
                if _conn is not None:
                    await _conn.close()
            except Exception:
                pass
        _GLOBAL_AGENTS.clear()
        _GLOBAL_CHECKPOINTER = None
        logger.info("[DeepAgent] 全部缓存 agent 已重置（将在下次请求时用新连接重建）")
