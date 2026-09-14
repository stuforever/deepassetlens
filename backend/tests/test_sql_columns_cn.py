# -*- coding: utf-8 -*-
"""明细表头中英双显（2026-09-12 用户需求）——查询结果列名中文映射测试。

变异锚点（何种生产改动使其红）：
- test_columns_cn_maps_entity_schema：映射逻辑漏 cnName 取值/列对齐错位 → 红；
- test_columns_cn_degrades_on_db_error：降级契约破坏（异常外抛阻断执行主链）→ 红；
- test_execute_sql_attaches_columns_cn：_kg_execute_sql 成功分支忘挂 columns_cn → 红；
- test_payload_passthrough：载荷白名单漏透传 columns_cn → 红。
"""
import pytest

from app.core.database import SessionLocal
from app.models.base import Entity
from app.services import kg_action_handlers as kgh

_SCHEMA = [
    {"name": "col_a", "type": "string", "cnName": "测试列甲", "isPrimaryKey": True},
    {"name": "col_b", "type": "string", "cnName": "测试列乙"},
]


@pytest.fixture()
def seeded_entity():
    """临时实体（真库 seed，finally 删——对齐 test_cov_db_crud 真库纪律）。"""
    db = SessionLocal()
    try:
        concept_id = db.query(Entity).first().concept_id  # 复用既有概念满足 FK
        ent = Entity(
            concept_id=concept_id,
            entity_code="_t_cn_ent",
            entity_name="测试实体_表头双显",
            entity_en_name="_t_cn_ent_table",
            properties_schema=_SCHEMA,
            source_mode="physical_table",
        )
        db.add(ent)
        db.commit()
        yield ent
        db.delete(ent)
        db.commit()
    finally:
        db.close()


def test_columns_cn_maps_entity_schema(seeded_entity):
    """三字段匹配取 cnName；未匹配列返空串（前端回退单行现状）。"""
    out = kgh._build_columns_cn(["col_a", "col_b", "unknown_col"], seeded_entity.entity_code)
    assert out == ["测试列甲", "测试列乙", ""]


def test_columns_cn_degrades_on_db_error(monkeypatch):
    """行为契约：DB 任何异常 → 全空串列表，永不阻断执行主链。"""
    from app.core import database as _dbmod

    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(_dbmod, "SessionLocal", _boom)
    out = kgh._build_columns_cn(["col_a"], "whatever")
    assert out == [""]


def test_execute_sql_attaches_columns_cn(seeded_entity, monkeypatch):
    """_kg_execute_sql 成功分支挂 columns_cn（模式锁守卫/错误分支零变化）。"""
    from app.services import sql_executor as _se

    def _fake_build(data_source_id=None):
        def _exec(sql):
            # EXPLAIN 预检与完整执行共用假桩（无 error 键 → 预检放行）
            return {"columns": ["col_a", "col_b"], "rows": [[1, "x"]], "row_count": 1}
        return _exec

    monkeypatch.setattr(_se, "build_execute_query_fn", _fake_build)
    res = kgh._kg_execute_sql(
        {"sql": "SELECT col_a, col_b FROM _t_cn_ent_table LIMIT 10",
         "entity_code": seeded_entity.entity_code}, "12:00:00")
    assert not res.get("error"), res
    assert res["columns_cn"] == ["测试列甲", "测试列乙"]


def test_payload_passthrough():
    """done 帧载荷白名单透传 columns_cn（SSE 实时帧同字段，e2e 面验证）。

    导入方式注记：经 importlib 直载 delivery.py（纯函数模块），绕过 app.api.freeplan
    包 __init__——后者拉起 endpoint/全 FastAPI 栈，触发 Python 3.13+pydantic v2 导入期
    copy 递归悬挂（2026-09-12 实测：单跑过/组合挂，faulthandler 取证于 _union_schema
    →copy(annotation)）；与本特性代码无关，属环境性 flake 规避。"""
    import importlib.util
    import os
    _spec = importlib.util.spec_from_file_location(
        "delivery_standalone",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "app", "api", "freeplan", "delivery.py"))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    sr = {"columns": ["col_a"], "rows": [[1]], "row_count": 1, "columns_cn": ["测试列甲"]}
    payload = _mod.build_sql_result_payload(sr, "SELECT 1")
    assert payload["columns_cn"] == ["测试列甲"]
