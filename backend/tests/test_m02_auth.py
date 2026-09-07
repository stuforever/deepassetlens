# -*- coding: utf-8 -*-
"""M02 单测：权限模型/路径分档/权限判定链/dev-login 双模式（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M02 spec §八验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.auth import ResourceACL, Role, User, UserRole  # noqa: E402


@pytest.fixture()
def db():
    from app.core.database import SessionLocal
    d = SessionLocal()
    yield d
    d.close()


@pytest.fixture()
def clean_acl(db):
    """清掉 m02test 系列残留，测试后清理。"""
    yield
    db.query(ResourceACL).filter(ResourceACL.resource_type.like("m02test%")).delete()
    db.commit()


# ---------------------------------------------------------------------------
# 任务 1：权限模型 4 表
# ---------------------------------------------------------------------------

def test_models_importable_and_constraints():
    """四表名+uq_resource_acl 四元组唯一（spec §三，防重复授权）。
    变异锚点：uq_resource_acl 约束删除 → 重复授权不报错。"""
    assert User.__tablename__ == "auth_users"
    assert Role.__tablename__ == "auth_roles"
    assert UserRole.__tablename__ == "auth_user_roles"
    assert ResourceACL.__tablename__ == "auth_resource_acl"
    uq = [c.name for c in ResourceACL.__table__.constraints if c.__class__.__name__ == "UniqueConstraint"]
    assert "uq_resource_acl" in uq
    uq2 = [c.name for c in UserRole.__table__.constraints if c.__class__.__name__ == "UniqueConstraint"]
    assert "uq_user_role" in uq2


# ---------------------------------------------------------------------------
# 任务 3：路径分档（三档白名单）
# ---------------------------------------------------------------------------

def test_path_classification():
    """三档路径分档：公开/可选认证/MCP 内部（spec §二.4）。
    变异锚点：_PUBLIC_PATHS 误删 /auth/config → 前端 OIDC 配置被挡。"""
    from app.core.auth import _MCP_INTERNAL_PATHS, _OPTIONAL_AUTH_PATHS, _PUBLIC_PATHS, _path_matches
    assert _path_matches("/api/v1/auth/config", _PUBLIC_PATHS)
    assert _path_matches("/api/v1/auth/me", _OPTIONAL_AUTH_PATHS)
    assert _path_matches("/mcp/sse", _MCP_INTERNAL_PATHS)
    assert not _path_matches("/api/v1/skills", _PUBLIC_PATHS)
    assert not _path_matches("/api/v1/data-intelligence/ask", _PUBLIC_PATHS)


# ---------------------------------------------------------------------------
# 任务 4：权限判定链
# ---------------------------------------------------------------------------

def test_permission_chain_admin_bypass(db):
    """一级：admin 角色直通（spec §四.1）。
    变异锚点：is_admin() 直通分支删除 → 管理员被误拒。"""
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="admin-sub", username="admin", email=None, groups=[], roles=["admin"])
    assert check_permission(db, u, "skill", "read") is True
    assert check_permission(db, u, "skill", "execute") is True


def test_permission_chain_user_acl(db, clean_acl):
    """二级：用户级 ACL 命中（spec §四.2）。
    变异锚点：_has_permission_via_acl 的 user 分支删除 → 显式授权失效。"""
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="u1", username="u1", email=None, groups=[], roles=[])
    db.add(ResourceACL(resource_type="m02test", resource_id="r1",
                       principal_type="user", principal_id="u1",
                       actions=["read"], expires_at=None))
    db.commit()
    assert check_permission(db, u, "m02test", "read", "r1") is True
    assert check_permission(db, u, "m02test", "write", "r1") is False


def test_permission_chain_role_wildcard(db, clean_acl):
    """四级：角色级 '*' 通配（spec §四.4）。
    变异锚点：通配 resource_id='*' 分支删除 → 角色全量授权失效。"""
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="u2", username="u2", email=None, groups=[], roles=["viewer"])
    db.add(ResourceACL(resource_type="m02test2", resource_id="*",
                       principal_type="role", principal_id="viewer",
                       actions=["read"], expires_at=None))
    db.commit()
    assert check_permission(db, u, "m02test2", "read") is True


def test_permission_chain_deny_default(db):
    """全不命中 → False（默认拒绝）。
    变异锚点：默认拒绝分支删除 → 未授权误放行。"""
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="u3", username="u3", email=None, groups=[], roles=["viewer"])
    assert check_permission(db, u, "skill", "execute") is False  # viewer 默认无 execute


def test_permission_chain_role_default_template(db):
    """五级：角色默认权限模板（spec §四.5）——viewer 可 read。
    变异锚点：_has_permission_via_role_default 分支删除 → 角色模板失效。"""
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="u4", username="u4", email=None, groups=[], roles=["viewer"])
    assert check_permission(db, u, "skill", "read") is True   # viewer 默认可读技能
    assert check_permission(db, u, "workflow", "read") is True


# ---------------------------------------------------------------------------
# 任务 5：认证 API（dev-login 双模式）
# ---------------------------------------------------------------------------

def test_dev_login_disabled_when_auth_enabled(monkeypatch):
    """ENABLE_AUTH=1 时 dev-login 端点 403 自证（spec §九 dev-login 仅限开发）。
    变异锚点：dev-login 的 ENABLE_AUTH 判定删除 → 生产可直连签发（安全洞）。
    用独立 FastAPI app + 仅挂 auth 路由（prefix=/auth），避免 main.app lifespan。"""
    import app.api.auth as api_auth
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(api_auth, "ENABLE_AUTH", True)
    app = FastAPI()
    app.include_router(api_auth.router)
    with TestClient(app) as client:
        r = client.post("/auth/dev-login")
        assert r.status_code == 403


def test_dev_login_enabled_when_auth_off(monkeypatch):
    """ENABLE_AUTH=0 时 dev-login 可签发（spec §八.1 dev-login 可签发）。
    变异锚点：dev-login 返回删 token/改 403 → 开发工具链断。"""
    import app.api.auth as api_auth
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(api_auth, "ENABLE_AUTH", False)
    app = FastAPI()
    app.include_router(api_auth.router)
    with TestClient(app) as client:
        r = client.post("/auth/dev-login")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["token"].startswith("dev.") and d["user"]["roles"] == ["admin"]
