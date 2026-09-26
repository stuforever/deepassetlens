# -*- coding: utf-8 -*-
"""R4 协同写作 MCP 3 件测试：列表/读取/两段臂写入。"""
from __future__ import annotations

from pathlib import Path

import pytest

import app.mcp_server as ms
from app.services import memory_runtime as mr
from app.services.sishu_full.co_writer import storage as cw_storage


@pytest.fixture(autouse=True)
def _tmp_docs(tmp_path, monkeypatch):
    root = tmp_path / "docs"

    class _PS:
        def get_co_writer_docs_dir(self):
            return root

        def get_co_writer_doc_root(self, doc_id):
            return root / f"doc_{doc_id}"  # 真实 path_service 加 doc_ 前缀（list_doc_ids 过滤依据）

        def get_co_writer_doc_manifest(self, doc_id):
            return root / f"doc_{doc_id}" / "manifest.json"

    st = cw_storage.CoWriterStorage(path_service=_PS())
    # mcp_server 是 from-import 绑定（_cws），须补丁消费方引用（注册期捕获引用则 patch 不可达）
    monkeypatch.setattr(ms, "_cws", lambda: st)
    return root


def test_list_and_two_arm_write():
    token = mr.set_runtime("sishu", "tester", "sess-cw")
    try:
        # 空列表
        r0 = ms.list_documents()
        assert r0["status"] == "ok" and r0["count"] == 0
        # 两段臂：预检
        r1 = ms.write_document(title="我的草稿", content="# 草稿\n正文")
        assert r1["status"] == "pending_confirmation" and r1["confirm_token"]
        # 错 token 拒
        r2 = ms.write_document(title="x", content="y", confirm_token="bad.token")
        assert r2["status"] == "denied"
        # 对 token 执行（新建）
        r3 = ms.write_document(title="我的草稿", content="# 草稿\n正文",
                               confirm_token=r1["confirm_token"])
        assert r3["status"] == "ok" and r3["id"]
        doc_id = r3["id"]
        # 读取
        rd = ms.read_document(doc_id)
        assert rd["status"] == "ok" and "草稿" in rd["content"]
        # 更新（两段臂）
        r4 = ms.write_document(doc_id=doc_id, content="# 草稿V2\n改好了")
        assert r4["status"] == "pending_confirmation"
        r5 = ms.write_document(doc_id=doc_id, content="# 草稿V2\n改好了",
                               confirm_token=r4["confirm_token"])
        assert r5["status"] == "ok"
        assert "V2" in ms.read_document(doc_id)["content"]
        # 列表计数
        assert ms.list_documents()["count"] == 1
        # 不存在的文档读取报错
        assert ms.read_document("nonexistent")["status"] == "error"
    finally:
        mr.set_runtime_token(token)
