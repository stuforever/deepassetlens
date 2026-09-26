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

import logging
from typing import Callable

# 业务逻辑单一源（@tool 和 MCP tool 共用）
from app.services.tupu_deepagent import dispatch_kg_action

# ---------------------------------------------------------------------------
# 权限重构T8a（design §8.2/§8.4）：/mcp 面 UserContext ASGI 中间件 + EXEC 两段臂
# ---------------------------------------------------------------------------
import hashlib as _hashlib
import hmac as _hmac
import json as _json2
import os as _os2
import time as _time2


class UserContextASGIMiddleware:
    """🔴-4 解法（design §8.2）：跨 MCP 边界传递用户身份。

    ①验 internal token（沿用现口径——auth=1 时平台 AuthMiddleware 已挡 /mcp，
      此处二次校验防直接绕行；auth=0 开发态放行）；②X-Tupu-User + HMAC 签名
      （±300s 新鲜度）→ memory_runtime 置 ContextVar；③缺头 → 不置位 → 教学工具
      经 current_user_strict fail-closed（与外部无头 client 同语义）。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        headers = {k.lower(): v for k, v in (scope.get("headers") or [])}
        internal = _os2.environ.get("TUPU_INTERNAL_TOKEN", "")
        authz = headers.get(b"authorization", b"").decode("latin-1")
        if internal and not (authz.startswith("Bearer ") and _hmac.compare_digest(authz[7:].strip(), internal)):
            # internal token 校验失败（auth=1 态平台中间件前置已挡；此处兜底）
            body = _json2.dumps({"detail": "MCP 端点需 Bearer 内部 token"}).encode()
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
            return

        user = headers.get(b"x-tupu-user", b"").decode("latin-1") or ""
        sig = headers.get(b"x-tupu-user-sig", b"").decode("latin-1") or ""
        reset_token = None
        if user and sig:
            ok, err = _verify_user_sig(user, sig)
            if ok:
                from app.services import memory_runtime as _mr
                reset_token = _mr.set_runtime_token({"expert_id": "wenshu", "user": user,
                                                     "session_id": "", "turn_id": ""})
            else:
                _log.warning("[T8a] X-Tupu-User 签名校验失败（%s）——按无头处理", err[:60])
        try:
            return await self.app(scope, receive, send)
        finally:
            if reset_token is not None:
                from app.services import memory_runtime as _mr
                _mr.reset_runtime_token(reset_token)


def _verify_user_sig(user: str, sig: str) -> tuple:
    """X-Tupu-User-Sig = HMAC_SHA256(TUPU_INTERNAL_TOKEN, user|ts)（±300s，§8.2）。"""
    try:
        s, ts_s = sig.rsplit(".", 1)
        ts = int(ts_s)
    except (ValueError, AttributeError):
        return False, "签名格式非法"
    if abs(_time2.time() - ts) > 300:
        return False, "签名过期"
    key = (_os2.environ.get("TUPU_INTERNAL_TOKEN") or "tupu-dev-internal").encode()
    expect = _hmac.new(key, f"{user}|{ts}".encode(), _hashlib.sha256).hexdigest()
    return (True, "") if _hmac.compare_digest(s, expect) else (False, "签名不匹配")


def user_sig_header(user: str) -> str:
    """agent 侧同款签名（_build_agent 注入 X-Tupu-User-Sig 用——算法单一源）。"""
    ts = int(_time2.time())
    key = (_os2.environ.get("TUPU_INTERNAL_TOKEN") or "tupu-dev-internal").encode()
    s = _hmac.new(key, f"{user}|{ts}".encode(), _hashlib.sha256).hexdigest()
    return f"{s}.{ts}"


def _exec_audit(tool: str, user: str, decision: str, reason: str) -> None:
    """T8a 两段臂双审计（①=approval ②=allow/deny）。尽力而为不阻塞。"""
    try:
        from app.core.database import SessionLocal as _SL
        from app.models.auth import AuthAuditLog as _AAL
        from app.services import memory_runtime as _mr
        db = _SL()
        try:
            rt = _mr.current_runtime() or {}
            db.add(_AAL(user_sub=user or "anonymous", resource_type="tool",
                        resource_id=tool, action="execute", decision=decision,
                        reason=(reason or "")[:500],
                        session_id=rt.get("session_id"), turn_id=rt.get("turn_id")))
            db.commit()
        finally:
            db.close()
    except Exception as _e:
        _log.warning(f"[T8a] EXEC 审计失败（不阻塞）: {_e}")


def _two_arm(tool: str, args: dict, confirm_token: str, summary: str, execute):
    """EXEC 两段臂通用体（design §8.4）：无 token=预检臂①（签发 pending）；
    携 token=执行臂②（校验才执行）。双审计：①approval ②allow/deny。"""
    from app.services import memory_runtime as _mr
    user = _mr.current()["user"]  # 未置位→anonymous 缺省（两段臂绑定用，教学件另有 strict）
    if not confirm_token:
        from app.services.tool_confirm import issue as _issue
        _exec_audit(tool, user, "approval", f"预检臂①：{summary[:120]}")
        return {"status": "pending_confirmation", "summary": summary,
                "confirm_token": _issue(tool, args, user),
                "hint": "携 confirm_token 原参数重调本工具即执行（确认卡为触发器）"}
    from app.services.tool_confirm import verify as _verify
    ok, err = _verify(tool, args, user, confirm_token)
    if not ok:
        _exec_audit(tool, user, "deny", f"执行臂②拒绝：{err}")
        return {"status": "denied", "error": err}
    out = execute()
    _exec_audit(tool, user, "allow", "执行臂②完成")
    return out


_log = logging.getLogger("tupu.mcp")

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
def execute_sql(sql: str, entity_code: str = "", confirm_token: str = "") -> dict:
    """执行 SELECT SQL 并返回结果（columns/rows/row_count）。自动修复 Unknown column。
    physical_table 模式必传 entity_code 以锁定数据源+模式守卫（非物理表模式会被拦截）。
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"sql": sql, "entity_code": entity_code}
    return _two_arm("execute_sql", args, confirm_token,
                    f"执行物理表 SQL：{sql[:120]}",
                    lambda: _with_result_ref(dispatch_kg_action("execute_sql", {
                        "sql": sql, **({"entity_code": entity_code} if entity_code else {})})))


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
def execute_api_sql(sql: str, confirm_token: str = "") -> dict:
    """执行多源 API 联邦 SQL（DuckDB，WHERE/JOIN 自动下推到 API 参数）。虚拟表名从 /api-endpoints/tables 查。
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    return _two_arm("execute_api_sql", {"sql": sql}, confirm_token,
                    f"执行多源 API 联邦查询：{sql[:160]}",
                    lambda: _with_result_ref(dispatch_kg_action("execute_api_sql", {"sql": sql})))


@mcp.tool()
def execute_entity_api(entity_code: str, filters: dict = {}, confirm_token: str = "") -> dict:
    """执行对象 API 映射（对象来源 API 时用，伪逻辑 SQL + 过滤条件自动下推）。
    filters 格式（值类型决定匹配方式；禁止把条件整段当字符串传入）：
      - {"列": 值}                              精确匹配（=）
      - {"列": {"contains": "子串"}}            包含匹配（LIKE '%子串%'）——名称/描述类模糊搜索用这个
      - {"列": {"_like": "前缀%"}}              通配匹配（LIKE 原样，"like" 同义）
      - {"列": [v1, v2]}                        IN 匹配
      - {"列": {"_range": [[">=", a], ["<=", b]]}}  范围匹配
    例：execute_entity_api(entity_code="dim_ps_project_def",
                           filters={"ProjectDescription": {"contains": "李钢柱"}})
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"entity_code": entity_code, "filters": filters or {}}
    return _two_arm("execute_entity_api", args, confirm_token,
                    f"执行对象 API 映射查询：{entity_code}",
                    lambda: _with_result_ref(dispatch_kg_action("execute_entity_api", args)))


