# -*- coding: utf-8 -*-
"""批A3 覆盖补全：秘书态状态机（每条带变异锚点）。

覆盖模块：secretary_state（LangGraph 秘书态——跨节点传递的核心状态载体）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.secretary_state import (  # noqa: E402
    AttributeLocationSnapshot,
    ConfirmedItems,
    SecretaryState,
    TaskSnapshot,
    secretary_state_to_dict,
)


def test_confirmed_items_entities_aggregation():
    """entities 聚合：主表 L2X+关联 L2X_related(is_main_table=False)+业务 L4X 主表。
    变异锚点：L75-85 任一分支删 → 对应实体漏聚。"""
    c = ConfirmedItems(L2X="配电变压器", L2X_related=["调压设备"], L4X="业务活动")
    ents = c.entities
    assert [e["entity_code"] for e in ents] == ["配电变压器", "调压设备", "业务活动"]
    assert ents[0]["is_main_table"] is True and ents[1]["is_main_table"] is False
    assert ConfirmedItems().entities == []


def test_confirmed_items_to_dict_roundtrip_keys():
    """to_dict 十三键齐全（跨节点契约面）。变异锚点：任一键删 → 契约破坏即时暴露。"""
    d = ConfirmedItems(L1="主数据", assembled_sql="SELECT 1").to_dict()
    for k in ("L1", "L2", "L2_id", "L2X", "L2X_related", "L3", "L4", "L4X",
              "attributes", "extra_entities", "relations", "assembled_sql", "sql_execution_result"):
        assert k in d


def test_mark_task_done_dedup_and_snapshot_status():
    """mark_task_done：completed_tasks 去重追加+已有快照置 done+touch。
    变异锚点：L205-206 去重判定删 → 重复任务名堆积。"""
    st = SecretaryState()
    snap = st.get_snapshot("SQL 拼装")
    snap.current_stage = "assembling"
    st.mark_task_done("SQL 拼装")
    st.mark_task_done("SQL 拼装")  # 二次调用不重复
    assert st.completed_tasks == ["SQL 拼装"]
    assert snap.status == "done"
    assert st.get_snapshot("SQL 拼装").current_stage == "assembling"  # 快照状态保留


def test_get_snapshot_creates_by_task_name():
    """按任务名建对应快照类；未知任务名 → TaskSnapshot 兜底。
    变异锚点：L235 creators.get 兜底删 → 未知任务名 KeyError。"""
    st = SecretaryState()
    assert isinstance(st.get_snapshot("属性定位"), AttributeLocationSnapshot)
    unknown = st.get_snapshot("神秘任务")
    assert type(unknown) is TaskSnapshot and unknown.task_name == "神秘任务"
    # 二调返回同一实例（缓存语义）
    assert st.get_snapshot("神秘任务") is unknown


def test_restore_snapshot_from_dict_safe_setattr():
    """dict 重建：已知字段回填、未知字段安全跳过不炸。
    变异锚点：L251 hasattr 判定删 → 未知字段 setattr 崩（pydantic 严格模式）。"""
    st = SecretaryState()
    snap = st.restore_snapshot_from_dict("属性定位", {
        "current_stage": "locked", "mode": "vector",
        "ghost_field": "未知字段",  # 应安全跳过
    })
    assert snap.current_stage == "locked" and snap.mode == "vector"


def test_is_all_flags_on_requires_all_five():
    """五旗全开才 True（主路线推进判定）。变异锚点：任一旗标从判定列表删 → 部分开即误放行。"""
    st = SecretaryState()
    assert st.is_all_flags_on() is False
    st.chain_locked = st.entity_locked = st.attribute_locked = True
    assert st.is_all_flags_on() is False
    st.relation_locked = st.sql_executed = True
    assert st.is_all_flags_on() is True


def test_add_dialog_appends_with_timestamp():
    """add_dialog 追加 role/content/timestamp。变异锚点：L270-276 追加删 → 历史不增长。"""
    st = SecretaryState()
    st.add_dialog("user", "查客户")
    st.add_dialog("assistant", "好的")
    assert [d["role"] for d in st.dialog_history] == ["user", "assistant"]
    assert all(d["timestamp"] for d in st.dialog_history)


def test_state_to_dict_full_contract():
    """序列化契约：确认项/快照展开（排除基类五字段）/旗标/结果字段全在。
    变异锚点：L305-333 任一键删 → 跨节点传递丢字段。"""
    st = SecretaryState()
    st.user_input = "查客户"
    snap = st.get_snapshot("属性定位")
    snap.locked_attributes = [{"name": "电话"}]
    d = secretary_state_to_dict(st)
    for k in ("user_input", "dialog_history", "confirmed", "task_snapshots", "current_task",
              "goal", "chain_locked", "entity_locked", "completed_tasks", "session_id",
              "final_answer", "recommendations"):
        assert k in d, f"缺 {k}"
    snap_d = d["task_snapshots"]["属性定位"]
    assert snap_d["status"] == "in_progress"           # 基类字段保留
    assert snap_d["locked_attributes"] == [{"name": "电话"}]  # 子类字段展开
    assert "task_name" in snap_d and "last_updated" in snap_d


def test_state_defaults_and_last_updated_touch():
    """默认值契约：五旗默认 False+goal 默认 sql_assembly+时间戳自动填充。
    变异锚点：默认值改动 → 直通/场景既有行为面漂移。"""
    st = SecretaryState()
    assert st.goal == "sql_assembly" and st.current_task == ""
    assert all(not getattr(st, f) for f in ("chain_locked", "entity_locked", "attribute_locked",
                                            "relation_locked", "sql_executed"))
    assert st.created_at and st.last_updated
    before = st.last_updated
    st.mark_task_done("探索")
    assert st.last_updated >= before  # touch 语义
