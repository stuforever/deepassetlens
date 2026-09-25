# -*- coding: utf-8 -*-
"""T3.6 迁移保底：首个 SuperTokens 管理员直写 user_roles(admin)（design §9 风险表——
require_permission("auth","write") 自锁的解法）。

用法（backend/ 目录下）：
    python scripts/_st_bootstrap_admin.py <email> <password> [username]

行为：
1. 在 SuperTokens Core 里 sign_up 该邮箱（已存在则复用）；
2. 本地 auth_users 镜像行 upsert（sub = ST user id）；
3. 直写 auth_user_roles(admin)（幂等——已挂 admin 则跳过）。

需要 tupu_supertokens 容器在线（SUPERTOKENS_CONNECTION_URI/SUPERTOKENS_API_KEY env
或 .env.infra）。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.api.auth as api_auth  # noqa: E402  — 触发 .env/.env.infra 装载 + ST init 帮手


async def _signup_or_get(email: str, password: str) -> str:
    api_auth._ensure_st_init()
    from supertokens_python.recipe.emailpassword import asyncio as ep_asyncio
    from supertokens_python.recipe.emailpassword.interfaces import (
        EmailAlreadyExistsError,
        SignUpOkResult,
    )

    result = await ep_asyncio.sign_up("", email, password)
    if isinstance(result, SignUpOkResult):
        return result.user.id
    if isinstance(result, EmailAlreadyExistsError):
        users = await _get_user_by_email(email)
        if users:
            return users[0].id
        raise SystemExit(f"[bootstrap] 邮箱已在身份层但取回用户失败：{email}")
    raise SystemExit(f"[bootstrap] sign_up 未预期结果：{result}")


async def _get_user_by_email(email: str):
    from supertokens_python import asyncio as st_asyncio

    users = await st_asyncio.get_users_newest_first_with_public_tenant_info(
        None, None, "emailpassword", email
    )
    return users


def _upsert_mirror(sub: str, email: str, username: str) -> None:
    from app.core.database import SessionLocal
    from app.models.auth import User

    db = SessionLocal()
    try:
        row = db.query(User).filter(User.sub == sub).first()
        if row is None:
            db.add(User(sub=sub, username=username, email=email, is_active=True,
                        last_login_at=None))
            action = "created"
        else:
            row.email = email
            action = "exists"
        db.commit()
        print(f"[bootstrap] 镜像行 {action}：sub={sub} username={username}")
    finally:
        db.close()


def _grant_admin(sub: str) -> None:
    from app.core.database import SessionLocal
    from app.models.auth import Role, UserRole, User

    db = SessionLocal()
    try:
        if db.query(UserRole).filter(UserRole.user_sub == sub,
                                     UserRole.role_code == "admin").first():
            print(f"[bootstrap] 该用户已是 admin，跳过")
            return
        if not db.query(Role).filter(Role.code == "admin").first():
            from app.core.auth import _DEFAULT_ROLE_PERMS
            db.add(Role(code="admin", name="Admin", is_system=True,
                        default_permissions=_DEFAULT_ROLE_PERMS.get("admin", {})))
        db.add(UserRole(user_sub=sub, role_code="admin", granted_by="st_bootstrap"))
        db.commit()
        print(f"[bootstrap] admin 角色已直写：sub={sub}")
    finally:
        db.close()


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    email, password = sys.argv[1], sys.argv[2]
    username = sys.argv[3] if len(sys.argv) > 3 else email.split("@")[0]

    user_id = asyncio.new_event_loop().run_until_complete(_signup_or_get(email, password))
    print(f"[bootstrap] ST 用户就绪：id={user_id}")
    _upsert_mirror(user_id, email, username)
    _grant_admin(user_id)
    print("[bootstrap] 完成——可用该邮箱密码登录（AUTH_PROVIDER=supertokens 时）。")


if __name__ == "__main__":
    main()