@mcp.tool()
def execute_doris_sql(entity_code: str = "", sql: str = "", filters: dict = {}, confirm_token: str = "") -> dict:
    """执行 Doris 整合 SQL（source_mode=sql_integration 的对象取数用）。

    优先传 entity_code：自动加载平台预配的 integration_sql + doris_catalog，并按 filters 下推 WHERE，无需自己拼 SQL。
    仅当对象未配 integration_sql 时才传 sql 自建，且 sql 必须用 3 段命名 catalog.db.table（否则报 No database selected）。
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。
    """
    args = {"entity_code": entity_code, "sql": sql, "filters": filters or {}}
    return _two_arm("execute_doris_sql", args, confirm_token,
                    f"执行 Doris 整合查询：{entity_code or sql[:100]}",
                    lambda: _with_result_ref(dispatch_kg_action("execute_doris_sql", args)))


@mcp.tool()
def sample_column_values(entity_code: str, column: str, limit: int = 50) -> dict:
    """取实体某列 distinct 值+频次（对分类/状态/类型列写 WHERE/GROUP BY 前必查，防枚举值猜测）。
    返回 {values:[{value,count}], null_count, total_rows, source_mode}。结果缓存 10 分钟。"""
    return dispatch_kg_action("sample_column_values", {
        "entity_code": entity_code, "column": column, "limit": limit})


