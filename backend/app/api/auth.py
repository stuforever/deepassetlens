"""
认证相关 API：
- GET  /api/v1/auth/config    OIDC 配置（前端用，无需登录）
- GET  /api/v1/auth/me        当前用户身份
- POST /api/v1/auth/dev-login 开发模式直连签发（仅当 ENABLE_AUTH=0 可用）
- GET  /api/v1/auth/users     管理员列出所有 user
- POST /api/v1/auth/grant     管理员授权资源给用户/角色
- DELETE /api/v1/auth/grant/{id} 撤销授权
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import (
    ENABLE_AUTH,
    AuthUser,
    get_current_user,
    require_permission,
)
from app.core.database import get_db


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
def auth_config():
    """OIDC 公开配置（前端登录跳转用）。"""
    base = os.environ.get("AUTHENTIK_BASE_URL", "http://localhost:9100")
    issuer = os.environ.get("AUTHENTIK_ISSUER", f"{base}/application/o/tupu/")
    client_id = os.environ.get(
        "AUTHENTIK_CLIENT_ID", "VzFcIQaMB1b2ETPl7oMg4bAF6VS25BbzERyZTPQf"
    )
    redirect = os.environ.get(
        "AUTHENTIK_FRONTEND_REDIRECT", "http://localhost:3000/auth/callback"
    )
    return {
        "code": 200,
        "data": {
            "enable_auth": ENABLE_AUTH,
            "issuer": issuer,
            "client_id": client_id,
            "redirect_uri": redirect,
            "authorization_endpoint": f"{base}/application/o/authorize/",
            "token_endpoint": f"{base}/application/o/token/",
            "end_session_endpoint": f"{issuer}end-session/",
            "scopes": ["openid", "profile", "email", "groups"],
        },
    }


@router.get("/me")
def auth_me(request: Request):
    user = get_current_user(request)
    return {"code": 200, "data": user.to_dict()}


class GrantRequest(BaseModel):
    resource_type: str
    resource_id: str  # '*' 表示该 type 的所有资源
    principal_type: str  # 'user' | 'role'
    principal_id: str
    actions: List[str]
    expires_at: Optional[datetime] = None


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "read")),
):
    from app.models.auth import User, UserRole

    users = db.query(User).all()
    out = []
    for u in users:
        roles = [
            ur.role_code
            for ur in db.query(UserRole).filter(UserRole.user_sub == u.sub).all()
        ]
        out.append({
            "sub": u.sub,
            "username": u.username,
            "email": u.email,
            "display_name": u.display_name,
            "roles": roles,
            "groups_snapshot": u.groups_snapshot,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        })
    return {"code": 200, "data": out}


@router.post("/grant")
def grant_resource(
    payload: GrantRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "write")),
):
    from app.models.auth import ResourceACL

    if payload.principal_type not in ("user", "role"):
        raise HTTPException(status_code=400, detail="principal_type 必须是 user 或 role")
    if not payload.actions:
        raise HTTPException(status_code=400, detail="actions 不能为空")

    granter = _user.sub
    existing = (
        db.query(ResourceACL)
        .filter(
            ResourceACL.resource_type == payload.resource_type,
            ResourceACL.resource_id == payload.resource_id,
            ResourceACL.principal_type == payload.principal_type,
            ResourceACL.principal_id == payload.principal_id,
        )
        .first()
    )
    if existing:
        existing.actions = payload.actions
        existing.expires_at = payload.expires_at
        existing.granted_by = granter
        existing.granted_at = datetime.utcnow()
        db.commit()
        return {"code": 200, "data": {"id": existing.id, "updated": True}}

    row = ResourceACL(
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        principal_type=payload.principal_type,
        principal_id=payload.principal_id,
        actions=payload.actions,
        granted_by=granter,
        expires_at=payload.expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"code": 200, "data": {"id": row.id, "created": True}}


@router.get("/grants")
def list_grants(
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "read")),
):
    from app.models.auth import ResourceACL

    q = db.query(ResourceACL)
    if resource_type:
        q = q.filter(ResourceACL.resource_type == resource_type)
    if resource_id:
        q = q.filter(ResourceACL.resource_id == resource_id)
    rows = q.all()
    return {
        "code": 200,
        "data": [
            {
                "id": r.id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "principal_type": r.principal_type,
                "principal_id": r.principal_id,
                "actions": r.actions,
                "granted_by": r.granted_by,
                "granted_at": r.granted_at.isoformat() if r.granted_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rows
        ],
    }


@router.delete("/grant/{grant_id}")
def revoke_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "write")),
):
    from app.models.auth import ResourceACL

    row = db.query(ResourceACL).filter(ResourceACL.id == grant_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="授权不存在")
    db.delete(row)
    db.commit()
    return {"code": 200, "data": {"revoked": grant_id}}
