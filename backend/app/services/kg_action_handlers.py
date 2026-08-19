"""
kg_api 动作处理器 —— dispatch_kg_action 16 分支从 tupu_deepagent.py 拆分（机械迁移，行为等价）

路由仍在 tupu_deepagent.py 的 kg_api @tool 与 MCP tool 共用此分发器。
"""

# v3.5: 无 entity_code 时，从 SQL FROM 子句提取主表名（反查实体配置的 source_mode/data_source_id）
# 支持 WITH CTE -> ... FROM main_table 和直接 FROM main_table
# 不处理子查询别名（取第一个 FROM 后的裸表名，已覆盖场景剧本的 SQL 模板模式）
_MAIN_TABLE_RE = __import__('re').compile(r'\bFROM\s+([a-zA-Z_][\w]*)', __import__('re').IGNORECASE)
def _extract_main_table(sql: str) -> str:
    """从 SQL 的 FROM 子句提取主表名。返回表名或空字符串。"""
    if not sql or not isinstance(sql, str):
        return ""
    m = _MAIN_TABLE_RE.search(sql)
    return m.group(1) if m else ""

# ============== 16 个 action 处理器（原 dispatch_kg_action 分支） ==============

def _kg_fetch_l1_l2_tree(body: dict, _ts: str) -> dict:
    from app.services.skill_injections import build_fetch_l1_l2_tree
    fn = build_fetch_l1_l2_tree()
    if not fn:
        return {"l1_list": [], "error": "查询函数不可用", "log": f"[{_ts}] 获取L1-L2树失败：查询函数不可用"}
    res = fn()
    l1_list = res.get("l1_list", []) if isinstance(res, dict) else []
    l2_count = sum(len((l1.get("l2_list") or l1.get("children") or [])) for l1 in l1_list)
    res["log"] = f"[{_ts}] 获取L1-L2层级树：共 {len(l1_list)} 个行业域(L1)，{l2_count} 个小类(L2)"
    return res

def _kg_validate_l2(body: dict, _ts: str) -> dict:
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

def _kg_fetch_subgraph(body: dict, _ts: str) -> dict:
    from app.services.skill_injections import build_fetch_subgraph_by_l2
    fn = build_fetch_subgraph_by_l2()
    if not fn:
        return {"l2x_entities": [], "error": "查询函数不可用", "log": f"[{_ts}] 获取子图失败：查询函数不可用"}
    res = fn(body.get("l2_id", ""))
    ents = (res or {}).get("l2x_entities", []) if isinstance(res, dict) else []
    ent_names = "、".join([str(e.get("entity_name", "") if isinstance(e, dict) else e) for e in ents[:6]])
    res["log"] = f"[{_ts}] 获取L2子图：该小类下共 {len(ents)} 个实体（{ent_names}{'...' if len(ents) > 6 else ''}）"
    return res

def _kg_validate_attributes(body: dict, _ts: str) -> dict:
    from app.api.kg_api import validate_attributes, ValidateAttrsRequest
    res = validate_attributes(ValidateAttrsRequest(**body))
    entity_code = (res or {}).get("entity_code", "") or body.get("entity_code", "")
    attrs = (res or {}).get("attributes", []) if isinstance(res, dict) else []
    attr_names = "、".join([str(a.get("attribute_name", "") if isinstance(a, dict) else a) for a in attrs[:8]])
    res["log"] = f"[{_ts}] 校验实体「{entity_code}」属性成功：命中 {len(attrs)} 个属性（{attr_names}{'...' if len(attrs) > 8 else ''}）"
    return res

def _kg_fetch_join_expr(body: dict, _ts: str) -> dict:
    from app.services.skill_runnable import _build_fetch_join_expr_fn
    fn = _build_fetch_join_expr_fn()
    src = body.get("source_entity", "")
    tgt = body.get("target_entity", "")
    join_on = fn(src, tgt) if fn else ""
    # P0 安全修复：缺失可信 JOIN 配置时明确失败，禁止默认编造 cust_id 关联键
    if not join_on:
        return {"error": f"未配置实体「{src}」与「{tgt}」的可信关联关系，不能执行跨表查询。请先在映射管理配置 JOIN ON 表达式。",
                "join_on": "", "source_entity": src, "target_entity": tgt,
                "log": f"[{_ts}] 关联关系查询失败：{src} ⋈ {tgt} 未配置可信 JOIN，不编造默认关联键"}
    return {"join_on": join_on, "source_entity": src, "target_entity": tgt,
            "log": f"[{_ts}] 查询关联关系：{src} ⋈ {tgt}，JOIN ON {join_on}"}

