# -*- coding: utf-8 -*-
"""R5批⑮（清单安全）契约测试。

- agentic_pipeline：APPLICATION 隔离下 exec 授权解析异常 fail-closed（原 fail-open）
- visualize.build_fallback_html：title/summary/note HTML 转义（原注入面）
变异锚点：fail-open 回 True / 转义删除 / 剥离删除 → 对应测红。
"""
import inspect

from app.services.sishu_full.agents.visualize.utils import build_fallback_html


def test_fallback_html_escapes():
    out = build_fallback_html(title='<script>alert(1)</script>',
                              summary="<img src=x onerror=alert(2)> 摘要",
                              note="注释<b>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "<img" not in out
    assert "&lt;b&gt;" in out


def test_agentic_exec_auth_fail_closed_source():
    """源码锚定：APPLICATION 分支的 except 路径 return False（不再 fail-open）。"""
    from app.services.sishu_full.agents.chat import agentic_pipeline as ap
    src = inspect.getsource(ap)
    assert "R5批⑮（清单安全）：解析异常不再 fail-open" in src
    # except 块内的 return False 存在于 APPLICATION 分支附近（粗粒度结构守卫）
    seg = src[src.index("IsolationLevel.APPLICATION"):src.index("IsolationLevel.APPLICATION") + 800]
    assert "return False" in seg
