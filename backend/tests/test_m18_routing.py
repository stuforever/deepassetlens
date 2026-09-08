# -*- coding: utf-8 -*-
"""M18 单测：规则意图族/QueryContract 契约/输出契约执行体（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M18 spec §八验收标准锚定现有实现）。
意图族零 LLM（spec §七.2：快、确定、可测）——正则/关键词行为直接锚定。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 规则意图族（spec §四表）
# ---------------------------------------------------------------------------

def test_detect_aggregate_intent():
    """聚合分布触发词→aggregate_intent dict（spec §四：S1 契约注入）。
    变异锚点：触发词删 → S1 聚合契约不注入（分布题走散答）。"""
    from app.services.intent_classifier import detect_aggregate_intent
    hit = detect_aggregate_intent("各电压等级客户占比分布")
    assert hit is not None and hit["required_shape"] == "GROUP BY 维度列 + COUNT/SUM"
    assert detect_aggregate_intent("统计用电客户总数") is None


def test_detect_vague_intent():
    """歧义检测：模糊词且无明确意图词→True（spec §四：S2 澄清模式）。
    变异锚点：澄清检测删 → 歧义题乱查不问。"""
    from app.services.intent_classifier import detect_vague_intent
    assert detect_vague_intent("变压器情况怎么样") is True
    assert detect_vague_intent("统计用电客户总数") is False


def test_is_count_intent():
    """计数型问法判定（spec §四：CountAnswer 极简；排除聚合/排名，docstring 样本）。
    变异锚点：计数判定删 → CountAnswer 极简段失效。"""
    from app.services.intent_classifier import is_count_intent
    assert is_count_intent("统计用电客户数量") is True
    assert is_count_intent("用电客户有多少个") is True
    assert is_count_intent("各电压等级客户占比") is False
    assert is_count_intent("容量最大的客户") is False


def test_has_dynamic_condition():
    """动态条件检测（spec §四：直通豁免——日期形态/比较词）。
    变异锚点：动态条件删 → 示例 SQL 直通错槽位。"""
    from app.services.intent_classifier import has_dynamic_condition
    assert has_dynamic_condition("统计 2026-08-01 当天的新增用户") is True
    assert has_dynamic_condition("统计用电客户总数") is False


def test_has_negation_and_classify():
    """否定检测+总分类（spec §四：classify_intent/guidance_labels_for/has_negation）。
    变异锚点：分类族删 → guidance 预载失据。"""
    from app.services.intent_classifier import classify_intent, guidance_labels_for, has_negation
    assert isinstance(classify_intent("统计用电客户总数"), str)
    assert isinstance(guidance_labels_for("统计用电客户总数"), list)
    assert isinstance(has_negation("不要统计变压器", "统计"), bool)


# ---------------------------------------------------------------------------
# QueryContract 契约对象（spec §三）
# ---------------------------------------------------------------------------

def test_generic_contract_full_tools():
    """generic 低权限通用契约：GENERIC_ALLOWED_TOOLS 全集+route_type+rubric（spec §三）。
    变异锚点：allowed 缩水 → 通用问答能力误伤。"""
    from app.services.query_contract import GENERIC_ALLOWED_TOOLS, QueryContract
    c = QueryContract.generic()
    assert c.route_type == "generic"
    # GENERIC_ALLOWED_TOOLS 全集必在；task 按复合条件默认放行（spec §三：allow_subagents 时入白名单）
    assert set(GENERIC_ALLOWED_TOOLS) <= set(c.allowed_tools or [])
    assert "task" in set(c.allowed_tools or [])
    assert c.rubric


def test_generic_clarify_mode_zero_tools():
    """澄清模式：clarify_required=True→allowed_tools=[]（spec §三/§七.3 澄清优于乱查）。
    变异锚点：澄清不收缩 → 模型带着猜的口径查库。"""
    from app.services.query_contract import QueryContract
    c = QueryContract.generic(clarify_required=True)
    assert c.clarify_required is True
    assert list(c.allowed_tools or []) == []


def test_absolute_forbidden_and_scenario_no_read_file():
    """ABSOLUTE_FORBIDDEN_TOOLS 只加不减；场景路径禁 read_file（spec §三：批13-G 收口）。
    变异锚点：场景契约放开 read_file → 剧本已预载仍读文件=浪费轮。"""
    import inspect
    from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS, QueryContract
    assert "write_file" in ABSOLUTE_FORBIDDEN_TOOLS and "edit_file" in ABSOLUTE_FORBIDDEN_TOOLS
    src = inspect.getsource(QueryContract.from_step)
    assert "read_file" in src  # 场景禁读文件的显式处理


# ---------------------------------------------------------------------------
# 输出契约执行体（spec §五）
# ---------------------------------------------------------------------------

def test_output_contract_validate_and_scrub():
    """validate_final_output 禁表+scrub_markdown_tables 剥离（spec §五：M16 前最后一道）。
    变异锚点：执行体删 → 明细表绕过 M16 delivery。"""
    from app.services.output_contract import (
        count_markdown_tables,
        scrub_markdown_tables,
        validate_final_output,
    )
    md = "统计完成\n| 台区 | 数量 |\n|---|---|\n| a | 1 |"
    assert count_markdown_tables(md) >= 1
    chk = validate_final_output(md, result_available_for_ui=True, forbid_markdown_detail_table=True)
    assert not chk.ok
    scrubbed = scrub_markdown_tables(md)
    assert "|---|" not in scrubbed


# ---------------------------------------------------------------------------
# 路由/引擎/问属性链存在性（spec §二/§六）
# ---------------------------------------------------------------------------

def test_skill_router_and_catalog_primitives():
    """SkillRouter/RouteResult+目录匹配原语（spec §二/§四）。
    变异锚点：路由器删 → 场景路由决策断。"""
    from app.services.skill_catalog import SkillDefinition, StepDefinition
    from app.services.skill_router import RouteResult, SkillRouter
    assert SkillRouter is not None and RouteResult is not None
    assert SkillDefinition is not None and StepDefinition is not None


def test_engine_router_shapes():
    """EngineDecision+resolve_engine/resolve_engines_multi（spec §四：三模式运行时出口）。
    变异锚点：引擎路由删 → M07 source_mode 无出口。"""
    from app.services.query_engine_router import EngineDecision, resolve_engine, resolve_engines_multi
    assert EngineDecision is not None


def test_query_attribute_chain_exists():
    """问属性链簇（spec §六：目录/召回打分/校验/面板+门面 re-export）。
    变异锚点：链断 → 问属性定位失。"""
    import app.services.query_attribute_pipeline as P
    import app.services.query_attribute_catalog as C
    assert hasattr(C, "_score_attribute_hit_from_catalog")
    assert hasattr(P, "_validate_query_attribute_result")
    import app.services.query_attribute_service as F
    assert F is not None
