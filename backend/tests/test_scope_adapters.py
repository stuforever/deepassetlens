"""ScopeAdapter 单测：四类数据工具的范围交叉校验。

验证：SQL 型工具从 WHERE 提取客户名、filters 型工具从 dict 提取客户名、
可信范围交叉校验（子集放行/越界拦截）、无可信范围跳过。
"""
import pytest
from app.services.scope_adapters import (
    check_scope_for_tool, extract_tool_args, extract_customer_names_from_filters
)
from app.services.scope_checker import ScopeCheck


class TestExtractToolArgs:
    """从 tool_call.args 提取参数（兼容 dict 和 JSON str）。"""

    def test_dict_args(self):
        tc = {"args": {"sql": "SELECT 1", "filters": {"cust_name": "x"}}}
        args = extract_tool_args(tc)
        assert args.sql == "SELECT 1"
        assert args.filters == {"cust_name": "x"}

    def test_json_str_args(self):
        tc = {"args": '{"sql": "SELECT 1", "entity_code": "cms20_cst_cust"}'}
        args = extract_tool_args(tc)
        assert args.sql == "SELECT 1"
        assert args.entity_code == "cms20_cst_cust"

    def test_empty_args(self):
        args = extract_tool_args({})
        assert args.sql == ""
        assert args.filters == {}


class TestExtractFromFilters:
    """从 filters dict 提取客户名。"""

    def test_list_value(self):
        names = extract_customer_names_from_filters({"cust_name": ["客户001", "客户003"]})
        assert names == {"客户001", "客户003"}

    def test_comma_string(self):
        names = extract_customer_names_from_filters({"customer_name": "客户001,客户003"})
        assert names == {"客户001", "客户003"}

    def test_alternative_keys(self):
        for key in ("cust_name", "customer_name", "customer_names", "cust_names"):
            names = extract_customer_names_from_filters({key: ["客户001"]})
            assert "客户001" in names, f"key={key} 未提取到"


class TestCheckScopeForTool:
    """按工具类型交叉校验可信范围。"""

    def test_no_trusted_scope_skips(self):
        """无可信范围时跳过（放行）。"""
        tc = {"args": {"sql": "SELECT * FROM t WHERE cust_name='客户001'"}}
        sc = check_scope_for_tool("execute_sql", tc, None)
        assert sc.ok

    def test_sql_subset_passes(self):
        """SQL 客户名是可信范围子集 -> 放行。"""
        tc = {"args": {"sql": "SELECT * FROM t WHERE cust_name IN ('客户001','客户003')"}}
        trusted = {"customer_names": ["客户001", "客户003"]}
        sc = check_scope_for_tool("execute_sql", tc, trusted)
        assert sc.ok, sc.reason

    def test_sql_superset_blocked(self):
        """SQL 客户名超出可信范围 -> 拦截。"""
        tc = {"args": {"sql": "SELECT * FROM t WHERE cust_name IN ('客户001','客户005')"}}
        trusted = {"customer_names": ["客户001", "客户003"]}
        sc = check_scope_for_tool("execute_sql", tc, trusted)
        assert not sc.ok, "越界客户未拦截"

    def test_sql_no_filter_blocked(self):
        """有可信范围但 SQL 无 cust_name 过滤 -> 拦截（越界风险）。"""
        tc = {"args": {"sql": "SELECT * FROM t"}}
        trusted = {"customer_names": ["客户001"]}
        sc = check_scope_for_tool("execute_sql", tc, trusted)
        assert not sc.ok, "无 cust_name 过滤未拦截"

    def test_entity_api_filters_subset_passes(self):
        """execute_entity_api 从 filters 提取客户名，子集放行。"""
        tc = {"args": {"entity_code": "cms20_cst_cust", "filters": {"cust_name": ["客户001"]}}}
        trusted = {"customer_names": ["客户001", "客户003"]}
        sc = check_scope_for_tool("execute_entity_api", tc, trusted)
        assert sc.ok, sc.reason

    def test_entity_api_filters_superset_blocked(self):
        """execute_entity_api filters 越界 -> 拦截。"""
        tc = {"args": {"entity_code": "cms20_cst_cust", "filters": {"cust_name": ["客户005"]}}}
        trusted = {"customer_names": ["客户001", "客户003"]}
        sc = check_scope_for_tool("execute_entity_api", tc, trusted)
        assert not sc.ok, "filters 越界未拦截"

    def test_doris_sql_carrier(self):
        """execute_doris_sql 优先 filters，其次 SQL。"""
        # 有 filters 时用 filters
        tc = {"args": {"sql": "SELECT * FROM t", "filters": {"cust_name": ["客户001"]}}}
        trusted = {"customer_names": ["客户001", "客户003"]}
        sc = check_scope_for_tool("execute_doris_sql", tc, trusted)
        assert sc.ok, sc.reason

    def test_doris_sql_fallback_to_sql(self):
        """execute_doris_sql 无 filters 时回退到 SQL 提取。"""
        tc = {"args": {"sql": "SELECT * FROM t WHERE cust_name='客户001'"}}
        trusted = {"customer_names": ["客户001", "客户003"]}
        sc = check_scope_for_tool("execute_doris_sql", tc, trusted)
        assert sc.ok, sc.reason

    def test_non_data_tool_skips(self):
        """非数据工具跳过。"""
        tc = {"args": {}}
        sc = check_scope_for_tool("read_file", tc, {"customer_names": ["客户001"]})
        assert sc.ok

    def test_trusted_as_list(self):
        """可信范围直接传 list 也兼容。"""
        tc = {"args": {"sql": "SELECT * FROM t WHERE cust_name='客户001'"}}
        sc = check_scope_for_tool("execute_sql", tc, ["客户001", "客户003"])
        assert sc.ok, sc.reason
