# -*- coding: utf-8 -*-
"""工具门控（权限体系重构 T5，design §6）。

三分类判定（🛠R5 语义写死）：
- READONLY_TOOLS：粗粒度 tool:execute（角色默认 or ACL）覆盖，允许/拒绝；
- EXEC_TOOLS：仅 ACL 显式授予（角色默认 tool:execute 不覆盖——设计明文）；
- WRITE_TOOLS：恒拒（系统级面外，admin 亦不放行；approval 动作位 v1 预留）。

fail-closed：未注册（TOOL_REGISTRY 之外）的工具一律剔除/拒绝。
审计：工具判定全量落（allow+deny 都落——design §6.1「调用量低」）；装配期
filter_tools_for_user 是清单过滤、非判定事件，不落审计。
ENABLE_AUTH=0：匿名=admin 全通——测试基建零影响（语义锚，回归测试钉住）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.auth import AuthAuditLog, ResourceACL
from app.services.permission_vocab import EXEC_TOOLS, READONLY_TOOLS, TOOL_REGISTRY, WRITE_TOOLS


@dataclass
class Decision:
    allowed: bool
    reason: str


def _is_admin_bypass(user) -> bool:
    """auth=0 匿名 / admin 角色 → 全通（写类恒拒除外——系统级面外不变）。"""
    from app.core.auth import ENABLE_AUTH

    if not ENABLE_AUTH:
        return True
    return user is not None and not user.is_anonymous and user.is_admin()


def _exec_granted_via_acl(db: Session, user, tool_name: str) -> bool:
    """EXEC 类仅认 ACL（role/user principal，actions 含 execute）。"""
    rows = db.query(ResourceACL).filter(
        ResourceACL.resource_type == "tool",
        ResourceACL.resource_id.in_([tool_name, "*"]),
    ).all()
    from datetime import datetime

    now = datetime.utcnow()
    user_ids = {user.sub} if user else set()
    role_codes = set(user.roles) if user else set()
    for row in rows:
        if row.expires_at and row.expires_at < now:
            continue
        actions = row.actions or []
        if "execute" not in actions and "*" not in actions:
            continue
        if row.principal_type == "user" and row.principal_id in user_ids:
            return True
        if row.principal_type == "role" and row.principal_id in role_codes:
            return True
    return False


def _readonly_granted(db: Session, user, tool_name: str) -> bool:
    """只读类：粗粒度 tool:execute（角色默认——DB 行权威，T2 语义）或 ACL。"""
    from app.core.auth import _has_permission_via_role_default, _has_permission_via_acl

    if _has_permission_via_role_default(db, user.roles, "tool", "execute"):
        return True
    return _has_permission_via_acl(db, user, "tool", tool_name, "execute")


def _write_audit(db: Session, user, tool_name: str, decision: str, reason: str,
                 session_ctx: Optional[dict]) -> None:
    try:
        db.add(AuthAuditLog(
            user_sub=(user.sub if user else "anonymous"),
            resource_type="tool",
            resource_id=tool_name,
            action="execute",
            decision=decision,
            reason=(reason or "")[:500],
            session_id=(session_ctx or {}).get("session_id"),
            turn_id=(session_ctx or {}).get("turn_id"),
        ))
        db.commit()
    except Exception:
        db.rollback()  # 审计失败不阻塞工具调用（记录为尽力而为）


def filter_tools_for_user(db: Session, user, tool_names: Iterable[str]) -> set:
    """装配期清单过滤：专家白名单（上游已∩）∩ 用户权限，fail-closed。

    ENABLE_AUTH=0 / admin：原样全量（开发态语义不变）。未注册工具剔除。
    """
    names = set(tool_names)
    if _is_admin_bypass(user):
        return names
    allowed: set = set()
    for name in names:
        if name not in TOOL_REGISTRY:
            continue  # fail-closed：未注册不入面
        if name in READONLY_TOOLS:
            if _readonly_granted(db, user, name):
                allowed.add(name)
        elif name in EXEC_TOOLS:
            if _exec_granted_via_acl(db, user, name):
                allowed.add(name)
        # WRITE_TOOLS 不可能出现在 MCP 注册面（面外集合）——防御性不添加
    return allowed


def check_tool_call(db: Session, user, tool_name: str,
                    expert_tools: Optional[Iterable[str]] = None,
                    session_ctx: Optional[dict] = None) -> Decision:
    """派发期复核（三态判定 + 审计落痕）。design §6.2 派发点语义。

    判定顺序：写类恒拒 → 未注册拒 → 专家面外拒 → admin 全通（写类除外）→
    只读类粗粒度/ACL → EXEC 仅 ACL。
    """
    if tool_name in WRITE_TOOLS:
        d = Decision(False, f"工具 {tool_name} 属系统级写类，恒拒（approval 位 v1 预留）")
        _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
        return d

    if tool_name not in TOOL_REGISTRY:
        d = Decision(False, f"工具 {tool_name} 未注册（fail-closed）")
        _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
        return d

    if expert_tools is not None and tool_name not in set(expert_tools):
        d = Decision(False, f"工具 {tool_name} 不在当前专家工具面")
        _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
        return d

    if _is_admin_bypass(user):
        d = Decision(True, "admin")
        _write_audit(db, user, tool_name, "allow", d.reason, session_ctx)
        return d

    if user is None or user.is_anonymous:
        d = Decision(False, "未登录用户不可调用受控工具")
        _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
        return d

    if tool_name in READONLY_TOOLS:
        if _readonly_granted(db, user, tool_name):
            d = Decision(True, "只读类粗粒度授权")
            _write_audit(db, user, tool_name, "allow", d.reason, session_ctx)
            return d
        d = Decision(False, f"未获工具 {tool_name} 使用授权")
        _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
        return d

    # EXEC：仅 ACL（角色默认 tool:execute 不覆盖——🛠R5）
    if tool_name in EXEC_TOOLS:
        if _exec_granted_via_acl(db, user, tool_name):
            d = Decision(True, "执行类 ACL 授权")
            _write_audit(db, user, tool_name, "allow", d.reason, session_ctx)
            return d
        d = Decision(False, f"未获工具 {tool_name} 使用授权（执行类需显式 ACL 授予）")
        _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
        return d

    d = Decision(False, f"工具 {tool_name} 分类未知（fail-closed）")
    _write_audit(db, user, tool_name, "deny", d.reason, session_ctx)
    return d


def seed_tool_permissions(db: Session) -> None:
    """上线种子（🛠R7，幂等）：
    1) 全部角色 default_permissions 并入 tool:["execute"]（只读粗粒度——含 viewer，
       只读件对全部角色可见）；
    2) viewer 之外的既有角色补 EXEC 4 件 role ACL（切换日问数能力不断）。
    admin 一票通过无需种子，但缺行时顺带补齐（统一循环）。"""
    from app.models.auth import Role

    roles = db.query(Role).all()
    # 系统 admin/operator/viewer 行可能未播种（无人登录过）——确保三行存在
    from app.core.auth import _DEFAULT_ROLE_PERMS

    for rc in ("admin", "operator", "viewer"):
        if not db.query(Role).filter(Role.code == rc).first():
            db.add(Role(code=rc, name=rc.title(), is_system=True,
                        default_permissions=_DEFAULT_ROLE_PERMS.get(rc, {})))
    db.flush()
    roles = db.query(Role).all()

    for role in roles:
        dp = dict(role.default_permissions or {})
        tool_actions = set(dp.get("tool") or [])
        if "execute" not in tool_actions:
            tool_actions.add("execute")
            dp["tool"] = sorted(tool_actions)
            role.default_permissions = dp
        if role.code == "viewer":
            continue  # viewer 除外：EXEC 不补（只读即可）
        for tool_name in EXEC_TOOLS:
            exists = db.query(ResourceACL).filter(
                ResourceACL.resource_type == "tool",
                ResourceACL.resource_id == tool_name,
                ResourceACL.principal_type == "role",
                ResourceACL.principal_id == role.code,
            ).first()
            if not exists:
                db.add(ResourceACL(resource_type="tool", resource_id=tool_name,
                                   principal_type="role", principal_id=role.code,
                                   actions=["execute"], granted_by="tool_gate_seed"))
    db.commit()
