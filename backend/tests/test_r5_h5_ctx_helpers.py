# -*- coding: utf-8 -*-
"""R5批⑫（清单安全）契约测试：本地 _h5_ctx 助手空白直通堵漏 + sessions 写端点隔离。

变异锚点：nullcontext 空白直通复活 / sessions 写端点参数或 with 删除 → 对应测红。
"""
import inspect

import pytest
from fastapi import HTTPException

import app.services.sishu_full.api.routers.mastery_path as mp
import app.services.sishu_full.api.routers.mother_question as mq
import app.services.sishu_full.api.routers.notebook as nb
from app.services.sishu_full.multi_user import h5 as h5mod


@pytest.mark.parametrize("mod", [mp, mq, nb])
def test_local_ctx_helpers_reject_whitespace(monkeypatch, mod):
    """u='  ' → 经守卫 401（access_code 启用时），不再 nullcontext 直通 admin。
    守卫在 _h5_ctx 调用时即执行（401 在构造期抛出）。"""
    monkeypatch.setattr(h5mod, "_load_h5_settings", lambda: {"access_code": "s"})
    with pytest.raises(HTTPException) as ei:
        mod._h5_ctx("  ")
    assert ei.value.status_code == 401
    # 缺省（None/""）仍回退 admin——现状等价守卫
    ctx = mod._h5_ctx("")
    assert hasattr(ctx, "__enter__")


def test_sessions_write_endpoints_isolated():
    """源码锚定：五个写端点签名带 u/code/x_access_code 且包 user_context(h5_user_guarded)。"""
    import app.services.sishu_full.api.routers.sessions as ss
    for fn_name in ("rename_session", "delete_session", "update_branch_selection",
                    "delete_turn_by_message", "record_quiz_results"):
        fn = getattr(ss, fn_name)
        names = list(inspect.signature(fn).parameters)
        assert {"u", "code", "x_access_code"} <= set(names), fn_name
        src = inspect.getsource(fn)
        assert "user_context(h5_user_guarded(u, code, x_access_code))" in src, fn_name
