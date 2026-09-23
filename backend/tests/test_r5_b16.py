# -*- coding: utf-8 -*-
"""R5批⑯（清单安全）契约测试。

- practice_generator._cache_path：chapter_id 净化（穿越拒绝）
- main._AuthedStatic：母题图片静态挂载包 require_auth（源码锚定）
- question parsed 模式：paper_path 收进 mimic 输出目录（源码锚定）
变异锚点：净化/包装/收口任一删除 → 对应测红。
"""
import inspect

import pytest

from app.services.sishu_full.learning import practice_generator as pg


def test_cache_path_sanitized():
    assert pg._cache_path("ch-1").name == "ch-1.json"
    assert pg._cache_path("第3章_要点").name == "第3章_要点.json"
    for bad in ("../evil", "a/b", "a:b", "", None, "x" * 200):
        with pytest.raises(ValueError):
            pg._cache_path(bad)


def test_mq_static_mount_authed():
    from app.services.sishu_full.api import main as mainmod
    src = inspect.getsource(mainmod)
    assert "_AuthedStatic" in src
    assert 'StaticFiles(directory=str(_mq_images_dir))' in src  # 仍由包装层托管
    assert 'name="mother-question-images"' in src


def test_paper_path_contained():
    from app.services.sishu_full.api.routers import question as q
    src = inspect.getsource(q)
    assert "paper_path 越界" in src
    assert "_mimic_root" in src
