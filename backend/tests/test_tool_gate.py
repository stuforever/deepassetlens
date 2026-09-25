# -*- coding: utf-8 -*-
"""权限重构 T5 单测：工具门控三态 + 专家交集 + 审计落痕 + 上线种子。

计划：docs/superpowers/plans/2026-09-24-权限体系重构-实施计划.md 任务 5（v1.4）。
规格：docs/superpowers/specs/2026-09-24-权限体系重构-design.md §6.1/§6.2。

变异锚点：
- EXEC 粗粒度误放行（role default tool:execute 覆盖执行类）→ 普通用户可跑 execute_sql（🛠R5 核心）
- fail-closed 缺失（未注册工具放行）→ 幽灵工具可调
- 审计 deny 缺行 → 验收 #7 不可对账
- 种子缺失 → 切换日普通用户问数一刀断（🛠R7）
- ENABLE_AUTH=0 过滤生效 → 测试基建/开发态全断（语义回归）
"""
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.auth as core_auth  # noqa: E402
from app.core.auth import AuthUser  # noqa: E402
from app.models.auth import ResourceACL, Role, User, UserRole  # noqa: E402
from app.services.permission_vocab import EXEC_TOOLS, READONLY_TOOLS, TOOL_REGISTRY  # noqa: E402
from app.services.tool_gate import (  # noqa: E402
    check_tool_call,
    filter_tools_for_user,
    seed_tool_permissions,
)


@pytest.fixture()
def tg_env(monkeypatch):
    """tgtest_* 行前后双清（live DB 纪律）+ ENABLE_AUTH=1（门控语义测试态）。"""
    import app.core.auth as core_auth_mod

    monkeypatch.setattr(core_auth_mod, "ENABLE_AUTH", True)
    from app.core.database import SessionLocal

    db = SessionLocal()

    def _clean():
        for r in db.query(Role).filter(Role.code.like("tgtest_%")).all():
            db.query(UserRole).filter(UserRole.role_code == r.code).delete(synchronize_session=False)
            db.query(ResourceACL).filter(
                ResourceACL.principal_type == "role",
                ResourceACL.principal_id == r.code).delete(synchronize_session=False)
            db.delete(r)
        for u in db.query(User).filter(User.username.like("tgtest_%")).all():
            db.query(UserRole).filter(UserRole.user_sub == u.sub).delete(synchronize_session=False)
            db.query(ResourceACL).filter(
                ResourceACL.principal_type == "user",
                ResourceACL.principal_id == u.sub).delete(synchronize_session=False)
            db.delete(u)
        db.commit()

    _clean()
    yield db
    _clean()
    db.close()


def _mkuser(db, name, role_codes):
    """建用户+角色（角色行缺则建，default_permissions 原样入行）。"""
    sub = f"tgtest_{uuid.uuid4().hex[:10]}"
    db.add(User(sub=sub, username=name, email=f"{name}@x.local"))
    for rc in role_codes:
        if not db.query(Role).filter(Role.code == rc).first():
            db.add(Role(code=rc, name=rc, is_system=False, default_permissions={}))
        db.add(UserRole(user_sub=sub, role_code=rc, granted_by="tgtest"))
    db.commit()
    roles = sorted({ur.role_code for ur in db.query(UserRole).filter(UserRole.user_sub == sub).all()})
    return AuthUser(sub=sub, username=name, email=f"{name}@x.local", groups=[], roles=roles)


def test_filter_excludes_exec_without_acl(tg_env):
    """无 EXEC ACL 的普通用户：过滤后不含 execute_sql；只读件保留（🛠R5/R1）。"""
    db = tg_env
    db.add(Role(code="tgtest_plain", name="plain", is_system=False,
                default_permissions={"tool": ["execute"]}))  # 只读粗粒度已授
    db.commit()
    user = _mkuser(db, "tgtest_u1", ["tgtest_plain"])
    allowed = filter_tools_for_user(db, user, TOOL_REGISTRY)
    assert "execute_sql" not in allowed
    assert "execute_doris_sql" not in allowed
    assert "search_kb" in allowed          # 🛠R1：只读件对全部角色可见
    assert "fetch_l1_l2_tree" in allowed
    assert len(allowed & EXEC_TOOLS) == 0


def test_filter_includes_exec_after_acl(tg_env):
    """显式 ACL 授予后 execute_sql 出现（允许/拒绝）。"""
    db = tg_env
    user = _mkuser(db, "tgtest_u2", ["tgtest_exec"])
    db.add(ResourceACL(resource_type="tool", resource_id="execute_sql",
                       principal_type="role", principal_id="tgtest_exec",
                       actions=["execute"], granted_by="tgtest"))
    db.commit()
    allowed = filter_tools_for_user(db, user, TOOL_REGISTRY)
    assert "execute_sql" in allowed
    assert "execute_doris_sql" not in allowed  # 只授了一件


def test_filter_drops_unregistered(tg_env):
    """fail-closed：未注册工具名直接剔除（🛠R1 幽灵工具防线）。"""
    db = tg_env
    db.add(Role(code="tgtest_plain", name="plain", is_system=False,
                default_permissions={"tool": ["execute"]}))
    db.commit()
    user = _mkuser(db, "tgtest_u3", ["tgtest_plain"])
    allowed = filter_tools_for_user(db, user, {"search_kb", "ghost_tool_xyz"})
    assert allowed == {"search_kb"}


