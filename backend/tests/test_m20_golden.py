# -*- coding: utf-8 -*-
"""M20 单测：规范化族/Tier1 确定性检索/降级语义/锚定块（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M20 spec §八验收标准锚定现有实现）。
Tier2 真值（Qdrant 向量检索/reseed）留联测；monkeypatch _safe_client→None 锚定
「Qdrant 不可用→静默降级仅 Tier1 不阻断」（spec §三）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 规范化族（spec §三）
# ---------------------------------------------------------------------------

def test_norm_question_and_count_normalize():
    """规范化：空白标点规整+计数同义归一（数量/多少个→总数，spec §三 Tier1 口径）。
    变异锚点：计数归一删 → 「同类问题二问」Tier1 不命中（弱 embedding 环境瞎）。"""
    from app.services.golden_qa_service import _count_normalize, _norm_question
    assert _norm_question("  统计 用电客户总数!  ") == _norm_question("统计用电客户总数")
    # 原地替换语义（数量/多少个→总数），词序不重排
    assert _count_normalize("用电客户数量") == _count_normalize("用电客户总数")
    assert _count_normalize("多少个台区") == "总数台区"


def test_core_suffix_strip():
    """核心词后缀剥离（「用电客户主数据」≈「用电客户」，spec §八.2）。
    变异锚点：后缀剥离删 → 口语化变体绕过 Tier1。"""
    from app.services.golden_qa_service import _CORE_SUFFIX_RE
    assert _CORE_SUFFIX_RE.sub("", "用电客户主数据") == "用电客户"
    assert _CORE_SUFFIX_RE.sub("", "变压器台账") == "变压器"


def test_infer_engine():
    """从 SQL 推断引擎兜底（spec §三 _infer_engine）。变异锚点：推断删 → 引擎兜底失据。"""
    from app.services.golden_qa_service import _infer_engine
    assert isinstance(_infer_engine("SELECT 1"), str)


# ---------------------------------------------------------------------------
# 常量契约（spec §二/§五三级阈值）
# ---------------------------------------------------------------------------

def test_golden_constants():
    """集合名/阈值/条数上限（spec §十锚点：tupu_golden_qa/0.75/_MAX_TOP 3）。
    变异锚点：阈值漂移 → 三级递进（0.75<0.85<0.90）失衡。"""
    from app.services import golden_qa_service as G
    assert G.GOLDEN_COLLECTION == "tupu_golden_qa"
    assert G._SCORE_THRESHOLD_DEFAULT == 0.75
    assert G._MAX_TOP == 3
    assert G.SEED_MAX == 60


def test_bundle_cache_settings():
    """bundle 短窗缓存设置（spec §四：TTL 60s/SIZE 128，spec §十 L450-451）。
    变异锚点：缓存设置漂移 → 同问二次检索行为变。"""
    import inspect
    from app.services import golden_qa_service as G
    src = inspect.getsource(G)
    assert "TUPU_BUNDLE_CACHE_TTL" in src and "128" in src


# ---------------------------------------------------------------------------
# Tier1 确定性检索+降级（spec §三/§八.1）
# ---------------------------------------------------------------------------

@pytest.fixture()
def golden_row():
    """造一条金标行（直插 DB 避开 add_golden 的 Qdrant 同步），测后清理。"""
    from app.core.database import SessionLocal
    from app.models.base import KgGoldenQaSet
    import uuid
    db = SessionLocal()
    q = "统计重过载台区总数"
    # Tier1 运行时现算 _norm_question(question) 比对（无 question_norm 落列——偏差登记）
    row = KgGoldenQaSet(
        question=q,
        expected_sql="SELECT COUNT(*) FROM kg_tupu_object WHERE object_type='transformer' AND status='overload'",
        expected_result_digest="{}",
        route_type="sql",
        enabled=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    yield row, db
    try:
        db.delete(row)
        db.commit()
    finally:
        db.close()


def test_tier1_exact_hit_with_degradation(monkeypatch, golden_row):
    """Tier1 规范化精确命中 score=1.0；Qdrant 不可用静默降级不阻断（spec §三/§八.1）。
    monkeypatch _safe_client→None 模拟向量库挂——降级路径强锚定。
    变异锚点：降级抛异常 → 向量库故障放大为问答故障（违反 §三）。"""
    from app.services import golden_qa_service as G
    monkeypatch.setattr(G, "_safe_client", lambda: None)
    row, db = golden_row
    hits = G.search_golden_qa(db, "统计重过载台区数量")  # 计数归一 → Tier1 命中
    assert isinstance(hits, list)
    assert any(h.get("score") == 1.0 for h in hits), f"Tier1 未命中: {hits}"
    assert all(h.get("sql") for h in hits)  # 金标行带 SQL（库内既有标准题或 fixture 行）


def test_tier1_no_hit_empty(monkeypatch):
    """无命中 → 空列表（降级模式，spec §五：无命中 block 空串不阻断）。"""
    from app.services import golden_qa_service as G
    monkeypatch.setattr(G, "_safe_client", lambda: None)
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        hits = G.search_golden_qa(db, "m20 完全不存在的词条组合 xyzz")
        assert hits == []
    finally:
        db.close()


def test_build_golden_payload_empty_graceful(monkeypatch):
    """锚定块：无命中/降级时 block 空串 hits 空不阻断（spec §五）。
    变异锚点：锚定块抛错 → 契约注入失败放大为问答中断。"""
    from app.services import golden_qa_service as G
    monkeypatch.setattr(G, "_safe_client", lambda: None)
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        payload = G.build_golden_payload(db, "m20 不存在词条 xyzz")
        block = payload.get("block") if isinstance(payload, dict) else payload
        assert isinstance(block, str) and block == ""
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 生命周期与 API 面（spec §六/§二）
# ---------------------------------------------------------------------------

def test_hit_count_and_feedback_functions():
    """命中计数+反馈记录函数（spec §六：bump_golden_hit/record_feedback）。
    变异锚点：计数删 → 金标热度统计失效（M22 观测断）。"""
    from app.services import golden_qa_service as G
    assert hasattr(G, "bump_golden_hit") and hasattr(G, "record_feedback")
    assert hasattr(G, "list_candidate_recommendations")


def test_golden_qa_api_endpoints():
    """golden-qa API 七端点（spec §二：CRUD+seed/reseed+candidates）。
    变异锚点：seed 删 → 种子提炼断（M10 成功日志不回流）。"""
    from app.api import golden_qa as A
    paths = " ".join(getattr(r, "path", "") for r in A.router.routes)
    assert "seed" in paths and "candidates" in paths
    assert len(A.router.routes) >= 7
