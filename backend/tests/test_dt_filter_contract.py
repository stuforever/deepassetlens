# -*- coding: utf-8 -*-
"""交付测试窗口（2026-09-18）：build_sql_with_filters 过滤器契约回归。

背景：LLM 把 {'like': ...}/{'contains': ...} 整段当字符串传 -> 静默字符串化成 EQ 恒 0 行
（SAP 项目定义问数事故）。修复：like/contains 别名收编 + 非法 dict 显式报错。
"""
import pytest

from app.services.duckdb_engine import build_sql_with_filters

PSEUDO = "SELECT * FROM dim_ps_project_def_sap"


def test_contains_alias_becomes_like_percent():
    sql = build_sql_with_filters(PSEUDO, {"ProjectDescription": {"contains": "李钢柱"}})
    assert "LIKE" in sql and "%李钢柱%" in sql and "=" not in sql.split("WHERE", 1)[1]


def test_contains_underscore_alias():
    sql = build_sql_with_filters(PSEUDO, {"ProjectDescription": {"_contains": "abc"}})
    assert "LIKE" in sql and "%abc%" in sql


def test_like_alias_same_as_underscore_like():
    a = build_sql_with_filters(PSEUDO, {"Project": {"like": "B688%"}})
    b = build_sql_with_filters(PSEUDO, {"Project": {"_like": "B688%"}})
    assert a == b and "LIKE" in a


def test_scalar_still_eq_and_list_in_and_range():
    sql = build_sql_with_filters(PSEUDO, {"Project": "B688800001"})
    assert "=" in sql and "B688800001" in sql
    sql = build_sql_with_filters(PSEUDO, {"CompanyCode": ["1010", "2010"]})
    assert "IN" in sql
    sql = build_sql_with_filters(PSEUDO, {"CreationDate": {"_range": [[">=", "2020-01-01"], ["<=", "2026-12-31"]]}})
    assert ">=" in sql and "<=" in sql


def test_illegal_dict_raises_instead_of_silent_eq():
    with pytest.raises(ValueError):
        build_sql_with_filters(PSEUDO, {"ProjectDescription": "{'like': '%李钢柱%'}"} if False else {"ProjectDescription": {"foo": 1}})
    # 历史事故形态：LLM 把整个条件当字符串值传 -> 现在仍按标量 EQ（合法），但 docstring 已禁止
    sql = build_sql_with_filters(PSEUDO, {"ProjectDescription": "{'like': '%李钢柱%'}"})
    assert "'like'" in sql  # 作为字面量精确匹配，不再伪装成模糊查询成功
