"""
数据智能 支持工具 —— 从 data_intelligence.py 拆分（机械迁移，行为等价）

迁移内容：_ACTION_TOOL_MAP/_SKILL_CODE_CN/_SESSION_LOCKS/_SESSION_LOCK_MAX 常量
与 10 个纯辅助函数（会话锁/客户名提取/推荐提取/最终交付构建/结果摘要等）。
data_intelligence.py 通过 re-export 保持路由可见性。
"""
from __future__ import annotations

from pydantic import BaseModel

# kg_api action -> 中文任务名（on_tool_start 映射 task_label）
# action -> (技能包中文名, 工具中文名)
_ACTION_TOOL_MAP: Dict[str, tuple] = {
    "fetch_l1_l2_tree":       ("定位",     "获取层级树"),
    "validate_l2":            ("定位",     "校验L2"),
    "fetch_subgraph":         ("定位",     "获取子图"),
    "validate_attributes":    ("定位",     "校验属性"),
    "get_entity_relations":   ("关系查询", "查实体关系"),
    "fetch_join_expr":        ("关系查询", "查JOIN字段"),
    "validate_safe_sql":      ("SQL执行",  "校验SQL安全"),
    "execute_sql":            ("SQL执行",  "执行SQL"),
    "list_tables":            ("SQL执行",  "列出表名"),
    "get_entity_source_mode": ("API取数",  "查数据源模式"),
    "execute_api_sql":        ("API取数",  "多源API联邦SQL"),
    "execute_entity_api":     ("API取数",  "对象API执行"),
    "execute_doris_sql":      ("Doris整合", "Doris跨对象SQL"),
    "search_entities":        ("搜索探索", "搜索实体"),
    "search_concepts":        ("搜索探索", "搜索概念"),
}

# read_file 技能目录 -> 技能中文名
_SKILL_CODE_CN: Dict[str, str] = {
    "locate": "定位", "relate": "关系查询", "sql-exec": "SQL执行",
    "explore": "搜索探索", "sql-query": "SQL拼接",
    "explain-concept": "概念解释", "explore-graph": "图谱浏览",
    "find-entity": "字段反查", "trace-lineage": "数据血缘",
}

# task_label 仍需保留（on_tool_end 按 task 匹配 result_summary）
_KG_ACTION_LABELS: Dict[str, str] = {
    "fetch_l1_l2_tree": "获取层级树", "validate_l2": "校验L2",
    "fetch_subgraph": "获取子图", "validate_attributes": "校验属性",
    "fetch_join_expr": "查JOIN字段", "validate_safe_sql": "校验SQL",
    "execute_sql": "SQL执行", "search_concepts": "搜索概念",
    "search_entities": "搜索实体", "get_entity_relations": "查关系",
    "list_tables": "列出表名", "get_entity_source_mode": "查数据源模式",
    "execute_api_sql": "API联邦SQL",
    "execute_entity_api": "对象API执行",
    "execute_doris_sql": "Doris跨对象SQL",
}

# v3.5 同一会话执行锁：防止同 thread_id 并发请求导致 checkpoint 分叉覆盖
# 不同会话可并发（各自持不同锁），同一会话串行
_SESSION_LOCKS: dict[str, "asyncio.Lock"] = {}
_SESSION_LOCK_MAX = 200  # P3: 防无界增长，超阈值清理已解锁的旧锁

