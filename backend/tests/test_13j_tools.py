# -*- coding: utf-8 -*-
"""批13-J 收尾：工具排除配置化测试（批13-W W-1 反转后同步更新为白名单语义）。

覆盖：get_tool_exclusions 白名单换算默认/fail-safe 语义反转/locked 强制保留；
validate_params allowed 语义（未知名拒绝/锁定不可取消/旧键退役）；seed 形态；
私有模型标识函数等价（问题一）。
"""
import pytest

from app.services import capability_config as cc
from app.core.init_db import CAPABILITY_POLICY_SEED


class TestToolExclusions:
    def test_默认5件(self):
        """白名单全勾基线：换算后 excluded=红线 5 件。
        ⑤R R1（批12）：先行版教学工具族 11 件已从 mcp_server 注册表退役摘除——
        退出 GENERIC_ALLOWED_TOOLS/universe，排除清单不再含教学件（结构上不达问数面，
        wenshu 零感知由「注册表不存在」结构性保证；TUTOR_TOOLS 冻结名单留作防御性剔除依据）。"""
        cfg = cc.get_tool_exclusions()
        assert sorted(cfg["excluded"]) == sorted([
            "edit_file", "execute", "glob", "grep", "write_file",
        ])
        assert "read_file" in cfg["locked"] and "ls" in cfg["locked"]

    def test_locked永不可入excluded(self):
        # W-1 反转后：旧 excluded 键 PATCH 直接拒（防黑名单语义混写回潮）
        err = cc.validate_params("tool_availability", {"excluded": ["read_file"]})
        assert err and "已退役" in err

    def test_fail_safe配置异常回默认(self):
        """语义反转登记（设计 §五.3）：黑名单版读崩=默认排除 5 件；白名单版读崩=默认允许全集。"""
        from unittest.mock import patch
        with patch.object(cc, "get_policy", side_effect=Exception("db down")):
            cfg = cc.get_tool_exclusions()
        # fail-safe 全勾 -> excluded 仍=红线 5 件（安全可用态，两种语义殊途同归）
        assert sorted(cfg["excluded"]) == ["edit_file", "execute", "glob", "grep", "write_file"]
        assert cfg["locked"] == cc.W1_LOCKED_TOOLS

    def test_validate_params_未知名拒绝(self):
        err = cc.validate_params("tool_availability", {"allowed": ["not_a_tool_xyz"]})
        assert err and "未知工具名" in err

    def test_validate_params_locked拒绝(self):
        # 白名单语义：锁定件从 allowed 缺席 = 取消 = 拒绝
        universe = cc._w1_managed_universe()
        err = cc.validate_params("tool_availability", {"allowed": sorted(universe - {"task"})})
        assert err and "不可取消" in err

    def test_validate_params_合法通过(self):
        # 业务工具 execute_sql 可从 allowed 取消（🔴 双 Modal 由前端+risk_level 承担）
        universe = cc._w1_managed_universe()
        assert cc.validate_params("tool_availability", {"allowed": sorted(universe - {"execute_sql"})}) is None

    def test_seed含tool_availability能力(self):
        ids = [p["capability_id"] for p in CAPABILITY_POLICY_SEED]
        assert "tool_availability" in ids
        p = next(x for x in CAPABILITY_POLICY_SEED if x["capability_id"] == "tool_availability")
        assert p["risk_level"] == "red"
        # W-1 反转：种子 params 改 allowed 形态（全勾=勾选域）
        assert sorted(p["params"]["allowed"]) == sorted(cc.w1_default_allowed())
        assert "excluded" not in p["params"]
        assert p["title"] == "工具白名单"


class TestModelIdentifierEquiv:
    """问题一：自写模型标识/厂商函数与 deepagents._models 私有 helper 等价（不依赖私有小门）。"""

    def test_等价_model_name(self):
        from app.services.tupu_deepagent import _get_model_identifier, _get_model_provider
        from deepagents._models import get_model_identifier, get_model_provider

        class _S:
            model_name = "deepseek-v4-flash"

            def _get_ls_params(self):
                return {"ls_provider": "deepseek"}

        s = _S()
        assert (_get_model_identifier(s), _get_model_provider(s)) == (get_model_identifier(s), get_model_provider(s))

    def test_等价_model属性(self):
        from app.services.tupu_deepagent import _get_model_identifier
        from deepagents._models import get_model_identifier

        class _S2:
            model = "glm-4-flash"

        s = _S2()
        assert _get_model_identifier(s) == get_model_identifier(s)

    def test_无私有import(self):
        """tupu_deepagent 不再 import deepagents._models（升级稳定性）。"""
        import ast
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "app" / "services" / "tupu_deepagent.py"
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "deepagents._models" in node.module:
                pytest.fail(f"仍有私有 import: {node.module}")
