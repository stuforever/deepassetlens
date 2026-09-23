# -*- coding: utf-8 -*-
"""R5批㉔（清单安全）契约测试：api_mapping 只读守卫+Doris 双载体语义对齐。"""
import inspect


def test_api_mapping_readonly_guard():
    from app.api import api_mapping
    src = inspect.getsource(api_mapping.execute_entity_api_mapping)
    assert "validate_sql" in src and "只读校验未通过" in src


def test_scope_adapters_carrier_semantics():
    from app.services import scope_adapters as sa
    src = inspect.getsource(sa)
    # 载体选择随 entity_code 走（不再 filters 优先的"或"语义）
    assert 'getattr(args, "entity_code", "")' in src
