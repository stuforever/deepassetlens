# -*- coding: utf-8 -*-
"""权限重构 T1 单测：权限词汇表 + 工具注册表单点 + 审计表模型。

计划：docs/superpowers/plans/2026-09-24-权限体系重构-实施计划.md 任务 1（v1.4）。
规格：docs/superpowers/specs/2026-09-24-权限体系重构-design.md §5.1 / §6.1。

变异锚点：
- 词汇表缺类型/动作 → 管理页矩阵编辑器少行少列、require_permission 校验漂移
- TOOL_REGISTRY 与 mcp_server 注册集漂移 → fail-closed 下已注册工具对所有人隐身（🛠R1）
- 审计表 decision 无约束 → 脏判定值落库，审计不可对账
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect as sa_inspect

from app.models.auth import AuthAuditLog
from app.services.permission_vocab import (
    EXEC_TOOLS,
    PERMISSION_VOCAB,
    READONLY_TOOLS,
    TOOL_REGISTRY,
    WRITE_TOOLS,
)


def test_vocab_resource_types():
    """词汇表 11 资源类型（design §5.1 原样）；tool 仅 execute（🛠R5 三态语义根基）。"""
    assert len(PERMISSION_VOCAB) == 11
    assert set(PERMISSION_VOCAB) == {
        "skill", "workflow", "data_source", "query_attribute", "query_entity",
        "metric", "expert", "sishu", "auth", "tool", "attachment",
    }
    assert PERMISSION_VOCAB["tool"] == ["execute"]
    # 动作词全部合法小写动单词（顺序按 design 原样，不做排序断言）
    for actions in PERMISSION_VOCAB.values():
        assert len(actions) == len(set(actions))
        assert all(a in {"read", "write", "execute", "delete", "use", "manage", "approval"} for a in actions)


def test_tool_registry_matches_mcp_server():
    """TOOL_REGISTRY 全集 = mcp_server 实际注册集（🛠R1：fail-closed 防已注册工具隐身）。

    W5/T8a 回挂教学 11 件前注册集=19 件；本测试在 T8a 后同步改为 30 件口径。
    """
    from app.mcp_server import mcp

    registered = {t.name for t in asyncio.run(mcp.list_tools())}
    assert TOOL_REGISTRY == registered
    assert len(TOOL_REGISTRY) == 30  # T8a：19 + 教学读 7 + 教学写 4
    assert "search_kb" in TOOL_REGISTRY          # 🛠R1：不在 GENERIC 但已注册——必须入册
    assert "read_file" not in TOOL_REGISTRY      # 框架工具面外（design §6.1 R14）
    # 三分类划分：READONLY ∪ EXEC == REGISTRY（WRITE 是系统级面外集合，不在注册表）
    assert not (READONLY_TOOLS & EXEC_TOOLS)
    assert READONLY_TOOLS | EXEC_TOOLS == TOOL_REGISTRY
    assert len(READONLY_TOOLS) == 22
    assert len(EXEC_TOOLS) == 8
    assert {"execute_sql", "execute_api_sql", "execute_entity_api", "execute_doris_sql"} < EXEC_TOOLS
    # T8a：教学 11 件全入册（读 7 在只读、写 4 在 EXEC）
    from app.services.permission_vocab import TUTOR_EXEC_TOOLS
    assert TUTOR_EXEC_TOOLS <= EXEC_TOOLS
    for n in ("fsrs_due", "mastery_query", "wrong_question_query", "select_exercises",
              "analyze_wrong_questions", "grade_answer", "generate_practice"):
        assert n in READONLY_TOOLS, n


def test_write_tools_align_with_engine_forbidden():
    """WRITE 恒拒 6 件 = query_contract.ABSOLUTE_FORBIDDEN_TOOLS（design §8.4 WRITE=6）。

    同时钉住引擎侧 DATA_TOOLS ⊆ 注册表——v1.4 实施裁定：DATA_TOOLS 语义是引擎
    一致性判定、T8a 后 EXEC(8)≠DATA(4)，故 query_contract 常量原地保留不 import
    vocab（反向才绑权限口径），漂移由本断言把关。
    """
    from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS, DATA_TOOLS

    assert WRITE_TOOLS == ABSOLUTE_FORBIDDEN_TOOLS
    assert len(WRITE_TOOLS) == 6
    assert DATA_TOOLS <= TOOL_REGISTRY
    # T8a：EXEC(8) 与引擎 DATA_TOOLS(4) 有意分叉——DATA ⊂ EXEC（写 4 件非引擎数据工具）
    assert DATA_TOOLS < EXEC_TOOLS


def test_auth_audit_log_model():
    """审计表 auth_audit_log：decision 三值 CheckConstraint（design §6.1 列清单）。"""
    assert AuthAuditLog.__tablename__ == "auth_audit_log"
    cols = {c.name for c in sa_inspect(AuthAuditLog).columns}
    assert {"id", "ts", "user_sub", "resource_type", "resource_id",
            "action", "decision", "reason", "session_id", "turn_id"} <= cols
    constraints = [c for c in AuthAuditLog.__table_args__] if isinstance(
        AuthAuditLog.__table_args__, tuple) else [AuthAuditLog.__table_args__]
    ck = [c for c in constraints if c.__class__.__name__ == "CheckConstraint"]
    assert any(all(v in str(c.sqltext) for v in ("decision", "allow", "deny", "approval"))
               for c in ck), ck


# ---------------------------------------------------------------------------
# 任务 2：iam 管理面 9 端点（design §5.2）
# ---------------------------------------------------------------------------

import uuid as _uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.models.auth import Role as RoleM  # noqa: E402
from app.models.auth import User as UserM  # noqa: E402
from app.models.auth import UserRole as UserRoleM  # noqa: E402


@pytest.fixture()
def iam_env(monkeypatch):
    """iam 路由独立 app：ENABLE_AUTH=1 + get_current_user 可换装（守卫矩阵三人格）。

    人格语义对齐计划 2.1：admin 全通 / 仅 auth.read 者 GET 过写 403 / 无授权
    （student2 语义）全 403。DB 行角色默认授权语义（验收 #4 地基）由
    test_role_default_permissions_db_authoritative 单独钉。
    """
    import app.core.auth as core_auth
    import app.api.iam as iam_mod
    from app.core.database import SessionLocal, engine
    from app.models.auth import AuthAuditLog

    # 测试基建：审计表随 T1 落模型，live DB 建表走后端启动 create_all——
    # 测试进程独立跑时按需补建（checkfirst 幂等）。
    AuthAuditLog.__table__.create(bind=engine, checkfirst=True)

    monkeypatch.setattr(core_auth, "ENABLE_AUTH", True)
    holder = {"user": None}

    def _fake_current_user(request):
        u = holder.get("user")
        if u is None:
            raise AssertionError("测试未设置当前用户")
        return u

    monkeypatch.setattr(core_auth, "get_current_user", _fake_current_user)

    app = FastAPI()
    app.include_router(iam_mod.router, prefix="/api/v1/iam")  # 与 main.py 挂载同口径
    with TestClient(app) as client:
        yield {"client": client, "holder": holder, "db": SessionLocal()}


@pytest.fixture()
def iam_cleanup(iam_env):
    """iamtest_* 行清理（live DB 纪律同 m02——先登记后跑，测后清场）。"""
    db = iam_env["db"]
    yield
    UserRoleM  # noqa: B018 —— mapper 确认
    # sub 前缀清理 + 建号面残留（POST /users 用随机 uuid 作 sub，按用户名兜底捞）
    orphan_subs = [u.sub for u in db.query(UserM).filter(UserM.username.like("iamtest_%")).all()]
    all_subs = {r[0] for r in db.query(UserRoleM.user_sub).filter(UserRoleM.user_sub.like("iamtest_%")).all()}
    all_subs.update(orphan_subs)
    if all_subs:
        db.query(UserRoleM).filter(UserRoleM.user_sub.in_(all_subs)).delete(synchronize_session=False)
    db.query(UserM).filter(UserM.username.like("iamtest_%")).delete(synchronize_session=False)
    db.query(UserM).filter(UserM.sub.like("iamtest_%")).delete(synchronize_session=False)
    db.query(RoleM).filter(RoleM.code.like("iamtest_%")).delete(synchronize_session=False)
    from app.models.auth import AuthAuditLog
    db.query(AuthAuditLog).filter(AuthAuditLog.user_sub.like("iamtest_%")).delete(synchronize_session=False)
    db.commit()


def _user(persona_roles, sub="iamtest_u1"):
    from app.core.auth import AuthUser
    return AuthUser(sub=sub, username="iamtester", email=None, groups=[], roles=persona_roles)


def test_iam_guard_matrix(iam_env, iam_cleanup):
    """admin 全通 / auth.read 人格 GET 过写 403 / 无授权 403（student2 语义）。"""
    c = iam_env["client"]
    iam_env["holder"]["user"] = _user(["iamtest_admin_ro"])  # 无 auth 权限人格
    assert c.get("/api/v1/iam/vocab").status_code == 403

    iam_env["holder"]["user"] = _user(["admin"])
    assert c.get("/api/v1/iam/vocab").status_code == 200
    body = c.get("/api/v1/iam/vocab").json()["data"]
    assert body == PERMISSION_VOCAB

    # auth.read-only 人格：经 DB 行默认授权（iamtest_reader 角色带 auth:read）
    db = iam_env["db"]
    db.add(RoleM(code="iamtest_reader", name="读-only", is_system=False,
                 default_permissions={"auth": ["read"]}))
    db.commit()
    iam_env["holder"]["user"] = _user(["iamtest_reader"])
    assert c.get("/api/v1/iam/vocab").status_code == 200
    assert c.get("/api/v1/iam/users").status_code == 200
    assert c.post("/api/v1/iam/roles", json={"code": "iamtest_x", "name": "x"}).status_code == 403


def test_iam_users_crud_flow(iam_env, iam_cleanup):
    """建号（T2 本地建号面，T3 换 ST SDK）→ 列表含角色/last_login → 启停 → 角色整体替换。"""
    c = iam_env["client"]
    iam_env["holder"]["user"] = _user(["admin"], sub="iamtest_admin")

    db = iam_env["db"]
    db.add(RoleM(code="iamtest_r1", name="r1", is_system=False, default_permissions={}))
    db.add(RoleM(code="iamtest_r2", name="r2", is_system=False, default_permissions={}))
    db.commit()

    r = c.post("/api/v1/iam/users", json={
        "username": "iamtest_new", "email": "iamtest_new@x.local",
        "display_name": "测试号", "roles": ["iamtest_r1"],
    })
    assert r.status_code == 200, r.text
    sub = r.json()["data"]["sub"]

    # 角色整体替换语义：初始 1 角色 → 换成 2 → user_roles 恰 2 行 → 再换 0 → 恰 0 行
    r = c.put(f"/api/v1/iam/users/{sub}/roles", json={"roles": ["iamtest_r1", "iamtest_r2"]})
    assert r.status_code == 200, r.text
    rows = db.query(UserRoleM).filter(UserRoleM.user_sub == sub).all()
    assert {x.role_code for x in rows} == {"iamtest_r1", "iamtest_r2"}
    assert all(x.granted_by == "iamtest_admin" for x in rows)

    r = c.put(f"/api/v1/iam/users/{sub}/roles", json={"roles": []})
    assert r.status_code == 200
    db.commit()  # 结束本会话 REPEATABLE READ 快照——端点走独立会话提交，必须重开读
    assert db.query(UserRoleM).filter(UserRoleM.user_sub == sub).count() == 0

    # 未知角色 → 400
    assert c.put(f"/api/v1/iam/users/{sub}/roles", json={"roles": ["no_such_role"]}).status_code == 400

    # PATCH 启停 + 列表字段
    assert c.patch(f"/api/v1/iam/users/{sub}", json={"is_active": False}).status_code == 200
    r = c.get("/api/v1/iam/users", params={"kw": "iamtest_new"})
    items = r.json()["data"]["items"]
    row = next(x for x in items if x["sub"] == sub)
    assert row["is_active"] is False and row["display_name"] == "测试号"
    assert "roles" in row and "last_login_at" in row


def test_iam_roles_flow(iam_env, iam_cleanup):
    """建自定义角色 → 重名/大写拒 → PATCH 默认权限 → system 拒改名拒删 → 有成员 409。"""
    c = iam_env["client"]
    iam_env["holder"]["user"] = _user(["admin"], sub="iamtest_admin")

    assert c.post("/api/v1/iam/roles", json={
        "code": "iamtest_r1", "name": "角色一", "description": "d",
    }).status_code == 200
    # 重名
    assert c.post("/api/v1/iam/roles", json={"code": "iamtest_r1", "name": "dup"}).status_code in (400, 409)
    # code 口径：小写字母数字下划线
    assert c.post("/api/v1/iam/roles", json={"code": "BadCode", "name": "x"}).status_code == 422

    # PATCH：自定义可改名；system 只许改 default_permissions
    assert c.patch("/api/v1/iam/roles/iamtest_r1", json={
        "default_permissions": {"auth": ["read"]},
    }).status_code == 200
    db = iam_env["db"]
    db.add(RoleM(code="iamtest_sys", name="系统样例", is_system=True, default_permissions={}))
    db.commit()
    assert c.patch("/api/v1/iam/roles/iamtest_sys", json={"name": "改名"}).status_code in (400, 409)
    assert c.delete("/api/v1/iam/roles/iamtest_sys").status_code in (400, 403, 409)

    # 有成员 409
    u = UserM(sub="iamtest_u2", username="iamtester2")
    db.add(u)
    db.add(UserRoleM(user_sub="iamtest_u2", role_code="iamtest_r1", granted_by="seed"))
    db.commit()
    assert c.delete("/api/v1/iam/roles/iamtest_r1").status_code == 409

    # 空成员自定义角色可删
    db.add(RoleM(code="iamtest_r3", name="r3", is_system=False, default_permissions={}))
    db.commit()
    assert c.delete("/api/v1/iam/roles/iamtest_r3").status_code == 200

    # 列表含成员数
    r = c.get("/api/v1/iam/roles")
    row = next(x for x in r.json()["data"] if x["code"] == "iamtest_r1")
    assert row["member_count"] == 1 and row["is_system"] is False


def test_role_default_permissions_db_authoritative(iam_env, iam_cleanup):
    """DB 行 default_permissions 参与判定（验收 #4 地基；🛠 §6.1 tool:execute 前提）。"""
    c = iam_env["client"]
    db = iam_env["db"]
    db.add(RoleM(code="iamtest_reader", name="读-only", is_system=False,
                 default_permissions={"auth": ["read"]}))
    db.commit()
    iam_env["holder"]["user"] = _user(["iamtest_reader"])
    assert c.get("/api/v1/iam/vocab").status_code == 200  # iamtest_reader DB 行 auth:read 生效
    assert c.post("/api/v1/iam/roles", json={"code": "iamtest_x2", "name": "x"}).status_code == 403
