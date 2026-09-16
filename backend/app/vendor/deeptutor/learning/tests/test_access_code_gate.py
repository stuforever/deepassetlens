"""R1 安全整改单测：访问码门禁全覆盖（R1-c）+ settings 明文码保护（R1-a/b）。

直接调用路由函数验证守卫行为；用 monkeypatch 把 USERS_ROOT 指向 tmp，
不触碰真实 data/ 目录（运行中的 server 不受影响）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from deeptutor.api.routers import h5_links, mother_question as mq
from deeptutor.api.routers import mastery_path as mp
from deeptutor.api.routers import notebook as nb
from deeptutor.multi_user import h5 as h5_mod


@pytest.fixture
def h5_settings(tmp_path: Path, monkeypatch):
    """写 access_code 到 tmp 设置目录，重定向 h5.py / h5_links 的 USERS_ROOT。"""
    users_root = tmp_path / "users"
    users_root.mkdir(parents=True, exist_ok=True)
    settings_dir = tmp_path / "user" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "h5.json").write_text(
        json.dumps(
            {"public_base": "https://h5.example.com", "access_code": "1234"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(h5_mod, "USERS_ROOT", users_root)
    monkeypatch.setattr(h5_links, "USERS_ROOT", users_root)
    return tmp_path


# --------------------------------------------------------------------------- #
# R1-a：GET /h5-settings 不回明文码                                           #
# --------------------------------------------------------------------------- #

def test_settings_get_hides_code_for_h5_user(h5_settings):
    out = h5_links.read_settings(u="小明")
    assert out["public_base"] == "https://h5.example.com"
    assert out["has_access_code"] is True
    assert "access_code" not in out
    assert "has_access_code" in out


def test_settings_get_full_for_admin(h5_settings):
    out = h5_links.read_settings(u="")
    assert out["access_code"] == "1234"


# --------------------------------------------------------------------------- #
# R1-b：PUT /h5-settings 带 u 时 403（防匿名篡改）                            #
# --------------------------------------------------------------------------- #

def test_settings_put_forbidden_for_h5_user(h5_settings):
    with pytest.raises(HTTPException) as exc:
        h5_links.write_settings({"access_code": "hack"}, u="小明")
    assert exc.value.status_code == 403
    # 设置未被篡改
    assert h5_links.get_h5_settings()["access_code"] == "1234"


def test_settings_put_ok_for_admin(h5_settings):
    out = h5_links.write_settings({"access_code": "9999"}, u="")
    assert out["access_code"] == "9999"


# --------------------------------------------------------------------------- #
# R1-c：门禁全覆盖（mother_question / mastery_path）                          #
# --------------------------------------------------------------------------- #

def test_mother_question_requires_code(h5_settings):
    with pytest.raises(HTTPException) as exc:
        with mq._h5_ctx("小明", "", ""):
            pass  # pragma: no cover
    assert exc.value.status_code == 401


def test_mother_question_code_ok(h5_settings):
    with mq._h5_ctx("小明", "1234", ""):
        pass  # 不抛


def test_mother_question_admin_unaffected(h5_settings):
    with mq._h5_ctx("", "", ""):
        pass  # u 缺省不受访问码约束


def test_mother_question_header_code_ok(h5_settings):
    # X-Access-Code 等效 ?code=
    with mq._h5_ctx("小明", "", "1234"):
        pass


def test_mastery_path_requires_code(h5_settings):
    with pytest.raises(HTTPException) as exc:
        with mp._h5_ctx("小明", "", ""):
            pass  # pragma: no cover
    assert exc.value.status_code == 401


def test_mastery_path_code_ok(h5_settings):
    with mp._h5_ctx("小明", "1234", ""):
        pass


def test_no_access_code_configured_allows(h5_settings, tmp_path: Path, monkeypatch):
    # 未配置 access_code 时任何 u 放行
    settings_dir = tmp_path / "user" / "settings"
    (settings_dir / "h5.json").write_text(
        json.dumps({"public_base": "", "access_code": ""}), encoding="utf-8"
    )
    with mq._h5_ctx("小明", "", ""):
        pass


# --------------------------------------------------------------------------- #
# R1-c：门禁全覆盖（notebook —— user_context/h5_user_guarded 手工收编模板）    #
# --------------------------------------------------------------------------- #

def test_notebook_requires_code(h5_settings):
    with pytest.raises(HTTPException) as exc:
        with nb._h5_ctx("小明", "", ""):
            pass  # pragma: no cover
    assert exc.value.status_code == 401


def test_notebook_code_ok(h5_settings):
    from deeptutor.multi_user.context import get_current_user_or_none

    with nb._h5_ctx("小明", "1234", ""):
        inside = get_current_user_or_none()
    # 上下文内是合成的 h5 用户，退出后还原
    assert inside is not None and inside.id == "h5_小明"
    assert get_current_user_or_none() is None


def test_notebook_header_code_ok(h5_settings):
    # X-Access-Code 等效 ?code=
    with nb._h5_ctx("小明", "", "1234"):
        pass


def test_notebook_admin_unaffected(h5_settings):
    with nb._h5_ctx("", "", ""):
        pass  # u 缺省（桌面 admin）不受访问码约束