def _get_session_lock(thread_id: str):
    """获取或创建会话级异步锁（P3: 超阈值时回收无锁定的旧锁）"""
    import asyncio as _asyncio
    if thread_id not in _SESSION_LOCKS:
        # 回收：超过上限时清理已解锁的旧锁（locked()=False 表示无人在用）
        if len(_SESSION_LOCKS) > _SESSION_LOCK_MAX:
            _stale = [k for k, v in _SESSION_LOCKS.items() if not v.locked() and k != thread_id]
            for k in _stale[:len(_SESSION_LOCKS) - _SESSION_LOCK_MAX // 2]:
                del _SESSION_LOCKS[k]
        _SESSION_LOCKS[thread_id] = _asyncio.Lock()
    return _SESSION_LOCKS[thread_id]


def _extract_customer_names_from_input(user_input: str) -> list:
    """从用户原始输入正则提取客户名（P0-1：可信范围来源）。

    匹配模式：客户001、客户003、客户A等"客户+标识"模式。
    提取到则返回客户名列表（写入 last_scope source=user_input），提取不到返回空列表。
    这是确定性解析，模型无权覆盖此来源的范围。
    """
    if not user_input:
        return []
    import re as _re
    # 匹配 "客户001"、"客户003"、"客户A" 等（中文"客户"+字母数字标识）
    _matches = _re.findall(r'客户([A-Za-z0-9]+)', user_input)
    if not _matches:
        return []
    # 去重保序
    _seen = set()
    _names = []
    for _m in _matches:
        _full = f"客户{_m}"
        if _full not in _seen:
            _seen.add(_full)
            _names.append(_full)
    return _names


def _extract_recommendations(final_answer: str) -> list:
    """从 LLM 最终答案提取推荐问题（P1-4：替代硬编码推荐）。

    匹配"如需进一步分析/可以："后的编号列表项（1. xxx 2. xxx 或 - xxx）。
    提取不到返回空列表（调用方用默认兜底）。
    """
    if not final_answer:
        return []
    import re as _re
    # 找"如需进一步分析"或"可以："后面的列表
    _marker_match = _re.search(r'(如需进一步|可以：|建议：|接下来可以)\s*[:：]?\s*(.+)', final_answer, _re.DOTALL)
    if not _marker_match:
        return []
    _tail = _marker_match.group(2)
    # 提取编号项 "1. xxx" 或 "2、xxx" 或 "- xxx"
    _items = _re.findall(r'(?:^|\n)\s*(?:\d+[.、)\s]+|[-*]\s+)(.+?)(?=\n\s*(?:\d+[.、)\s]+|[-*]\s+|\Z))', _tail, _re.DOTALL)
    _recs = []
    for _item in _items:
        _clean = _item.strip().rstrip('。.，,')
        # 去掉括号说明（如"查看过载台区下哪些客户负载占有率最高（倒排影响最大的用户）" -> 取主干）
        _clean = _re.sub(r'[（(].*?[）)]', '', _clean).strip()
        if _clean and len(_clean) <= 50:  # 过长的不适合做推荐问题
            _recs.append(_clean)
        if len(_recs) >= 3:
            break
    return _recs


def _safe_error_summary(err) -> str:
    """提取安全的错误摘要：取首行、压缩空白、截断，避免把内部细节全量暴露给用户。"""
    if not err:
        return "未知错误"
    s = str(err).strip().splitlines()[0].strip()
    s = " ".join(s.split())
    return (s[:160] + "...") if len(s) > 160 else (s or "未知错误")


def _empty_result_text() -> str:
    return "未查询到符合当前条件的数据。\n可尝试：调整日期、客户、台区、负荷类型或状态条件。"


def _build_final_delivery(user_input: str, final_answer: str, structured,
                          sql_result, sql_error=None, sql_executed=False,
                          l2_name="", entity_name="") -> dict:
    """统一最终交付构建（A-E 确定性降级，绝不调用第二个 LLM 生成四段式总结）。

    最终结果交付任务书：
      A. structured_response 存在 -> 直接采用（row_count 用工具真实结果校正，禁止模型编造）
      B. 有最终文本、无 structured -> 保留文本 + 最小 FinalDelivery（标记降级，不额外"润色"）
      C. 无最终文本、有真实 SQL 结果 -> 纯 Python 确定性交付（不调用模型）
      D. 工具返回空数据 -> "未查询到符合当前条件的数据"
      E. 执行错误 -> 安全错误提示

    禁止行为：
    - 不根据 rows[:3] 推断任何全量业务结论（如"所有客户都正常"）
    - 不把 L2 / 主表 / SQL / 执行过程塞入最终业务答案

    Returns:
        {"final_answer": str, "final_delivery": dict, "degraded": bool}
    """
    delivery = {
        "answer_type": "data_list",
        "title": user_input or "查询结果",
        "summary": [],
        "findings": [],
        "warnings": [],
        "recommendations": [],
        "row_count": 0,
        "result_available_for_ui": False,
    }
    row_count = 0
    has_ui_data = False
    if isinstance(sql_result, dict) and not sql_result.get("error"):
        row_count = int(sql_result.get("row_count", 0) or 0)
        cols = sql_result.get("columns") or []
        has_ui_data = row_count > 0 and bool(cols)

    # structured 可能是 Pydantic 实例或 dict（response_format 生效时）
    if isinstance(structured, BaseModel):
        structured = structured.model_dump()
    if not isinstance(structured, dict):
        structured = None

    # A. 有结构化结果
    if structured:
        delivery["answer_type"] = structured.get("answer_type", "data_list")
        delivery["title"] = structured.get("title") or delivery["title"]
        delivery["summary"] = list(structured.get("summary") or [])
        delivery["findings"] = list(structured.get("findings") or [])
        delivery["warnings"] = list(structured.get("warnings") or [])
        delivery["recommendations"] = list(structured.get("recommendations") or [])
        # row_count 必须来自工具真实结果，禁止模型编造
        delivery["row_count"] = row_count if has_ui_data else int(structured.get("row_count") or 0)
        delivery["result_available_for_ui"] = has_ui_data or bool(structured.get("result_available_for_ui"))
        return {"final_answer": final_answer or "", "final_delivery": delivery, "degraded": False}

    # B. 有最终文本、无 structured -> 保留文本，构建最小交付
    if final_answer and final_answer.strip():
        if sql_error:
            delivery["answer_type"] = "error"
            delivery["summary"] = [f"查询未完成：{_safe_error_summary(sql_error)}。已完成的步骤和原因请见上方执行过程。"]
        elif has_ui_data:
            delivery["answer_type"] = "data_list"
            delivery["row_count"] = row_count
            delivery["result_available_for_ui"] = True
        elif sql_result is not None:
            delivery["answer_type"] = "empty"
            delivery["summary"] = [_empty_result_text()]
        else:
            delivery["answer_type"] = "knowledge"
        return {"final_answer": final_answer, "final_delivery": delivery, "degraded": True}

    # E. 执行错误（无文本）
    if sql_error:
        delivery["answer_type"] = "error"
        _safe = _safe_error_summary(sql_error)
        delivery["summary"] = [f"查询未完成：{_safe}。已完成的步骤和原因请见上方执行过程。"]
        return {"final_answer": f"查询未完成：{_safe}\n已完成的步骤和原因请见上方执行过程。",
                "final_delivery": delivery, "degraded": True}

    # D. 空结果（row_count=0 或无 columns）
    if sql_result is not None and not has_ui_data:
        delivery["answer_type"] = "empty"
        delivery["summary"] = [_empty_result_text()]
        return {"final_answer": _empty_result_text(), "final_delivery": delivery, "degraded": True}

    # C. 无最终文本、有真实 SQL 结果 -> 纯 Python 确定性交付
    if has_ui_data:
        cols = sql_result.get("columns") or []
        key_fields = "、".join(str(c) for c in cols[:8]) + (" 等" if len(cols) > 8 else "")
        delivery["answer_type"] = "data_list"
        delivery["row_count"] = row_count
        delivery["result_available_for_ui"] = True
        delivery["summary"] = [
            f"共返回 {row_count} 条，完整明细见下方查询结果表。",
            f"关键字段：{key_fields}。",
        ]
        delivery["recommendations"] = [
            "按客户、台区、日期或状态进一步筛选",
            f"统计{l2_name or '该业务域'}记录总数",
        ]
        text = (
            f"查询结果：\n共返回 {row_count} 条，完整明细见下方查询结果表。\n\n"
            f"关键字段：{key_fields}\n\n"
            f"提示：如需进一步按客户、台区、日期或状态筛选，请继续说明条件。"
        )
        return {"final_answer": text, "final_delivery": delivery, "degraded": True}

    # 兜底：无任何工具结果也无文本
    delivery["answer_type"] = "knowledge"
    delivery["summary"] = ["未查询到符合当前条件的数据。"]
    return {"final_answer": "未查询到符合当前条件的数据。", "final_delivery": delivery, "degraded": True}


def _build_action_detail(name: str, action: str, inp: dict) -> str:
    """on_tool_start 时拼接自然语言 detail：调用'XX'技能包的'XX'工具。"""
    if name == "read_file":
        fp = inp.get("file_path", "") if isinstance(inp, dict) else ""
        skill_cn = ""
        if isinstance(fp, str) and "/skills/" in fp:
            code = fp.split("/skills/")[-1].split("/")[0]
            skill_cn = _SKILL_CODE_CN.get(code, code)
        return f"调用{skill_cn}技能的'读取技能文件'" if skill_cn else "读取技能文件"
    if name == "write_todos":
        todos = inp.get("todos", []) if isinstance(inp, dict) else []
        steps = [t.get("content", "") if isinstance(t, dict) else str(t) for t in todos][:5]
        return "LLM规划任务步骤：" + "；".join(s for s in steps if s) if steps else "LLM规划任务步骤"
    if name == "kg_api":
        pkg_tool = _ACTION_TOOL_MAP.get(action)
        if pkg_tool:
            pkg_cn, tool_cn = pkg_tool
            return f"调用{pkg_cn}技能的'{tool_cn}{action}'"
        return f"调用工具'{action}'"
    return f"调用工具 {name}"


def _infer_decision_task(tc_name: str, tc_args) -> str:
    """根据 LLM 决策的工具调用推断判定标题（带推理结论）。"""
    if tc_name == "read_file":
        fp = tc_args.get("file_path", "") if isinstance(tc_args, dict) else ""
        code = ""
        if "/skills/" in str(fp):
            code = str(fp).split("/skills/")[-1].split("/")[0]
        cn = _SKILL_CODE_CN.get(code, code)
        return f"选择技能（判定使用'{cn}'技能）" if cn else "选择技能"
    if tc_name == "write_todos":
        return "LLM规划任务步骤"
    if tc_name == "kg_api":
        action = tc_args.get("action", "") if isinstance(tc_args, dict) else ""
        params = tc_args.get("params", "") if isinstance(tc_args, dict) else ""
        pkg_tool = _ACTION_TOOL_MAP.get(action)
        tool_cn = pkg_tool[1] if pkg_tool else action
        conclusion = ""
        try:
            import json as _j
            p = _j.loads(params) if params else {}
        except Exception:
            p = {}
        if action == "validate_l2" and p.get("l2_name"):
            conclusion = f"，推理出L2={p['l2_name']}"
        elif action == "execute_sql" and p.get("sql"):
            conclusion = f"，SQL：{str(p['sql'])[:50]}"
        elif action == "search_entities" and p.get("keyword"):
            conclusion = f"，关键词：{p['keyword']}"
        return f"判定{tool_cn}{conclusion}" if conclusion else f"判定：调用'{tool_cn}'"
    return "LLM思考判定"


def _build_result_summary(last_task: str, parsed: dict) -> str:
    """on_tool_end 时根据工具返回结果拼接自然语言结论 result_summary。"""
    if not isinstance(parsed, dict):
        return ""
    # 通用: 工具返回 error 字段 -> 执行失败(优先于各工具正常分支, 避免 SQL 报错被当成"返回0行")
    if parsed.get("error"):
        return f"执行失败：{parsed.get('error')}"
    if last_task == "读技能":
        # read_file 返回的是技能文件内容，无法从内容提取技能名，靠 detail 已含
        return "判定使用该技能"
    if last_task == "获取层级树":
        l1_cnt = len(parsed.get("l1_list", [])) if isinstance(parsed.get("l1_list"), list) else 0
        # 统计 L2 总数
        l2_cnt = 0
        for l1 in parsed.get("l1_list", []) or []:
            if isinstance(l1, dict):
                l2_cnt += len(l1.get("l2_list", []) or [])
        return f"返回 {l1_cnt} 个L1、{l2_cnt} 个L2"
    if last_task == "校验L2":
        if parsed.get("valid"):
            return f"锁定 L2：{parsed.get('l2_name', '')}"
        return f"L2 校验未通过：{parsed.get('reason', '')}"
    if last_task == "获取子图":
        entities = parsed.get("l2x_entities", []) or []
        cnt = len(entities)
        main_tbl = next((e.get("entity_name", "") for e in entities if isinstance(e, dict) and e.get("is_main_table")), "")
        return f"该 L2 下共 {cnt} 个实体" + (f"，主表：{main_tbl}" if main_tbl else "")
    if last_task == "校验属性":
        attrs = parsed.get("attributes", []) or []
        names = [a.get("attribute_name", "") for a in attrs if isinstance(a, dict)][:5]
        return f"命中 {len(attrs)} 个属性" + (f"：{', '.join(names)}" if names else "")
    if last_task == "查关系":
        rels = parsed.get("relations", []) or []
        return f"找到 {len(rels)} 条关联关系"
    if last_task == "搜索实体":
        ents = parsed.get("entities", []) or []
        flds = parsed.get("fields", []) or []
        return f"命中 {len(ents)} 个实体、{len(flds)} 个字段"
    if last_task == "查JOIN字段":
        join_on = parsed.get("join_on", "")
        return f"JOIN 字段：{join_on}" if join_on else "未找到 JOIN 关系"
    if last_task == "校验SQL":
        if parsed.get("safe"):
            return "SQL 校验通过"
        return f"校验失败：{parsed.get('reason', '')}"
    if last_task == "SQL执行":
        row_cnt = parsed.get("row_count", 0)
        cols = parsed.get("columns", []) or []
        col_str = ", ".join(str(c) for c in cols[:4])
        return f"返回 {row_cnt} 行数据" + (f"，字段：{col_str}{'...' if len(cols) > 4 else ''}" if cols else "")
    # 兜底：用 tool_log 首行
    log = parsed.get("log", "")
    if log:
        return log.split("\n")[0][:80]
    return ""


def _build_nonjson_result_summary(last_task: str, tool_name: str, out_str: str) -> str:
    """on_tool_end 时 parsed=None（非 JSON 返回，如 read_file 返回技能文件内容）的结果摘要。"""
    if not out_str:
        return "工具执行完成"
    if last_task == "读技能" or tool_name == "read_file":
        # 技能文件内容，提取标题行（# 开头）
        for line in out_str.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not line.startswith("# ---"):
                return f"读取技能文件：{line[2:].strip()}"
        return f"读取技能文件（{len(out_str)} 字符）"
    if tool_name == "write_todos":
        return "任务规划完成"
    # 兜底：取前 80 字符
    return out_str[:80].replace("\n", " ").strip() + ("..." if len(out_str) > 80 else "")


# --------------------------------------------------------------------------- #
# Pydantic 模型
# --------------------------------------------------------------------------- #
