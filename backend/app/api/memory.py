# -*- coding: utf-8 -*-
"""memory.py - 最小记忆管理 API（记忆插槽②，spec §九；全部 admin——浏览用户记忆数据，
隐私属性）。四端点：tree/file/consolidate/events。file 端点路径穿越防护：resolve 后
必须落请求树内否则 403。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


def _require_admin(request: Request) -> None:
    user = get_current_user(request)
    if user is None or not user.is_admin():
        raise HTTPException(status_code=403, detail="仅管理员可访问记忆管理")


def _tree_root(expert_id: str, user: str, root: str = "user") -> Path:
    from app.services.expert_paths import memory_expert_root, memory_user_root
    # R5批④：根构造校验失败（穿越/非法段）→ 400，不落 500
    try:
        return memory_expert_root(expert_id) if root == "expert" else memory_user_root(expert_id, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree")
def tree(request: Request, expert_id: str = Query(...), user: str = Query(...),
         root: str = Query("user")):
    """目录扫描（树浏览器数据源；admin-only）。root=expert 浏览专家根（手册）。"""
    _require_admin(request)
    base = _tree_root(expert_id, user, root)
    if not base.exists():
        return {"items": []}
    out = []
    for p in sorted(base.rglob("*")):
        if "backup" in p.parts:
            continue
        out.append({"path": f"/memory/{p.relative_to(base).as_posix()}",
                    "is_dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0,
                    "modified_at": p.stat().st_mtime if p.is_file() else None})
    return {"items": out}


@router.get("/file")
def file(request: Request, expert_id: str = Query(...), user: str = Query(...),
         path: str = Query(...), root: str = Query("user")):
    """只读内容（md 原文/jsonl 尾部 N 行）。路径穿越防护：resolve 后必须落请求树内。
    root=expert 读专家根（手册/L2L3 专家态）。"""
    _require_admin(request)
    base = _tree_root(expert_id, user, root).resolve()
    p = (base / path.removeprefix("/memory/")).resolve()
    if not str(p).startswith(str(base)):                 # 穿越防护（spec §九铁则）
        raise HTTPException(status_code=403, detail="路径越界")
    if not p.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    text = p.read_text("utf-8", errors="replace")
    if p.suffix == ".jsonl":
        text = "\n".join(text.splitlines()[-100:])       # 尾部 100 行
    return {"path": path, "content": text}


@router.post("/consolidate")
async def consolidate(request: Request, body: dict):
    """手动固化（②验收主通道）：update+audit 返回报告。"""
    _require_admin(request)
    from app.services.memory_consolidator import run_consolidation, ModeNotImplemented
    try:
        return await run_consolidation(body.get("expert_id", ""), body.get("user", ""))
    except ModeNotImplemented as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/events")
def events(request: Request, expert_id: Optional[str] = Query(None),
           kind: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    """台账流水（memory_write/memory_consolidated 过滤）。"""
    _require_admin(request)
    from app.models.base import ExpertEvent
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        q = db.query(ExpertEvent).order_by(ExpertEvent.ts.desc())
        if expert_id:
            q = q.filter(ExpertEvent.expert_id == expert_id)
        rows = q.limit(limit).all()
        kinds = ("memory_write", "memory_consolidated")
        rows = [r for r in rows if r.action in kinds and (kind is None or r.action == kind)]
        return {"items": [{"expert_id": r.expert_id, "ts": r.ts.isoformat() if r.ts else None,
                           "kind": r.action, "detail": r.detail} for r in rows]}
    finally:
        db.close()
