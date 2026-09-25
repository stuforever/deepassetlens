# -*- coding: utf-8 -*-
"""权限重构 T3 单测：provider 表驱动验签 + 双桶 JWKS + ST 形态 token + sub 迁移。

计划：docs/superpowers/plans/2026-09-24-权限体系重构-实施计划.md 任务 3（v1.4）。
规格：docs/superpowers/specs/2026-09-24-权限体系重构-design.md §4.2/§4.3。

变异锚点：
- provider 路由删除 → Authentik 旧 token 失验（回滚门失效）
- 双桶缓存合并 → 双跑期 ST/Authentik 键互串（伪造签名通过）
- ST token 校验 iss/aud → ST access token（无 iss/aud）全被拒，登录死
- sub 迁移漏写 legacy_sub → 回滚 AUTH_PROVIDER=authentik 后迁移用户失联（🛠R3）
- group-claim 覆盖残留 → 双跑期管理页角色编辑被登录冲掉（🛠R6）
"""
import json
import sys
import uuid
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.core.auth as core_auth  # noqa: E402
from app.models.auth import ResourceACL, Role, User, UserRole  # noqa: E402


# ---------------------------------------------------------------------------
# 双 provider 测试键具（两把独立 RSA——桶隔离的物理前提）
# ---------------------------------------------------------------------------

def _make_key(kid: str):
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm.to_jwk(priv.public_key()))
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return priv, jwk


@pytest.fixture()
def dual(monkeypatch):
    """双 provider 测试环境：假 JWKS 源 + 独立缓存桶 + fetch 打点。"""
    ak_priv, ak_jwk = _make_key("ak-test-kid")
    st_priv, st_jwk = _make_key("st-test-kid")
    fetches = []

    def fake_fetch(url: str):
        fetches.append(url)
        if "authentik.test" in url:
            return [ak_jwk]
        return [st_jwk]

    monkeypatch.setattr(core_auth, "_PROVIDERS", {
        "authentik": {"jwks": "http://authentik.test/jwks",
                      "issuer": "http://authentik.test/o/tupu/", "aud": "tupu-aud"},
        "supertokens": {"jwks": "http://st.test/jwks", "issuer": None, "aud": None},
    })
    monkeypatch.setattr(core_auth, "_fetch_remote_jwks", fake_fetch)
    monkeypatch.setattr(
        core_auth, "_JWKS_CACHE",
        {p: {"keys": [], "fetched_at": 0.0, "ttl": 600} for p in core_auth._PROVIDERS},
    )
    return {"ak": ak_priv, "st": st_priv, "fetches": fetches}


def _sign(priv, claims):
    return jwt.encode(claims, priv, algorithm="RS256", headers={"kid": "x"})


def _sign_with_kid(priv, kid, claims):
    return jwt.encode(claims, priv, algorithm="RS256", headers={"kid": kid})


# ---------------------------------------------------------------------------
# 验签路由（design §4.2）
# ---------------------------------------------------------------------------

def test_authentik_token_still_verifies(dual):
    """provider=authentik 旧 token 可验（回归——回滚门 🛠R3 的验签半边）。"""
    token = _sign_with_kid(dual["ak"], "ak-test-kid", {
        "iss": "http://authentik.test/o/tupu/", "aud": "tupu-aud",
        "sub": "ak-sub-1", "preferred_username": "akuser", "exp": 4102444800,
    })
    claims = core_auth._verify_jwt(token)
    assert claims["sub"] == "ak-sub-1"
    assert any("authentik.test" in u for u in dual["fetches"])


def test_supertokens_token_verifies_without_iss_aud(dual):
    """ST 形态 JWT（无 iss/aud）走 ST 桶可验——验签+exp 即可（design §4.2）。"""
    token = _sign_with_kid(dual["st"], "st-test-kid", {
        "sub": "st-sub-1", "exp": 4102444800,
    })
    claims = core_auth._verify_jwt(token)
    assert claims["sub"] == "st-sub-1"
    assert any("st.test" in u for u in dual["fetches"])


def test_st_expired_token_rejected(dual):
    """ST 路径 exp 仍校验——过期 401。"""
    token = _sign_with_kid(dual["st"], "st-test-kid", {"sub": "st-sub-1", "exp": 1000000000})
    with pytest.raises(core_auth.HTTPException) as ei:
        core_auth._verify_jwt(token)
    assert ei.value.status_code == 401


