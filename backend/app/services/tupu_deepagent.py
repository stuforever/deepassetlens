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
from typing import Annotated, Any, Dict, List, Literal, TypedDict

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
    # v3.5 结构化会话上下文：跨轮继承客户范围，不依赖 LLM 指代消解概率
    last_scope: NotRequired[dict]                             # {customer_names: [...], ordered: bool, commitment: str, source_turn_id: str}
    # 评审 P1-5 受控上下文跨轮：确定性代码在路由成功后写回 checkpoint，供下轮"连续上下文优先"
    last_skill: NotRequired[str]                              # 本轮命中场景 skill_id（generic 时为 None）
    last_step: NotRequired[str]                               # 本轮命中步骤 id


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

# v3.2 下一步判断闸门 feature flag：TUPU_DECISION_GATE=1 启用（灰度，默认关）
# 启用后：system_prompt 注入"下一步判断"指令 + create_tupu_agent 装配 DecisionGateMiddleware
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
5. **禁止调用 task 子代理做分块查询**：task 子代理仅用于需要独立推理链的复杂分析，不用于简单的全量数据查询。
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
    # 解析 ⟦实体中文名⟧ -> 物理表名（entity_en_name）
    content = _resolve_entity_refs(content)
    return content


# ⟦中文名⟧ 正则：匹配 ⟦ 和 ⟧ 之间的内容（不含换行）
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


class SkillEntityResolverMiddleware(AgentMiddleware):
    """技能文件 ⟦中文名⟧ -> 物理表名 解析中间件。

    单一职责：read_file 成功返回技能文件内容后，对其中的 ⟦实体中文名⟧ 占位符
    做物理表名解析（与 SKILL.md 主文件一致）。

    安全说明（P0 修复）：原 SkillEntityRefMiddleware 含磁盘 fallback 职责，当 read_file
    在 StateBackend 找不到子文件时直接从磁盘读取--这是目录穿越漏洞的根因。现已切换到
    CompositeBackend + FilesystemBackend(virtual_mode=True)，子文件由原生 Backend 安全提供，
    不再需要任何磁盘逃生通道。本中间件只处理已由安全 Backend 成功读取的内容，绝不自行访问磁盘。
    """

    async def awrap_tool_call(self, request, handler):
        tool_name = request.tool_call.get("name", "")
        tool_result = await handler(request)
        if tool_name != "read_file":
            return tool_result

        # ⟦中文名⟧ 解析（正常路径：文件已由 CompositeBackend 安全读取）
        try:
            content = getattr(tool_result, "content", None)
            if isinstance(content, str) and '⟦' in content:
                resolved = _resolve_entity_refs(content)
                if resolved != content:
                    object.__setattr__(tool_result, "content", resolved)
        except Exception:
            pass  # 解析失败不阻断 read_file
        return tool_result


# 数据查询工具集合：返回 {columns, rows, row_count} 格式的工具，统一做摘要截断
_DATA_QUERY_TOOLS = frozenset({
    "execute_doris_sql",    # Doris 联邦
    "execute_sql",          # 物理直连
    "execute_entity_api",   # DuckDB API 联邦（单对象）
    "execute_api_sql",      # DuckDB API 联邦（多源SQL）
})
_SUMMARY_THRESHOLD = 10  # 超过此行数则截断为摘要


