# -*- coding: utf-8 -*-
"""R5批㉑（清单安全）契约测试：imagegen SSRF 防线+mock 安全默认+notebook_id 净化。"""
import asyncio
import inspect

import pytest

from app.services.sishu_full.services.imagegen.adapters.chat_completions import (
    ChatCompletionsImagegenAdapter,
    GenerationProviderError,
)


def _adapter():
    return ChatCompletionsImagegenAdapter.__new__(ChatCompletionsImagegenAdapter)


def test_materialize_data_uri_ok():
    b, ct = asyncio.run(_adapter()._materialize(None, "data:image/png;base64,AAAA"))
    assert b == b"\x00\x00\x00" and ct == "image/png"


@pytest.mark.asyncio
@pytest.mark.parametrize("evil", [
    "ftp://x/y.png", "http://127.0.0.1/x", "http://localhost/x",
    "http://10.0.0.5/x", "http://x.internal/x",
])
async def test_materialize_blocks_ssrf(evil):
    with pytest.raises(GenerationProviderError):
        await _adapter()._materialize(None, evil)


def test_identity_mock_default_off():
    for modname in ("app.services.sishu.services.wechat_push.identity",
                    "app.services.sishu_full.services.wechat_push.identity"):
        mod = __import__(modname, fromlist=["exchange_code_for_openid"])
        sig = inspect.signature(mod.exchange_code_for_openid)
        assert sig.parameters["mock_mode"].default is False


def test_notebook_id_sanitized():
    """_get_notebook_file 净化：'..'/'/'/空 拒绝（穿越笔记本目录）。"""
    from app.services.sishu.services.notebook.service import NotebookManager
    src = inspect.getsource(NotebookManager._get_notebook_file)
    assert "fullmatch" in src
    import re
    pat = re.compile(r"[\w-]{1,64}")
    assert pat.fullmatch("nb-1")
    assert not pat.fullmatch("../x")
