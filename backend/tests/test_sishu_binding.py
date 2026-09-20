# -*- coding: utf-8 -*-
"""v4批2 2.4：?u= 绑定单点 TDD（R3-C2）。
auth=0 桌面缺省=admin；auth=1 student 两形（username/h5_{username}）放行；
auth=1 跨用户 u=→403「未获该用户数据授权」。auth-mode-agnostic：monkeypatch ENABLE_AUTH。"""
from fastapi import HTTPException
import pytest

from app.core.auth import AuthUser
from app.services.sishu_data.binding import sishu_user_binding


def _req_as(username: str, roles: list[str] | None = None):
    """构造 get_current_user 可读的 request（state.user=AuthUser）。"""

    class _State:
        pass

    class _FakeRequest:
        pass

    r = _FakeRequest()
    r.state = _State()
    r.state.user = AuthUser(sub=username, username=username, email=None,
                            groups=[], roles=roles or ["viewer"])
    return r


def test_binding_auth0_desktop_default(monkeypatch):
    monkeypatch.setattr("app.services.sishu_data.binding.ENABLE_AUTH", False)
    assert sishu_user_binding(None, _req_as("anyone")) == "admin"      # 桌面语义：u 缺省=admin
    assert sishu_user_binding("h5_someone", _req_as("anyone")) == "h5_someone"  # auth=0 自由透传


def test_binding_auth1_student_ok(monkeypatch):
    monkeypatch.setattr("app.services.sishu_data.binding.ENABLE_AUTH", True)
    req = _req_as("student", ["viewer"])
    assert sishu_user_binding("student", req) == "student"
    assert sishu_user_binding("h5_student", req) == "h5_student"       # 两形别名


def test_binding_auth1_cross_user_403(monkeypatch):
    monkeypatch.setattr("app.services.sishu_data.binding.ENABLE_AUTH", True)
    with pytest.raises(HTTPException) as e:
        sishu_user_binding("h5_student1", _req_as("student2", ["viewer"]))   # C2 负向
    assert e.value.status_code == 403
    assert "未获该用户数据授权" in e.value.detail


def test_binding_auth1_student_no_u_403(monkeypatch):
    monkeypatch.setattr("app.services.sishu_data.binding.ENABLE_AUTH", True)
    with pytest.raises(HTTPException) as e:
        sishu_user_binding(None, _req_as("student", ["viewer"]))             # 非 admin 缺省 u=→403
    assert e.value.status_code == 403


def test_binding_auth1_admin_passthrough(monkeypatch):
    monkeypatch.setattr("app.services.sishu_data.binding.ENABLE_AUTH", True)
    assert sishu_user_binding("h5_other", _req_as("akadmin", ["admin"])) == "h5_other"  # admin 一票
