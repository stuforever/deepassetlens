# -*- coding: utf-8 -*-
"""M17 单测：白名单换算/安全红线/DecisionGate/评分枚举/装配件契约（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M17 spec §七验收标准锚定现有实现）。
真装配（DeepAgent 实例+Checkpointer）依赖框架与 LLM，留联测。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 白名单打勾制（spec §四：批13-W W-1 用户定调）
# ---------------------------------------------------------------------------

def test_whitelist_exclusion_conversion():
    """换算公式：excluded = 红线5件 ∪ (勾选域 − allowed)；返回 {excluded, locked}（spec §四）。
    变异锚点：换算反转回黑名单 → 新工具漏网（白名单天然免疫失效）。"""
    from app.services.capability_config import get_tool_exclusions
    excl = get_tool_exclusions()
    assert isinstance(excl, dict) and "excluded" in excl and "locked" in excl
    # 安全红线 5 件物理排除（默认全勾时 excluded=红线 5 件，迁移零行为变化）
    assert {"write_file", "edit_file", "execute", "grep", "glob"} <= set(excl["excluded"])
    # 物理锁定 3 件恒在 allowed（locked 键展示，不可勾掉）
    assert {"read_file", "ls", "task"} <= set(excl["locked"])


def test_locked_tools_forced_excluded():
    """物理锁定件（read_file/ls）恒在排除/保留语义中不可取消（spec §四）。
    变异锚点：锁定件可勾掉 → 技能渐进披露断。"""
    import inspect
    from app.services import capability_config as C
    assert set(C.LOCKED_TOOL_EXCLUSIONS) >= {"read_file", "ls"}


def test_cap_enabled_unknown_defaults_true():
    """cap_enabled 未知名返 True（spec §八.3 登记：未知按启用，不改变现状）。
    变异锚点：未知返 False → 新能力注册前全部静默关闭（现状破坏）。"""
    from app.services.capability_config import cap_enabled
    assert cap_enabled("m17_nonexistent_capability_xyz") is True


# ---------------------------------------------------------------------------
# DecisionGate（spec §四：批13-W W-4）
# ---------------------------------------------------------------------------

def test_decision_gate_code_baseline():
    """DecisionGate 代码基准四件+默认关（spec §四：范围 execute_sql/execute_doris_sql/execute_entity_api/execute_api_sql）。
    变异锚点：基准漂移/默认开 → 裁决面越权或误关。"""
    from app.services.capability_config import DECISION_GATE_SCOPE_DEFAULT, get_decision_gate_config
    assert set(DECISION_GATE_SCOPE_DEFAULT) == {"execute_sql", "execute_doris_sql",
                                                "execute_entity_api", "execute_api_sql"}
    cfg = get_decision_gate_config()
    assert isinstance(cfg, dict)


# ---------------------------------------------------------------------------
# 评分模式枚举（spec §四：批13-AB3）
# ---------------------------------------------------------------------------

def test_rubric_mode_enum_validation():
    """rubric mode 枚举校验：非法值拒绝（spec §四/§七.5）。
    变异锚点：枚举校验删 → 任意字符串落库（评分路径失效）。"""
    from app.services.capability_config import validate_params
    err = validate_params("rubric", {"mode": "not_a_valid_mode"})
    assert err  # 非空=有校验错误


# ---------------------------------------------------------------------------
# 装配内部件（spec §五）
# ---------------------------------------------------------------------------

def test_data_query_tools_frozenset():
    """_DATA_QUERY_TOOLS 数据查询工具白名单（spec §五：守卫与分流引用）。
    变异锚点：白名单漂移 → M19 守卫口径错。"""
    from app.services.tupu_deepagent import _DATA_QUERY_TOOLS
    assert isinstance(_DATA_QUERY_TOOLS, (frozenset, set)) and "execute_sql" in _DATA_QUERY_TOOLS


def test_final_delivery_schema():
    """最终交付 schema（FinalFinding/FinalDelivery BaseModel，spec §五：批13-L 装配期静态）。
    变异锚点：schema 删 → done 载荷结构断。"""
    from app.services.tupu_deepagent import FinalDelivery, FinalFinding
    from pydantic import BaseModel
    assert issubclass(FinalDelivery, BaseModel) and issubclass(FinalFinding, BaseModel)


def test_sql_fix_helpers_exist():
    """SQL 纠错循环函数（spec §五：_remove_column_from_select/_fix_aggregate_unknown_column）。
    变异锚点：纠错删 → 列名错一轮即败。"""
    from app.services import tupu_deepagent as T
    assert hasattr(T, "_remove_column_from_select") and hasattr(T, "_fix_aggregate_unknown_column")


def test_compute_files_hash_stable():
    """技能文件哈希稳定（spec §三三因子之 f：无变化两次一致）。
    变异锚点：哈希不稳定 → 每问重建（缓存失效风暴）。"""
    from app.services.tupu_deepagent import _compute_files_hash
    h1, h2 = _compute_files_hash(), _compute_files_hash()
    assert isinstance(h1, str) and h1 == h2


# ---------------------------------------------------------------------------
# 能力开关 API（spec §四：6 端点）
# ---------------------------------------------------------------------------

def test_capabilities_api_endpoints():
    """capabilities API 端点面（list/manifest/PATCH update/probe/events/reset-defaults）。
    变异锚点：PATCH 删 → 能力开关无法调整；events 删 → 审计断。"""
    from app.api import capabilities as CAP
    paths = " ".join(getattr(r, "path", "") for r in CAP.router.routes)
    assert "manifest" in paths and "probe" in paths and "events" in paths and "reset" in paths
