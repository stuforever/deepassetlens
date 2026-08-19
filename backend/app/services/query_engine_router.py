"""query_engine_router.py - 三引擎唯一选择（受控 Skill 问答平台 v2，设计 §5.3）

职责：根据 batch_entity_source_mode 的**真实返回**决定本次查询走哪个数据引擎，
并把契约的 allowed_tools 收窄为该引擎唯一工具（引擎确认后其他查询工具失效）。

引擎选择不由模型拍板，不由前端猜测：本模块是唯一裁判，被 SkillPolicyMiddleware 调用。
设计 §5.2 引擎表：
  - 物理表 (physical)     -> execute_sql
  - API 虚拟表 (duckdb)   -> execute_api_sql / execute_entity_api
  - doris_catalog (doris) -> execute_doris_sql
空结果不得换引擎重查（row_count=0 是"数据不存在"，不是技术错误）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# recommended_tool -> engine 标识
RECOMMENDED_TOOL_TO_ENGINE: Dict[str, str] = {
    "execute_doris_sql": "doris",
    "execute_api_sql": "duckdb",
    "execute_entity_api": "duckdb",
    "execute_sql": "physical",
}
# engine -> 允许的数据工具（唯一）
ENGINE_EXEC_TOOLS: Dict[str, List[str]] = {
    "doris": ["execute_doris_sql"],
    "duckdb": ["execute_api_sql", "execute_entity_api"],
    "physical": ["execute_sql"],
}
# source_mode（get/batch 返回的逐实体 source_mode）-> engine 标识
SOURCE_MODE_TO_ENGINE: Dict[str, str] = {
    "api_integration": "duckdb",
    "sql_integration": "doris",
    "physical_table": "physical",
    "physical": "physical",
}


@dataclass(frozen=True)
class EngineDecision:
    engine: str                 # doris | duckdb | physical
    reason: str                 # 依据（batch_entity_source_mode 真实返回）
    exec_tools: List[str]
    recommended_tool: str

    def to_dict(self) -> dict:
        return {
            "engine": self.engine, "reason": self.reason,
            "exec_tools": list(self.exec_tools), "recommended_tool": self.recommended_tool,
        }


def resolve_engines_multi(source_mode_result: Dict[str, Any]) -> Optional[List[str]]:
    """多引擎技能：从 batch 返回的 items[]（逐实体 source_mode）推导引擎集合。

    用于预算(api)->duckdb + 成本(sql)->doris 这类跨源分发的场景：
    引擎不由模型拍板，按每实体真实 source_mode 逐源确认。
    """
    if not isinstance(source_mode_result, dict):
        return None
    items = source_mode_result.get("items") or []
    if not isinstance(items, list):
        return None
    engines: List[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        sm = it.get("source_mode") or ""
        e = SOURCE_MODE_TO_ENGINE.get(sm)
        if e and e not in engines:
            engines.append(e)
    if not engines:
        return None
    return engines


def resolve_engine(source_mode_result: Dict[str, Any]) -> Optional[EngineDecision]:
    """从 batch_entity_source_mode 的返回结果解析唯一引擎选择。

    Args:
        source_mode_result: batch_entity_source_mode 的返回 dict（含 recommended_tool /
            has_api_integration / has_catalog / doris_catalog / entity_codes 等）。
    Returns:
        可用的 EngineDecision；recommended_tool 无法识别时返回 None（不猜测）。
    """
    if not isinstance(source_mode_result, dict):
        return None
    rec = source_mode_result.get("recommended_tool") or ""
    engine = RECOMMENDED_TOOL_TO_ENGINE.get(rec)
    if not engine:
        return None
    codes = source_mode_result.get("entity_codes") or "多"
    parts = [f"batch_entity_source_mode 返回 recommended_tool={rec}，涉及 {codes} 表"]
    if source_mode_result.get("has_api_integration"):
        parts.append("含 API 虚拟表")
    if source_mode_result.get("has_catalog"):
        parts.append(f"已纳管 catalog={source_mode_result.get('doris_catalog') or '?'}")
    return EngineDecision(
        engine=engine,
        reason="，".join(parts),
        exec_tools=list(ENGINE_EXEC_TOOLS.get(engine, [])),
        recommended_tool=rec,
    )
