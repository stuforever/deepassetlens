# -*- coding: utf-8 -*-
"""iam 管理面 9 端点（权限体系重构 T2，design §5.2；挂载 /api/v1/iam）。

口径（🛠R8）：本路由 9 端点（vocab/users/users 建号/users PATCH/roles 替换/roles
列表/roles 建/roles PATCH/roles DELETE）；+audit 端点随 T5.5 落；grant 三件套沿用
现有 /api/v1/auth/grant*。全部 require_permission("auth","read"|"write") 守卫；
ENABLE_AUTH=0 时匿名=admin 直通（与全平台语义一致）。

身份面登记（T3 边界）：POST /users 在 T2 为本地建号面（仅镜像行+初始角色，不调
身份提供方）；T3 交付 SuperTokens SDK 后此端点改为先 ST 建号再落镜像（password
参数本任务已收，留待 T3 消费）。
"""
from __future__ import annotations

import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthUser, require_permission
from app.core.database import get_db
from app.models.auth import Role, User, UserRole
from app.services.permission_vocab import PERMISSION_VOCAB

router = APIRouter()

_ROLE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# ---------------------------------------------------------------------------
# 请求体模型
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    email: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=128)
    roles: List[str] = Field(default_factory=list)
    # T3 边界：ST SDK 建号消费；T2 仅收参不落库（本地面无密码存储）
    password: Optional[str] = Field(default=None, description="T3 ST 建号用，T2 不消费")


class UserPatch(BaseModel):
    is_active: Optional[bool] = None
    display_name: Optional[str] = Field(default=None, max_length=128)


class RolesReplace(BaseModel):
    roles: List[str] = Field(default_factory=list)


class RoleCreate(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=500)
    default_permissions: Optional[dict] = None


class RolePatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = Field(default=None, max_length=500)
    default_permissions: Optional[dict] = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_user_or_404(db: Session, sub: str) -> User:
    row = db.query(User).filter(User.sub == sub).first()
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return row


def _get_role_or_404(db: Session, code: str) -> Role:
    row = db.query(Role).filter(Role.code == code).first()
    if row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return row


def _validate_role_codes(db: Session, codes: List[str]) -> None:
    if not codes:
        return
    found = {r.code for r in db.query(Role).filter(Role.code.in_(codes)).all()}
    missing = [c for c in codes if c not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"未知角色：{','.join(missing)}")


# ---------------------------------------------------------------------------
# vocab / users
# ---------------------------------------------------------------------------

@router.get("/vocab")
def get_vocab(_: AuthUser = Depends(require_permission("auth", "read"))):
    """权限词汇表原样（design §5.1）——前端矩阵编辑器数据源。"""
    return {"code": 200, "data": PERMISSION_VOCAB}


