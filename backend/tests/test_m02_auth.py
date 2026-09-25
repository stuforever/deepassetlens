# -*- coding: utf-8 -*-
"""M02 单测：权限模型/路径分档/权限判定链/dev-login 双模式（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M02 spec §八验收标准锚定现有实现）。
"""

# ---------------------------------------------------------------------------
# 验收标准映射（M02 spec §八，2026-09-08 测试补全）：
# §八.1 ENABLE_AUTH=0 匿名贯穿+dev-login 可签发 → test_auth_off_anonymous_bypass
#       （本次补，本文件）+ test_dev_login_enabled_when_auth_off（本文件）
# §八.2 ENABLE_AUTH=1 token 校验族 → test_auth_on_missing_token_401 +
#       test_auth_on_forged_token_401 + test_auth_on_expired_token_401 +
#       test_auth_on_wrong_aud_401 + test_auth_on_valid_token_upsert_user
#       （均本次补，本文件；JWKS 外部件以本地 RSA 密钥桩化，RS256 验签全真）
# §八.3 权限链五级 → test_permission_chain_admin_bypass（一级）+
#       test_permission_chain_user_acl（二级）+ test_permission_chain_role_acl
#       （三级，本次补）+ test_permission_chain_role_wildcard（四级）+
#       test_permission_chain_role_default_template（五级）（本文件）
# §八.4 grant→撤销 全流程（含 expires_at 过期失效） → test_grant_revoke_full_flow +
#       test_grant_expires_at_expiry（均本次补，本文件）
# §八.5 SSE 长流在鉴权开启时不中断 → test_auth_on_sse_stream_passthrough
#       （本次补，本文件：中间件级多分片原样透传锚定）；
#       全链路「流式问答完整送达」映射引用 tests/ 下手工 e2e 脚本（e2e_api，非 pytest
#       收集、文件级引用非测试名，不新写 Playwright）
# §八.6 /mcp + X-Internal-Service: tupu-agent（ENABLE_AUTH=1） →
#       test_mcp_internal_header_access（本次补，本文件）+ test_path_classification
#       （本文件：三档白名单分档表）
# 既有测试保留（非 §八 主锚点）：test_models_importable_and_constraints（四表/uq 约束）、
#       test_dev_login_disabled_when_auth_enabled（dev-login 门 §九登记态）、
#       test_permission_chain_deny_default（默认拒绝兜底，不入五级序号）
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 任务 6（2026-09-08 测试补全）：spec §八 验收缺口——匿名贯穿/token 校验族/
# 三级 ACL/grant 全流程/SSE 透传/MCP 内部头
# ---------------------------------------------------------------------------

import time  # noqa: E402


def _make_token_kit(kid: str):
    """本地 RSA 密钥对 → (公开 JWK[假 JWKS], 私钥 PEM[本地签发 token])。
    spec §八.2 外部依赖件桩化纪律：Authentik JWKS 换成本地假件（monkeypatch
    _fetch_jwks），RS256 验签/kid 检索/iss·aud·exp 校验全部走真逻辑。"""
    import jwt as pyjwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = pyjwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwk, pem


def _sign_token(claims: dict, pem, kid: str) -> str:
    import jwt as pyjwt
    return pyjwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def _mw_app():
    """最小鉴权集成 app（生产同构）：add_middleware(AuthMiddleware) + 受保护路由
    + /mcp 探针路由；不走 main.app lifespan（避开重依赖启动钩子）。"""
    from fastapi import FastAPI, Request
    from app.core.auth import AuthMiddleware, get_current_user

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/v1/protected-thing")
    def protected(request: Request):
        u = get_current_user(request)
        return {"user": u.username, "roles": u.roles, "anon": u.is_anonymous}

    @app.get("/mcp/probe")
    def mcp_probe(request: Request):
        u = get_current_user(request)
        return {"user": u.username}

    return app