# ---------------------------------------------------------------------------
# 权限重构T8a（v1.3 W5）：教学 11 件重新回挂——薄包装单源消费 tutor_inprocess.SPECS
# （拷贝源纪律：description 逐字沿用 SPECS，不许手抄）；user 由 /mcp 面 UserContext
# 中间件置位（X-Tupu-User+HMAC），impl 内 current_user_strict fail-closed（🔴-4）；
# 写 4 件走 EXEC 两段臂（design §8.4：无 confirm_token=预检臂①，携 token=执行臂②）。
# 只读 7 件直通（user_strict 解析后调 impl）。T8a 灰度开关已随 twin 收尾摘除——
# 本面为唯一教学工具路径（切换 R6）。
# ---------------------------------------------------------------------------
from app.services.learning.tutor_inprocess import SPECS as _TUTOR_SPECS
from app.services.memory_runtime import current_user_strict as _tutor_user_strict

_TUTOR_WRITE_4 = frozenset({"wrong_question_add", "fsrs_review",
                            "mother_question_find_or_create", "export_wrong_book"})


def _register_tutor_tools() -> int:
    import inspect as _inspect

    registered = 0
    for _spec in _TUTOR_SPECS:
        _sig = _inspect.signature(_spec["impl"])
        _params = list(_sig.parameters.values())[1:]  # 剥 user 首参
        _is_write = _spec["name"] in _TUTOR_WRITE_4

        def _mk(pkeys: list, write: bool, name: str):
            def _run(**kwargs):
                user = _tutor_user_strict()  # fail-closed：runtime 未置位即抛（🔴-4）
                args = {k: kwargs.get(k) for k in pkeys}
                # impl 运行期按 _impl_{name} 规约解析（单源 twin 同款命名）——
                # 测试 monkeypatch 可达；注册期捕获引用则 patch 不可达（e2e 实测）。
                from app.services.learning import tutor_inprocess as _ti
                impl = getattr(_ti, f"_impl_{name}")
                if write:
                    def _exec():
                        return impl(user, **args)
                    return _two_arm(name, args, kwargs.get("confirm_token", ""),
                                    f"教学写操作 {name}：{str(args)[:120]}", _exec)
                return impl(user, **args)

            full = list(_params)
            if write:
                full.append(_inspect.Parameter("confirm_token", _inspect.Parameter.KEYWORD_ONLY,
                                               default=""))
            _run.__signature__ = _sig.replace(parameters=full, return_annotation=dict)
            _run.__annotations__ = {q.name: q.annotation for q in _params
                                    if q.annotation is not _inspect.Parameter.empty}
            _run.__annotations__["return"] = dict  # FastMCP 输出模型显式化（dict 直通）
            if write:
                _run.__annotations__["confirm_token"] = str
            _run.__name__ = str(name)
            _run.__doc__ = str(_spec["description"]) + (
                " T8a 两段臂：先无 confirm_token 调用取 pending_confirmation，再携 token 原参数重调执行。"
                if write else "")
            return _run

        mcp.tool()(_mk([q.name for q in _params], _is_write, str(_spec["name"])))
        registered += 1
    return registered