class DataSummaryMiddleware(AgentMiddleware):
    """数据查询结果摘要中间件：明细数据不传 LLM 全量。

    拦截 execute_doris_sql / execute_sql / execute_entity_api / execute_api_sql：
    1. adispatch_custom_event("data_result", 完整数据) 推给前端（前端直出表格）
    2. ToolMessage content 截断为摘要（前10行 + row_count + _summary），LLM 只看摘要写结论
    row_count <= 10 时不截断（数据量小，全量给 LLM 无妨）。
    """

    async def awrap_tool_call(self, request, handler):
        tool_name = request.tool_call.get("name", "")
        tool_result = await handler(request)
        if tool_name not in _DATA_QUERY_TOOLS:
            return tool_result
        try:
            await self._summarize_and_dispatch(tool_result, request)
        except Exception as e:
            logger.warning(f"[DataSummary] 摘要截断失败({tool_name}): {e}", exc_info=True)
        return tool_result

    async def _summarize_and_dispatch(self, tool_result, request):
        """解析工具结果 -> 推完整数据给前端 -> 截断为摘要给 LLM。"""
        import json as _json

        content = getattr(tool_result, "content", None)
        if content is None:
            return
        # LangChain content blocks: [{"type":"text","text":"<JSON>"}] -> 取第一个 text block
        if isinstance(content, list):
            for _block in content:
                if isinstance(_block, dict) and _block.get("type") == "text" and isinstance(_block.get("text"), str):
                    content = _block["text"]
                    break
        if not isinstance(content, str):
            content = _json.dumps(content, ensure_ascii=False, default=str)
        if len(content) < 20:
            return  # 错误消息等短内容不处理

        # 解析 MCP 格式 {"type":"text","text":"<JSON>"} 或裸 JSON
        parsed = None
        try:
            parsed = _json.loads(content)
        except Exception:
            return
        # 解嵌套 text 字段（MCP tool 包装格式）
        if isinstance(parsed, dict) and isinstance(parsed.get("text"), str):
            try:
                parsed = _json.loads(parsed["text"])
            except Exception:
                return
        if not isinstance(parsed, dict):
            return
        # 必须有 rows + row_count 才处理
        if "rows" not in parsed or "row_count" not in parsed:
            return

        columns = parsed.get("columns", [])
        rows = parsed.get("rows", [])
        row_count = parsed.get("row_count", len(rows))
        logger.info(f"[DataSummary] {request.tool_call.get('name','')} row_count={row_count}, 派发 data_result + 截断摘要")

        # 派发完整数据给前端：前端拿到的是完整 rows -> is_preview 必须为 false。
        # 模型是否只看前 N 行分析样本，用 llm_is_preview / llm_preview_row_count 表达，不混用。
        config = request.runtime.config if request.runtime else None
        full_payload = {
            "columns": columns, "rows": rows,
            "row_count": row_count, "tool_name": request.tool_call.get("name", ""),
            "sql": parsed.get("sql", ""),                               # SQL 文本（前端"复制SQL"按钮用）
            "returned_rows": len(rows),                              # 前端实际拿到行数（=row_count，完整数据）
            "preview_row_count": min(_SUMMARY_THRESHOLD, row_count), # 兼容旧字段（前端不再依赖）
            "is_preview": False,                                     # 前端拿完整数据，一律 false
            "llm_is_preview": row_count > _SUMMARY_THRESHOLD,        # 模型是否只看前 N 行分析样本
            "llm_preview_row_count": min(_SUMMARY_THRESHOLD, row_count),  # 模型样本行数
            "result_available_for_ui": True,                          # 完整数据已推前端表格
            # 批3：数据快照披露（API 内存缓存命中时携带，前端对话卡标注快照时间）
            "data_snapshot_at": parsed.get("data_snapshot_at"),
            "cache_sources": parsed.get("cache_sources"),
        }
        await _dispatch_data_result(full_payload, config)

        # row_count <= 阈值：不截断，全量给 LLM
        if row_count <= _SUMMARY_THRESHOLD:
            return

        # 截断为摘要：前 N 行 + _summary
        summary_rows = rows[:_SUMMARY_THRESHOLD]
        # P0-B: 显著指令放在 JSON 前面，让 LLM 第一眼看到"数据已完整"
        _limit_reached = row_count >= 500  # SQL 强制 LIMIT 500
        _limit_hint = "（已达 LIMIT 500 上限，可能还有更多数据未取回）" if _limit_reached else "（未触发 LIMIT 截断，已是全部结果）"
        _directive = (
            f"【数据已完整获取】共 {row_count} 行{_limit_hint}。\n"
            f"下方仅展示前 {_SUMMARY_THRESHOLD} 行分析样本，完整 {row_count} 行数据已推前端查询结果表展示（is_preview=false）。\n"
            f"JSON 中 row_count={row_count}（完整结果数）、returned_rows={row_count}（前端拿到的完整行数）、"
            f"llm_is_preview=true、llm_preview_row_count={len(summary_rows)}（你的分析样本行数）、result_available_for_ui=true。\n"
            f"前 {_SUMMARY_THRESHOLD} 行只是你的分析样本，不是面向用户的展示数据：禁止复述为'明细如下'或制作预览表格。"
            f"row_count 就是全部数量，样本行数≠数据不完整。"
            f"**只能对 row_count 下全量结论；对行内字段只能说'样本显示'；'全部 X/所有 Y 均 Z'类结论必须由 SQL 聚合统计提供证据。**"
            f"禁止分页重查、禁止分段查询、禁止调用 task 子代理。"
            f"{'可能需要提示用户缩小范围。' if _limit_reached else '请直接基于 row_count 和样本写结论，并注明完整明细见下方查询结果表。'}\n"
        )
        summary = {
            "columns": columns,
            "rows": summary_rows,
            "row_count": row_count,                                  # 完整结果数
            "returned_rows": row_count,                              # 前端实际拿到的行数（完整数据）
            "preview_row_count": len(summary_rows),                  # 兼容旧字段（=llm_preview_row_count）
            "is_preview": False,                                     # 前端拿完整数据，一律 false
            "llm_is_preview": True,                                  # 你（模型）只拿到分析样本
            "llm_preview_row_count": len(summary_rows),              # 你的样本行数
            "result_available_for_ui": True,                         # 完整数据已推前端
            "_summary": f"共 {row_count} 行，仅展示前 {_SUMMARY_THRESHOLD} 行样例，完整数据已推前端直出",
            "_truncated": True,
            "_limit_reached": _limit_reached,
        }
        # 重新包装为 MCP 格式，指令前置
        new_inner = _json.dumps(summary, ensure_ascii=False, default=str)
        new_content = _json.dumps({"type": "text", "text": _directive + new_inner}, ensure_ascii=False, default=str)
        object.__setattr__(tool_result, "content", new_content)
        logger.info(f"[DataSummary] 已截断为前{_SUMMARY_THRESHOLD}行摘要（原{row_count}行，limit_reached={_limit_reached}）")


