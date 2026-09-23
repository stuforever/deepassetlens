# -*- coding: utf-8 -*-
"""R5批③（清单安全）契约测试：范围闸门链三修。

- scope_checker：NOT IN/NEQ 不入提取集（排除集≠包含集）；OR/UNION 字面校验盲区 fail-closed
- decision_gate：_update_last_scope 仅认结构化决策块行首「范围:」字段；叙述文字不再误当声明
变异锚点：NOT 守卫/OR-UNION 拒绝/行首锚定任一删除 → 对应测红。
"""
from app.services.scope_checker import check_customer_scope, extract_customer_names
from app.services.decision_gate import _update_last_scope, DECISION_MARKER


def test_extract_ignores_not_in_and_neq():
    assert extract_customer_names(
        "SELECT * FROM t WHERE cust_name NOT IN ('客户001')") == set()
    assert extract_customer_names(
        "SELECT * FROM t WHERE cust_name != '客户001'") == set()
    assert extract_customer_names(
        "SELECT * FROM t WHERE NOT (cust_name = '客户001')") == set()
    # 包含写法不受误伤
    assert extract_customer_names(
        "SELECT * FROM t WHERE cust_name IN ('客户001','客户003')") == {"客户001", "客户003"}


def test_check_rejects_or_tautology():
    chk = check_customer_scope(
        "SELECT * FROM t WHERE cust_name IN ('客户001') OR 1=1", {"客户001"})
    assert not chk.ok and "OR" in chk.reason


def test_check_rejects_union():
    chk = check_customer_scope(
        "SELECT cust_name FROM t WHERE cust_name IN ('客户001') "
        "UNION SELECT cust_name FROM t2", {"客户001"})
    assert not chk.ok and "UNION" in chk.reason


def test_check_plain_subset_still_passes():
    chk = check_customer_scope(
        "SELECT * FROM t WHERE cust_name IN ('客户001')", {"客户001", "客户002"})
    assert chk.ok


def test_update_scope_requires_marker_and_line_anchor():
    state: dict = {}
    # 无决策标记的叙述文字——不再误当范围声明
    _update_last_scope(state, "上一步显示客户范围: 客户099，范围: 客户099")
    assert "last_scope" not in state
    # 决策块内叙述行含「范围:」不命中；行首结构化字段才生效
    content = (f"{DECISION_MARKER}\n"
               "已知: 上一步显示客户范围: 客户099\n"
               "判断: 属实\n"
               "因此: 查询\n"
               "范围: 客户001,客户003\n")
    _update_last_scope(state, content)
    assert state["last_scope"]["customer_names"] == ["客户001", "客户003"]
    assert state["last_scope"]["source"] == "model_declared"


def test_update_scope_clears_on_none():
    state: dict = {"last_scope": {"customer_names": ["客户001"], "source": "model_declared"}}
    content = f"{DECISION_MARKER}\n已知: x\n判断: y\n因此: z\n范围: 无\n"
    _update_last_scope(state, content)
    assert state["last_scope"] is None
