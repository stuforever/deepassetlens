"""tupu MCP Server - 把 kg_api 的 17 个业务工具暴露为标准 MCP 工具。

架构：
  deepagent(MCP client) ──┐
  外部 client(zcode/Claude)──┤── SSE /mcp/sse ── FastMCP(17 tool) ── dispatch_kg_action ── app/api/kg_api.py

  - 工具和 deepagent 解耦：deepagent 不再用 @tool，改 MCP client 加载
  - 17 个 tool 单一职责（vs 原 kg_api 一个工具 16 个 action）
  - 复用 dispatch_kg_action（业务逻辑单一源）
  - 统一 SSE 传输（内外都用 http://127.0.0.1:28000/mcp/sse，端口由 __start_8000.py 启动）
"""
from typing import Any
from mcp.server.fastmcp import FastMCP

# 业务逻辑单一源（@tool 和 MCP tool 共用）
from app.services.tupu_deepagent import dispatch_kg_action

mcp = FastMCP("tupu-kg")


# ---------------------------------------------------------------------------
# 16 个 MCP 工具（单一职责，LLM 易选）
# ---------------------------------------------------------------------------

@mcp.tool()
def fetch_l1_l2_tree() -> dict:
    """获取行业域 L1/L2 层级树（定位业务域用）。返回 l1_list。"""
    return dispatch_kg_action("fetch_l1_l2_tree", {})


@mcp.tool()
def validate_l2(l2_name: str, l2_id: str = "") -> dict:
    """校验 L2 业务域：按 l2_name 反查真实 UUID，或校验 l2_id 是否有效。"""
    return dispatch_kg_action("validate_l2", {"l2_name": l2_name, "l2_id": l2_id})


@mcp.tool()
def fetch_subgraph(l2_id: str) -> dict:
    """获取 L2 业务域下的实体子图（L2X 实体+属性）。l2_id 为 UUID。"""
    return dispatch_kg_action("fetch_subgraph", {"l2_id": l2_id})


@mcp.tool()
def validate_attributes(entity_code: str, attributes: list = ()) -> dict:
    """校验实体属性 code（按 attribute_name 回填真实 code）。attributes 形如 [{"attribute_code":"x","attribute_name":"y"}]。"""
    return dispatch_kg_action("validate_attributes", {
        "entity_code": entity_code,
        "attributes": list(attributes) if attributes else [],
    })


@mcp.tool()
def fetch_join_expr(source_entity: str, target_entity: str) -> dict:
    """查两个实体表之间的 JOIN 关联字段。返回 join_on。"""
    return dispatch_kg_action("fetch_join_expr", {
        "source_entity": source_entity,
        "target_entity": target_entity,
    })


@mcp.tool()
def validate_safe_sql(sql: str) -> dict:
    """校验 SQL 安全性（只允许 SELECT/WITH，禁止 DDL/DML）。"""
    return dispatch_kg_action("validate_safe_sql", {"sql": sql})


# ---------------------------------------------------------------------------
# 批13-AB4 数据摘要站一件三拆：四查询工具出口统一「全量暂存+模型摘要视图」。
# 全量数据存 query_result_store（uuid4+TTL 10min+上限 64），SSE 路由层按 result_ref
# 取回派发前端（data_intelligence_stream.on_tool_end）；DataSummaryMiddleware 退役。
# ---------------------------------------------------------------------------
from app.services import query_result_store as _qrs

_SUMMARY_THRESHOLD = 10  # 超过此行数则截断为摘要（自 tupu_deepagent._SUMMARY_THRESHOLD 随迁）


