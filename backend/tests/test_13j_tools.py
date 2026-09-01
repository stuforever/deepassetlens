# -*- coding: utf-8 -*-
"""批13-J 收尾：工具黑名单配置化（问题二）测试。

覆盖：get_tool_exclusions 默认/fail-safe/locked 保护；validate_params 未知工具名拒绝/
locked 不可排除；seed 含 tool_availability 能力（定稿能力项名）；私有模型标识函数等价（问题一）。
"""
import pytest

from app.services import capability_config as cc
from app.core.init_db import CAPABILITY_POLICY_SEED


class TestToolExclusions:
    def test_默认5件(self):
        cfg = cc.get_tool_exclusions()
        assert cfg["excluded"] == ["grep", "glob", "write_file", "edit_file", "execute"]
        assert "read_file" in cfg["locked"] and "ls" in cfg["locked"]

    def test_locked永不可入excluded(self):
        # 即使配置里写 locked 件，也会被过滤掉
        from unittest.mock import patch
        with patch.object(cc, "get_policy", return_value={
            "capability_id": "tool_availability", "params": {"excluded": ["read_file", "grep"]}}):
            cfg = cc.get_tool_exclusions()
        assert "read_file" not in cfg["excluded"]
        assert "grep" in cfg["excluded"]

    def test_fail_safe配置异常回默认(self):
        from unittest.mock import patch
        with patch.object(cc, "get_policy", side_effect=Exception("db down")):
            cfg = cc.get_tool_exclusions()
        assert cfg["excluded"] == ["grep", "glob", "write_file", "edit_file", "execute"]

    def test_validate_params_未知名拒绝(self):
        err = cc.validate_params("tool_availability", {"excluded": ["not_a_tool_xyz"]})
        assert err and "未知工具名" in err

    def test_validate_params_locked拒绝(self):
        err = cc.validate_params("tool_availability", {"excluded": ["read_file"]})
        assert err and "物理锁定" in err

    def test_validate_params_合法通过(self):
        # 业务工具 execute_sql 在注册表内（受控工具）——可排除（🟡 确认级）
        assert cc.validate_params("tool_availability", {"excluded": ["execute_sql"]}) is None

    def test_seed含tool_availability能力(self):
        ids = [p["capability_id"] for p in CAPABILITY_POLICY_SEED]
        assert "tool_availability" in ids
        p = next(x for x in CAPABILITY_POLICY_SEED if x["capability_id"] == "tool_availability")
        assert p["risk_level"] == "red"
        assert p["params"]["excluded"] == ["grep", "glob", "write_file", "edit_file", "execute"]


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