@router.get("/users")
def list_users(
    kw: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: AuthUser = Depends(require_permission("auth", "read")),
    db: Session = Depends(get_db),
):
    """用户列表：搜索/分页/含角色与最近登录（design §5.2）。"""
    q = db.query(User)
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            User.username.like(like) | User.email.like(like) | User.display_name.like(like)
        )
    total = q.count()
    rows = (
        q.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    subs = [r.sub for r in rows]
    role_map: dict = {}
    if subs:
        for ur in db.query(UserRole).filter(UserRole.user_sub.in_(subs)).all():
            role_map.setdefault(ur.user_sub, []).append(ur.role_code)
    items = [
        {
            "sub": r.sub,
            "username": r.username,
            "email": r.email,
            "display_name": r.display_name,
            "is_active": r.is_active,
            "last_login_at": r.last_login_at.isoformat() if r.last_login_at else None,
            "roles": sorted(role_map.get(r.sub, [])),
        }
        for r in rows
    ]
    return {"code": 200, "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.post("/users")
async def create_user(
    payload: UserCreate,
    user: AuthUser = Depends(require_permission("auth", "write")),
    db: Session = Depends(get_db),
):
    """建用户：ST SDK 建号 + 镜像行 + 初始角色（design §5.2）。

    T2 为本地面；T3 起身份创建走 SuperTokens（emailpassword sign_up），ST 不可达
    报 503（禁静默本地建号——身份与镜像行失配会让迁移语义失效）。带 password 走
    ST 建号，不带则本地面（测试/服务号）。"""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    _validate_role_codes(db, payload.roles)

    if payload.password:
        from app.api.auth import _ensure_st_init
        from supertokens_python.recipe import emailpassword as ep_recipe
        from supertokens_python.recipe.emailpassword.interfaces import (
            EmailAlreadyExistsError,
            SignUpOkResult,
        )

        _ensure_st_init()
        result = await ep_recipe.asyncio.sign_up(
            "", payload.email or f"{payload.username}@local.tupu", payload.password)
        if isinstance(result, EmailAlreadyExistsError):
            raise HTTPException(status_code=409, detail="邮箱已在身份层注册")
        if not isinstance(result, SignUpOkResult):
            raise HTTPException(status_code=503, detail=f"ST 建号失败: {result}")
        sub = result.user.id
        if db.query(User).filter(User.sub == sub).first():
            raise HTTPException(status_code=409, detail="该身份镜像已存在")
    else:
        sub = str(uuid.uuid4())

    db.add(User(
        sub=sub,
        username=payload.username,
        email=payload.email,
        display_name=payload.display_name or payload.username,
    ))
    for code in sorted(set(payload.roles)):
        db.add(UserRole(user_sub=sub, role_code=code, granted_by=user.sub))
    db.commit()
    return {"code": 200, "data": {"sub": sub, "username": payload.username}}


@router.patch("/users/{sub}")
def patch_user(
    sub: str,
    payload: UserPatch,
    _: AuthUser = Depends(require_permission("auth", "write")),
    db: Session = Depends(get_db),
):
    """启停 / 改显示名（design §5.2）。"""
    row = _get_user_or_404(db, sub)
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.display_name is not None:
        row.display_name = payload.display_name
    db.commit()
    return {"code": 200, "data": {"sub": row.sub, "is_active": row.is_active, "display_name": row.display_name}}


@router.put("/users/{sub}/roles")
def replace_user_roles(
    sub: str,
    payload: RolesReplace,
    user: AuthUser = Depends(require_permission("auth", "write")),
    db: Session = Depends(get_db),
):
    """角色集整体替换（写 user_roles，granted_by 记操作人——design §5.2）。"""
    _get_user_or_404(db, sub)
    _validate_role_codes(db, payload.roles)
    db.query(UserRole).filter(UserRole.user_sub == sub).delete(synchronize_session=False)
    for code in sorted(set(payload.roles)):
        db.add(UserRole(user_sub=sub, role_code=code, granted_by=user.sub))
    db.commit()
    rows = db.query(UserRole).filter(UserRole.user_sub == sub).all()
    return {"code": 200, "data": {"sub": sub, "roles": sorted(r.role_code for r in rows)}}


# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------

@router.get("/roles")
def list_roles(
    _: AuthUser = Depends(require_permission("auth", "read")),
    db: Session = Depends(get_db),
):
    """角色列表（含成员数子查询——design §5.2）。"""
    from sqlalchemy import func

    counts = dict(
        (row[0], row[1])
        for row in db.query(UserRole.role_code, func.count(UserRole.id)).group_by(UserRole.role_code).all()
    )
    rows = db.query(Role).order_by(Role.is_system.desc(), Role.code).all()
    return {
        "code": 200,
        "data": [
            {
                "code": r.code,
                "name": r.name,
                "description": r.description,
                "is_system": r.is_system,
                "default_permissions": r.default_permissions or {},
                "member_count": counts.get(r.code, 0),
            }
            for r in rows
        ],
    }


@router.post("/roles")
def create_role(
    payload: RoleCreate,
    _: AuthUser = Depends(require_permission("auth", "write")),
    db: Session = Depends(get_db),
):
    """建自定义角色（code 小写字母数字下划线，is_system=false——design §5.2）。"""
    if not _ROLE_CODE_RE.match(payload.code):
        raise HTTPException(status_code=422, detail="角色 code 仅限小写字母/数字/下划线，且字母开头")
    if db.query(Role).filter(Role.code == payload.code).first():
        raise HTTPException(status_code=409, detail="角色 code 已存在")
    db.add(Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        default_permissions=payload.default_permissions or {},
        is_system=False,
    ))
    db.commit()
    return {"code": 200, "data": {"code": payload.code}}


@router.patch("/roles/{code}")
def patch_role(
    code: str,
    payload: RolePatch,
    _: AuthUser = Depends(require_permission("auth", "write")),
    db: Session = Depends(get_db),
):
    """改名/描述/default_permissions；system 角色只许改 default_permissions（design §5.2）。"""
    row = _get_role_or_404(db, code)
    if row.is_system and (payload.name is not None or payload.description is not None):
        raise HTTPException(status_code=400, detail="内置角色仅允许修改 default_permissions")
    if payload.name is not None:
        row.name = payload.name
    if payload.description is not None:
        row.description = payload.description
    if payload.default_permissions is not None:
        row.default_permissions = payload.default_permissions
    db.commit()
    return {"code": 200, "data": {"code": row.code}}


@router.delete("/roles/{code}")
def delete_role(
    code: str,
    _: AuthUser = Depends(require_permission("auth", "write")),
    db: Session = Depends(get_db),
):
    """删非 system 角色；有成员 409（design §5.2）。"""
    row = _get_role_or_404(db, code)
    if row.is_system:
        raise HTTPException(status_code=400, detail="内置角色禁止删除")
    members = db.query(UserRole).filter(UserRole.role_code == code).count()
    if members:
        raise HTTPException(status_code=409, detail=f"角色仍有 {members} 名成员，禁止删除")
    db.delete(row)
    db.commit()
    return {"code": 200, "data": {"code": code}}
