# -*- coding: utf-8 -*-
"""B2（v4§三/§四）契约测试：wenshu 3 角色卡 + ChatRequest.role_id 注入。

先红后绿（TDD）——实现前运行应 ImportError/AttributeError 失败：
- wenshu 3 角色卡注册表（默认分析师=现状等价/业务白话型/技术 detail 型，文案照 v4§四）
- apply_role：None=现状等价（逐字节不变）；角色卡=基座+风格段（角色改怎么说，不拆工作流契约）
- 未知 role_id / 非 wenshu 专家拒绝（ValueError）
- apply_role 纯函数（不改入参卡）
- 装配缓存键：role None 键逐字节不变；role 真值进键（切换角色=重建，不命中旧 agent）
- ChatRequest.role_id（None 默认）
- GET /api/experts/{expert_id}/roles 角色下拉数据源（wenshu 3 张、其他专家空）
"""
import pytest


def test_chat_request_accepts_role_id():
    from app.api.data_intelligence import ChatRequest
    req = ChatRequest(user_input="统计用电客户总数")
    assert req.role_id is None
    req2 = ChatRequest(user_input="q", role_id="analyst_default")
    assert req2.role_id == "analyst_default"


def test_wenshu_role_cards_preset():
    from app.services.wenshu_roles import WENSHU_ROLE_CARDS
    assert [c["role_id"] for c in WENSHU_ROLE_CARDS] == [
        "analyst_default", "business_plain", "tech_detail"]
    assert [c["name"] for c in WENSHU_ROLE_CARDS] == [
        "默认分析师", "业务白话型", "技术 detail 型"]
    # 默认分析师=现状等价：无风格段
    assert WENSHU_ROLE_CARDS[0].get("style_prompt") in (None, "")


def test_apply_role_none_is_identity():
    from app.services.wenshu_roles import apply_role
    card = {"expert_id": "wenshu", "system_prompt": "BASE", "version": 3}
    out = apply_role("wenshu", None, card)
    assert out["system_prompt"] == "BASE"


def test_apply_role_default_analyst_equals_status_quo():
    from app.services.wenshu_roles import apply_role
    card = {"expert_id": "wenshu", "system_prompt": "BASE", "version": 3}
    out = apply_role("wenshu", "analyst_default", card)
    assert out["system_prompt"] == "BASE"


def test_apply_role_style_appended_not_replacing():
    from app.services.wenshu_roles import apply_role
    card = {"expert_id": "wenshu", "system_prompt": "基座工作流规则", "version": 3}
    for rid in ("business_plain", "tech_detail"):
        out = apply_role("wenshu", rid, dict(card))
        # 基座保留（角色改怎么说，不拆工作流契约）+ 风格段在场
        assert out["system_prompt"].startswith("基座工作流规则")
        assert len(out["system_prompt"]) > len(card["system_prompt"])


def test_apply_role_unknown_rejected():
    from app.services.wenshu_roles import apply_role
    with pytest.raises(ValueError):
        apply_role("wenshu", "no_such_role", {"expert_id": "wenshu", "system_prompt": "B"})


def test_apply_role_wenshu_only():
    from app.services.wenshu_roles import apply_role
    with pytest.raises(ValueError):
        apply_role("sishu", "business_plain", {"expert_id": "sishu", "system_prompt": "B"})


def test_apply_role_does_not_mutate_input():
    from app.services.wenshu_roles import apply_role
    card = {"expert_id": "wenshu", "system_prompt": "BASE"}
    apply_role("wenshu", "business_plain", card)
    assert card["system_prompt"] == "BASE"


def test_assembly_cache_key_role_factor():
    from app.services.tupu_deepagent import _assembly_cache_key
    base = _assembly_cache_key("conn1", 1, 2, "fh", "wenshu", 3)
    assert _assembly_cache_key("conn1", 1, 2, "fh", "wenshu", 3, role_id=None) == base
    assert _assembly_cache_key("conn1", 1, 2, "fh", "wenshu", 3, role_id="business_plain") != base


def test_roles_endpoint_lists_wenshu_three():
    from app.api.experts import list_expert_roles
    out = list_expert_roles("wenshu")
    ids = [r["role_id"] for r in out["roles"]]
    assert ids == ["analyst_default", "business_plain", "tech_detail"]
    assert list_expert_roles("sishu")["roles"] == []
