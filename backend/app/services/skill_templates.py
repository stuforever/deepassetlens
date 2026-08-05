"""
技能模板库
内置常用技能模板，支持快速创建
"""

from typing import List, Dict, Any, Optional


SKILL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "tpl_query_data",
        "name": "数据查询",
        "description": "执行 SQL 查询并返回结果",
        "skill_type": "sql",
        "content": {
            "schema_version": "1.0",
            "sql": "SELECT * FROM {{table}} WHERE 1=1 LIMIT {{limit}}",
            "database": "default"
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "title": "表名", "default": "users"},
                "limit": {"type": "integer", "title": "返回条数", "default": 100}
            },
            "required": ["table"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "rows": {"type": "array"},
                "row_count": {"type": "integer"}
            }
        }
    },
    {
        "id": "tpl_api_call",
        "name": "API 调用",
        "description": "发送 HTTP 请求调用外部 API",
        "skill_type": "http",
        "content": {
            "schema_version": "1.0",
            "method": "GET",
            "url": "https://api.example.com/data",
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            "body_template": "",
            "auth": {"type": "none"}
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "title": "API 端点"}
            },
            "required": ["endpoint"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "body": {"type": "object"}
            }
        }
    },
    {
        "id": "tpl_data_transform",
        "name": "数据清洗转换",
        "description": "使用 Python 对输入数据进行清洗和转换",
        "skill_type": "python",
        "content": {
            "schema_version": "1.0",
            "script": "def execute(inputs):\n    data = inputs.get('data', [])\n    result = []\n    for item in data:\n        if item:\n            result.append({\n                'cleaned': str(item).strip().lower(),\n                'length': len(str(item))\n            })\n    return {'result': result, 'count': len(result)}",
            "entrypoint": "execute"
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "title": "输入数据"}
            },
            "required": ["data"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "array"},
                "count": {"type": "integer"}
            }
        }
    },
    {
        "id": "tpl_send_notification",
        "name": "发送通知",
        "description": "发送消息通知（自然语言技能，供 LLM 调用）",
        "skill_type": "natural",
        "content": {
            "schema_version": "1.0",
            "prompt": "请帮用户发送以下通知：\n\n标题：{{title}}\n内容：{{content}}\n接收人：{{recipient}}\n\n请确认通知内容是否合适，并总结发送要点。"
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "title": "通知标题"},
                "content": {"type": "string", "title": "通知内容"},
                "recipient": {"type": "string", "title": "接收人"}
            },
            "required": ["title", "content"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "skill_code": {"type": "string"}
            }
        }
    },
    {
        "id": "tpl_mixed_pipeline",
        "name": "数据处理流水线",
        "description": "混合技能：先查询数据，再清洗转换",
        "skill_type": "mixed",
        "content": {
            "schema_version": "1.0",
            "steps": [
                {
                    "step_id": "query",
                    "name": "查询数据",
                    "type": "sql",
                    "skill_code": "query_data",
                    "input_mapping": {"table": "{{input.table}}", "limit": "{{input.limit}}"}
                },
                {
                    "step_id": "transform",
                    "name": "数据转换",
                    "type": "python",
                    "skill_code": "transform_data",
                    "input_mapping": {"data": "{{query.output.rows}}"}
                }
            ]
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "title": "表名"},
                "limit": {"type": "integer", "title": "返回条数"}
            },
            "required": ["table"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "final_output": {"type": "object"},
                "step_results": {"type": "object"}
            }
        }
    }
]


def list_templates() -> List[Dict[str, Any]]:
    """列出所有模板"""
    return SKILL_TEMPLATES


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """获取指定模板"""
    for tpl in SKILL_TEMPLATES:
        if tpl["id"] == template_id:
            return tpl
    return None


def apply_template(template_id: str, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    应用模板创建技能数据
    返回可以直接用于 create_skill + create_version 的数据结构
    """
    tpl = get_template(template_id)
    if not tpl:
        raise ValueError(f"模板不存在: {template_id}")

    data = {
        "name": tpl["name"],
        "description": tpl["description"],
        "skill_type": tpl["skill_type"],
        "content": tpl["content"],
        "input_schema": tpl.get("input_schema", {"type": "object", "properties": {}}),
        "output_schema": tpl.get("output_schema", {"type": "object", "properties": {}}),
    }
    if overrides:
        data.update(overrides)
    return data