def _with_result_ref(result: dict) -> dict:
    """13-AB ④：查询工具出口统一处理——全量暂存+返回模型摘要视图。
    row_count<=10: 全量返回(带 result_ref)；>10: 截断前10行+指令(带 result_ref)。"""
    if not isinstance(result, dict) or "rows" not in result or "row_count" not in result:
        return result                                    # 错误消息/非查询结果原样放行
    ref = _qrs.put(result)                               # 全量进暂存柜
    row_count = result.get("row_count", len(result["rows"]))
    if row_count <= _SUMMARY_THRESHOLD:
        return {**result, "result_ref": ref}             # 小结果全量给模型+指针(前端表格走同一派发通道)
    _limit_reached = row_count >= 500                    # SQL 强制 LIMIT 500(现状口径)
    _limit_hint = "（已达 LIMIT 500 上限，可能还有更多数据未取回）" if _limit_reached else "（未触发 LIMIT 截断，已是全部结果）"
    directive = (                                        # 原 DataSummaryMiddleware._directive 原文迁移,一字不改
        f"【数据已完整获取】共 {row_count} 行{_limit_hint}。\n"
        f"下方仅展示前 {_SUMMARY_THRESHOLD} 行分析样本，完整 {row_count} 行数据已推前端查询结果表展示（is_preview=false）。\n"
        f"JSON 中 row_count={row_count}（完整结果数）、returned_rows={row_count}（前端拿到的完整行数）、"
        f"llm_is_preview=true、llm_preview_row_count={_SUMMARY_THRESHOLD}（你的分析样本行数）、result_available_for_ui=true。\n"
        f"前 {_SUMMARY_THRESHOLD} 行只是你的分析样本，不是面向用户的展示数据：禁止复述为'明细如下'或制作预览表格。"
        f"row_count 就是全部数量，样本行数≠数据不完整。"
        f"**只能对 row_count 下全量结论；对行内字段只能说'样本显示'；'全部 X/所有 Y 均 Z'类结论必须由 SQL 聚合统计提供证据。**"
        f"禁止分页重查、禁止分段查询、禁止调用 task 子代理。"
        f"{'可能需要提示用户缩小范围。' if _limit_reached else '请直接基于 row_count 和样本写结论，并注明完整明细见下方查询结果表。'}\n"
    )
    return {
        "columns": result.get("columns", []),
        "rows": result["rows"][:_SUMMARY_THRESHOLD],
        "row_count": row_count, "returned_rows": row_count,
        "is_preview": False, "llm_is_preview": True, "llm_preview_row_count": _SUMMARY_THRESHOLD,
        "result_available_for_ui": True,
        "result_ref": ref,                               # ← SSE 路由层取全量的接力棒
        "sql": result.get("sql", ""),
        "data_snapshot_at": result.get("data_snapshot_at"),
        "cache_sources": result.get("cache_sources"),
        "_directive": directive,                         # 指令文本(模型读；JSON 形态不破坏既有解析链)
    }


@mcp.tool()
def execute_sql(sql: str, entity_code: str = "") -> dict:
    """执行 SELECT SQL 并返回结果（columns/rows/row_count）。自动修复 Unknown column。
    physical_table 模式必传 entity_code 以锁定数据源+模式守卫（非物理表模式会被拦截）。"""
    body = {"sql": sql}
    if entity_code:
        body["entity_code"] = entity_code
    return _with_result_ref(dispatch_kg_action("execute_sql", body))


@mcp.tool()
def search_concepts(keyword: str = "") -> dict:
    """搜索概念定义（explain-concept 技能用）。keyword 为空则返回全部。"""
    return dispatch_kg_action("search_concepts", {"keyword": keyword})


@mcp.tool()
def search_entities(keyword: str = "", entity_code: str = "") -> dict:
    """搜实体/字段：传 entity_code 查数据字典；传 keyword 搜实体名/属性/物理表名。返回含 entity_en_name（写 SQL 必须用）。"""
    body: dict[str, Any] = {}
    if entity_code:
        body["entity_code"] = entity_code
    if keyword:
        body["keyword"] = keyword
    return dispatch_kg_action("search_entities", body)


@mcp.tool()
def search_entities_batch(keywords: list = None, entity_codes: list = None) -> dict:
    """一次批量定位实体（spec 2026-09-09 件②）：keywords/entity_codes 逐项返回（含 hit/miss），
    未命中自动走一次向量召回合并。"""
    return dispatch_kg_action("search_entities_batch",
                              {"keywords": keywords or [], "entity_codes": entity_codes or []})


@mcp.tool()
def get_entity_relations(entity_code: str = "") -> dict:
    """查实体关联关系（含物理表名）。entity_code 为空则返回全部关系。"""
    return dispatch_kg_action("get_entity_relations", {"entity_code": entity_code})


@mcp.tool()
def list_tables(keyword: str = "") -> dict:
    """列出知识图谱实体对应的物理表名（entity_en_name），用于验证表是否真实存在。keyword 过滤。"""
    return dispatch_kg_action("list_tables", {"keyword": keyword})


