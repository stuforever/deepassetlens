# -*- coding: utf-8 -*-
"""⑤R 接线点1（唯一交棒 批3.1）：DT 认证 shim——同名同形，原仓依赖签名零感知。

- 原仓挂载面 `dependencies=[Depends(require_auth)]` / `require_admin` 由本模块同位替换；
- ENABLE_AUTH=0（现网常驻）：tupu auth_middleware 已注入匿名 admin——放行（桌面语义与
  原仓本机 AUTH_ENABLED=false 一致）；执法点③（expert ACL 统一门）在此单点生效：
  vendor 子树全部复刻 router 经由本 shim 的 require_auth，教学域对非授权 expert 关闭；
- ENABLE_AUTH=1：get_current_user 验 JWT，admin 判定走 tupu 角色模型；
- vendor 内部 handler 的 `multi_user.context.get_current_user()`（ContextVar+local_admin
  桌面语义、?u= 选择）原样保留——不改 vendor 一行。

批4 B2 实测修正（登记）：vendor 路由挂载改用 vendored auth.require_auth（原结构照搬）——
其 Header/Cookie 形签名对 WS 路由可解（Request 形 shim 在 WS 域不可解致握手 500）；
auth=0 下两者行为等价（放行+桌面语义）。本模块保留：auth=1 单点接线位（批18/20.2/20.3）。"""
from typing import Any

from fastapi import HTTPException, Request

from app.core.auth import ENABLE_AUTH, get_current_user


def _auth(request: Request) -> Any:
    """原仓 `_auth = [Depends(require_auth)]` 的同位替换（接线点1）。"""
    return get_current_user(request)


def require_auth(request: Request) -> Any:
    """原仓 `from deeptutor.api.routers.auth import require_auth` 的同名同形替换。

    执法点③（vendor 统一门，批16 v2 语义）：所有 vendor 复刻 router 的挂载依赖
    都经过本函数——expert ACL 单点判定（use 动作，expert_id=tutor）。
    auth=0 时 tupu 语义=匿名 admin 一票通过，与原仓本机模式行为一致。"""
    user = get_current_user(request)
    try:
        from app.services.expert_auth import ensure_expert_allowed

        ensure_expert_allowed(request, "tutor", "use")
    except HTTPException:
        raise
    except Exception:
        pass  # ACL 设施缺位时保持放行（auth=0 桌面语义），不阻塞复刻面
    return user


def require_admin(request: Request) -> Any:
    """原仓 `require_admin` 的同名同形替换。"""
    user = get_current_user(request)
    if ENABLE_AUTH and not user.is_admin():
        raise HTTPException(status_code=403, detail="admin required")
    return user
