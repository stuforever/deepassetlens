"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
import urllib.parse

import httpx

from app.services.sishu_full.services.path_service import get_path_service

logger = logging.getLogger(__name__)

WECHAT_OAUTH_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


def _identity_path() -> Path:
    return get_path_service().get_settings_dir() / "wechat_identity.json"


def load_bindings() -> dict[str, dict]:
    try:
        p = _identity_path()
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")).get("bindings", {})
    except Exception:
        logger.warning("wechat_identity read failed", exc_info=True)
    return {}


def _save_bindings(bindings: dict[str, dict]) -> None:
    p = _identity_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"bindings": bindings, "updated_at": time.time()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_binding(openid: str) -> dict | None:
    return load_bindings().get(openid)


def bind_openid(
    openid: str,
    *,
    role: str = "student",
    display_name: str = "",
    student_openid: str = "",
) -> dict:
    """Bind a WeChat openid to a role (student|parent)."""
    if role not in ("student", "parent"):
        raise ValueError("role must be 'student' or 'parent'")
    bindings = load_bindings()
    entry = {
        "role": role,
        "display_name": display_name or ("家长" if role == "parent" else "学生"),
        "bound_at": time.time(),
    }
    if role == "parent":
        # 家长必须关联到某个学生 openid
        if not student_openid:
            raise ValueError("parent binding requires student_openid")
        entry["student_openid"] = student_openid
    bindings[openid] = entry
    _save_bindings(bindings)
    return entry


def unbind_openid(openid: str) -> bool:
    bindings = load_bindings()
    if openid not in bindings:
        return False
    del bindings[openid]
    _save_bindings(bindings)
    return True


def list_bindings() -> dict[str, dict]:
    return load_bindings()


def openid_to_profile_openid(openid: str) -> str:
    """Return the openid whose LearnerProfile this identity should read.

    - student -> itself
    - parent -> its linked student_openid
    """
    binding = load_bindings().get(openid)
    if binding and binding.get("role") == "parent":
        return binding.get("student_openid", openid)
    return openid


def role_of_openid(openid: str) -> str | None:
    """Return the bound role ('student' / 'parent') or None when unbound."""
    binding = load_bindings().get(openid)
    if not binding:
        return None
    return str(binding.get("role") or "student")


def filter_subscribers_by_role(openids: list[str], role: str) -> list[str]:
    """Keep only subscribers bound to *role*.

    - A subscriber bound to *role* stays.
    - An **unbound** subscriber is kept only for the default ``student`` role
      (so a brand-new openid that just subscribed still receives study pushes);
      for ``parent`` unbound subscribers are dropped (no student linkage).
    """
    if role not in ("student", "parent"):
        return list(openids)
    out = []
    for oid in openids:
        r = role_of_openid(oid)
        if r == role:
            out.append(oid)
        elif r is None and role == "student":
            out.append(oid)
    return out


async def exchange_code_for_openid(
    code: str,
    *,
    appid: str = "",
    secret: str = "",
    mock_mode: bool = True,
) -> str:
    """WeChat OAuth2: exchange an authorization code for the user's openid.

    mock_mode returns ``mock_openid_<code>`` so tests work without a real
    WeChat app.
    """
    if mock_mode:
        return f"mock_openid_{code[:16]}"
    if not appid or not secret:
        raise ValueError("appid/secret required for real OAuth")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            WECHAT_OAUTH_TOKEN_URL,
            params={
                "appid": appid,
                "secret": secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        data = resp.json()
    openid = data.get("openid", "")
    if not openid:
        raise RuntimeError(f"WeChat OAuth failed: {data}")
    return openid


def build_oauth_redirect_url(
    *,
    appid: str,
    redirect_uri: str,
    scope: str = "snsapi_userinfo",
    state: str = "wechat_login",
) -> str:
    """Build the WeChat web-authorization redirect URL."""
    return (
        "https://open.weixin.qq.com/connect/oauth2/authorize?"
        + urllib.parse.urlencode(
            {
                "appid": appid,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope,
                "state": state,
            }
        )
        + "#wechat_redirect"
    )


__all__ = [
    "bind_openid",
    "build_oauth_redirect_url",
    "exchange_code_for_openid",
    "filter_subscribers_by_role",
    "get_binding",
    "list_bindings",
    "load_bindings",
    "openid_to_profile_openid",
    "role_of_openid",
    "unbind_openid",
]