def test_dual_bucket_cache_isolation(dual):
    """双桶缓存互不串（🛠 design §4.2：JWKS 缓存按 provider 分桶）。"""
    ak_token = _sign_with_kid(dual["ak"], "ak-test-kid", {
        "iss": "http://authentik.test/o/tupu/", "aud": "tupu-aud",
        "sub": "ak-sub-1", "exp": 4102444800,
    })
    st_token = _sign_with_kid(dual["st"], "st-test-kid", {"sub": "st-sub-1", "exp": 4102444800})
    assert core_auth._verify_jwt(ak_token)["sub"] == "ak-sub-1"
    assert core_auth._verify_jwt(st_token)["sub"] == "st-sub-1"
    urls = sorted(dual["fetches"])
    assert len([u for u in urls if "authentik.test" in u]) == 1
    assert len([u for u in urls if "st.test" in u]) == 1
    # 第二轮全走缓存：零新增 fetch
    core_auth._verify_jwt(ak_token)
    core_auth._verify_jwt(st_token)
    assert len(dual["fetches"]) == 2


def test_unknown_iss_fails_both(dual):
    """未知签发者两路皆败 → 401（fail-closed）。"""
    third_priv, _ = _make_key("third-kid")
    token = _sign_with_kid(third_priv, "third-kid", {
        "iss": "http://evil.test/", "aud": "whatever", "sub": "e1", "exp": 4102444800,
    })
    with pytest.raises(core_auth.HTTPException) as ei:
        core_auth._verify_jwt(token)
    assert ei.value.status_code == 401


# ---------------------------------------------------------------------------
# 用户镜像与 sub 迁移（design §4.3，🛠R3/R6/R12）
# ---------------------------------------------------------------------------

@pytest.fixture()
def sttest_cleanup():
    from app.core.database import SessionLocal
    from app.core.init_db import _ensure_auth_legacy_sub_column
    db = SessionLocal()
    _ensure_auth_legacy_sub_column(db)  # 测试进程独立跑时补回滚门列（幂等）

    def _clean():
        subs = [r[0] for r in db.query(User.sub).filter(User.sub.like("sttest_%")).all()]
        subs += [r[0] for r in db.query(User.sub).filter(User.username.like("sttest_%")).all()]
        from sqlalchemy import distinct
        role_subs = [r[0] for r in db.query(distinct(UserRole.user_sub)).all()]
        for s in set(subs) & set(role_subs):
            db.query(UserRole).filter(UserRole.user_sub == s).delete(synchronize_session=False)
        db.query(ResourceACL).filter(ResourceACL.principal_id.like("sttest_%")).delete(synchronize_session=False)
        db.query(UserRole).filter(UserRole.user_sub.like("sttest_%")).delete(synchronize_session=False)
        db.query(UserRole).filter(UserRole.role_code.like("sttest_%")).delete(synchronize_session=False)
        db.query(Role).filter(Role.code.like("sttest_%")).delete(synchronize_session=False)
        db.query(User).filter(User.sub.like("sttest_%")).delete(synchronize_session=False)
        db.query(User).filter(User.username.like("sttest_%")).delete(synchronize_session=False)
        db.commit()

    _clean()  # 前置清场（防上次运行残留毒化本次）
    yield db
    _clean()  # 后置清场
    db.close()


def test_upsert_sub_migration_writes_legacy_sub(sttest_cleanup):
    """迁移命中：同事务改 sub + 旧值写 legacy_sub + user_roles/ACL 引用同步（🛠R3/R12）。"""
    db = sttest_cleanup
    old_sub = f"sttest_old_{uuid.uuid4().hex[:8]}"
    db.add(User(sub=old_sub, username="sttest_mig", email="sttest_mig@x.local"))
    db.add(Role(code="sttest_r", name="r", is_system=False, default_permissions={}))
    db.add(UserRole(user_sub=old_sub, role_code="sttest_r", granted_by="seed"))
    db.add(ResourceACL(resource_type="skill", resource_id="s1", principal_type="user",
                       principal_id=old_sub, actions=["read"], granted_by="seed"))
    db.commit()
    db.expire_all()  # 与端点同型的独立提交语义——先过期身份图再进被测函数

    new_sub = f"sttest_{uuid.uuid4().hex[:12]}"
    claims = {"sub": new_sub, "email": "sttest_mig@x.local", "preferred_username": "sttest_mig"}
    user = core_auth._upsert_user(db, claims)

    assert user.sub == new_sub
    row = db.query(User).filter(User.sub == new_sub).one()
    assert row.legacy_sub == old_sub
    # 引用同步
    assert db.query(UserRole).filter(UserRole.user_sub == new_sub,
                                      UserRole.role_code == "sttest_r").count() == 1
    assert db.query(UserRole).filter(UserRole.user_sub == old_sub).count() == 0
    acl = db.query(ResourceACL).filter(ResourceACL.principal_type == "user",
                                       ResourceACL.principal_id == new_sub).all()
    assert len(acl) == 1 and acl[0].resource_id == "s1"
    assert db.query(ResourceACL).filter(ResourceACL.principal_id == old_sub).count() == 0


