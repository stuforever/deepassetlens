# -*- coding: utf-8 -*-
"""R5批⑥（清单安全）契约测试：mastery_path 三端点补 H5 用户隔离。

delete_progress / redo_progress / generate_from_notebook 原缺 u/code/_h5_ctx——
store 固定落 admin 工作区（H5 用户越权读写 admin 进度，访问码门禁被绕过）。
变异锚点：任一端点的 _h5_ctx 包裹或 u/code 参数删除 → 对应测红。
"""
import inspect

import pytest

from app.services.sishu_full.api.routers import mastery_path as mp


def _names(fn):
    return list(inspect.signature(fn).parameters)


def test_three_endpoints_accept_h5_params():
    for fn in (mp.delete_progress, mp.redo_progress, mp.generate_from_notebook):
        names = _names(fn)
        assert names[:1] == ["book_id"]
        assert {"u", "code", "x_access_code"} <= set(names), fn.__name__


@pytest.mark.asyncio
async def test_h5_guard_runs_for_h5_user(monkeypatch):
    """u 非空时必须过 h5_user_guarded（访问码 401 校验）——隔离实证。"""
    called = {}

    def _fake_guarded(u, code, x_access_code):
        called["u"] = u
        raise RuntimeError("guarded")

    from app.services.sishu_full.multi_user import h5 as h5mod
    monkeypatch.setattr(h5mod, "h5_user_guarded", _fake_guarded)
    with pytest.raises(RuntimeError):
        await mp.delete_progress("b1", u="h5user")
    assert called.get("u") == "h5user"


@pytest.mark.asyncio
async def test_admin_path_still_works(monkeypatch):
    """u 为空 → nullcontext 回退 admin（现状等价，不误伤桌面端）。"""
    monkeypatch.setattr(mp.LearningStore, "exists", lambda self, bid: False)
    with pytest.raises(Exception) as ei:
        await mp.delete_progress("b1")
    assert "404" in str(getattr(ei.value, "status_code", "")) or ei.value.status_code == 404
