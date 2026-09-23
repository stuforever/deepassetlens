# -*- coding: utf-8 -*-
"""R5批⑩（清单安全）契约测试：图片 URL 回解析 + path_service 外部 ID 净化。

- resolve_url_to_path（vendor 双拷贝）：绝对路径分支废除 + ../ 逃逸拒绝（归一化后必须
  落图片根内）
- path_service：task_id/session_id/notebook_id/doc_id 外部 ID 净化（穿越拒绝）
变异锚点：绝对路径分支/归一化校验/ID 净化任一删除 → 对应测红。
"""
import pytest


@pytest.fixture()
def img_root(tmp_path, monkeypatch):
    root = tmp_path / "images"
    (root / "mq" / "2026-09-23").mkdir(parents=True)
    (root / "mq" / "2026-09-23" / "a.jpg").write_bytes(b"jpg")
    for modname in ("app.services.sishu.learning.image_pipeline",
                    "app.services.sishu_full.learning.image_pipeline"):
        mod = __import__(modname, fromlist=["_images_root"])
        monkeypatch.setattr(mod, "_images_root", lambda r=root: r)
        monkeypatch.setattr(mod, "_public_base", lambda: "/api/v1/files")
    return root


def test_resolve_public_url_ok(img_root):
    for modname in ("app.services.sishu.learning.image_pipeline",
                    "app.services.sishu_full.learning.image_pipeline"):
        mod = __import__(modname, fromlist=["resolve_url_to_path"])
        p = mod.resolve_url_to_path("/api/v1/files/mq/2026-09-23/a.jpg")
        assert p is not None and p.name == "a.jpg"


def test_resolve_rejects_absolute_and_traversal(img_root):
    for modname in ("app.services.sishu.learning.image_pipeline",
                    "app.services.sishu_full.learning.image_pipeline"):
        mod = __import__(modname, fromlist=["resolve_url_to_path"])
        existing = str(img_root.parent / "secret.txt")
        (img_root.parent / "secret.txt").write_bytes(b"s")
        assert mod.resolve_url_to_path(existing) is None          # 绝对路径分支废除
        assert mod.resolve_url_to_path("/api/v1/files/../../secret.txt") is None  # 穿越
        assert mod.resolve_url_to_path("https://cdn.example.com/a.png") is None
        assert mod.resolve_url_to_path("") is None


def test_path_service_id_sinks_sanitized():
    from app.services.sishu.services.path_service import PathService
    svc = PathService.get_instance()
    for bad in ("../evil", "a/b", "a\b", "a:b", "..", ""):
        with pytest.raises(ValueError):
            svc.get_task_workspace("chat", bad)
        with pytest.raises(ValueError):
            svc.get_session_workspace("chat", bad)
    with pytest.raises(ValueError):
        svc.get_notebook_file("../nb")
    with pytest.raises(ValueError):
        svc.get_co_writer_doc_root("../doc")
    ok = svc.get_task_workspace("chat", "task-1")
    assert str(ok).replace("\\", "/").endswith("/chat/task-1") or ok.name == "task-1"