def test_upsert_email_duplicate_skips_migration(sttest_cleanup):
    """同 email 多行 → 跳过迁移+告警（🛠R12：email 非唯一键，不查重会静默错绑）。"""
    db = sttest_cleanup
    db.add(User(sub="sttest_dup_a", username="sttest_dup_a", email="sttest_dup@x.local"))
    db.add(User(sub="sttest_dup_b", username="sttest_dup_b", email="sttest_dup@x.local"))
    db.commit()

    new_sub = f"sttest_{uuid.uuid4().hex[:12]}"
    user = core_auth._upsert_user(db, {"sub": new_sub, "email": "sttest_dup@x.local",
                                       "preferred_username": "sttest_dup_new"})
    # 不动旧行、不产生第三行（新行=新建镜像而非错误绑定）
    assert db.query(User).filter(User.email == "sttest_dup@x.local").count() == 3
    assert db.query(User).filter(User.sub == new_sub).count() == 1
    assert all(u.legacy_sub is None for u in
               db.query(User).filter(User.email == "sttest_dup@x.local").all())


def test_upsert_no_group_claim_role_overwrite(sttest_cleanup):
    """双跑起停 group-claim 覆盖（🛠R6）：已有角色不被 groups claim 冲掉；无角色兜底 viewer。"""
    db = sttest_cleanup
    sub = "sttest_roles_keep"
    db.add(User(sub=sub, username="sttest_roles_keep"))
    db.add(Role(code="sttest_r", name="r", is_system=False, default_permissions={}))
    db.add(UserRole(user_sub=sub, role_code="sttest_r", granted_by="seed"))
    db.commit()

    # groups claim 指向 viewer 也不得覆盖既有角色
    user = core_auth._upsert_user(db, {"sub": sub, "preferred_username": "sttest_roles_keep",
                                       "groups": ["tupu-viewer"]})
    codes = {ur.role_code for ur in db.query(UserRole).filter(UserRole.user_sub == sub).all()}
    assert codes == {"sttest_r"}

    # 无任何角色的全新用户 → viewer 兜底（语义保留）
    fresh_sub = f"sttest_{uuid.uuid4().hex[:12]}"
    user2 = core_auth._upsert_user(db, {"sub": fresh_sub, "preferred_username": "sttest_fresh"})
    assert user2.roles == ["viewer"]


# ---------------------------------------------------------------------------
# T3 集成：活 ST 容器（localhost:13567）——登录→自研验签→续期→登出全链路
# ---------------------------------------------------------------------------

def _st_email():
    return f"sttest_live_{uuid.uuid4().hex[:8]}@x.local"


async def _st_cleanup_user(user_id: str):
    try:
        import app.api.auth as api_auth
        api_auth._ensure_st_init()
        from supertokens_python import asyncio as st_asyncio
        await st_asyncio.delete_user(user_id)
    except Exception:
        pass


def test_session_login_refresh_logout_live_st(sttest_cleanup):
    """验收 #2 骨架（T3 单测层）：sign_up→login→JWT 形态 access_token 经自研
    JWKS 验签→refresh 续期→logout 撤销。需活 tupu_supertokens 容器。"""
    import asyncio

    import app.api.auth as api_auth
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    api_auth._ensure_st_init()
    from supertokens_python import asyncio as st_asyncio
    from supertokens_python.recipe import emailpassword as ep_recipe
    from supertokens_python.recipe.emailpassword.interfaces import (
        EmailAlreadyExistsError,
        SignUpOkResult,
    )

    email = _st_email()
    created_user_ids = []

    def _cleanup():
        for uid in created_user_ids:
            asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
                _st_cleanup_user(uid))

    app = FastAPI()
    app.include_router(api_auth.router)

    with TestClient(app) as client:
        async def _signup():
            from supertokens_python.recipe.emailpassword import asyncio as ep_asyncio
            return await ep_asyncio.sign_up("", email, "Passw0rd!123")

        result = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_signup())
        assert isinstance(result, SignUpOkResult), result
        created_user_ids.append(result.user.id)

        # 登录
        r = client.post("/auth/session", json={"email": email, "password": "Passw0rd!123"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        at = data["access_token"]
        assert at and "sRefreshToken" in r.cookies
        assert data["user"]["roles"] == ["viewer"]  # 🛠R6 兜底语义

        # 关键实证：access token 是 JWT 且经自研双桶验签路径通过（JWKS 活端点）
        claims = core_auth._verify_jwt(at)
        assert claims["sub"] == created_user_ids[0]

        # 续期（🛠R2）
        r2 = client.post("/auth/session/refresh", json={"refresh_token": data["refresh_token"]})
        assert r2.status_code == 200, r2.text
        at2 = r2.json()["data"]["access_token"]
        assert core_auth._verify_jwt(at2)["sub"] == created_user_ids[0]

        # 登出撤销
        r3 = client.delete("/auth/session", headers={"Authorization": f"Bearer {at2}"})
        assert r3.status_code == 200, r3.text

    _cleanup()
