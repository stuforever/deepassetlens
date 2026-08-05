"""
轻量级 JSON Schema 校验器
不依赖外部库，支持 JSON Schema Draft-07 核心子集
"""

import json
import re
from typing import Any, Dict, List, Optional, Union


class SchemaValidationError(Exception):
    """Schema 校验错误"""
    pass


class JSONSchemaValidator:
    """
    轻量级 JSON Schema 校验器
    支持：type, required, properties, items, minimum/maximum,
          minLength/maxLength, pattern, enum, const, default,
          oneOf, anyOf, allOf, format(email, date, date-time, uri)
    """

    FORMAT_PATTERNS = {
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "date": r"^\d{4}-\d{2}-\d{2}$",
        "date-time": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$",
        "uri": r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
        "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    }

    def __init__(self):
        self.errors: List[str] = []

    def validate(self, data: Any, schema: Dict[str, Any], path: str = "") -> bool:
        """校验数据是否符合 Schema"""
        self.errors = []
        self._validate_value(data, schema, path)
        return len(self.errors) == 0

    def validate_with_errors(self, data: Any, schema: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """校验并返回详细错误信息"""
        self.errors = []
        self._validate_value(data, schema, path)
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors.copy(),
            "error": "; ".join(self.errors) if self.errors else None
        }

    def _add_error(self, path: str, message: str):
        full_path = path if path else "<root>"
        self.errors.append(f"[{full_path}] {message}")

    def _validate_value(self, data: Any, schema: Dict[str, Any], path: str):
        if not isinstance(schema, dict):
            return

        # const
        if "const" in schema:
            if data != schema["const"]:
                self._add_error(path, f"值必须为 {schema['const']!r}")
            return

        # enum
        if "enum" in schema:
            if data not in schema["enum"]:
                self._add_error(path, f"值必须是以下之一: {schema['enum']}")
            return

        # type
        if "type" in schema:
            if not self._check_type(data, schema["type"]):
                self._add_error(path, f"类型错误: 期望 {schema['type']}, 实际为 {type(data).__name__}")
                return

        # string 校验
        if isinstance(data, str):
            self._validate_string(data, schema, path)

        # number 校验
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            self._validate_number(data, schema, path)

        # array 校验
        if isinstance(data, list):
            self._validate_array(data, schema, path)

        # object 校验
        if isinstance(data, dict):
            self._validate_object(data, schema, path)

        # anyOf
        if "anyOf" in schema:
            if not any(self._quick_validate(data, s) for s in schema["anyOf"]):
                self._add_error(path, "数据不匹配 anyOf 中任何一个 schema")

        # oneOf
        if "oneOf" in schema:
            matches = sum(1 for s in schema["oneOf"] if self._quick_validate(data, s))
            if matches != 1:
                self._add_error(path, f"oneOf 要求恰好匹配一个 schema，实际匹配了 {matches} 个")

        # allOf
        if "allOf" in schema:
            for s in schema["allOf"]:
                self._validate_value(data, s, path)

        # if/then/else
        if "if" in schema:
            if self._quick_validate(data, schema["if"]):
                if "then" in schema:
                    self._validate_value(data, schema["then"], path)
            else:
                if "else" in schema:
                    self._validate_value(data, schema["else"], path)

    def _check_type(self, data: Any, expected: Union[str, List[str]]) -> bool:
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        types_to_check = [expected] if isinstance(expected, str) else expected
        for t in types_to_check:
            expected_type = type_map.get(t)
            if expected_type and isinstance(data, expected_type):
                # 排除 bool 是 int 子类的情况
                if t == "integer" and isinstance(data, bool):
                    return False
                return True
        return False

    def _validate_string(self, data: str, schema: Dict[str, Any], path: str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            self._add_error(path, f"字符串长度至少为 {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            self._add_error(path, f"字符串长度至多为 {schema['maxLength']}")
        if "pattern" in schema:
            if not re.search(schema["pattern"], data):
                self._add_error(path, f"字符串不匹配正则: {schema['pattern']}")
        if "format" in schema:
            fmt = schema["format"]
            pattern = self.FORMAT_PATTERNS.get(fmt)
            if pattern and not re.match(pattern, data):
                self._add_error(path, f"字符串格式错误: 期望 {fmt}")

    def _validate_number(self, data: Union[int, float], schema: Dict[str, Any], path: str):
        if "minimum" in schema and data < schema["minimum"]:
            self._add_error(path, f"数值不能小于 {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            self._add_error(path, f"数值不能大于 {schema['maximum']}")
        if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
            self._add_error(path, f"数值必须大于 {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
            self._add_error(path, f"数值必须小于 {schema['exclusiveMaximum']}")
        if "multipleOf" in schema and data % schema["multipleOf"] != 0:
            self._add_error(path, f"数值必须是 {schema['multipleOf']} 的倍数")

    def _validate_array(self, data: List[Any], schema: Dict[str, Any], path: str):
        if "minItems" in schema and len(data) < schema["minItems"]:
            self._add_error(path, f"数组元素个数至少为 {schema['minItems']}")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            self._add_error(path, f"数组元素个数至多为 {schema['maxItems']}")
        if "uniqueItems" in schema and schema["uniqueItems"]:
            seen = set()
            for item in data:
                key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
                if key in seen:
                    self._add_error(path, "数组元素必须唯一")
                    break
                seen.add(key)
        if "items" in schema:
            for i, item in enumerate(data):
                self._validate_value(item, schema["items"], f"{path}[{i}]")
        if "prefixItems" in schema:
            for i, item in enumerate(data):
                if i < len(schema["prefixItems"]):
                    self._validate_value(item, schema["prefixItems"][i], f"{path}[{i}]")

    def _validate_object(self, data: Dict[str, Any], schema: Dict[str, Any], path: str):
        # required
        if "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    self._add_error(path, f"缺少必填字段: {field}")

        # properties
        if "properties" in schema:
            for prop, prop_schema in schema["properties"].items():
                if prop in data:
                    prop_path = f"{path}.{prop}" if path else prop
                    self._validate_value(data[prop], prop_schema, prop_path)

        # additionalProperties
        if "additionalProperties" in schema and not schema["additionalProperties"]:
            allowed = set(schema.get("properties", {}).keys()) | set(schema.get("patternProperties", {}).keys())
            for key in data:
                if key not in allowed:
                    self._add_error(path, f"不允许额外字段: {key}")

        # propertyNames
        if "propertyNames" in schema and "pattern" in schema["propertyNames"]:
            pattern = schema["propertyNames"]["pattern"]
            for key in data:
                if not re.search(pattern, key):
                    self._add_error(path, f"属性名 '{key}' 不匹配正则: {pattern}")

        # minProperties / maxProperties
        if "minProperties" in schema and len(data) < schema["minProperties"]:
            self._add_error(path, f"对象属性数至少为 {schema['minProperties']}")
        if "maxProperties" in schema and len(data) > schema["maxProperties"]:
            self._add_error(path, f"对象属性数至多为 {schema['maxProperties']}")

    def _quick_validate(self, data: Any, schema: Dict[str, Any]) -> bool:
        """快速校验（不收集错误）"""
        validator = JSONSchemaValidator()
        validator._validate_value(data, schema, "")
        return len(validator.errors) == 0


def validate_input(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """便捷函数：校验输入数据"""
    validator = JSONSchemaValidator()
    return validator.validate_with_errors(data, schema)


def generate_default_value(schema: Dict[str, Any]) -> Any:
    """根据 Schema 生成默认值"""
    if "default" in schema:
        return schema["default"]

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = schema_type[0]

    if schema_type == "object":
        result = {}
        props = schema.get("properties", {})
        for key, prop_schema in props.items():
            if key in (schema.get("required") or []):
                result[key] = generate_default_value(prop_schema)
        return result
    elif schema_type == "array":
        return []
    elif schema_type == "string":
        if "enum" in schema:
            return schema["enum"][0]
        return ""
    elif schema_type == "integer":
        return schema.get("default", 0)
    elif schema_type == "number":
        return schema.get("default", 0.0)
    elif schema_type == "boolean":
        return schema.get("default", False)
    elif schema_type == "null":
        return None

    # oneOf / anyOf
    if "anyOf" in schema:
        return generate_default_value(schema["anyOf"][0])
    if "oneOf" in schema:
        return generate_default_value(schema["oneOf"][0])
    if "allOf" in schema:
        merged = {}
        for s in schema["allOf"]:
            merged.update(s)
        return generate_default_value(merged)

    return None