_TUTOR_REGISTERED = _register_tutor_tools()


# ---------------------------------------------------------------------------
# 切换 v3.0 R0-③（G6）：文档生成 4 件——vendor skills/builtin/{docx,pptx,xlsx,pdf}
# 平台化重写，生成库留用（app/services/doc_tools.py），EXEC 两段臂确认流全走平台。
# 产物落 data/exports/documents/，写后回读校验；4 件皆写文件 → EXEC 类。
# ---------------------------------------------------------------------------
from app.services import doc_tools as _dt


@mcp.tool()
def generate_docx(blocks: list, output_name: str = "文档.docx", confirm_token: str = "") -> dict:
    """生成 Word 文档（.docx）。blocks 每项一种块：
    {"type":"heading","text":标题,"level":1} / {"type":"para","text":段落} /
    {"type":"bullet","text":要点} / {"type":"number","text":编号项} /
    {"type":"table","headers":[表头],"rows":[[行]]}。返回生成文件路径。
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"blocks": blocks, "output_name": output_name}
    return _two_arm("generate_docx", args, confirm_token,
                    f"生成 Word 文档 {output_name}（{len(blocks or [])} 个块）",
                    lambda: _dt.generate_docx(blocks, output_name))


@mcp.tool()
def generate_pptx(slides: list, output_name: str = "演示.pptx", confirm_token: str = "") -> dict:
    """生成 PowerPoint 演示文稿（.pptx）。slides 每项 {"title":页标题,"bullets":[要点列表]}，
    首页自动用标题版式。返回生成文件路径。
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"slides": slides, "output_name": output_name}
    return _two_arm("generate_pptx", args, confirm_token,
                    f"生成演示文稿 {output_name}（{len(slides or [])} 页）",
                    lambda: _dt.generate_pptx(slides, output_name))


@mcp.tool()
def generate_xlsx(sheets: list, output_name: str = "表格.xlsx", confirm_token: str = "") -> dict:
    """生成 Excel 工作簿（.xlsx）。sheets 每项 {"name":表名,"headers":[表头],"rows":[[行]]}。
    返回生成文件路径。T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"sheets": sheets, "output_name": output_name}
    return _two_arm("generate_xlsx", args, confirm_token,
                    f"生成 Excel {output_name}（{len(sheets or [])} 个工作表）",
                    lambda: _dt.generate_xlsx(sheets, output_name))


@mcp.tool()
def generate_pdf(blocks: list, output_name: str = "文档.pdf", confirm_token: str = "") -> dict:
    """生成 PDF 文档。blocks 块格式同 generate_docx（heading/para/bullet/number/table），
    中文渲染内置 STSong-Light 字体。返回生成文件路径。
    T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"blocks": blocks, "output_name": output_name}
    return _two_arm("generate_pdf", args, confirm_token,
                    f"生成 PDF 文档 {output_name}（{len(blocks or [])} 个块）",
                    lambda: _dt.generate_pdf(blocks, output_name))


# ---------------------------------------------------------------------------
# 切换 R2：笔记本 3 件——vendor tools/list_notebook+write_note+tool_composition
# （_shared）的平台 MCP 重写，数据层 NotebookManager（per-user JSON 文件）收编留用。
# has_notebooks/list_notebook 只读；write_note 写文件 → EXEC 两段臂。
# ---------------------------------------------------------------------------
from app.services.sishu_full.tools.list_notebook import list_notebooks_or_records as _lnr
from app.services.sishu_full.tools.write_note import write_note as _wn
from app.services.sishu_full.agents._shared.tool_composition import user_has_notebooks as _uhn


@mcp.tool()
def has_notebooks() -> dict:
    """检查当前用户是否已有笔记本（写笔记前必查——无笔记本时先告知用户去建，勿臆造 notebook_id）。"""
    try:
        return {"has_notebooks": bool(_uhn())}
    except Exception as e:
        return {"has_notebooks": False, "error": str(e)[:200]}


