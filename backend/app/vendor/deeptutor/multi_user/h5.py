"""H5 多用户支撑层（design 续篇 §四 MU-1..4）。

H5 分享链接通过 ``?u=<名字>`` 携带用户标识。后端据此合成一个 *轻量
用户*（仿 ``partners`` 的合成用户模式），把所有 data-class 存储
（学习画像 / 母题 / 记忆 / 笔记 / 会话）隔离到各自工作区：

    data/users/h5_<slug>/

关键设计（与续篇一致）：
* **owner 归 admin**：H5 用户 role 设为 "admin"，``is_admin=True``
  跳过 LLM grant 检查（答疑无需给每个 H5 用户配模型），但
  ``scope.root`` 仍指向自己的目录，存储照常隔离。
* **u 缺省 = admin**：URL 不带 ``u`` 时回退 ``local_admin_user()``，
  零迁移、不破坏桌面行为。
* **中文 slug 安全化**：保留中文与 ``\w``，拦截 ``..`` / 盘符 /
  路径分隔符注入。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Header, HTTPException, Query, status

from .models import CurrentUser, UserScope
from .paths import USERS_ROOT, admin_scope, local_admin_user, user_context  # noqa: F401

#: h5 用户 id 前缀（仿 ``partner_``）。
H5_USER_PREFIX = "h5_"

#: 只允许 \w（含下划线、数字、英文）+ 中文；拦截 ../、盘符、空格等。
_H5_SLUG_RE = re.compile(r"^[\w\u4e00-\u9fff]{1,32}$")
#: 危险片段（路径穿越 / 盘符 / 分隔符），在正则之外的二次防线。
_DANGEROUS = ("..", ":", "/", "\\", "\x00", "\r", "\n")


def h5_slug(u: str) -> str:
    """把任意 ``?u=`` 值安全化为工作区目录名。

    - 空 / 非法 -> 抛 400（避免静默落到 admin 目录造成数据混淆）
    - 合法中文 / 英文 / 数字 / 下划线原样保留
    """
    if not u or not isinstance(u, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="u 参数缺失或非法",
        )
    u = u.strip()
    if len(u) > 32:
        u = u[:32]
    if any(d in u for d in _DANGEROUS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="u 参数包含非法字符",
        )
    if not _H5_SLUG_RE.match(u):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="u 参数只能包含中文、字母、数字、下划线",
        )
    return u


def h5_user_id(slug: str) -> str:
    return f"{H5_USER_PREFIX}{slug}"


def is_h5_user_id(user_id: str) -> bool:
    return user_id.startswith(H5_USER_PREFIX)


def h5_workspace_root(slug: str) -> Path:
    # 运行时读 paths.USERS_ROOT（而非 import 时绑定），保证测试
    # monkeypatch paths.USERS_ROOT 时随之生效。
    from .paths import USERS_ROOT as _USERS_ROOT

    return (_USERS_ROOT / h5_user_id(slug)).resolve()


def h5_scope(slug: str) -> UserScope:
    return UserScope(
        kind="user",
        user_id=h5_user_id(slug),
        root=h5_workspace_root(slug),
    )


def h5_user(slug: str) -> CurrentUser:
    """合成 H5 用户：id=h5_<slug>，username=slug，role=admin。

    role=admin（is_admin=True）→ 复用 admin 的 LLM 授权/默认模型；
    scope.root 指向自己的工作区 → 存储照常隔离。
    """
    return CurrentUser(
        id=h5_user_id(slug),
        username=slug,
        role="admin",  # owner 归 admin：不单独配 LLM
        scope=h5_scope(slug),
    )


def resolve_h5_current_user(u: str | None) -> CurrentUser:
    """``?u=`` 解析：缺省/空 -> admin；否则合成 H5 用户（400 on 非法）。"""
    if not u:
        return local_admin_user()
    return h5_user(h5_slug(u))


def current_admin() -> CurrentUser:
    """显式切回 admin 上下文（内容创建类 API 使用）。"""
    return local_admin_user()


def is_admin_scope(scope: Any) -> bool:
    return scope.kind == "admin" if scope is not None else False


def _load_h5_settings() -> dict:
    """读取 data/user/settings/h5.json（P3-B：access_code）。

    独立实现以避免与 api.routers.h5_links 循环依赖（后者 import 本模块的
    h5_slug）；两处都读同一文件，无 import 耦合。
    """
    p = USERS_ROOT.parent / "user" / "settings" / "h5.json"
    if not p.exists():
        return {}
    try:
        import json

        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def access_code_ok(u: str, code: str) -> bool:
    """访问码门禁（P3-B）：u 缺省（admin/桌面）不受约束；access_code 非空时
    必须匹配 ?code= / X-Access-Code，否则 401。"""
    if not isinstance(u, str) or not u:
        return True
    settings = _load_h5_settings()
    ac = str(settings.get("access_code") or "").strip()
    if not ac:
        return True
    return (code or "").strip() == ac


async def h5_scope_dep(
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
) -> AsyncIterator[CurrentUser]:
    """FastAPI 依赖：按 ``?u=`` 包 user_context（async generator 依赖与
    端点在同一个 asyncio Task 上下文运行，contextvar 正确传播；依赖
    cleanup 时自动 reset，不泄漏到后续请求）。

    - u 缺省/空 -> admin（local_admin_user），零迁移不破坏桌面
    - u 合法 -> 合成 H5 用户（存储隔离到 data/users/h5_<slug>/）
    - u 非法 -> HTTP 400
    - access_code 启用且 u 非空时，?code= 或 X-Access-Code 不匹配 -> HTTP 401
    """
    if not access_code_ok(u, code or x_access_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要访问码",
        )
    user = resolve_h5_current_user(u)
    with user_context(user):
        yield user


def h5_user_guarded(
    u: str,
    code: str = "",
    x_access_code: str = "",
) -> CurrentUser:
    """统一守卫（R1-c）：手动收编点共用，替代散落的 ``h5_user(h5_slug(u))``。

    - u 缺省/空 -> admin（桌面不受访问码约束）
    - access_code 非空时要求 ``?code=`` / ``X-Access-Code`` 匹配，否则 401
    - u 非法 -> h5_slug 抛 HTTP 400
    """
    if not isinstance(u, str) or not u.strip():
        return local_admin_user()
    if not access_code_ok(u, code or x_access_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要访问码",
        )
    return h5_user(h5_slug(u))


__all__ = [
    "H5_USER_PREFIX",
    "h5_slug",
    "h5_user_id",
    "is_h5_user_id",
    "h5_workspace_root",
    "h5_scope",
    "h5_user",
    "resolve_h5_current_user",
    "current_admin",
    "is_admin_scope",
    "h5_scope_dep",
    "h5_user_guarded",
]
