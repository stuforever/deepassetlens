# -*- coding: utf-8 -*-
"""M09 单测：Qdrant 基座/混合评分/词法管线过滤/静态同义兜底（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M09 spec §九验收标准锚定现有实现；
Qdrant/本地模型重依赖路径以降级桩+纯函数锚定，真值留联测）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.services.tupu_qdrant_client import (  # noqa: E402
    _to_filter,
    is_qdrant_backend_enabled,
)


# ---------------------------------------------------------------------------
# 任务 1：Qdrant 基座封装（spec §四）
# ---------------------------------------------------------------------------

def test_to_filter_conversion():
    """must 条件 dict→Qdrant Filter（spec §四 _to_filter；qdrant FieldCondition 完整形态）。
    变异锚点：过滤转换删 → 集合检索无法按 payload 过滤。"""
    f = _to_filter([{"key": "object_type", "match": {"value": "entity"}}])
    assert f is not None and f.must[0].key == "object_type"
    # 空入参→None
    assert _to_filter(None) is None
    assert _to_filter([]) is None


def test_backend_switch_env(monkeypatch):
    """后端开关 env（spec §三：TUPU_VECTOR_BACKEND=qdrant 切换）。
    变异锚点：开关读取删 → Qdrant 停机时业务层直连崩。"""
    monkeypatch.setenv("TUPU_VECTOR_BACKEND", "qdrant")
    assert is_qdrant_backend_enabled() is True
    monkeypatch.setenv("TUPU_VECTOR_BACKEND", "off")
    assert is_qdrant_backend_enabled() is False


# ---------------------------------------------------------------------------
# 任务 4：混合评分（spec §九.4 权重融合正确）
# ---------------------------------------------------------------------------

def test_hybrid_score_modes_and_weights():
    """hybrid_score：keyword/vector 直通；hybrid 按 (kw*kw_w+sem*sem_w)/total 融合。
    变异锚点：权重融合式改 → 语义/关键词配比漂移。"""
    from app.services.semantic_retrieval import hybrid_score
    cfg = {"retrieval_mode": "hybrid", "keyword_weight": 0.4, "vector_weight": 0.6}
    assert hybrid_score(1.0, 0.0, cfg) == pytest.approx(0.4)
    assert hybrid_score(0.0, 1.0, cfg) == pytest.approx(0.6)
    assert hybrid_score(0.5, 0.5, cfg) == pytest.approx(0.5)
    # 模式直通
    assert hybrid_score(0.7, 0.9, {**cfg, "retrieval_mode": "keyword"}) == pytest.approx(0.7)
    assert hybrid_score(0.7, 0.9, {**cfg, "retrieval_mode": "vector"}) == pytest.approx(0.9)
    # 权重传 0 → `or 0.4/0.6` falsy 陷阱：缺省权重生效（实测行为锚定，total<=0 分支不可达）
    assert hybrid_score(0.2, 0.8, {**cfg, "keyword_weight": 0, "vector_weight": 0}) == pytest.approx(0.56)


# ---------------------------------------------------------------------------
# 任务 5：混合检索词法管线（spec §九.5）
# ---------------------------------------------------------------------------

def test_tokenize_query_filters_and_preserves():
    """tokenize_query：空入参空返回；停用词剔除；域短语整词保留；数字 token 处理。
    变异锚点：停用词剔除删 → 「的/了」污染相似度；域短语切散 → 术语相似度崩。"""
    from app.services import hybrid_retrieval as H
    assert H.tokenize_query("") == []
    assert H.tokenize_query(None) == []
    # 停用词（取静态表样本构造，抗词表演进）
    if H._STOP_WORDS:
        sw = sorted(H._STOP_WORDS, key=len, reverse=True)[0]
        toks = H.tokenize_query(f"{sw}重过载台区")
        assert sw not in toks
    # 域短语整词保留（取静态集合样本）
    if H._DOMAIN_PHRASE_SET:
        phrase = sorted(H._DOMAIN_PHRASE_SET, key=len, reverse=True)[0]
        toks = H.tokenize_query(phrase)
        assert phrase in toks


def test_expand_synonyms_static_fallback():
    """同义词扩展静态兜底（spec §八.6：无 DB 时静态表可用；docstring：命中返回组变体，无命中 []）。
    变异锚点：静态兜底删 → 未 load DB 时扩展恒空；失败静默破坏。"""
    from app.services import hybrid_retrieval as H
    # 无命中 → []
    assert H.expand_synonyms_for_query("zz不存在的词xx") == []
    assert H.expand_synonyms_for_query("") == []
    # 静态表命中（取 _SYNONYM_MAP 首个 key 构造查询，抗词表演进）
    if H._SYNONYM_MAP:
        key = sorted(H._SYNONYM_MAP.keys())[0]
        variants = H.expand_synonyms_for_query(key)
        assert key in variants                       # 标准词在变体中
        for s in H._SYNONYM_MAP[key]:
            assert s in variants                     # 同义词全展开
        # max_variants 夹取
        capped = H.expand_synonyms_for_query(key, max_variants=1)
        assert len(capped) <= 1


# ---------------------------------------------------------------------------
# 词条 point 构建（spec §五 L2 归一化）
# ---------------------------------------------------------------------------

def test_l2_normalize_unit_vector():
    """_l2_normalize 输出单位向量（spec §五 point 构建含 L2 归一化）。
    变异锚点：归一化删 → 余弦相似度随向量幅值漂移。"""
    from app.services.standard_semantic_qdrant import _l2_normalize
    v = _l2_normalize([3.0, 4.0])
    norm = sum(x * x for x in v) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-6)
    # 零向量容错
    z = _l2_normalize([0.0, 0.0])
    assert all(x == 0 for x in z) or sum(x * x for x in z) ** 0.5 <= 1.0 + 1e-9