def test_anonymous_admin_all_pass(tg_env, monkeypatch):
    """ENABLE_AUTH=0 匿名=admin 全通——测试基建零影响（语义回归锚）。"""
    import app.core.auth as core_auth_mod

    monkeypatch.setattr(core_auth_mod, "ENABLE_AUTH", False)
    db = tg_env
    from app.core.auth import _ANONYMOUS
    allowed = filter_tools_for_user(db, _ANONYMOUS, TOOL_REGISTRY)
    assert allowed == set(TOOL_REGISTRY)
    d = check_tool_call(db, _ANONYMOUS, "execute_sql", session_ctx=None)
    assert d.allowed is True


def test_check_exec_denied_by_role_default_alone(tg_env):
    """🛠R5 核心：role default tool:execute 不覆盖 EXEC 类——仅 ACL 放行。"""
    db = tg_env
    # 角色默认权限带 tool:execute（模拟种子后的只读粗粒度）
    db.add(Role(code="tgtest_ro", name="ro", is_system=False,
                default_permissions={"tool": ["execute"]}))
    db.commit()
    user = _mkuser(db, "tgtest_u4", ["tgtest_ro"])
    d = check_tool_call(db, user, "execute_sql", session_ctx=None)
    assert d.allowed is False
    d2 = check_tool_call(db, user, "search_kb", session_ctx=None)
    assert d2.allowed is True


def test_check_write_always_deny(tg_env):
    """写类恒拒（含 admin 语义外——admin 一票通过在 check 最前？design：写类恒拒
    优先于 ACL，admin 亦不例外——系统级面外）。"""
    db = tg_env
    user = _mkuser(db, "tgtest_u5", ["admin"])  # admin 也不放行写类
    d = check_tool_call(db, user, "write_file", session_ctx=None)
    assert d.allowed is False and "恒" in (d.reason or "") or d.allowed is False


def test_check_audit_rows(tg_env):
    """判定全量落审计（allow+deny 都有行——design §6.1 工具判定全量落）。"""
    from app.models.auth import AuthAuditLog

    db = tg_env
    db.add(Role(code="tgtest_audit", name="audit", is_system=False,
                default_permissions={"tool": ["execute"]}))
    db.commit()
    user = _mkuser(db, "tgtest_u6", ["tgtest_audit"])
    check_tool_call(db, user, "search_kb", session_ctx={"session_id": "s1", "turn_id": "t1"})
    check_tool_call(db, user, "execute_sql", session_ctx={"session_id": "s1", "turn_id": "t1"})
    rows = (db.query(AuthAuditLog)
            .filter(AuthAuditLog.user_sub == user.sub,
                    AuthAuditLog.resource_type == "tool")
            .all())
    decisions = {r.resource_id: r.decision for r in rows}
    assert decisions.get("search_kb") == "allow"
    assert decisions.get("execute_sql") == "deny"
    assert all(r.session_id == "s1" and r.turn_id == "t1" for r in rows)


def test_seed_tool_permissions(tg_env):
    """上线种子：只读粗粒度并入全角色默认；EXEC ACL 补非 viewer 角色；幂等（🛠R7）。"""
    db = tg_env
    db.add(Role(code="tgtest_op", name="op", is_system=False, default_permissions={}))
    db.commit()
    seed_tool_permissions(db)

    op = db.query(Role).filter(Role.code == "tgtest_op").one()
    vw = db.query(Role).filter(Role.code == "viewer").one()
    assert "tool" in (op.default_permissions or {}) and "execute" in op.default_permissions["tool"]
    assert "tool" in (vw.default_permissions or {}) and "execute" in vw.default_permissions["tool"]
    # EXEC ACL：operator 有、viewer 无
    op_acls = [r.resource_id for r in db.query(ResourceACL).filter(
        ResourceACL.principal_type == "role", ResourceACL.principal_id == "tgtest_op",
        ResourceACL.resource_type == "tool").all()]
    vw_acls = [r.resource_id for r in db.query(ResourceACL).filter(
        ResourceACL.principal_type == "role", ResourceACL.principal_id == "viewer",
        ResourceACL.resource_type == "tool").all()]
    assert set(op_acls) == set(EXEC_TOOLS)
    assert vw_acls == []
    # 幂等：重跑不翻倍
    before = db.query(ResourceACL).filter(ResourceACL.principal_id == "tgtest_op").count()
    seed_tool_permissions(db)
    after = db.query(ResourceACL).filter(ResourceACL.principal_id == "tgtest_op").count()
    assert before == after


def test_audit_endpoint_requires_auth_read(iam_client_like):
    """GET /iam/audit 挂 auth.read 守卫（design §5.2 表）。"""
    client, holder = iam_client_like
    holder["user"] = _mkuser_named(holder, ["tgtest_noperm"])
    resp = client.get("/api/v1/iam/audit")
    assert resp.status_code == 403
    holder["user"] = _mkuser_named(holder, ["admin"])
    resp = client.get("/api/v1/iam/audit")
    assert resp.status_code == 200


# ---- 复用 test_iam 的独立 app 形态（guard 矩阵同构） ----

@pytest.fixture()
def iam_client_like(monkeypatch):
    import app.api.iam as iam_mod
    import app.core.auth as core_auth_mod
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setattr(core_auth_mod, "ENABLE_AUTH", True)
    holder = {"user": None}

    def _fake(request):
        u = holder.get("user")
        if u is None:
            raise AssertionError("未设置用户")
        return u

    monkeypatch.setattr(core_auth_mod, "get_current_user", _fake)
    app = FastAPI()
    app.include_router(iam_mod.router, prefix="/api/v1/iam")
    with TestClient(app) as client:
        yield client, holder


def _mkuser_named(holder, persona_roles, sub=None):
    from app.core.auth import AuthUser
    return AuthUser(sub=sub or f"tgtest_{uuid.uuid4().hex[:8]}", username="tgtester",
                    email=None, groups=[], roles=persona_roles)