def _kg_validate_safe_sql(body: dict, _ts: str) -> dict:
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

def _kg_execute_sql(body: dict, _ts: str) -> dict:
    # 硬守卫：若带 entity_code，校验 source_mode 必须为 physical_table；并取 per-entity 数据源
    entity_code_exec = body.get("entity_code", "")
    data_source_id = None
    if not entity_code_exec:
        # v3.5 防御兜底：无 entity_code 时，从 SQL FROM 子句提取主表名反查实体配置
        # 避免场景剧本忘传 entity_code 导致绕过模式守卫 + 走全局默认源
        _extracted = _extract_main_table(body.get("sql", ""))
        if _extracted:
            entity_code_exec = _extracted
    if entity_code_exec:
        from app.models.base import Entity
        from app.core.database import SessionLocal
        from sqlalchemy import or_
        _db_guard = SessionLocal()
        try:
            # 三字段匹配：entity_code（语义代码）、entity_en_name（物理表名）、entity_name（中文名）
            _ent = _db_guard.query(Entity).filter(
                or_(Entity.entity_code == entity_code_exec,
                    Entity.entity_en_name == entity_code_exec,
                    Entity.entity_name == entity_code_exec)
            ).first()
            if _ent:
                if _ent.source_mode and _ent.source_mode != "physical_table":
                    _hint_tool = "execute_entity_api" if _ent.source_mode == "api_integration" else "execute_doris_sql"
                    _via = "SQL FROM 自动推断" if not body.get("entity_code", "") else "entity_code"
                    return {"error": f"模式锁：实体 {entity_code_exec} source_mode={_ent.source_mode}，禁止 execute_sql，请用 {_hint_tool}",
                            "log": f"[{_ts}] 模式守卫拦截：{entity_code_exec} 非 physical_table（{_via}），不降级不重试"}
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

    # P0 安全校验：AST 只读校验 + 强制 LIMIT（不可绕过，内置到执行器）
    from app.services.secure_query_executor import validate_sql
    _chk = validate_sql(sql_text)
    if not _chk.ok:
        return {"error": f"SQL安全校验未通过: {_chk.reason}", "log": f"[{_ts}] SQL校验失败：{_chk.reason}"}
    sql_text = _chk.sql
    current_sql = sql_text
    current_sql = sql_text
    from app.services.engine_errors import apply_error_class
    try:
        res = exec_fn(current_sql)
    except Exception as e:
        err_msg = str(e)
        _hint = ""
        if "doesn't exist" in err_msg or "1146" in err_msg:
            import re as _re1146
            _tm = _re1146.search(r"Table '[^']*?\.([^']+)'", err_msg)
            _tn = _tm.group(1) if _tm else "该表"
            _hint = f" | 提示：表「{_tn}」不存在，请用 kg_api(action=list_tables, params='{{}}') 查真实表名，或用 search_entities 重新定位"
        res = apply_error_class({"error": f"SQL执行异常: {e}{_hint}",
                                 "log": f"[{_ts}] SQL执行异常：{e}{_hint}",
                                 "sql": current_sql})
    else:
        if isinstance(res, dict):
            if res.get("error"):
                err_msg = str(res.get("error", ""))
                _hint2 = ""
                if "doesn't exist" in err_msg or "1146" in err_msg:
                    import re as _re1146b
                    _tm2 = _re1146b.search(r"Table '[^']*?\.([^']+)'", err_msg)
                    _tn2 = _tm2.group(1) if _tm2 else "该表"
                    _hint2 = f" | 提示：表「{_tn2}」不存在，请用 kg_api(action=list_tables) 查真实表名"
                if "Unknown column" in err_msg:
                    _hint2 = f" | 提示：列名错误，请用 kg_api(action=search_entities, params={{'entity_code':'<表名>'}}) 确认正确列名后修改重试"
                res = apply_error_class(res)
                res["error"] = str(res.get("error", err_msg)) + _hint2
                res["log"] = f"[{_ts}] SQL执行失败：{err_msg}{_hint2}"
                res["sql"] = current_sql
            else:
                row_cnt = res.get("row_count", 0)
                cols = res.get("columns", []) or []
                res["log"] = f"[{_ts}] SQL执行成功：返回 {row_cnt} 行数据，字段（{', '.join(cols[:6])}{'...' if len(cols) > 6 else ''}）"
                res["sql"] = current_sql
    return res

