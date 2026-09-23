# -*- coding: utf-8 -*-
"""R5批⑪（清单安全）契约测试：grants 路径净化+读取失败 fail-closed+path_service 不回退。

变异锚点：净化删除/空白名单回退改回/共享实例回退复活 → 对应测红。
"""
import json

import pytest


def test_grant_path_rejects_traversal(tmp_path, monkeypatch):
    from app.services.sishu.compat import grants
    monkeypatch.setattr(grants, "GRANTS_DIR", tmp_path)
    for bad in ("../x", "a/b", "a" + chr(92) + "b", "a:b", "..", "", None):
        with pytest.raises(ValueError):
            grants.grant_path(bad)


def test_load_grant_corrupt_file_fails_closed(tmp_path, monkeypatch):
    from app.services.sishu.compat import grants
    monkeypatch.setattr(grants, "GRANTS_DIR", tmp_path)
    (tmp_path / "u1.json").write_text("{corrupt!!", encoding="utf-8")
    g = grants.load_grant("u1")
    # 半写/损坏 → 全空白名单（fail-closed），不是 enabled_tools=None 的全量放行
    assert g["enabled_tools"] == []
    assert g["mcp_tools"] == []
    assert g["cli_apps"] == []
    assert g["exec_enabled"] is False


def test_load_grant_missing_file_keeps_default(tmp_path, monkeypatch):
    """文件不存在=从未配置 → v2 语义默认不受限（现状等价，fail-closed 只针对损坏）。"""
    from app.services.sishu.compat import grants
    monkeypatch.setattr(grants, "GRANTS_DIR", tmp_path)
    g = grants.load_grant("nobody")
    assert g["enabled_tools"] is None


def test_get_path_service_no_shared_fallback(monkeypatch):
    import app.services.sishu.compat.paths as paths_mod
    from app.services.sishu.services import path_service as ps

    def _boom():
        raise RuntimeError("resolution failed")

    monkeypatch.setattr(paths_mod, "get_current_path_service", _boom)
    with pytest.raises(RuntimeError):
        ps.get_path_service()
