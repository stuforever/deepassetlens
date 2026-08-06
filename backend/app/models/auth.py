"""
权限系统数据模型
================

四张表：
- users: Authentik sub 同步的用户镜像（不存密码，不存 email/group claim 直接来）
- roles: 角色定义（admin/operator/viewer + 自定义）
- user_roles: 用户-角色 N:N
- resource_acl: 资源级 ACL（resource_type + resource_id + principal_id + actions）

设计原则：
- 用户登录时若不存在则自动 upsert（来自 JWT claims）
- 角色基线：通过 Authentik group claim 映射 tupu-admin/tupu-operator/tupu-viewer
- resource_acl 让 admin 可以"把 skill_x 的 read 权限授给 user_y"做到资源级
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, ForeignKey, UniqueConstraint, Index,
    Boolean,
)
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "auth_users"

    # Authentik sub (UUID 字符串) 作主键，避免本地数字 id 冲突
    sub = Column(String(64), primary_key=True)
    username = Column(String(128), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # raw groups from JWT (用于 debug + 角色刷新)
    groups_snapshot = Column(JSON, nullable=True)


class Role(Base):
    __tablename__ = "auth_roles"

    code = Column(String(64), primary_key=True)  # admin / operator / viewer / custom_xxx
    name = Column(String(128), nullable=False)
    description = Column(String(500), nullable=True)
    # 默认全局权限模板：{"skill": ["read","write","execute"], "workflow": ["read"]}
    default_permissions = Column(JSON, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserRole(Base):
    __tablename__ = "auth_user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_sub = Column(String(64), ForeignKey("auth_users.sub", ondelete="CASCADE"), nullable=False)
    role_code = Column(String(64), ForeignKey("auth_roles.code", ondelete="CASCADE"), nullable=False)
    granted_by = Column(String(64), nullable=True)  # 授权人 sub
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_sub", "role_code", name="uq_user_role"),
        Index("ix_user_roles_user", "user_sub"),
    )


class ResourceACL(Base):
    """
    资源级 ACL：admin 可在 UI 上把"具体 skill / workflow / data_source"授权给指定 user。

    principal_type=user → principal_id 是 user.sub
    principal_type=role → principal_id 是 role.code (该角色全局生效)
    actions: ["read","write","execute","delete","admin"] 的子集
    """
    __tablename__ = "auth_resource_acl"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String(64), nullable=False)  # skill / workflow / data_source / metric / ...
    resource_id = Column(String(255), nullable=False)   # 具体资源标识；'*' 表示所有
    principal_type = Column(String(16), nullable=False) # user | role
    principal_id = Column(String(64), nullable=False)
    actions = Column(JSON, nullable=False)              # 列表
    granted_by = Column(String(64), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "resource_type", "resource_id", "principal_type", "principal_id",
            name="uq_resource_acl",
        ),
        Index("ix_acl_resource", "resource_type", "resource_id"),
        Index("ix_acl_principal", "principal_type", "principal_id"),
    )


__all__ = ["User", "Role", "UserRole", "ResourceACL"]
