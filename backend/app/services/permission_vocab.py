# -*- coding: utf-8 -*-
"""权限词汇表 + 工具注册表单点（权限体系重构 T1，design §5.1/§6.1）。

单一事实源纪律：
- PERMISSION_VOCAB：11 资源类型 × 合法动作词，原样 design §5.1；GET /api/v1/iam/vocab
  原样吐出（T2），前端矩阵编辑器数据源。
- TOOL_REGISTRY：全集 = mcp_server 实际注册集（T8a 回挂教学 11 件后 = 30 件，含
  search_kb 🛠R1）。**漂移由 tests/test_iam.py 用 mcp.list_tools() 实测断言把关**——
  本文件用字面量集合而靘认证 mcp_server 导入，避免权限判定路径反向依赖 MCP 服务
  模块（重导入链）；新增/摘除 MCP 工具时必须同步本表，测试会拦住遗漏。
- 三分类（🛠R5 语义写死）：
  - READONLY_TOOLS：角色默认 tool:execute 覆盖，允许/拒绝二态；
  - EXEC_TOOLS：仅 ACL 显式授予（角色默认不含）。注意 T8a 后 EXEC=8（+教学写 4），
    与引擎侧 query_contract.DATA_TOOLS（恒 4，引擎一致性判定语义）**有意分叉**——
    两者关系由 test_write_tools_align_with_engine_forbidden 钉住；
  - WRITE_TOOLS：系统级面外 6 件恒拒（= query_contract.ABSOLUTE_FORBIDDEN_TOOLS），
    数据模型预留 approval 动作位（真开放走审批三态）。
- 面外声明（design §6.1 R14）：read_file 框架工具不入册（装载/派发两执行点碰不到）；
  TUTOR_TOOLS 教学族 11 件在 T8a 回挂前不入册（编排承接过渡态）。
"""
from __future__ import annotations

from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# 权限词汇表（design §5.1 原样）
# ---------------------------------------------------------------------------

PERMISSION_VOCAB: Dict[str, list] = {
    "skill": ["read", "write", "execute", "delete"],
    "workflow": ["read", "write", "execute", "delete"],
    "data_source": ["read", "write"],
    "query_attribute": ["read", "execute"],
    "query_entity": ["read", "execute"],
    "metric": ["read", "write"],
    "expert": ["use", "manage"],
    "sishu": ["use", "manage"],
    "auth": ["read", "write"],
    "tool": ["execute"],  # W3 新增（🛠R5：粗粒度语义见 EXEC_TOOLS）
    "attachment": ["read", "write"],
}

# ---------------------------------------------------------------------------
# 工具注册表（全集 = mcp_server 注册集，🛠R1；三分类 🛠R5）
# ---------------------------------------------------------------------------

TOOL_REGISTRY: FrozenSet[str] = frozenset({
    # 定位类（只读元数据）
    "fetch_l1_l2_tree", "validate_l2", "fetch_subgraph",
    "search_entities", "search_entities_batch", "search_concepts",
    "get_entity_relations", "list_tables",
    # 校验类（只读）
    "validate_attributes", "fetch_join_expr", "validate_safe_sql",
    # 取样类（G3：分类/状态/类型列写 WHERE 前先取真实枚举值）
    "sample_column_values",
    # 源模式确认
    "get_entity_source_mode", "batch_entity_source_mode",
    # 知识库检索（🛠R1：已注册但不在 GENERIC_ALLOWED_TOOLS——必须入册防隐身）
    "search_kb",
    # 执行类（受 validate_safe_sql / ScopeChecker / 引擎锁定闸门保护）
    "execute_sql", "execute_api_sql", "execute_entity_api", "execute_doris_sql",
    # T8a 教学读面 7 件（LLM 臂两件数据面只读，落审计）
    "fsrs_due", "mastery_query", "wrong_question_query", "select_exercises",
    "analyze_wrong_questions", "grade_answer", "generate_practice",
    # T8a 教学写面 4 件（应用域写——两段臂+确认流+审计）
    "fsrs_review", "wrong_question_add", "mother_question_find_or_create",
    "export_wrong_book",
})

# 执行类（T8a 后 8 件：原 4 execute_* + 教学写 4）：仅 ACL 显式授予（🛠R5）
EXEC_TOOLS: FrozenSet[str] = frozenset({
    "execute_sql", "execute_api_sql", "execute_entity_api", "execute_doris_sql",
    # T8a 教学写 4 件（design §8.4——应用域写：learning_* 四表 owner=当前用户，
    # 编排确认流+两段臂+审计三保险；系统级恒拒类语义只留给 shell/文件系统级）
    "fsrs_review", "wrong_question_add",
    "mother_question_find_or_create", "export_wrong_book",
})

# T8a 教学写 4 件（EXEC 的子集——种子/两段臂定位用）
TUTOR_EXEC_TOOLS: FrozenSet[str] = EXEC_TOOLS & {
    "fsrs_review", "wrong_question_add",
    "mother_question_find_or_create", "export_wrong_book",
}

# 只读类（T8a 后 22）：允许/拒绝二态，角色默认 tool:execute 覆盖
READONLY_TOOLS: FrozenSet[str] = TOOL_REGISTRY - EXEC_TOOLS

# 写类恒拒（6，系统级面外——与引擎 ABSOLUTE_FORBIDDEN 同集，关系由测试钉住）
WRITE_TOOLS: FrozenSet[str] = frozenset({
    "task",        # 子 Agent
    "write_file",  # 写文件
    "edit_file",   # 改文件
    "execute",     # Shell
    "grep",        # 搜文件内容
    "glob",        # 列文件
})

__all__ = [
    "PERMISSION_VOCAB",
    "TOOL_REGISTRY",
    "READONLY_TOOLS",
    "EXEC_TOOLS",
    "WRITE_TOOLS",
]
