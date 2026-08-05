"""
数据智能对话 - 秘书态（Secretary State）

设计要点
--------
- 秘书态 = LangGraph state = 整个对话的全景记忆
- 使用 pydantic BaseModel（非 dataclass），解决 InMemorySaver 序列化卡死
- 包含 4 个核心区块：
    1. 已确认项 (confirmed)：L1/L2/L2X/L3/L4/L4X + 字段 + 关系
    2. 任务快照 (task_snapshots)：每个任务的独立快照
    3. 反馈历史 (feedback_history)：用户评价历史
    4. 跨任务关联 (cross_task_links)：任务间的链路追踪
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# 已确认项
# --------------------------------------------------------------------------- #


class ConfirmedItems(BaseModel):
    """所有已确认项的容器"""

    # 主数据链
    L1: Optional[str] = None
    L2: Optional[str] = None
    L2_id: Optional[str] = None
    L2X: Optional[str] = None
    L2X_related: List[str] = Field(default_factory=list)

    # 业务链
    L3: Optional[str] = None
    L4: Optional[str] = None
    L4X: Optional[str] = None

    # 字段
    attributes: List[Dict[str, Any]] = Field(default_factory=list)

    # 跨实体属性（用户问的属性分布在多个实体表时）
    extra_entities: List[Dict[str, Any]] = Field(default_factory=list)

    # 关系
    relations: List[Dict[str, Any]] = Field(default_factory=list)

    # SQL 与结果
    assembled_sql: Optional[str] = None
    sql_execution_result: Optional[Dict[str, Any]] = None

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "L1": self.L1,
            "L2": self.L2,
            "L2_id": self.L2_id,
            "L2X": self.L2X,
            "L2X_related": self.L2X_related,
            "L3": self.L3,
            "L4": self.L4,
            "L4X": self.L4X,
            "attributes": self.attributes,
            "extra_entities": self.extra_entities,
            "relations": self.relations,
            "assembled_sql": self.assembled_sql,
            "sql_execution_result": self.sql_execution_result,
        }

    @property
    def entities(self) -> List[Dict[str, Any]]:
        """所有已锁实体（主表 + 关联实体 + 业务实体）"""
        ents: List[Dict[str, Any]] = []
        if self.L2X:
            ents.append({"entity_code": self.L2X, "entity_name": self.L2X, "is_main_table": True})
        for r in self.L2X_related:
            ents.append({"entity_code": r, "entity_name": r, "is_main_table": False})
        if self.L4X:
            ents.append({"entity_code": self.L4X, "entity_name": self.L4X, "is_main_table": True})
        return ents


# --------------------------------------------------------------------------- #
# 任务快照基类
# --------------------------------------------------------------------------- #


class TaskSnapshot(BaseModel):
    """所有任务快照的基类"""

    task_name: str = ""
    current_stage: str = "init"
    status: str = "in_progress"
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = {"arbitrary_types_allowed": True}

    def touch(self) -> None:
        self.last_updated = datetime.utcnow().isoformat()


# --------------------------------------------------------------------------- #
# 任务 2 快照：属性定位
# --------------------------------------------------------------------------- #


class AttributeLocationSnapshot(TaskSnapshot):
    """任务 2：属性定位快照"""

    mode: Optional[str] = None
    rewritten_query: str = ""

    vector_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    llm_inference: Optional[Dict[str, Any]] = None
    user_has_confirmed_mode_a: bool = False

    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    clarification: Optional[Dict[str, Any]] = None
    locked_attributes: List[Dict[str, Any]] = Field(default_factory=list)
    confirmed_by_user: bool = False


# --------------------------------------------------------------------------- #
# 秘书态
# --------------------------------------------------------------------------- #


class SecretaryState(BaseModel):
    """LangGraph 状态：数据智能对话秘书态（pydantic BaseModel，支持 InMemorySaver 序列化）"""

    # 用户输入与对话
    user_input: str = ""
    original_query: str = ""
    dialog_history: List[Dict[str, Any]] = Field(default_factory=list)

    # 已确认项
    confirmed: ConfirmedItems = Field(default_factory=ConfirmedItems)

    # 任务快照
    task_snapshots: Dict[str, Any] = Field(default_factory=dict)

    # 当前任务
    current_task: str = ""
    goal: str = "sql_assembly"

    # 完成旗标
    chain_locked: bool = False
    entity_locked: bool = False
    attribute_locked: bool = False
    relation_locked: bool = False
    sql_executed: bool = False

    # 已完成的任务列表
    completed_tasks: List[str] = Field(default_factory=list)

    # 任务结果
    task_result: Optional[Dict[str, Any]] = None
    task_result_summary: str = ""

    # 知识问答结果
    knowledge_answer: str = ""
    knowledge_sources: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_items: List[Dict[str, Any]] = Field(default_factory=list)

    # 最终答案（LLM 生成的 1./2./3. 编号长文，问数模式为空）
    final_answer: str = ""

    # 相似问题推荐（LLM 动态生成，↪ 红箭头列表）
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)

    # Think循环历史
    think_history: List[Dict[str, Any]] = Field(default_factory=list)

    # 反馈历史
    feedback_history: List[Dict[str, Any]] = Field(default_factory=list)

    # 跨任务关联
    cross_task_links: List[Dict[str, Any]] = Field(default_factory=list)

    # 澄清与中断
    pending_clarification: Optional[Dict[str, Any]] = None

    # 用户主动选择
    user_selection: List[Dict[str, Any]] = Field(default_factory=list)
    user_has_selected_fields: bool = False

    # 元数据
    session_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = {"arbitrary_types_allowed": True}

    # --------------------------------------------------------------------------- #
    # 工具方法
    # --------------------------------------------------------------------------- #

    def mark_task_done(self, task_name: str) -> None:
        if task_name not in self.completed_tasks:
            self.completed_tasks.append(task_name)
        snap = self.task_snapshots.get(task_name)
        if snap:
            snap.status = "done"
            snap.touch()
        self.last_updated = datetime.utcnow().isoformat()

    def get_snapshot(self, task_name: str) -> TaskSnapshot:
        if task_name not in self.task_snapshots:
            self.task_snapshots[task_name] = self._create_snapshot(task_name)
        return self.task_snapshots[task_name]

    def _create_snapshot(self, task_name: str) -> TaskSnapshot:
        from app.services.tasks.entity_location import EntityLocationSnapshot
        from app.services.tasks.relation_location import RelationLocationSnapshot
        from app.services.tasks.lineage_location import LineageLocationSnapshot
        from app.services.tasks.sql_assembly import SqlAssemblySnapshot
        from app.services.tasks.sql_execution import SqlExecutionSnapshot
        from app.services.tasks.exploration import ExplorationSnapshot

        creators: Dict[str, Any] = {
            "属性定位": AttributeLocationSnapshot,
            "实体定位": EntityLocationSnapshot,
            "关系定位": RelationLocationSnapshot,
            "溯源定位": LineageLocationSnapshot,
            "SQL 拼装": SqlAssemblySnapshot,
            "SQL 执行": SqlExecutionSnapshot,
            "探索": ExplorationSnapshot,
        }
        cls = creators.get(task_name, TaskSnapshot)
        return cls(task_name=task_name)

    def restore_snapshot_from_dict(self, task_name: str, snap_dict: Dict[str, Any]) -> TaskSnapshot:
        """从 dict 重建任务快照"""
        from app.services.tasks.entity_location import EntityLocationSnapshot
        cls_for_name = {
            "属性定位": AttributeLocationSnapshot,
            "实体定位": EntityLocationSnapshot,
        }
        cls = cls_for_name.get(task_name, TaskSnapshot)
        try:
            snap = cls(task_name=task_name)
        except Exception:
            snap = self._create_snapshot(task_name)
        for k, v in (snap_dict or {}).items():
            if hasattr(snap, k):
                try:
                    setattr(snap, k, v)
                except Exception:
                    pass
        return snap

    def is_all_flags_on(self) -> bool:
        return all(
            [
                self.chain_locked,
                self.entity_locked,
                self.attribute_locked,
                self.relation_locked,
                self.sql_executed,
            ]
        )

    def add_dialog(self, role: str, content: str) -> None:
        self.dialog_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


# --------------------------------------------------------------------------- #
# 序列化辅助
# --------------------------------------------------------------------------- #


def secretary_state_to_dict(state: SecretaryState) -> Dict[str, Any]:
    """序列化秘书态为 dict，便于 LangGraph 跨节点传递"""
    snaps_serialized: Dict[str, Any] = {}
    for name, snap in (state.task_snapshots or {}).items():
        if not snap:
            continue
        snap_d = {
            "task_name": snap.task_name,
            "current_stage": snap.current_stage,
            "status": snap.status,
            "started_at": snap.started_at,
            "last_updated": snap.last_updated,
        }
        if hasattr(snap, "model_fields"):
            for field_name in snap.model_fields:
                if field_name in ("task_name", "current_stage", "status",
                                  "started_at", "last_updated"):
                    continue
                snap_d[field_name] = getattr(snap, field_name, None)
        snaps_serialized[name] = snap_d

    return {
        "user_input": state.user_input,
        "original_query": state.original_query,
        "dialog_history": state.dialog_history,
        "confirmed": state.confirmed.to_dict(),
        "task_snapshots": snaps_serialized,
        "current_task": state.current_task,
        "goal": state.goal,
        "chain_locked": state.chain_locked,
        "entity_locked": state.entity_locked,
        "attribute_locked": state.attribute_locked,
        "relation_locked": state.relation_locked,
        "sql_executed": state.sql_executed,
        "completed_tasks": state.completed_tasks,
        "think_history": state.think_history,
        "feedback_history": state.feedback_history,
        "cross_task_links": state.cross_task_links,
        "pending_clarification": state.pending_clarification,
        "user_selection": state.user_selection,
        "user_has_selected_fields": state.user_has_selected_fields,
        "session_id": state.session_id,
        "task_result": state.task_result,
        "task_result_summary": state.task_result_summary,
        "knowledge_answer": state.knowledge_answer,
        "knowledge_sources": state.knowledge_sources,
        "knowledge_items": state.knowledge_items,
        "final_answer": state.final_answer,
        "recommendations": state.recommendations,
    }


__all__ = [
    "SecretaryState",
    "ConfirmedItems",
    "TaskSnapshot",
    "AttributeLocationSnapshot",
    "secretary_state_to_dict",
]