@mcp.tool()
def search_kb(kb_id: str, query: str, top_k: int = 6) -> dict:
    """④（spec D9）：知识库检索——专家卡 knowledge_sources 声明 kb:{id} 后可用。
    indexed 型=Qdrant 相似检索；connected 型=外部 ES 透传。返回 matches[{text,score,filename,chunk_idx}]。"""
    from app.services.kb_query import kb_query
    return kb_query(kb_id=kb_id, query=query, top_k=int(top_k or 6))


@mcp.tool()
def get_entity_source_mode(entity_code: str) -> dict:
    """查询实体数据源模式（physical_table/api_integration/sql_integration）。"""
    return dispatch_kg_action("get_entity_source_mode", {"entity_code": entity_code})


@mcp.tool()
def batch_entity_source_mode(entity_codes: list) -> dict:
    """批量查询多实体的数据源模式 + 路由建议（取数前必调，一次查全所有涉及表，不要逐表查询）。
    入参: entity_codes = ["vw_transformer", "cms20_dist_sta", ...]（SQL 涉及的所有表名）
    返回:
      - items: 每个表的 source_mode 信息
      - recommended_tool: 按路由优先级推荐的执行工具：
        - 任一 api_integration -> execute_entity_api（DuckDB 联邦）
        - 有 doris_catalog 的表（无 api）-> execute_doris_sql（Doris 联邦，三段命名 pg_tupu.public.表名）
        - 未绑 catalog 的物理表 -> execute_sql（物理直连）
      - has_api_integration / has_catalog: 是否含对应模式
    """
    return dispatch_kg_action("batch_entity_source_mode", {"entity_codes": entity_codes or []})


@mcp.tool()
def execute_api_sql(sql: str) -> dict:
    """执行多源 API 联邦 SQL（DuckDB，WHERE/JOIN 自动下推到 API 参数）。虚拟表名从 /api-endpoints/tables 查。"""
    return _with_result_ref(dispatch_kg_action("execute_api_sql", {"sql": sql}))


@mcp.tool()
def execute_entity_api(entity_code: str, filters: dict = {}) -> dict:
    """执行对象 API 映射（对象来源 API 时用，伪逻辑 SQL + 过滤条件自动下推）。"""
    return _with_result_ref(dispatch_kg_action("execute_entity_api", {"entity_code": entity_code, "filters": filters or {}}))


@mcp.tool()
def execute_doris_sql(entity_code: str = "", sql: str = "", filters: dict = {}) -> dict:
    """执行 Doris 整合 SQL（source_mode=sql_integration 的对象取数用）。

    优先传 entity_code：自动加载平台预配的 integration_sql + doris_catalog，并按 filters 下推 WHERE，无需自己拼 SQL。
    仅当对象未配 integration_sql 时才传 sql 自建，且 sql 必须用 3 段命名 catalog.db.table（否则报 No database selected）。
    """
    return _with_result_ref(dispatch_kg_action("execute_doris_sql", {"entity_code": entity_code, "sql": sql, "filters": filters or {}}))


@mcp.tool()
def sample_column_values(entity_code: str, column: str, limit: int = 50) -> dict:
    """取实体某列 distinct 值+频次（对分类/状态/类型列写 WHERE/GROUP BY 前必查，防枚举值猜测）。
    返回 {values:[{value,count}], null_count, total_rows, source_mode}。结果缓存 10 分钟。"""
    return dispatch_kg_action("sample_column_values", {
        "entity_code": entity_code, "column": column, "limit": limit})


# ---------------------------------------------------------------------------
# ⑤批2（⑤b）：教学工具族九件（spec §一契约表+§二三铁律）。
# 铁律①：参数一律不含 user_id——user 由运行时严格解析（🔴-4 修正 2026-09-15：MCP HTTP
# 面走 fail-closed，runtime 未置位即抛，绝不静默落 anonymous 共享桶；agent 装配面走
# 进程内 twin（tutor_inprocess.py 单源 SPECS）——HTTP SSE 跳数的独立 ASGI 请求无
# ContextVar，恒 anonymous 共享桶已拆除）。
# 铁律②：fsrs_review 可选 now 注入（测试不 sleep）；
# 铁律③：超阈值沉降走 _with_result_ref（沿①既有机制）。
# ---------------------------------------------------------------------------
import json as _json

