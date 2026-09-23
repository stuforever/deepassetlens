# -*- coding: utf-8 -*-
"""R5批⑨（清单安全）契约测试：h5 访问码门禁双轨堵漏。

- h5_user_guarded：纯空白 u 不再在门禁前直通 admin（?u=%20 绕过）
- learner_profile.ask：改走统一守卫（带 code/access-code 校验）
- resolve_h5_current_user 不再公开导出（防未来误用）
变异锚点：空白直通/守卫旁路任一回退 → 对应测红。
"""
import inspect

import pytest
from fastapi import HTTPException

from app.services.sishu_full.multi_user import h5 as h5full
from app.services.sishu.compat import h5 as h5sishu


@pytest.mark.parametrize("mod", [h5full, h5sishu])
def test_whitespace_u_no_longer_bypasses(monkeypatch, mod):
    monkeypatch.setattr(mod, "_load_h5_settings", lambda: {"access_code": "secret"})
    with pytest.raises(HTTPException) as ei:
        mod.h5_user_guarded("  ")          # 原行为：直通 local_admin_user
    assert ei.value.status_code == 401
    with pytest.raises(HTTPException) as ei:
        mod.h5_user_guarded("%20")         # 编码空格同理
    assert ei.value.status_code == 401


@pytest.mark.parametrize("mod", [h5full, h5sishu])
def test_empty_u_still_admin_and_correct_code_passes(monkeypatch, mod):
    monkeypatch.setattr(mod, "_load_h5_settings", lambda: {"access_code": "secret"})
    u = mod.h5_user_guarded("")            # 缺省=admin（现状等价）
    assert u.role == "admin"
    u2 = mod.h5_user_guarded("stu1", code="secret")   # 正确访问码放行
    assert u2.username == "stu1"
    with pytest.raises(HTTPException):
        mod.h5_user_guarded("stu1", code="wrong")


def test_resolve_removed_from_exports():
    for mod in (h5full, h5sishu):
        assert "resolve_h5_current_user" not in (mod.__all__ or [])


def test_ask_endpoint_uses_guard():
    """源码锚定：两份 ask 端点必须走 h5_user_guarded（不再旁路 resolve）。"""
    from app.services.sishu_full.api.routers import learner_profile as lp_full
    from app.api.sishu_learning import learner_profile as lp_sishu
    for mod in (lp_full, lp_sishu):
        src = inspect.getsource(mod)
        assert "h5_user_guarded(u" in src
        assert "resolve_h5_current_user(" not in src
