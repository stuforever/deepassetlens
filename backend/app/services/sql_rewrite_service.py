# -*- coding: utf-8 -*-
"""SQL 字段校验与 AI 改写服务

职责：校验 integration_sql 输出字段（列名+类型）与实体 properties_schema 字段定义是否匹配，
不匹配时调 LLM 改写 SQL（加 CAST/AS 别名），使输出与实体字段完全对齐。

类型兼容性判断交给 LLM：把 pymysql 类型名（VAR_STRING/NEWDECIMAL 等）和实体 type
（string/varchar/decimal(38,18) 等）原始传入，由 LLM 对照规则判断，无需后端写归一化表。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from app.services.llm_client import (
    call_openai_compatible_chat,
    get_default_llm_connection,
    get_llm_connection_by_id,
)

_SYSTEM_PROMPT = """你是 Doris SQL 专家。任务：校验 SQL 输出字段与实体字段定义是否完全匹配，不匹配则改写 SQL。

## 匹配规则
1. 列名必须与实体字段 name 完全一致（数量对应，顺序可调整）
2. 类型要兼容。常见对应关系（实体 type ↔ Doris/pymysql 类型名）：
   - string / varchar ↔ VAR_STRING / VARCHAR
   - bigint ↔ LONGLONG
   - int ↔ LONG
   - decimal / decimal(38,18) ↔ NEWDECIMAL
   - datetime ↔ DATETIME
   - date ↔ DATE
   - double ↔ DOUBLE
   - number ↔ 可为 LONG 或 NEWDECIMAL

## 改写规则
- 列名不一致：用 `AS <实体字段名>` 别名对齐
- 类型不一致：用 `CAST(expr AS <Doris类型>)` 转换（如 CAST(x AS VARCHAR) / CAST(x AS DECIMAL(38,18)) / CAST(x AS DATETIME)）
- 只能调整 SELECT 子句的列表达式，不能改 FROM/JOIN 的表、WHERE 条件、UNION 结构
- 若 SQL 含 UNION/UNION ALL，每个分支都要对齐字段

## 输出格式
返回纯 JSON（不要 markdown 代码块、不要多余文字）：
{
  "matched": true 或 false,
  "differences": [
    {"field": "实体字段名", "issue": "列名不匹配" 或 "类型不兼容" 或 "缺失列" 或 "多余列", "detail": "具体说明"}
  ],
  "rewritten_sql": "改写后的完整SQL；若已完全匹配则原样返回"
}
"""


def _parse_json_response(raw: str) -> Dict[str, Any]:
    """清理 LLM 返回的 markdown 代码块并解析 JSON"""
    text = raw.strip()
    # 去掉 ```json ... ``` 或 ``` ... ``` 包裹
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    # 截取第一个 { 到最后一个 }
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        text = text[s:e + 1]
    return json.loads(text)


def ai_rewrite_sql(
    sql: str,
    sql_columns: List[Dict[str, str]],
    entity_fields: List[Dict[str, Any]],
    connection_id: str = None,
) -> Dict[str, Any]:
    """调 LLM 校验 SQL 输出字段与实体字段是否匹配，不匹配则改写

    Args:
        sql: 原始 integration_sql
        sql_columns: SQL 输出列 [{name, type}]（来自 doris_engine.describe_sql_columns）
        entity_fields: 实体字段 [{name, type, cnName}]（来自 properties_schema）
        connection_id: 指定 LLM 连接 id（让用户选模型）；None 则用默认 chat 连接

    Returns:
        {matched, differences, rewritten_sql, model} 或 {matched:False, error, rewritten_sql}
        model: 实际使用的连接 {name, model_name}，便于前端展示
    """
    if connection_id:
        conn = get_llm_connection_by_id(connection_id, "chat")
    else:
        conn = get_default_llm_connection("chat")
    if not conn:
        if connection_id:
            return {
                "matched": False,
                "error": "所选 LLM 连接不可用（不存在/已禁用/非 chat 能力），请重新选择",
                "rewritten_sql": sql,
                "differences": [],
                "model": None,
            }
        return {
            "matched": False,
            "error": "未配置默认 chat LLM 连接，请在「LLM配置」页启用一条 chat 连接，或在下方选择指定模型",
            "rewritten_sql": sql,
            "differences": [],
            "model": None,
        }

    user_prompt = (
        f"## 原始 SQL\n```\n{sql}\n```\n\n"
        f"## 实体字段定义（需匹配的目标）\n```\n{json.dumps(entity_fields, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## SQL 输出列（列名 + Doris/pymysql 类型名）\n```\n{json.dumps(sql_columns, ensure_ascii=False, indent=2)}\n```\n\n"
        "请按规则校验并改写，返回纯 JSON。"
    )

    raw = ""
    try:
        raw = call_openai_compatible_chat(
            conn,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )
        result = _parse_json_response(raw)
        result.setdefault("matched", False)
        result.setdefault("differences", [])
        result.setdefault("rewritten_sql", sql)
        result["model"] = {"name": conn.name, "model_name": conn.model_name}
        return result
    except Exception as e:
        return {
            "matched": False,
            "error": f"LLM 调用或解析失败: {e}",
            "rewritten_sql": sql,
            "differences": [],
            "model": {"name": conn.name, "model_name": conn.model_name},
        }
