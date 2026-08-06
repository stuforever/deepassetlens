from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base


def _uuid_str():
    return str(uuid.uuid4())


class TaskQueue(Base):
    __tablename__ = "kg_task_queue"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    task_code = Column(String(100), unique=True, nullable=False, index=True)
    task_type = Column(String(50), nullable=False)
    task_ref_id = Column(String(36), nullable=False)

    status = Column(String(20), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=1, index=True)

    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)

    timeout_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_task_queue_status_priority', 'status', 'priority'),
    )


class DebugSession(Base):
    __tablename__ = "kg_debug_sessions"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    session_code = Column(String(100), unique=True, nullable=False, index=True)

    skill_id = Column(String(36), nullable=False)
    skill_code = Column(String(100), nullable=False)

    debug_mode = Column(String(20), nullable=False, default="step")

    input_payload = Column(JSON, nullable=True)

    breakpoints = Column(JSON, nullable=True)
    watch_variables = Column(JSON, nullable=True)

    execution_state = Column(JSON, nullable=True)
    variable_snapshots = Column(JSON, nullable=True)

    logs = Column(JSON, nullable=True)

    status = Column(String(20), nullable=False, default="active")
    current_step = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillSchedule(Base):
    __tablename__ = "kg_skill_schedules"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    schedule_code = Column(String(100), unique=True, nullable=False, index=True)
    skill_id = Column(String(36), nullable=False, index=True)
    skill_code = Column(String(100), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    input_payload = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    workspace_id = Column(String(36), nullable=True)

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(20), nullable=True)
    run_count = Column(Integer, nullable=False, default=0)
    fail_count = Column(Integer, nullable=False, default=0)

    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_skill_schedules_status', 'status', 'next_run_at'),
    )


class Conversation(Base):
    __tablename__ = "kg_conversations"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    conversation_code = Column(String(100), unique=True, nullable=False, index=True)
    scene_code = Column(String(100), nullable=True, index=True)
    page_code = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    conversation_meta = Column("metadata", JSON, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationMessage(Base):
    __tablename__ = "kg_conversation_messages"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    conversation_id = Column(String(36), ForeignKey("kg_conversations.id"), nullable=False, index=True)
    message_code = Column(String(100), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", backref="messages")


class AgentRun(Base):
    __tablename__ = "kg_agent_runs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_code = Column(String(100), unique=True, nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("kg_conversations.id"), nullable=True, index=True)
    scene_code = Column(String(100), nullable=True, index=True)
    page_code = Column(String(100), nullable=True, index=True)
    entry_type = Column(String(50), nullable=False, default="workflow")
    target_type = Column(String(50), nullable=False, default="workflow")
    target_code = Column(String(100), nullable=True, index=True)
    workflow_code = Column(String(100), nullable=True, index=True)
    workflow_execution_code = Column(String(100), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversation = relationship("Conversation", backref="runs")


class RunEvent(Base):
    __tablename__ = "kg_run_events"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_id = Column(String(36), ForeignKey("kg_agent_runs.id"), nullable=False, index=True)
    event_code = Column(String(100), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_order = Column(Integer, nullable=False)
    step_id = Column(String(100), nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("AgentRun", backref="events")

    __table_args__ = (
        Index('idx_run_events_run_order', 'run_id', 'event_order'),
    )
