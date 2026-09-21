"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.services.sishu_full.multi_user.h5 import h5_slug
from app.services.sishu_full.multi_user.paths import USERS_ROOT

logger = logging.getLogger(__name__)

router = APIRouter()
settings_router = APIRouter()

_lock = threading.RLock()


# --------------------------------------------------------------------------- #
# h5_links.json（USERS_ROOT.parent = data/）                                   #
# --------------------------------------------------------------------------- #

def _links_path() -> Path:
    return USERS_ROOT.parent / "h5_links.json"


def _load_links() -> list[dict[str, Any]]:
    p = _links_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("links", [])
    except Exception:
        return []


def _save_links(links: list[dict[str, Any]]) -> None:
    p = _links_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"links": links}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@router.get("")
def list_links(parent: str = Query("", description="家长 H5 用户名")):
    """列出某家长关联的孩子（只读视角注册表）。"""
    if not parent:
        raise HTTPException(400, "parent 必填")
    parent_slug = h5_slug(parent)
    links = _load_links()
    return {
        "children": [
            {"child": l.get("child"), "note": l.get("note", "")}
            for l in links
            if l.get("parent") == parent_slug
        ]
    }


@router.post("")
def add_link(payload: dict = Body(default={})):
    """建立家长-孩子关联（去重）。"""
    parent = h5_slug(str(payload.get("parent", "")).strip())
    child = h5_slug(str(payload.get("child", "")).strip())
    note = str(payload.get("note", "") or "").strip()
    with _lock:
        links = _load_links()
        if not any(
            l.get("parent") == parent and l.get("child") == child for l in links
        ):
            links.append(
                {
                    "parent": parent,
                    "child": child,
                    "note": note,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            _save_links(links)
    return {"ok": True}


@router.delete("")
def remove_link(
    parent: str = Query("", description="家长 H5 用户名"),
    child: str = Query("", description="孩子 H5 用户名"),
):
    """解除家长-孩子关联。"""
    parent_slug = h5_slug(parent)
    child_slug = h5_slug(child)
    with _lock:
        links = _load_links()
        new = [
            l
            for l in links
            if not (l.get("parent") == parent_slug and l.get("child") == child_slug)
        ]
        _save_links(new)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# data/user/settings/h5.json（P3-B 公网地址 + 访问码）                         #
# --------------------------------------------------------------------------- #

def _settings_path() -> Path:
    return USERS_ROOT.parent / "user" / "settings" / "h5.json"


def get_h5_settings() -> dict[str, str]:
    """读取 h5 设置（公网地址 / 访问码）。供访问码校验与分享页复用。"""
    p = _settings_path()
    if not p.exists():
        return {"public_base": "", "access_code": ""}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"public_base": "", "access_code": ""}


@settings_router.get("")
def read_settings(
    u: str = Query("", description="H5 用户标识：带 u 时不回明文访问码"),
):
    """GET /api/v1/h5-settings。

    R1-a：带 u（H5 用户）只回 public_base + has_access_code，不回明文 access_code；
    u 缺省（admin/桌面）回全量（分享页生成二维码需要 public_base + access_code）。
    """
    s = get_h5_settings()
    if isinstance(u, str) and u.strip():
        return {
            "public_base": s.get("public_base", ""),
            "has_access_code": bool(s.get("access_code")),
        }
    return s


@settings_router.put("")
def write_settings(
    payload: dict = Body(default={}),
    u: str = Query("", description="H5 用户标识：带 u 时禁止修改（仅管理员可改）"),
):
    """PUT /api/v1/h5-settings <- {public_base?, access_code?}（校验前缀）。

    R1-b：仅 u 缺省（管理员）可修改；带 u（H5 用户）一律 403，防匿名篡改
    access_code / public_base。
    """
    if isinstance(u, str) and u.strip():
        raise HTTPException(403, "仅管理员可修改 H5 设置")
    s = get_h5_settings()
    if "public_base" in payload:
        pb = str(payload.get("public_base") or "").strip().rstrip("/")
        if pb and not pb.startswith(("http://", "https://")):
            raise HTTPException(400, "public_base 需以 http(s):// 开头")
        s["public_base"] = pb
    if "access_code" in payload:
        s["access_code"] = str(payload.get("access_code") or "").strip()
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s


__all__ = ["router", "settings_router", "get_h5_settings"]
