# -*- coding: utf-8 -*-
"""权限重构T6批3（design §7 批3）：vendor users.json 存储面退役——用户读取面改
平台 auth_users 表为唯一数据源（T6.3 slug=username：grants/分目录键=用户名）。

原 JSON 用户库/密码哈希/JWT secret/头像文件管理随批3 删除（建号走 /api/v1/iam/users，
SuperTokens 托管口令）。存活面仅剩 grants 管理所需的两只读函数：

- ``get_user_by_id(user_id)``：grants 保存校验 + 可指派用户判定（admin 拒指派）。
  键=username（slug）；旧 grant 文件若存平台 sub 亦兜底可查。
- ``list_user_info()``：multi-user 管理面 GET /users 的用户清单。

返回 dict 保持 vendor 原形状（id/username/role/created_at/disabled/avatar）——
消费方（multi_user/router.py、grants.py）零改。
"""
from __future__ import annotations

from typing import Any


def _platform_users() -> dict[str, dict[str, Any]]:
    """平台用户 → vendor 记录形状映射。role=admin 取决于 auth_user_roles 含 admin。"""
    from app.core.database import SessionLocal
    from app.models.auth import User as _PlatformUser
    from app.models.auth import UserRole as _PlatformUserRole

    db = SessionLocal()
    try:
        rows = db.query(_PlatformUser).all()
        role_map: dict[str, list[str]] = {}
        subs = [r.sub for r in rows]
        if subs:
            for ur in db.query(_PlatformUserRole).filter(_PlatformUserRole.user_sub.in_(subs)).all():
                role_map.setdefault(ur.user_sub, []).append(ur.role_code)
        out: dict[str, dict[str, Any]] = {}
        for u in rows:
            roles = role_map.get(u.sub, [])
            out[u.username] = {
                "id": u.username,  # T6.3 slug=username
                "username": u.username,
                "role": "admin" if "admin" in roles else "user",
                "created_at": u.created_at.isoformat() if u.created_at else "",
                "disabled": not bool(u.is_active),
                "avatar": "",
            }
        return out
    finally:
        db.close()


def list_user_info() -> list[dict[str, Any]]:
    """Platform-backed 用户清单（vendor 原形状）。"""
    return list(_platform_users().values())


def get_user_by_id(user_id: str) -> tuple[str, dict[str, Any]] | None:
    """按 id 查用户 → (username, record)。键=username（slug）；兜底平台 sub
    （旧 grant 文件对账）。未命中返回 None（调用方 404）。"""
    users = _platform_users()
    if user_id in users:
        record = dict(users[user_id])
        return user_id, record
    # sub 兜底
    from app.core.database import SessionLocal
    from app.models.auth import User as _PlatformUser
    from app.models.auth import UserRole as _PlatformUserRole

    db = SessionLocal()
    try:
        u = db.query(_PlatformUser).filter(_PlatformUser.sub == user_id).first()
        if u is None:
            return None
        roles = [
            ur.role_code
            for ur in db.query(_PlatformUserRole).filter(_PlatformUserRole.user_sub == u.sub).all()
        ]
        record = {
            "id": u.username,
            "username": u.username,
            "role": "admin" if "admin" in roles else "user",
            "created_at": u.created_at.isoformat() if u.created_at else "",
            "disabled": not bool(u.is_active),
            "avatar": "",
        }
        return u.username, record
    finally:
        db.close()
