"""tupu MCP Server - 把 kg_api 的 16 个业务工具暴露为标准 MCP 工具。

架构：
  deepagent(MCP client) ──┐
  外部 client(zcode/Claude)──┤── SSE /mcp/sse ── FastMCP(16 tool) ── dispatch_kg_action ── app/api/kg_api.py

  - 工具和 deepagent 解耦：deepagent 不再用 @tool，改 MCP client 加载
  - 16 个 tool 单一职责（vs 原 kg_api 一个工具 16 个 action）
  - 复用 dispatch_kg_action（业务逻辑单一源）
  - 统一 SSE 传输（内外都用 http://127.0.0.1:8000/mcp/sse）
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


@mcp.tool()
def execute_sql(sql: str, entity_code: str = "") -> dict:
    """执行 SELECT SQL 并返回结果（columns/rows/row_count）。自动修复 Unknown column。
    physical_table 模式必传 entity_code 以锁定数据源+模式守卫（非物理表模式会被拦截）。"""
    body = {"sql": sql}
    if entity_code:
        body["entity_code"] = entity_code
    return dispatch_kg_action("execute_sql", body)


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
def get_entity_relations(entity_code: str = "") -> dict:
    """查实体关联关系（含物理表名）。entity_code 为空则返回全部关系。"""
    return dispatch_kg_action("get_entity_relations", {"entity_code": entity_code})


@mcp.tool()
def list_tables(keyword: str = "") -> dict:
    """列出知识图谱实体对应的物理表名（entity_en_name），用于验证表是否真实存在。keyword 过滤。"""
    return dispatch_kg_action("list_tables", {"keyword": keyword})


@mcp.tool()
def get_entity_source_mode(entity_code: str) -> dict:
    """查询实体数据源模式（physical_table/api_integration/sql_integration）。"""
    return dispatch_kg_action("get_entity_source_mode", {"entity_code": entity_code})


@mcp.tool()
def execute_api_sql(sql: str) -> dict:
    """执行多源 API 联邦 SQL（DuckDB，WHERE/JOIN 自动下推到 API 参数）。虚拟表名从 /api-endpoints/tables 查。"""
    return dispatch_kg_action("execute_api_sql", {"sql": sql})


@mcp.tool()
def execute_entity_api(entity_code: str, filters: dict = {}) -> dict:
    """执行对象 API 映射（对象来源 API 时用，伪逻辑 SQL + 过滤条件自动下推）。"""
    return dispatch_kg_action("execute_entity_api", {"entity_code": entity_code, "filters": filters or {}})


@mcp.tool()
def execute_doris_sql(entity_code: str = "", sql: str = "", filters: dict = {}) -> dict:
    """执行 Doris 整合 SQL（source_mode=sql_integration 的对象取数用）。

    优先传 entity_code：自动加载平台预配的 integration_sql + doris_catalog，并按 filters 下推 WHERE，无需自己拼 SQL。
    仅当对象未配 integration_sql 时才传 sql 自建，且 sql 必须用 3 段命名 catalog.db.table（否则报 No database selected）。
    """
    return dispatch_kg_action("execute_doris_sql", {"entity_code": entity_code, "sql": sql, "filters": filters or {}})


# ---------------------------------------------------------------------------
# 挂载到 FastAPI（SSE 传输，复用 8000 端口）
# ---------------------------------------------------------------------------

def mount_mcp(app) -> None:
    """把 MCP Server 挂载到 FastAPI app（SSE 传输）。

    挂载后：
      - SSE endpoint: http://127.0.0.1:8000/mcp/sse
      - Messages:     http://127.0.0.1:8000/mcp/messages/

    内部 deepagent 和外部 client 都连 /mcp/sse。
    """
    app.mount("/mcp", mcp.sse_app())
