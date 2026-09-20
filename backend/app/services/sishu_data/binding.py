# -*- coding: utf-8 -*-
"""v4批2 2.4：?u= 会话绑定单点（协议 F② / R3-C2）。
auth=1 非 admin：u 必须等于会话用户绑定 slug（两形：username / h5_{username}），
否则 403「未获该用户数据授权」；auth=0 或 admin：桌面语义（缺省=admin）。
批6-14 全域 ?u= 端点消费——一个函数覆盖全部消费点，端点永不自由收 u=。"""
from fastapi import HTTPException, Request

from ...core.auth import ENABLE_AUTH, get_current_user


def sishu_user_binding(u: str | None, request: Request) -> str:
    if not ENABLE_AUTH:
        return u or "admin"
    user = get_current_user(request)
    if user.is_admin():
        return u or "admin"
    name = (getattr(user, "username", "") or "").strip().lower()
    if not u or u not in (name, f"h5_{name}"):
        raise HTTPException(status_code=403, detail="未获该用户数据授权")
    return u
