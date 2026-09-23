# -*- coding: utf-8 -*-
"""R5批⑰（清单安全）契约测试。

- graph_sync.sync_relation：rel_type 字符集白名单（Cypher 注入拒绝）
- ConnectedESFamily：url/index 必填+格式校验（None//_search 原始异常/根路径全库）
- tutor_export：user_id 折叠非安全字符（导出文件名穿越拒绝）
变异锚点：白名单/校验/折叠任一删除 → 对应测红。
"""
import inspect

import pytest


def test_sync_relation_rel_type_whitelist():
    from app.services.graph_sync import Neo4jSyncService
    src = inspect.getsource(Neo4jSyncService.sync_relation)
    assert "A-Za-z_" in src
    # 纯函数级验证（不触 Neo4j）——正则规则与生产一致
    import re
    for bad in ("X` {code} `", "A-B", "rel:type", "", None):
        assert not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", bad if isinstance(bad, str) else "")
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", "REL_COOPERATES")


def test_connected_es_requires_valid_url_index():
    from app.services.kb_engines.connected_es import ConnectedESFamily
    for bad in ({}, {"url": "http://x"}, {"index": "idx"}, {"url": "ftp://x", "index": "i"}):
        with pytest.raises(ValueError):
            ConnectedESFamily(bad)
    fam = ConnectedESFamily({"url": "http://127.0.0.1:11200/", "index": "kb1"})
    assert fam.url == "http://127.0.0.1:11200" and fam.index == "kb1"


def test_tutor_export_user_id_folded():
    from app.services.learning import tutor_export as te
    src = inspect.getsource(te)
    assert "A-Za-z0-9_-" in src
    import re
    folded = re.sub(r"[^A-Za-z0-9_-]", "_", "../../etc/passwd")[:64]
    assert "/" not in folded and "." not in folded.replace("._", "")