def test_auth_off_anonymous_bypass(monkeypatch):
    """§八.1：ENABLE_AUTH=0 全平台可用——无 token 直访非公开路径 200，匿名 admin
    user 贯穿（中间件注入 _ANONYMOUS 到 request.state.user）。
    变异锚点：短路分支删/匿名注入删 → 无 token 401 或 user 形态漂移红。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", False)
    from fastapi.testclient import TestClient
    client = TestClient(_mw_app())
    r = client.get("/api/v1/protected-thing")  # 无 Authorization 头
    assert r.status_code == 200
    d = r.json()
    assert d["user"] == "anonymous"
    assert d["roles"] == ["admin"]  # 关闭 auth 时按 admin 处理（向后兼容）
    assert d["anon"] is True


def test_auth_on_missing_token_401(monkeypatch):
    """§八.2：ENABLE_AUTH=1 无 token 访问非公开路径 → 401 JSON（{"detail": ...}）。
    变异锚点：缺 token 短路改放行/改 403/响应非 JSON → 形态断言红。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    from fastapi.testclient import TestClient
    client = TestClient(_mw_app())
    r = client.get("/api/v1/protected-thing")
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body and "Bearer" in body["detail"]


def test_auth_on_forged_token_401(monkeypatch):
    """§八.2：伪造 token → 401。两个伪造面：kid 撞库假签名（签名者私钥≠JWKS 公钥）
    + 非 JWT 乱串（头部解析即拒）。
    变异锚点：验签跳过（verify_signature=False）/kid 检索删 → 假签名 token 200 红。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    jwk, _ = _make_token_kit("m02-forged-kid")
    _, attacker_pem = _make_token_kit("m02-forged-kid")  # 另一对密钥，kid 撞库
    monkeypatch.setattr("app.core.auth._fetch_jwks", lambda provider: [jwk])  # T3：provider 分桶签名
    from fastapi.testclient import TestClient
    from app.core.auth import AUTHENTIK_ISSUER, AUTHENTIK_AUDIENCE
    client = TestClient(_mw_app())
    claims = {
        "sub": "m02-forged-sub", "preferred_username": "forger",
        "iss": AUTHENTIK_ISSUER, "aud": AUTHENTIK_AUDIENCE,
        "exp": int(time.time()) + 600,
    }
    tok = _sign_token(claims, attacker_pem, "m02-forged-kid")
    r = client.get("/api/v1/protected-thing", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert "验证失败" in r.json()["detail"]
    r2 = client.get("/api/v1/protected-thing", headers={"Authorization": "Bearer not.a.jwt"})
    assert r2.status_code == 401
    assert "无效 JWT 头部" in r2.json()["detail"]


def test_auth_on_expired_token_401(monkeypatch):
    """§八.2：过期 token（exp 早于当前）→ 401「Token 已过期」。
    变异锚点：verify_exp 关闭/exp 判定删 → 过期 token 200 红。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    jwk, pem = _make_token_kit("m02-exp-kid")
    monkeypatch.setattr("app.core.auth._fetch_jwks", lambda provider: [jwk])  # T3：provider 分桶签名
    from fastapi.testclient import TestClient
    from app.core.auth import AUTHENTIK_ISSUER, AUTHENTIK_AUDIENCE
    claims = {
        "sub": "m02-expired-sub", "preferred_username": "expired",
        "iss": AUTHENTIK_ISSUER, "aud": AUTHENTIK_AUDIENCE,
        "exp": int(time.time()) - 3600,
    }
    tok = _sign_token(claims, pem, "m02-exp-kid")
    client = TestClient(_mw_app())
    r = client.get("/api/v1/protected-thing", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert "过期" in r.json()["detail"]


def test_auth_on_wrong_aud_401(monkeypatch):
    """§八.2：aud 不匹配（他应用 token 串用）→ 401「audience 不匹配」。
    变异锚点：verify_aud 关闭/audience 比对删 → 跨应用 token 200 红。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    jwk, pem = _make_token_kit("m02-aud-kid")
    monkeypatch.setattr("app.core.auth._fetch_jwks", lambda provider: [jwk])  # T3：provider 分桶签名
    from fastapi.testclient import TestClient
    from app.core.auth import AUTHENTIK_ISSUER
    claims = {
        "sub": "m02-aud-sub", "preferred_username": "otherapp",
        "iss": AUTHENTIK_ISSUER, "aud": "other-app-client-id",
        "exp": int(time.time()) + 600,
    }
    tok = _sign_token(claims, pem, "m02-aud-kid")
    client = TestClient(_mw_app())
    r = client.get("/api/v1/protected-thing", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert "audience" in r.json()["detail"]


def test_auth_on_valid_token_upsert_user(monkeypatch, db):
    """§八.2：合法 token → 验签通过 + 用户 upsert（auth_users 落库，二次登录
    last_login_at 更新）+ group claim 映射角色（tupu-viewer→viewer）。
    变异锚点：_upsert_user 调用删/last_login_at 更新删 → 首登不落库或二登不更新红。"""
    from datetime import datetime
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    jwk, pem = _make_token_kit("m02-valid-kid")
    monkeypatch.setattr("app.core.auth._fetch_jwks", lambda provider: [jwk])  # T3：provider 分桶签名
    from fastapi.testclient import TestClient
    from app.core.auth import AUTHENTIK_ISSUER, AUTHENTIK_AUDIENCE
    from app.models.auth import User, UserRole
    sub = "m02-upsert-sub"
    # 预清理（幂等重跑）
    db.query(UserRole).filter(UserRole.user_sub == sub).delete()
    db.query(User).filter(User.sub == sub).delete()
    db.commit()
    claims = {
        "sub": sub, "preferred_username": "m02upsert",
        "email": "m02upsert@example.com", "groups": ["tupu-viewer"],
        "iss": AUTHENTIK_ISSUER, "aud": AUTHENTIK_AUDIENCE,
        "exp": int(time.time()) + 600, "iat": int(time.time()),
    }
    tok = _sign_token(claims, pem, "m02-valid-kid")
    client = TestClient(_mw_app())
    r = client.get("/api/v1/protected-thing", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    d = r.json()
    assert d["user"] == "m02upsert"
    assert d["roles"] == ["viewer"]  # GROUP_ROLE_MAP: tupu-viewer→viewer
    u = db.query(User).filter(User.sub == sub).first()
    assert u is not None, "合法 token 首登应 upsert auth_users 行"
    assert u.groups_snapshot == ["tupu-viewer"]
    # 回拨 last_login_at → 二次登录必须更新（严格大于回拨基线，确定性断言）
    u.last_login_at = datetime(2000, 1, 1)
    db.commit()
    r2 = client.get("/api/v1/protected-thing", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    db.expire_all()
    u2 = db.query(User).filter(User.sub == sub).first()
    assert u2.last_login_at is not None and u2.last_login_at > datetime(2001, 1, 1)
    # 清理
    db.query(UserRole).filter(UserRole.user_sub == sub).delete()
    db.query(User).filter(User.sub == sub).delete()
    db.commit()


def test_permission_chain_role_acl(db, clean_acl):
    """三级：角色级 ACL 命中具体资源（spec §四.3，用户任一角色即放行）。
    变异锚点：ACL 的 role 分支（principal_type=='role'）删 → 角色授权失效红；
    角色不匹配/动作不匹配仍应拒绝。"""
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="u5", username="u5", email=None, groups=[], roles=["operator"])
    db.add(ResourceACL(resource_type="m02test4", resource_id="r9",
                       principal_type="role", principal_id="operator",
                       actions=["execute"], expires_at=None))
    db.commit()
    assert check_permission(db, u, "m02test4", "execute", "r9") is True
    assert check_permission(db, u, "m02test4", "write", "r9") is False   # 动作不在授权集
    u_other = AuthUser(sub="u6", username="u6", email=None, groups=[], roles=["viewer"])
    assert check_permission(db, u_other, "m02test4", "execute", "r9") is False  # 角色不匹配


def test_grant_revoke_full_flow(monkeypatch, db, clean_acl):
    """§八.4：grant→撤销 全流程（API 级）：POST /grant 落库生效 → check_permission True
    → 四元组重复 grant 改写（updated=True 不重复建行）→ DELETE /grant/{id} 撤销
    → check_permission False + 行已删；撤销不存在的 grant → 404。
    变异锚点：撤销端点删改/撤销未删行 → 撤销后仍 True 红。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", False)  # §八.1 匿名 admin 贯穿放行管理端点
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.auth as api_auth
    from app.core.auth import AuthMiddleware, AuthUser, check_permission
    from app.models.auth import ResourceACL
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    app.include_router(api_auth.router, prefix="/api/v1")
    client = TestClient(app)
    payload = {
        "resource_type": "m02test-grant", "resource_id": "r1",
        "principal_type": "user", "principal_id": "m02-grant-user",
        "actions": ["read"],
    }
    r = client.post("/api/v1/auth/grant", json=payload)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["created"] is True
    gid = d["id"]
    u = AuthUser(sub="m02-grant-user", username="g", email=None, groups=[], roles=[])
    assert check_permission(db, u, "m02test-grant", "read", "r1") is True
    r2 = client.post("/api/v1/auth/grant", json={**payload, "actions": ["read", "write"]})
    assert r2.status_code == 200
    assert r2.json()["data"]["updated"] is True  # uq 四元组命中 → 改写不重复建行
    assert r2.json()["data"]["id"] == gid
    r3 = client.delete(f"/api/v1/auth/grant/{gid}")
    assert r3.status_code == 200
    assert r3.json()["data"]["revoked"] == gid
    # 撤销裁决复验用全新会话：db 会话在撤销前已开读事务（REPEATABLE READ 快照），
    # 同事务内看不到其他会话的 DELETE 提交，须新事务才能裁决「行已删」
    from app.core.database import SessionLocal
    with SessionLocal() as fresh:
        assert check_permission(fresh, u, "m02test-grant", "read", "r1") is False
        assert fresh.query(ResourceACL).filter(ResourceACL.resource_type == "m02test-grant").count() == 0
    r4 = client.delete(f"/api/v1/auth/grant/{gid}")
    assert r4.status_code == 404


def test_grant_expires_at_expiry(db, clean_acl):
    """§八.4：expires_at 过期失效——过期行仍在库但裁决不放行；未过期/无期限放行
    （expires_at 判定在查询时，spec §九 无清理 job 为登记态）。
    变异锚点：过期判定（expires_at < now: continue）删 → 过期授权仍 True 红。"""
    from datetime import datetime, timedelta
    from app.core.auth import AuthUser, check_permission
    u = AuthUser(sub="m02-exp-sub", username="e", email=None, groups=[], roles=[])
    now = datetime.utcnow()
    db.add(ResourceACL(resource_type="m02test-exp", resource_id="r_past",
                       principal_type="user", principal_id="m02-exp-sub",
                       actions=["read"], expires_at=now - timedelta(hours=1)))
    db.add(ResourceACL(resource_type="m02test-exp", resource_id="r_future",
                       principal_type="user", principal_id="m02-exp-sub",
                       actions=["read"], expires_at=now + timedelta(hours=1)))
    db.add(ResourceACL(resource_type="m02test-exp", resource_id="r_never",
                       principal_type="user", principal_id="m02-exp-sub",
                       actions=["read"], expires_at=None))
    db.commit()
    assert check_permission(db, u, "m02test-exp", "read", "r_past") is False    # 已过期失效
    assert check_permission(db, u, "m02test-exp", "read", "r_future") is True   # 未过期仍放行
    assert check_permission(db, u, "m02test-exp", "read", "r_never") is True    # 无期限仍放行


def test_auth_on_sse_stream_passthrough(monkeypatch):
    """§八.5：ENABLE_AUTH=1 合法 token 下，SSE 长流多分片经 AuthMiddleware 原样逐帧
    透传（纯 ASGI 直接透传 send：http.response.start + 分片 body + more_body 标志
    不合并不缓冲）——问数域流式问答依赖此性质（spec §二.2 禁改回 BaseHTTPMiddleware）。
    变异锚点：send 被封装缓冲/分片合并（如改回 BaseHTTPMiddleware）→ 4 个 body 帧
    被并帧或标志丢失红；流式路径被 401 误伤 → 帧形态为单条 401 JSON 红。"""
    import asyncio
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    jwk, pem = _make_token_kit("m02-sse-kid")
    monkeypatch.setattr("app.core.auth._fetch_jwks", lambda provider: [jwk])  # T3：provider 分桶签名
    from app.core.auth import AUTHENTIK_ISSUER, AUTHENTIK_AUDIENCE, AuthMiddleware, AuthUser

    def _fake_upsert(_db, _claims):
        return AuthUser(sub="m02-sse-sub", username="sse", email=None, groups=[], roles=[])
    monkeypatch.setattr("app.core.auth._upsert_user", _fake_upsert)  # 本测锚点=透传，upsert 已由 §八.2 真库测锚定

    claims = {
        "sub": "m02-sse-sub", "preferred_username": "sse",
        "iss": AUTHENTIK_ISSUER, "aud": AUTHENTIK_AUDIENCE,
        "exp": int(time.time()) + 600,
    }
    tok = _sign_token(claims, pem, "m02-sse-kid")

    async def stream_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")]})
        for i in range(3):
            await send({"type": "http.response.body",
                        "body": f"event: token\ndata: chunk-{i}\n\n".encode("utf-8"),
                        "more_body": True})
        await send({"type": "http.response.body", "body": b"data: [DONE]\n\n", "more_body": False})

    async def _receive():
        return {"type": "http.disconnect"}

    msgs = []

    async def _capture(msg):
        msgs.append(msg)

    scope = {
        "type": "http", "method": "GET",
        "path": "/api/data-intelligence/chat/freeplan/stream",
        "headers": [(b"authorization", f"Bearer {tok}".encode("latin-1"))],
    }
    asyncio.run(AuthMiddleware(stream_app)(scope, _receive, _capture))
    starts = [m for m in msgs if m["type"] == "http.response.start"]
    bodies = [m for m in msgs if m["type"] == "http.response.body"]
    assert len(starts) == 1 and starts[0]["status"] == 200
    assert any(v == b"text/event-stream" for _k, v in starts[0]["headers"])
    assert len(bodies) == 4, f"SSE 分片应逐帧透传（4 帧），实际 {len(bodies)} 帧（被合并/缓冲?）"
    assert [m["more_body"] for m in bodies] == [True, True, True, False]
    assert b"chunk-0" in bodies[0]["body"] and b"chunk-2" in bodies[2]["body"]
    assert b"[DONE]" in bodies[3]["body"]


def test_mcp_internal_header_access(monkeypatch):
    """§八.6（R1批 R#1 修订）：X-Internal-Service 兜底废除（header 客户端可控=提权面）——
    /mcp 仅接受 Bearer 内部 token（进程内自动生成，deepagent 客户端同源同读 env）；
    无 token 配置 → 一律 401（含伪造 header）。
    变异锚点：Bearer 分支删 → 内部 Agent 通道 401 断（M17/M08 断链）。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    monkeypatch.setenv("TUPU_INTERNAL_TOKEN", "test-internal-token")
    from fastapi.testclient import TestClient
    client = TestClient(_mw_app())
    r = client.get("/mcp/probe", headers={"Authorization": "Bearer test-internal-token"})
    assert r.status_code == 200
    assert r.json()["user"] == "anonymous"  # 内部身份走匿名上下文贯穿
    r2 = client.get("/mcp/probe")           # 无身份
    assert r2.status_code == 401
    r3 = client.get("/mcp/probe", headers={"X-Internal-Service": "tupu-agent"})  # 伪造 header（兜底已废）
    assert r3.status_code == 401
    r4 = client.get("/mcp/probe", headers={"Authorization": "Bearer wrong"})     # 错 token
    assert r4.status_code == 401

def test_mcp_internal_no_token_all_denied(monkeypatch):
    """R1批 R#1：TUPU_INTERNAL_TOKEN 未配置 → /mcp 一律 401（X-Internal-Service 兜底废除）。"""
    monkeypatch.setattr("app.core.auth.ENABLE_AUTH", True)
    monkeypatch.delenv("TUPU_INTERNAL_TOKEN", raising=False)
    from fastapi.testclient import TestClient
    client = TestClient(_mw_app())
    for headers in ({}, {"X-Internal-Service": "tupu-agent"}):
        r = client.get("/mcp/probe", headers=headers)
        assert r.status_code == 401
