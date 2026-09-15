# -*- coding: utf-8 -*-
"""⑥-2a（spec D2/D4）：专家资源执法——判定单点，四执法点全走此。

判定规则（与 core.check_permission 同语义，不重议）：admin 一票通过；否则
user 直授 ∪ role 授权命中即过。auth=0（ENABLE_AUTH=False）下匿名=admin
一票通过——执法先上、全通语义零变化（spec Runbook 步 1 判定）。

动作词汇（M00 词汇表登记——expert 资源专用）：use=可见可用（门户+对话+功能页）、
manage=+专家后台。resource_type 固定 "expert"，resource_id=专家 slug。
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request

from ..core.auth import ENABLE_AUTH, check_permission, get_current_user
from ..core.database import SessionLocal

EXPERT_403 = "未获专家授权，请联系管理员"


def _user_or_anonymous(request: Request):
    return get_current_user(request)


def ensure_expert_allowed(request: Request, expert_id: str, action: str = "use"):
    """命令式执法（chat 入口等非依赖注入面用）。未命中→403（中文可读）。"""
    user = _user_or_anonymous(request)
    db = SessionLocal()
    try:
        if not check_permission(db, user, "expert", action, resource_id=expert_id):
            raise HTTPException(status_code=403, detail=EXPERT_403)
    finally:
        db.close()
    return user


def require_expert(action: str, expert_id: Optional[str] = None):
    """依赖工厂：action ∈ {"use", "manage"}。expert_id 缺省时从查询参数/路径取
    （FastAPI 依赖注入 expert_id: str）——固定域路由（/api/tutor 等）显式传 slug。"""

    def _dep(request: Request, expert_id_param: str = "") -> object:
        eid = expert_id or expert_id_param
        user = _user_or_anonymous(request)
        db = SessionLocal()
        try:
            if not check_permission(db, user, "expert", action, resource_id=eid):
                raise HTTPException(status_code=403, detail=EXPERT_403)
        finally:
            db.close()
        return user

    return _dep


def filter_visible_experts(request: Request, rows: list[dict]) -> list[dict]:
    """执法点①：专家列表数据源收口——auth=1 且非 admin 时只留 use 命中集；
    auth=0（匿名=admin）或 admin → 原样全量（门户/侧栏随之）。"""
    user = _user_or_anonymous(request)
    if not ENABLE_AUTH or user.is_admin():
        return rows
    db = SessionLocal()
    try:
        out = []
        for r in rows:
            slug = r.get("expert_id") or ""
            if check_permission(db, user, "expert", "use", resource_id=slug):
                out.append(r)
        return out
    finally:
        db.close()