def _kg_search_concepts(body: dict, _ts: str) -> dict:
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

def _kg_search_entities(body: dict, _ts: str) -> dict:
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
            # 支持按 entity_code(如 DistributionTransformer) 或 entity_en_name(如 vw_transformer) 查
            row = db.execute(text(
                "SELECT entity_code, entity_name, entity_en_name, description, properties_schema "
                "FROM kg_entities WHERE entity_code = :code OR entity_en_name = :code LIMIT 1"
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
                        # properties_schema 结构: {name(=PG物理列名), type, cnName(中文名), description, isPrimaryKey}
                        col_name = str(p.get("name") or p.get("attribute_code") or "")
                        attrs.append({
                            "column_name": col_name,
                            "column_cn": str(p.get("cnName") or p.get("attribute_name") or ""),
                            "data_type": str(p.get("type") or ""),
                            "is_pk": bool(p.get("isPrimaryKey") or False),
                            # 兼容旧字段名
                            "attribute_code": col_name,
                            "attribute_name": str(p.get("cnName") or p.get("name") or ""),
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

def _kg_get_entity_relations(body: dict, _ts: str) -> dict:
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

def _kg_list_tables(body: dict, _ts: str) -> dict:
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

def _kg_get_entity_source_mode(body: dict, _ts: str) -> dict:
    # NL2API 路由：查询实体的数据源模式（sql_integration/api_integration/physical_table）
    from app.api.kg_api import get_entity_source_mode
    entity_code = body.get("entity_code", "")
    res = get_entity_source_mode(entity_code)
    source_mode = res.get("source_mode", "physical_table")
    res["log"] = f"[{_ts}] 实体「{entity_code}」数据源模式={source_mode}"
    return res

def _kg_batch_entity_source_mode(body: dict, _ts: str) -> dict:
    # 批量查询多实体数据源模式 + 路由建议（一次查全所有涉及表，不逐表查询）
    from app.api.kg_api import batch_entity_source_mode
    codes = body.get("entity_codes", [])
    res = batch_entity_source_mode({"entity_codes": codes})
    _rec_tool = res.get("recommended_tool", "execute_sql")
    _has_api = res.get("has_api_integration", False)
    _has_catalog = res.get("has_catalog", False)
    _summary = f"{len(codes)}表: API={_has_api}, Doris联邦={_has_catalog}, 推荐={_rec_tool}"
    res["log"] = f"[{_ts}] 批量数据源模式查询 {_summary}"
    return res

def _kg_execute_api_sql(body: dict, _ts: str) -> dict:
    # 多源API联邦SQL：DuckDB 执行，WHERE/JOIN 自动下推到 API 参数
    from app.services.duckdb_engine import execute_sql as _exec_api_sql, load_endpoints_from_db
    from app.core.database import SessionLocal
    from app.services.secure_query_executor import validate_sql
    sql_text = body.get("sql", "").strip()
    if not sql_text:
        return {"error": "缺少 sql 参数", "log": f"[{_ts}] API联邦查询失败：缺少sql"}
    # P0 安全校验：AST 只读校验 + 强制 LIMIT（不可绕过，替代仅预检的 validate_safe_sql）
    _chk = validate_sql(sql_text)
    if not _chk.ok:
        return {"error": f"SQL安全校验未通过: {_chk.reason}", "log": f"[{_ts}] API联邦SQL校验失败：{_chk.reason}"}
    sql_text = _chk.sql
    db = SessionLocal()
    try:
        endpoints = load_endpoints_from_db(db)
        if not endpoints:
            return {"error": "尚未配置任何API端点", "log": f"[{_ts}] API联邦查询失败：无端点"}
        # 自动给物理表加 pg. 前缀：DuckDB ATTACH 了 PG，物理表需 pg.表名 才能访问
        # API 虚拟表（endpoint table_name）不加前缀；其余表名自动加 pg.
        from app.models.base import Entity, EntityApiMapping
        import re as _re
        api_tables = set(endpoints.keys())
        # api_integration 实体的 entity_en_name 也要映射到虚拟表（pseudo_sql 引用的端点表名）
        # 特别处理：vw_cust_power_ts 这类"视图型 api_integration"实体，LLM 会用 entity_en_name 写 SQL
        # 需要把它替换为对应的 pseudo_sql 子查询
        api_mappings = db.query(EntityApiMapping).all()
        _ent_map = {e.id: e for e in db.query(Entity).filter(Entity.source_mode == "api_integration").all()}
        for m in api_mappings:
            ent = _ent_map.get(m.entity_id)
            if ent and ent.entity_en_name and ent.entity_en_name not in api_tables and m.pseudo_sql:
                # 把 entity_en_name 替换为 (pseudo_sql) 子查询
                sql_text = _re.sub(
                    rf'(?<![\w.]){_re.escape(ent.entity_en_name)}(?![\w.])',
                    f"({m.pseudo_sql})",
                    sql_text
                )
        physical_tables = set()
        for ent in db.query(Entity).filter(Entity.source_mode == "physical_table").all():
            if ent.entity_en_name and ent.entity_en_name not in api_tables:
                physical_tables.add(ent.entity_en_name)
        # 也加 view 模式的实体
        for ent in db.query(Entity).filter(Entity.source_mode == "view").all():
            if ent.entity_en_name and ent.entity_en_name not in api_tables:
                physical_tables.add(ent.entity_en_name)
        for tbl in sorted(physical_tables, key=len, reverse=True):
            # 只替换未被前缀修饰的裸表名（避免重复加 pg.）
            sql_text = _re.sub(
                rf'(?<![\w.]){_re.escape(tbl)}(?![\w.])',
                f'pg.{tbl}',
                sql_text
            )
        # P0-2: 改写后重新校验（pseudo_sql 替换可能引入非只读操作，必须重校）
        _chk2 = validate_sql(sql_text)
        if not _chk2.ok:
            return {"error": f"SQL改写后安全校验未通过: {_chk2.reason}", "log": f"[{_ts}] API联邦SQL改写后校验失败：{_chk2.reason}"}
        sql_text = _chk2.sql
        result = _exec_api_sql(sql_text, endpoints)
        pushed = result.get("pushed_down", {})
        result["log"] = f"[{_ts}] API联邦SQL执行成功：返回 {result.get('row_count', 0)} 行，下推表 {list(pushed.keys())}"
        return result
    except Exception as e:
        from app.services.engine_errors import wrap_engine_exception
        _err = wrap_engine_exception(e, prefix="API联邦查询异常: ")
        _err["log"] = f"[{_ts}] API联邦查询异常：{e}"
        return _err
    finally:
        db.close()

def _kg_execute_entity_api(body: dict, _ts: str) -> dict:
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
        # F1: build_sql_with_filters 改写后必须经 secure_query_executor 校验（不可绕过）
        from app.services.secure_query_executor import validate_sql
        _chk = validate_sql(sql)
        if not _chk.ok:
            return {"error": f"SQL安全校验未通过: {_chk.reason}", "log": f"[{_ts}] 对象API SQL校验失败：{_chk.reason}"}
        sql = _chk.sql
        endpoints = load_endpoints_from_db(db)
        if not endpoints:
            return {"error": "尚未配置任何API端点", "log": f"[{_ts}] 无API端点"}
        result = _exec_api_sql(sql, endpoints)
        pushed = result.get("pushed_down", {})
        result["log"] = f"[{_ts}] 对象「{entity_code}」API执行成功：返回 {result.get('row_count', 0)} 行，下推 {list(pushed.keys())}"
        return result
    except Exception as e:
        from app.services.engine_errors import wrap_engine_exception
        _err = wrap_engine_exception(e, prefix="对象API执行异常: ")
        _err["log"] = f"[{_ts}] 对象API执行异常：{e}"
        return _err
    finally:
        db.close()

def _kg_execute_doris_sql(body: dict, _ts: str) -> dict:
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
        from sqlalchemy import or_
        db = SessionLocal()
        try:
            # 三字段匹配：entity_code（语义代码）、entity_en_name（物理表名）、entity_name（中文名）
            ent = db.query(Entity).filter(
                or_(Entity.entity_code == entity_code,
                    Entity.entity_en_name == entity_code,
                    Entity.entity_name == entity_code)
            ).first()
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
    # P0 安全校验：AST 只读校验 + 强制 LIMIT（不可绕过）
    from app.services.secure_query_executor import validate_sql
    _chk = validate_sql(sql_text)
    if not _chk.ok:
        return {"error": f"SQL安全校验未通过: {_chk.reason}", "log": f"[{_ts}] Doris SQL校验失败：{_chk.reason}"}
    sql_text = _chk.sql
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
        from app.services.engine_errors import wrap_engine_exception
        _err = wrap_engine_exception(e, prefix="Doris查询异常: ")
        _err["log"] = f"[{_ts}] Doris查询异常：{e}"
        return _err

# ============== G3（融合设计 §4.2）：列值取样 ==============
import re as _re_sample

_SAMPLE_TTL_SECONDS = 600
_SAMPLE_CACHE: dict = {}  # (entity_code, column) -> (ts, result)；进程内 10 分钟缓存

def _kg_sample_column_values(body: dict, _ts: str) -> dict:
    """G3: 取实体指定列 distinct 值+频次（分类/状态/类型列写 WHERE/GROUP BY 前必查，防枚举值猜测）。

    路由到三引擎（复用 execute_sql 的实体解析/引擎锁定逻辑）：
      - physical_table   -> 物理直连，GROUP BY 取样
      - sql_integration  -> Doris 整合，对 integration_sql 子查询取样（无需猜 catalog.db.table 三段命名）
      - api_integration  -> 不支持列取样，优雅降级（建议 execute_entity_api 直查）
    进程内 10 分钟缓存。返回 {values:[{value,count}], null_count, total_rows, source_mode}。
    """
    from datetime import datetime as _dt
    entity_code = (body.get("entity_code") or "").strip()
    column = (body.get("column") or "").strip()
    try:
        limit = int(body.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))
    if not entity_code or not column:
        return {"error": "缺少 entity_code 或 column", "log": f"[{_ts}] 取样失败：缺参"}
    # 列名安全校验：仅物理标识符（防 SQL 注入；中文列名/属性名请先用 validate_attributes 取真实 code）
    if not _re_sample.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
        return {"error": f"列名非法（仅支持英文标识符，中文列名请先 validate_attributes 取真实 code）: {column}",
                "log": f"[{_ts}] 取样失败：列名非法 {column}"}
    # 进程内 10 分钟缓存
    _now = _dt.now().timestamp()
    _hit = _SAMPLE_CACHE.get((entity_code, column))
    if _hit and (_now - _hit[0]) < _SAMPLE_TTL_SECONDS:
        _cached = dict(_hit[1])
        _cached["log"] = f"[{_ts}] 取样命中缓存（10 分钟 TTL）"
        return _cached
    # 解析实体 -> 物理表 / source_mode / 数据源 / catalog（三字段匹配，与 execute_sql 同构）
    from app.models.base import Entity
    from app.core.database import SessionLocal
    from sqlalchemy import or_
    _db = SessionLocal()
    try:
        _ent = _db.query(Entity).filter(
            or_(Entity.entity_code == entity_code,
                Entity.entity_en_name == entity_code,
                Entity.entity_name == entity_code)
        ).first()
    finally:
        _db.close()
    if not _ent:
        return {"error": f"对象不存在: {entity_code}", "log": f"[{_ts}] 取样失败：对象不存在 {entity_code}"}
    _mode = _ent.source_mode or "physical_table"
    _table = (_ent.entity_en_name or "").strip()
    if not _table:
        return {"error": f"对象无物理表名: {entity_code}", "log": f"[{_ts}] 取样失败：{entity_code} 无 entity_en_name"}
    # 列不存在提示（G2 自愈闭环：模型据提示用 search_entities/validate_attributes 确认真实列名）
    def _hint_col(res: dict) -> dict:
        _msg = str(res.get("error", ""))
        if "UndefinedColumn" in _msg or "Unknown column" in _msg or "Column not found" in _msg:
            res["error"] = _msg + " | 提示：列不存在，请用 search_entities/validate_attributes 确认真实列名后重试"
        return res
    _sampled = None
    if _mode == "physical_table":
        from app.services.sql_executor import build_execute_query_fn
        _exec = build_execute_query_fn(data_source_id=str(_ent.data_source_id) if _ent.data_source_id else None)
        if not _exec:
            return {"error": "执行函数不可用", "log": f"[{_ts}] 取样失败：执行函数不可用"}
        _sql = (f"SELECT {column} AS value, COUNT(*) AS cnt FROM {_table} "
                f"GROUP BY {column} ORDER BY cnt DESC, value ASC LIMIT {limit}")
        from app.services.secure_query_executor import validate_sql
        _chk = validate_sql(_sql)
        if not _chk.ok:
            return {"error": f"SQL安全校验未通过: {_chk.reason}", "log": f"[{_ts}] 取样 SQL 校验失败：{_chk.reason}"}
        try:
            _sampled = _exec(_chk.sql)
        except Exception as e:
            from app.services.engine_errors import apply_error_class
            _err = apply_error_class({"error": f"取样执行异常: {e}"})
            _err["log"] = f"[{_ts}] 取样执行异常：{e}"
            return _hint_col(_err)
    elif _mode == "sql_integration":
        # Doris 整合：对 integration_sql 子查询取样（平台预配 SQL 为可信来源，无需猜 catalog.db.table）
        from app.services.doris_engine import execute_sql as _doris_exec
        _base = (_ent.integration_sql or "").strip()
        if not _base:
            return {"error": f"对象未配置 integration_sql: {entity_code}", "log": f"[{_ts}] 取样失败：{entity_code} 无 integration_sql"}
        _sql = (f"SELECT {column} AS value, COUNT(*) AS cnt FROM ( {_base} ) _t "
                f"GROUP BY {column} ORDER BY cnt DESC, value ASC LIMIT {limit}")
        from app.services.secure_query_executor import validate_sql
        _chk = validate_sql(_sql)
        if not _chk.ok:
            return {"error": f"SQL安全校验未通过: {_chk.reason}", "log": f"[{_ts}] 取样 SQL 校验失败：{_chk.reason}"}
        try:
            _sampled = _doris_exec(_chk.sql, catalog=_ent.doris_catalog or None)
        except Exception as e:
            from app.services.engine_errors import wrap_engine_exception
            _err = wrap_engine_exception(e, prefix="取样异常: ")
            _err["log"] = f"[{_ts}] 取样异常：{e}"
            return _err
    else:
        return {"error": f"对象 {entity_code} source_mode={_mode} 不支持列取样（API 对象建议 execute_entity_api 直查）",
                "log": f"[{_ts}] 取样跳过：{_mode} 不支持列取样"}
    if _sampled.get("error"):
        _err = _hint_col(dict(_sampled))
        _err["log"] = f"[{_ts}] 取样失败：{_sampled.get('error')}"
        return _err
    # 归一化：values / null_count / total_rows
    _cols = _sampled.get("columns", []) or []
    _rows = _sampled.get("rows", []) or []
    _values = []
    _total = 0
    _nulls = 0
    if _rows and len(_cols) >= 2:
        for _r in _rows:
            _v = _r[0]
            _c = int(_r[1]) if len(_r) > 1 and _r[1] is not None else 0
            _total += _c
            if _v is None:
                _nulls = _c
            else:
                _values.append({"value": _v, "count": _c})
    _out = {
        "values": _values,
        "null_count": _nulls,
        "total_rows": _total,
        "source_mode": _mode,
        "log": f"[{_ts}] 取样完成：列 {column} 共 {_total} 行（null={_nulls}），Top{min(len(_values), limit)} 个值",
    }
    _SAMPLE_CACHE[(entity_code, column)] = (_now, _out)
    return _out

_KG_ACTION_HANDLERS = {
    "fetch_l1_l2_tree": _kg_fetch_l1_l2_tree,
    "validate_l2": _kg_validate_l2,
    "fetch_subgraph": _kg_fetch_subgraph,
    "validate_attributes": _kg_validate_attributes,
    "fetch_join_expr": _kg_fetch_join_expr,
    "validate_safe_sql": _kg_validate_safe_sql,
    "execute_sql": _kg_execute_sql,
    "search_concepts": _kg_search_concepts,
    "search_entities": _kg_search_entities,
    "get_entity_relations": _kg_get_entity_relations,
    "list_tables": _kg_list_tables,
    "get_entity_source_mode": _kg_get_entity_source_mode,
    "batch_entity_source_mode": _kg_batch_entity_source_mode,
    "execute_api_sql": _kg_execute_api_sql,
    "execute_entity_api": _kg_execute_entity_api,
    "execute_doris_sql": _kg_execute_doris_sql,
    "sample_column_values": _kg_sample_column_values,
}

def dispatch_kg_action(action: str, body: dict) -> dict:
    """kg_api 业务逻辑分发（@tool 和 MCP tool 共用，单一逻辑源）。action/参数见 kg_api docstring。"""
    from datetime import datetime as _dt
    _ts = _dt.now().strftime("%H:%M:%S")
    handler = _KG_ACTION_HANDLERS.get(action)
    if handler is not None:
        return handler(body, _ts)
    return {"error": f"未知 action: {action}"}