async def _dispatch_data_result(payload: dict, config):
    """派发 data_result 自定义事件给前端。"""
    try:
        from langchain_core.callbacks import adispatch_custom_event
        await adispatch_custom_event("data_result", payload, config=config)
    except Exception as e:
        logger.warning(f"[DataSummary] dispatch data_result 失败: {e}")


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

    if _DECISION_GATE_ENABLED:
        parts.append(_DECISION_GATE_RULES)
    parts.append(_DATA_COMPLETENESS_RULES)
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
    # content 解包（LangChain blocks / MCP 包装），与 DataSummaryMiddleware 同构
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
_LAST_GOOD_ASSEMBLY: dict = {"caps": None, "caps_version": 0}


async def _build_agent(checkpointer, connection_id: str, caps: dict):
    """按能力开关条件装配 DeepAgent（批13-Q 4.1）。失败抛异常，由 create_tupu_agent 包装器 fail-safe。"""
    from deepagents import create_deep_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient

    from app.services.llm_client import get_chat_model
    # streaming=True 让 on_chat_model_stream 产出 token 事件，避免长时间无反馈（对齐数据问答修复）
    # v3.6: 按 connection_id 选模型（让前端选模型真正生效）
    # S1d: 问数场景温度固化 0.1（要稳不要浪；rubric 判定模型保持 0.0 不变）
    # 注：batch 路由修复（sql_integration->execute_doris_sql）后 0.1 不再引发计数题回归（早前 0/3 为引擎锁死锁所致）
    model = get_chat_model(temperature=0.1, streaming=True, connection_id=connection_id)

    # MCP client 加载业务工具（16 个 tool，走 SSE，与 deepagent 解耦）
    # P3-a: 加内部服务身份 header（ENABLE_AUTH=1 时 MCP server 端校验，防外部直连）
    import os as _os
    _internal_token = _os.getenv("TUPU_INTERNAL_TOKEN", "")
    _mcp_headers = {"X-Internal-Service": "tupu-agent"}
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

    def _cap(cid: str) -> dict:
        return caps.get(cid) or {}

    def _on(cid: str) -> bool:
        return bool((_cap(cid) or {}).get("enabled"))

    from deepagents.backends import StateBackend, FilesystemBackend, CompositeBackend
    from pathlib import Path as _Path

    # CompositeBackend: /skills/ 路由到只读 FilesystemBackend（virtual_mode 防目录穿越），其他走 StateBackend
    # 安全原则（P0 修复）：原生 SkillsMiddleware 自动发现 SKILL.md frontmatter，Agent 按需 read_file 子文件，
    # 不再需要 data_intelligence.py 手工枚举 + 注入；FilesystemBackend 限制只能读技能目录。
    # M2（融合设计 §4.4）：/memory/ 路由到只读 FilesystemBackend（data/memory），供 MemoryMiddleware
    # 常驻纪律 AGENTS.md（全局长期纪律，运营可改文件；职责边界=动态系统提示仍由 _build_dynamic_system_prompt 承担）。
    # 批13-Q：filesystem_tools 关闭 -> 退化 StateBackend（无文件路由，文件工具不可用面收窄）。
    _skills_root = _Path(__file__).resolve().parent.parent.parent / "data" / "skills"
    _skills_backend = FilesystemBackend(root_dir=str(_skills_root), virtual_mode=True)
    _memory_root = _Path(__file__).resolve().parent.parent.parent / "data" / "memory"
    _memory_backend = FilesystemBackend(root_dir=str(_memory_root), virtual_mode=True)
    if _on("filesystem_tools"):
        backend = CompositeBackend(
            default=StateBackend(),
            routes={"/skills/": _skills_backend, "/memory/": _memory_backend},
        )
    else:
        backend = StateBackend()
        logger.warning("[Capability] filesystem_tools 已关闭：backend 退化为 StateBackend（文件路由不可用）")
    # 权限规则（按序匹配，首条命中生效，无命中默认允许）：
    #   1. 允许读 /skills/**（技能文件）
    #   2. 拒绝读 /**（兜底封堵：/skills/../../、/etc/passwd、.env 等全部 deny）
    #   3. 拒绝写 /**（业务问答不写文件）
    # 批13-Q：permissions 关闭 -> 不装配权限规则（backend 路由仍限制根目录，virtual_mode 防穿越仍在）。
    permissions = None
    if _on("permissions"):
        from deepagents.middleware.filesystem import FilesystemPermission
        permissions = [
            FilesystemPermission(operations=["read"], paths=["/skills/**"], mode="allow"),
            FilesystemPermission(operations=["read"], paths=["/**"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
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
    # 批13-J 收尾（问题二）：工具黑名单配置化——excluded 从 capability_policies.tool_availability 读
    # （定稿《装配层配置化设计》W-1；管理员可调整；默认 5 件与历史硬编码完全一致=迁移零变化）；
    # fail-safe：配置读崩 -> 默认 5 件（绝不全放开）。
    try:
        from app.services import capability_config as _cc
        _excl_cfg = _cc.get_tool_exclusions()
        _excluded = frozenset(_excl_cfg["excluded"])
    except Exception:
        _excluded = frozenset({"grep", "glob", "write_file", "edit_file", "execute"})
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
    logger.info(f"[HarnessProfile] 已注册 {len(_registered_keys)} 个 key: {_registered_keys}：排除 grep/glob/write_file/edit_file/execute"
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
    middleware_list.insert(0, SkillPolicyMiddleware())
    logger.info("[SkillPolicy] 受控执行契约中间件已装配（最外层闸门，技能/步骤/模板/引擎/终止硬校验）")
    # read_file 结果 ⟦中文名⟧ -> 物理表名 解析（技能子文件 reference/*.md templates/*.sql 受益）
    middleware_list.append(SkillEntityResolverMiddleware())
    # 数据查询结果摘要：明细不传 LLM 全量，推完整数据给前端 + ToolMessage 截断为前10行摘要
    middleware_list.append(DataSummaryMiddleware())
    if _DECISION_GATE_ENABLED:
        from app.services.decision_gate import SCOPE_GATED_TOOLS, DecisionGateMiddleware
        middleware_list.append(DecisionGateMiddleware(scope_gated=SCOPE_GATED_TOOLS))
        logger.info("[DecisionGate] 下一步判断闸门已启用 (TUPU_DECISION_GATE=1)：全工具理由校验 + execute_sql 范围强校验")
    else:
        logger.warning("[DecisionGate] 下一步判断闸门未启用 (TUPU_DECISION_GATE 未设为 1)：工具调用前不强制「已知/判断/因此」")

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

    # M3（融合设计 §5.1）：自评闸门 RubricMiddleware —— 仅调用方传 rubric 时激活（generic 契约，
    # scenario 不传即不激活）。grader 模型缺省会话模型；TUPU_RUBRIC_CONNECTION_ID 可指轻量连接。
    # max_iterations=1（只评不改，grader 放弃时不篡改消息，前端按 SSE 展示）；on_evaluation 走治理+sink。
    # TUPU_RUBRIC_DISABLED=1 时跳过装配（§6.2 eval 开/关对比度量净收益）。
    from deepagents.middleware.rubric import RubricMiddleware
    import os as _os3
    if _os3.getenv("TUPU_RUBRIC_DISABLED", "") != "1" and _on("rubric"):
        _rubric_conn = _os3.getenv("TUPU_RUBRIC_CONNECTION_ID", "") or connection_id
        _rubric_model = get_chat_model(temperature=0.0, streaming=True, connection_id=_rubric_conn)
        _rubric_mw = _TupuRubricMiddleware(model=_rubric_model, max_iterations=1,
                                           on_evaluation=_on_rubric_evaluation)
        middleware_list.append(_rubric_mw)
        logger.info(f"[Rubric] 自评闸门已装配（max_iterations=1，grader conn='{_rubric_conn}'，含批10-B'-1 clean_aggregate 豁免）"
                    f" 实例类={type(_rubric_mw).__name__} 覆写生效={type(_rubric_mw).after_agent is not RubricMiddleware.after_agent}")
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
            system_prompt=_build_dynamic_system_prompt(),
            state_schema=TupuAgentState,
            context_schema=TupuAgentContext,  # F4: 原生运行时上下文（不进 checkpoint）
            response_format=_response_format,  # F5/批13-Q: 结构化最终答案（按能力开关装配）
            checkpointer=checkpointer,
            backend=backend,
            permissions=permissions,  # 批13-Q: 按能力开关装配（None=无规则约束）
            skills=["/skills/"] if _on("skills") else None,  # 批13-Q: 按能力开关装配
            memory=["/memory/AGENTS.md"] if _on("memory") else None,  # M2/批13-Q: 常驻纪律（按能力开关装配）
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
        # 批13-J 收尾（问题二）：装配清单记实际排除名单（探针据此断言黑名单真生效 + 抓框架升级改工具名漂移）
        try:
            from app.services import capability_config as _cc2
            manifest_items["tool_availability_installed"] = sorted(_cc2.get_tool_exclusions()["excluded"])
        except Exception:
            manifest_items["tool_availability_installed"] = sorted(
                {"grep", "glob", "write_file", "edit_file", "execute"})
        _ASSEMBLY_MANIFEST.clear()
        _ASSEMBLY_MANIFEST.update({
            "version": _cap_version(), "agent_key": connection_id or "__default__",
            "items": manifest_items,
        })
    except Exception as _mfe:
        logger.warning(f"[Capability] 装配清单写入失败（不影响运行）: {_mfe}")

    return agent


async def create_tupu_agent(checkpointer=None, connection_id: str = ""):
    """创建 tupu DeepAgent（业务工具走 MCP）——批13-Q fail-safe 包装器。

    按能力开关（capability_config）条件装配；新配置装配失败自动回退上一可用版本
    （fallback 事件+告警，配置写坏不至于全瘫）；回退也失败则 fail-closed 阻止创建（P0-1）。
    """
    from app.services import capability_config
    caps = {p["capability_id"]: p for p in capability_config.get_policies()}
    try:
        agent = await _build_agent(checkpointer=checkpointer, connection_id=connection_id, caps=caps)
        _LAST_GOOD_ASSEMBLY["caps"] = caps
        _LAST_GOOD_ASSEMBLY["caps_version"] = capability_config.get_version()
        return agent
    except Exception as e:
        if _LAST_GOOD_ASSEMBLY.get("caps"):
            logger.error(f"[Capability] 新配置装配失败，fail-safe 回退上一可用版本: {e}")
            try:
                capability_config.record_event(
                    "assembly", "fallback",
                    detail={"reason": str(e)[:300], "failed_version": capability_config.get_version(),
                            "fallback_version": _LAST_GOOD_ASSEMBLY.get("caps_version")},
                    updated_by="assembly", _sync=True)
                return await _build_agent(checkpointer=checkpointer, connection_id=connection_id,
                                          caps=_LAST_GOOD_ASSEMBLY["caps"])
            except Exception as e2:
                logger.error(f"[Capability] 回退装配也失败（fail-closed 阻止创建）: {e2}")
                raise
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


def _evict_old_agents(current_key: str) -> None:
    """批13-Q：LRU 保留最近 2 个 capability 版本的 Agent 实例，更旧版本回收。

    缓存键形如 "<conn>#g{guard_ver}#c{caps_ver}"；按 caps 版本排序，保留最新 2 档。
    在跑请求持有的旧实例引用不受 dict 回收影响（Python 引用计数）。
    """
    import re as _re
    try:
        entries = []
        for k in list(_GLOBAL_AGENTS.keys()):
            m = _re.search(r"#c(\d+)", k)
            entries.append((int(m.group(1)) if m else 0, k))
        versions = sorted({v for v, _ in entries}, reverse=True)
        keep_versions = set(versions[:2])
        for v, k in entries:
            if v not in keep_versions and k != current_key:
                _GLOBAL_AGENTS.pop(k, None)
                logger.info(f"[DeepAgent] LRU 回收旧能力版本 Agent: {k}")
    except Exception as e:
        logger.warning(f"[DeepAgent] LRU 回收失败（不影响运行）: {e}")


async def get_tupu_agent(connection_id: str = ""):
    """获取 tupu DeepAgent（按 connection_id + capability 版本缓存，让前端选模型/能力开关真正生效）。

    v3.6: 按 connection_id 缓存不同模型的 Agent 实例（空串用默认模型）。
    批13-Q: 缓存键并入能力版本号（<conn>#g{guard}#c{caps}）——PATCH 能力开关后 version+1 ->
    新键建新实例；旧实例 LRU 保留最近 2 个版本（在跑请求不断）；重建写 capability_events(rebuild)。
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
    _cache_key = f"{connection_id or '__default__'}#g{_gver}#c{_cver}"
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
                )
                _GLOBAL_AGENTS[_cache_key] = agent
                _evict_old_agents(_cache_key)
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
