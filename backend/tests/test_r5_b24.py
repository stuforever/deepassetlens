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


def test_contract_trace_roundtrip():
    """批⑥：契约轨迹落库/查询回路（thread_id 主键 upsert 语义）。"""
    import time as _time

    from app.core.database import SessionLocal, engine
    from app.models.contract_trace import ContractTrace
    from app.services.contract_trace import get_contract_trace, record_contract_trace

    ContractTrace.__table__.create(bind=engine, checkfirst=True)  # 后端未重启时补建
    tid = "ct-test-roundtrip"
    record_contract_trace(tid, "wenshu", {"route_type": "scenario", "skill_id": "demo"})
    trace = None
    for _ in range(20):  # 写入是 fire-and-forget 线程——轮询等待
        trace = get_contract_trace(tid)
        if trace is not None:
            break
        _time.sleep(0.2)
    assert trace is not None and trace["expert_id"] == "wenshu"
    assert trace["contract"]["skill_id"] == "demo"
    record_contract_trace(tid, "wenshu", {"route_type": "generic"})  # upsert 覆盖
    for _ in range(20):
        if (get_contract_trace(tid) or {}).get("contract", {}).get("route_type") == "generic":
            break
        _time.sleep(0.2)
    assert get_contract_trace(tid)["contract"]["route_type"] == "generic"
    assert get_contract_trace("no-such-thread") is None