from app.services.learning.tutor_inprocess import (
    _impl_fsrs_due, _impl_fsrs_review, _impl_mastery_query, _impl_grade_answer,
    _impl_generate_practice, _impl_select_exercises, _impl_wrong_question_add,
    _impl_wrong_question_query, _impl_export_wrong_book,
)


def _tutor_user() -> str:
    """教学工具 user 严格解析（🔴-4 fail-closed）：runtime 未置位即抛——绝不静默
    缺省 anonymous（跨用户泄漏面）。"""
    from app.services.memory_runtime import current_user_strict
    return current_user_strict()


@mcp.tool()
def fsrs_due(kind: str = "") -> str:
    """到期复习清单（due<=now 按 due 升序，含 stability/reps）——读面。"""
    return _impl_fsrs_due(_tutor_user(), kind=kind or "")


@mcp.tool()
def fsrs_review(item_id: str, rating: int, kind: str = "mother_question",
                now: float | None = None) -> str:
    """提交复习评分(1-4)→FSRS 调度→落卡+流水（engine 直写——算出来的不许模型编）。
    ⑤b 铁律①：参数不含 user_id（从 memory_runtime ContextVar 取）；铁律②：now 可注入
    （测试不 sleep；fastmcp 禁下划线参数——spec 的 _now 更名 now，语义不变）。"""
    return _impl_fsrs_review(_tutor_user(), item_id, rating, kind=kind, now=now)


@mcp.tool()
def mastery_query(knowledge_point_id: str) -> str:
    """查知识点掌握度+复习史统计（读面）——学情画像与选题权重的数据源。"""
    return _impl_mastery_query(_tutor_user(), knowledge_point_id)


@mcp.tool()
def grade_answer(question: str, user_answer: str, expected_answer: str = "",
                 rubric: str = "") -> str:
    """判分（LLM 臂）：对照预期答案/评分要点给分值+逐条评语（判分必走本工具不自评）。"""
    return _impl_grade_answer(_tutor_user(), question, user_answer,
                              expected_answer=expected_answer, rubric=rubric)


@mcp.tool()
def generate_practice(knowledge_point_id: str, band: str = "基础") -> str:
    """生成变式练习题（LLM 臂）：band ∈ 基础|提高|挑战；返回题干+参考答案。"""
    return _impl_generate_practice(_tutor_user(), knowledge_point_id, band=band)


@mcp.tool()
def select_exercises(knowledge_point_id: str, n: int = 5, band: str = "") -> str:
    """选题+图谱邻居扩展：本知识点+前置/后继知识点入选题池（⑤b 唯一新算法语义）
    →母题按掌握度加权（掌握度低→权高）→top-n（含变式计数）。"""
    return _impl_select_exercises(_tutor_user(), knowledge_point_id, n=n, band=band)


@mcp.tool()
def wrong_question_add(variant_text: str, mother_question_id: str = "",
                       error_context: str = "") -> str:
    """错题入库（engine 写臂）：判分错误后登记变式题。返回 wq_id。"""
    return _impl_wrong_question_add(_tutor_user(), variant_text,
                                    mother_question_id=mother_question_id,
                                    error_context=error_context)


@mcp.tool()
def wrong_question_query(status: str = "", limit: int = 20) -> str:
    """错题列表（读面）：status ∈ open|resolved|空（全部）。仅本人错题。"""
    return _impl_wrong_question_query(_tutor_user(), status=status, limit=limit)


@mcp.tool()
def export_wrong_book(format: str = "md") -> str:
    """导出错题本（engine 臂）：落文件返回 result_ref（tab_export 纪律——大对象不进对话）。"""
    return _impl_export_wrong_book(_tutor_user(), format=format)


# ---------------------------------------------------------------------------
# 挂载到 FastAPI（SSE 传输，复用 8000 端口）
# ---------------------------------------------------------------------------

def mount_mcp(app) -> None:
    """把 MCP Server 挂载到 FastAPI app（SSE 传输）。

    挂载后（端口由 uvicorn 启动参数决定，本项目固定 28000）：
      - SSE endpoint: http://127.0.0.1:28000/mcp/sse
      - Messages:     http://127.0.0.1:28000/mcp/messages/

    内部 deepagent 和外部 client 都连 /mcp/sse。
    """
    app.mount("/mcp", mcp.sse_app())
