"""P2-C2 / P3-B：H5 家庭关联 + 公网设置端点测试。

覆盖：links 增/查/删去重；settings 读写与 public_base 前缀校验。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from deeptutor.api.routers import h5_links


@pytest.fixture
def tmp_links(tmp_path: Path, monkeypatch):
    """把 USERS_ROOT 重定向到 tmp/users（h5_links.json/settings 落在 tmp/）。"""
    users_root = tmp_path / "users"
    users_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(h5_links, "USERS_ROOT", users_root)
    return tmp_path


def test_add_and_list_link(tmp_links: Path):
    assert h5_links.add_link({"parent": "妈妈", "child": "小明", "note": "儿子"}) == {"ok": True}
    out = h5_links.list_links(parent="妈妈")
    assert out == {"children": [{"child": "小明", "note": "儿子"}]}
    # 反查：小明视角不应列出
    out2 = h5_links.list_links(parent="小明")
    assert out2 == {"children": []}


def test_add_link_dedup(tmp_links: Path):
    h5_links.add_link({"parent": "妈妈", "child": "小明"})
    h5_links.add_link({"parent": "妈妈", "child": "小明", "note": "覆盖不生效"})
    out = h5_links.list_links(parent="妈妈")
    assert len(out["children"]) == 1
    assert out["children"][0]["note"] == ""


def test_remove_link(tmp_links: Path):
    h5_links.add_link({"parent": "妈妈", "child": "小明"})
    h5_links.add_link({"parent": "妈妈", "child": "小红"})
    assert h5_links.remove_link(parent="妈妈", child="小明") == {"ok": True}
    out = h5_links.list_links(parent="妈妈")
    assert [c["child"] for c in out["children"]] == ["小红"]


def test_illegal_parent_rejected(tmp_links: Path):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        h5_links.list_links(parent="../evil")
    assert exc.value.status_code == 400


def test_settings_read_default(tmp_links: Path):
    s = h5_links.get_h5_settings()
    assert s == {"public_base": "", "access_code": ""}


def test_settings_write_and_read(tmp_links: Path):
    h5_links.write_settings({"public_base": "https://abc.trycloudflare.com", "access_code": "1234"})
    s = h5_links.get_h5_settings()
    assert s["public_base"] == "https://abc.trycloudflare.com"
    assert s["access_code"] == "1234"


def test_settings_public_base_must_be_http(tmp_links: Path):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        h5_links.write_settings({"public_base": "abc.com"})
    assert exc.value.status_code == 400


# --------------------------------------------------------------------------- #
# P3-B 访问码门禁（multi_user.h5.access_code_ok）                              #
# --------------------------------------------------------------------------- #

def test_access_code_admin_unaffected(tmp_path: Path, monkeypatch):
    """u 缺省（admin/桌面）不受访问码约束。"""
    from deeptutor.multi_user import h5 as h5_mod

    monkeypatch.setattr(h5_mod, "USERS_ROOT", tmp_path / "users")
    assert h5_mod.access_code_ok("", "") is True
    assert h5_mod.access_code_ok("", "anything") is True


def test_access_code_disabled_by_default(tmp_path: Path, monkeypatch):
    """未配置 access_code 时任何 u 都放行。"""
    from deeptutor.multi_user import h5 as h5_mod

    monkeypatch.setattr(h5_mod, "USERS_ROOT", tmp_path / "users")
    assert h5_mod.access_code_ok("小明", "") is True


def test_access_code_requires_match(tmp_path: Path, monkeypatch):
    """配置 access_code 后：u 非空必须带正确 code。"""
    import json

    from deeptutor.multi_user import h5 as h5_mod

    users_root = tmp_path / "users"
    users_root.mkdir(parents=True, exist_ok=True)
    settings_dir = tmp_path / "user" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "h5.json").write_text(
        json.dumps({"access_code": "1234"}), encoding="utf-8"
    )
    monkeypatch.setattr(h5_mod, "USERS_ROOT", users_root)

    assert h5_mod.access_code_ok("小明", "") is False
    assert h5_mod.access_code_ok("小明", "wrong") is False
    assert h5_mod.access_code_ok("小明", "1234") is True
    # admin 仍不受约束
    assert h5_mod.access_code_ok("", "1234") is True
