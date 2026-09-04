# -*- coding: utf-8 -*-
"""批13-L 分型精简格式 单测。

- COUNT 型判定复用 intent_classifier.is_count_intent（批9 直通判定同源）
- 契约消息：COUNT 型注入 CountAnswer 极简指令段；分析/分布型不注入
- 直通管道不经过契约消息（天然极简，设计原话）
"""
import pytest

from app.services.intent_classifier import is_count_intent
from app.services.skill_router import route_user_input


def test_count型判定():
    """计数问法 True；聚合/排名/分析问法 False（is_count_intent 既有判据复用）。"""
    assert is_count_intent("统计用电客户数量") is True
    assert is_count_intent("用电客户有多少个") is True
    assert is_count_intent("统计重过载台区数量") is True
    assert is_count_intent("各电压等级客户占比") is False      # 聚合
    assert is_count_intent("查询重过载台区") is False          # 明细/判定
    assert is_count_intent("容量最大的客户") is False          # 排名


def test_契约消息COUNT注入():
    """generic COUNT 型 -> _CONTRACT_COUNT_ANSWER 段注入；场景/非 COUNT 型不注入。

    2026-08-25 e2e 实测修正：场景契约不注入（「要数量 vs 模板结构冻结」结构性冲突，
    scenario_strict 禁结构变化，模型 reasoning 打结 163s）——场景 COUNT 出口留待模板层扩展。
    """
    from app.api.data_intelligence import (
        _build_contract_system_message, _CONTRACT_COUNT_ANSWER,
    )
    # generic COUNT 型注入
    r = route_user_input("统计配电变压器数量")
    assert r.route_type != "scenario"
    msg = _build_contract_system_message(r.contract, question="统计配电变压器数量")
    assert _CONTRACT_COUNT_ANSWER in msg
    # 非 COUNT 场景题不注入
    r2 = route_user_input("查询重过载台区")
    msg2 = _build_contract_system_message(r2.contract, question="查询重过载台区")
    assert _CONTRACT_COUNT_ANSWER not in msg2
    # COUNT 型命中场景契约不注入（结构性冲突豁免）
    r3 = route_user_input("统计重过载台区数量")
    assert r3.route_type == "scenario"
    msg3 = _build_contract_system_message(r3.contract, question="统计重过载台区数量")
    assert _CONTRACT_COUNT_ANSWER not in msg3


def test_极简指令段内容约束():
    """指令段含 CountAnswer 形态约束三要素：一句结论/口径注/禁止四段展开。"""
    from app.api.data_intelligence import _CONTRACT_COUNT_ANSWER
    assert "一句结论" in _CONTRACT_COUNT_ANSWER
    assert "口径注" in _CONTRACT_COUNT_ANSWER
    assert "禁止" in _CONTRACT_COUNT_ANSWER and "四段展开" in _CONTRACT_COUNT_ANSWER
    assert "150 字" in _CONTRACT_COUNT_ANSWER
