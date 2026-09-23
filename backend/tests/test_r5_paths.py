# -*- coding: utf-8 -*-
"""R5批④（清单安全）契约测试：路径净化链。

- memory_slots：slot_key 字符集约束（防逃逸 /memory/L3）+ RAW_MD path 全 writer 校验+'..' 拒绝
- expert_paths：expert_id/user 路径段净化（穿越拒绝、空串拒绝、None→anonymous）
- expert_auth：require_expert 依赖形参名=expert_id（路径绑定，非客户端可控查询参数）
变异锚点：任一净化删除 → 对应测红。
"""
import inspect

import pytest
from fastapi import HTTPException


def _slot(**over):
    base = {"type": "L3_PROFILE", "slot": "s1", "slot_key": "k1", "read": "不注入"}
    base.update(over)
    return base


def test_slot_key_charset_constrained():
    from app.services.memory_slots import validate_slots
    with pytest.raises(ValueError):
        validate_slots([_slot(slot_key="../evil")], consolidator_on=True)
    with pytest.raises(ValueError):
        validate_slots([_slot(slot_key="a b")], consolidator_on=True)
    with pytest.raises(ValueError):
        validate_slots([_slot(slot_key=123)], consolidator_on=True)
    validate_slots([_slot(slot_key="ok-key_1")], consolidator_on=True)  # 合法直通


def test_raw_md_path_validated_for_all_writers():
    from app.services.memory_slots import validate_slots
    raw = {"type": "RAW_MD", "slot": "n1", "path": "/memory/u1/notes.md", "read": "不注入"}
    validate_slots([raw], consolidator_on=True)  # 合法（writer 非 agent_edit 也校验但通过）
    for bad in ("/etc/passwd", "/memory/u1/../expert/x.md", "/memory/AGENTS.md"):
        with pytest.raises(ValueError):
            validate_slots([{**raw, "path": bad}], consolidator_on=True)


def test_memory_roots_sanitized():
    from app.services.expert_paths import memory_expert_root, memory_user_root
    with pytest.raises(ValueError):
        memory_expert_root("../../etc")
    with pytest.raises(ValueError):
        memory_expert_root("wenshu/x")
    with pytest.raises(ValueError):
        memory_user_root("wenshu", "")          # 空串不再并入共享匿名树
    assert str(memory_user_root("wenshu", None)).replace("\\", "/").endswith("memory/wenshu/anonymous")
    assert str(memory_user_root("wenshu", "u1")).replace("\\", "/").endswith("memory/wenshu/u1")


def test_tree_root_valueerror_maps_400():
    from app.api.memory import _tree_root
    with pytest.raises(HTTPException) as ei:
        _tree_root("../../etc", "u1")
    assert ei.value.status_code == 400


def test_require_expert_dep_binds_path_param_name():
    from app.services.expert_auth import require_expert
    dep = require_expert("use")
    params = list(inspect.signature(dep).parameters)
    assert params == ["request", "expert_id"]  # 原名 expert_id_param=客户端可控查询参数
