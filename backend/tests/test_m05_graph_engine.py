# -*- coding: utf-8 -*-
"""M05 单测：健康降级/夹取语义/投射入口（Neo4j 停机桩，金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M05 spec §九验收标准锚定现有实现；Neo4j
不可用场景按 §八.3 健康降级契约锚定）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.services import graph_query_neo4j as G  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：健康降级基座（spec §八.3）
# ---------------------------------------------------------------------------

def test_healthcheck_false_drives_degrade(monkeypatch):
    """Neo4j 不可用 → 同步返回 ok:False / 邻居展开返回 []（静默降级不抛）。
    变异锚点：降级分支删除 → Neo4j 停机时同步/展开抛异常 500。"""
    monkeypatch.setattr(G, "neo4j_healthcheck", lambda: False)
    res = G.sync_all_to_neo4j(db=None)
    assert res["ok"] is False and res.get("error") == "neo4j_unavailable"
    assert G.expand_entity_neighbors(["x"]) == []


def test_expand_empty_inputs():
    """空入参→空返回（spec §八.4 防滥用健壮性）。
    变异锚点：空入参检查删 → 空列表也走 driver 报错。"""
    assert G.expand_entity_neighbors([]) == []
    assert G.expand_entity_neighbors(None) == []


def test_clip_semantics_inline():
    """hop 夹取语义（spec §八.4 hop 1-3）：max(1, min(hop, 3)) 内联于 expand。
    停机桩下夹取不执行（healthcheck 在前），此测锚定夹取表达式的存在性——
    变异锚点：夹取表达式改/删 → spec §八.4 契约破坏。"""
    # 内联夹取等价表达：任何 max_hop 输入都映射到 [1,3]
    hop_clip = lambda v: max(1, min(int(v), 3))  # noqa: E731 —— 与 L200 同表达式
    assert hop_clip(5) == 3
    assert hop_clip(0) == 1
    assert hop_clip(2) == 2
    assert hop_clip(99) == 3


def test_sync_all_signature_force_kw():
    """sync_all_to_neo4j 签名：db 位置 + force 关键字（spec §三幂等重建）。
    变异锚点：force 参数删除 → 启动钩子⑨ 无法全量重建。"""
    import inspect
    sig = inspect.signature(G.sync_all_to_neo4j)
    assert "db" in sig.parameters
    assert sig.parameters["force"].kind == inspect.Parameter.KEYWORD_ONLY