@mcp.tool()
def list_notebook(notebook_id: str = "") -> dict:
    """列笔记本（空 notebook_id=索引模式：全部笔记本概览）或列指定笔记本的记录（新→旧）。
    返回 text（LLM 可读清单）+ summary（mode/count）。notebook_id 必须来自本工具索引输出，
    未知 id 会报错并列出有效 id。"""
    out = _lnr(notebook_id=(notebook_id or "").strip())
    if not out.ok:
        return {"status": "error", "error": out.error}
    return {"status": "ok", "text": out.text, "summary": out.summary}


@mcp.tool()
def write_note(mode: str, notebook_id: str, record_id: str = "", title: str = "",
               content: str = "", note: str = "", confirm_token: str = "") -> dict:
    """写笔记本记录（mode=append 新增 | edit 修改指定 record_id）。
    append：title/content（或 note 简注）；edit：record_id 必传，title/content 覆盖。
    notebook_id 须来自 list_notebook 索引。T8a 两段臂：先无 token 调用取
    pending_confirmation+confirm_token，再携 token 原参数重调执行。"""
    args = {"mode": mode, "notebook_id": notebook_id, "record_id": record_id,
            "title": title, "content": content, "note": note}
    return _two_arm("write_note", args, confirm_token,
                    f"写笔记 {mode} → {notebook_id}（{title[:40]}）",
                    lambda: _wn(mode=mode, notebook_id=notebook_id, record_id=record_id,
                                title=title, content=content, note=note))


# ---------------------------------------------------------------------------
# 切换 R4（G4）：协同写作 3 件——vendor co_writer/storage.py（per-user JSON 文档）
# 数据层收编留用，注册面走平台 MCP。list/read 只读；write 增改 → EXEC 两段臂。
# 长任务（动画渲染）已在双轨 run_visualize 图内+SSE 进度承接（G4 图内异步方案）。
# ---------------------------------------------------------------------------
from app.services.sishu_full.co_writer.storage import get_co_writer_storage as _cws


@mcp.tool()
def list_documents() -> dict:
    """列出当前用户的协同写作文档（id/标题/预览/更新时间）。写文档前先查重。"""
    try:
        items = [{"id": d.id, "title": d.title, "preview": d.preview,
                  "updated_at": d.updated_at} for d in _cws().list_documents()]
        return {"status": "ok", "items": items, "count": len(items)}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@mcp.tool()
def read_document(doc_id: str) -> dict:
    """读取指定协同写作文档全文（Markdown）。doc_id 来自 list_documents。"""
    doc = _cws().load_document((doc_id or "").strip())
    if doc is None:
        return {"status": "error", "error": f"文档不存在: {doc_id}"}
    return {"status": "ok", "id": doc.id, "title": doc.title,
            "content": doc.content, "updated_at": doc.updated_at}


@mcp.tool()
def write_document(doc_id: str = "", title: str = "", content: str = "",
                   confirm_token: str = "") -> dict:
    """写协同写作文档（doc_id 空=新建；非空=更新该文档的标题/内容，Markdown 全文覆盖）。
    返回文档 id 与标题。T8a 两段臂：先无 token 调用取 pending_confirmation+confirm_token，
    再携 token 原参数重调执行。"""
    args = {"doc_id": doc_id, "title": title, "content": content}
    return _two_arm("write_document", args, confirm_token,
                    f"写作文档 {'更新 ' + doc_id if doc_id else '新建'}：{title[:40]}",
                    lambda: _exec_write_document(doc_id, title, content))


def _exec_write_document(doc_id: str, title: str, content: str) -> dict:
    storage = _cws()
    did = (doc_id or "").strip()
    if did:
        doc = storage.update_document(did, title=(title or None), content=content or None)
        if doc is None:
            return {"status": "error", "error": f"文档不存在: {did}"}
    else:
        doc = storage.create_document(title=(title or None), content=content or "")
    return {"status": "ok", "id": doc.id, "title": doc.title,
            "chars": len(doc.content or "")}


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
    # 权限重构T8a（design §8.2）：UserContext ASGI 中间件包装——X-Tupu-User+HMAC
    # 签名验签 → memory_runtime 置位（教学工具 current_user_strict 数据源）。
    # /mcp 仅内部可达（loopback/compose 内网），不对外发布端口（§8.2 暴露面纪律）。
    app.mount("/mcp", UserContextASGIMiddleware(mcp.sse_app()))
