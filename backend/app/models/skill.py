from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
import uuid

from .base import Base


def _uuid_str():
    return str(uuid.uuid4())


class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String(36), primary_key=True, default=_uuid_str)
    skill_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    skill_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="draft", server_default="draft")

    current_version_id = Column(String(36), nullable=True, index=True)

    storage_path = Column(String(500), nullable=True)

    tags = Column(JSON, nullable=True, default=list)

    priority = Column(Integer, nullable=False, default=0, server_default="0")

    timeout = Column(Integer, nullable=False, default=30, server_default="30")
    retry_policy = Column(JSON, nullable=False, default=lambda: {"max_retries": 0, "retry_delay": 1})
    resource_limits = Column(JSON, nullable=False, default=lambda: {"memory_mb": 512, "timeout_seconds": 30})

    permissions = Column(JSON, nullable=False, default=lambda: {"network": True, "filesystem": False, "shell": False, "risk_level": "low", "allowed_env": []})

    app_type = Column(String(50), nullable=True)
    target_menu = Column(String(50), nullable=True)

    workspace_id = Column(String(36), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)

    __table_args__ = (
        Index('idx_skills_current_version', 'current_version_id'),
        Index('idx_skills_status_priority', 'status', 'priority'),
    )

    versions = relationship("SkillVersion", foreign_keys="SkillVersion.skill_id", backref="skill")
    exec_logs = relationship("SkillExecLog", foreign_keys="SkillExecLog.skill_id", backref="skill")


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    version_id = Column(String(36), primary_key=True, default=_uuid_str)
    skill_id = Column(String(36), ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(20), nullable=False)

    status = Column(String(20), nullable=False, default="draft", server_default="draft")

    input_schema = Column(JSON, nullable=False, default=lambda: {"type": "object", "properties": {}, "required": []})
    output_schema = Column(JSON, nullable=False, default=lambda: {"type": "object", "properties": {}})

    content = Column(JSON, nullable=False, default=dict)

    dependencies = Column(JSON, nullable=False, default=lambda: {"pip": [], "apt": [], "env_vars": {}})

    changelog = Column(Text, nullable=True)

    released_by = Column(String(100), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint('skill_id', 'version', name='uq_skill_version'),
        Index('idx_skill_versions_status', 'skill_id', 'status'),
    )

    exec_logs = relationship("SkillExecLog", backref="version", cascade="all, delete-orphan")


class SkillExecLog(Base):
    __tablename__ = "skill_exec_logs"

    log_id = Column(String(36), primary_key=True, default=_uuid_str)
    version_id = Column(String(36), ForeignKey("skill_versions.version_id", ondelete="SET NULL"), nullable=True, index=True)
    skill_id = Column(String(36), ForeignKey("skills.skill_id", ondelete="SET NULL"), nullable=True, index=True)

    execution_code = Column(String(100), nullable=False, index=True)

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)

    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    environment = Column(JSON, nullable=True)

    created_via = Column(String(20), nullable=False, default='manual')
    is_debug = Column(Boolean, nullable=False, default=False, server_default="0")
    stack_info = Column(JSON, nullable=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_exec_logs_status_time', 'status', 'started_at'),
        Index('idx_exec_logs_created_via_time', 'created_via', 'started_at'),
        CheckConstraint("created_via IN ('manual', 'agent', 'workflow', 'schedule', 'debug')", name='ck_exec_logs_created_via'),
    )


class SkillApiBinding(Base):
    __tablename__ = "skill_api_bindings"

    binding_id = Column(String(36), primary_key=True, default=_uuid_str)
    skill_id = Column(String(36), ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String(36), ForeignKey("skill_versions.version_id", ondelete="SET NULL"), nullable=True, index=True)

    api_code = Column(String(100), nullable=False, index=True)
    api_name = Column(String(255), nullable=False)
    api_type = Column(String(50), nullable=False, default="capability", server_default="capability")
    provider_type = Column(String(50), nullable=False, default="internal", server_default="internal")
    target_ref = Column(String(255), nullable=False)

    enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    timeout_seconds = Column(Integer, nullable=False, default=30, server_default="30")
    retry_policy = Column(JSON, nullable=False, default=lambda: {"max_retries": 0, "retry_delay": 1})
    auth_mode = Column(String(50), nullable=True)
    route_config = Column(JSON, nullable=True)
    remark = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint('skill_id', 'api_code', name='uq_skill_api_binding'),
        Index('idx_skill_api_bindings_enabled', 'skill_id', 'enabled'),
    )


class SkillType(Base):
    __tablename__ = "skill_types"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    type_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    sort_order = Column(Integer, nullable=False, default=0)
    ext = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
