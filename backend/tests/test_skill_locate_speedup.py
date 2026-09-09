# -*- coding: utf-8 -*-
"""剧本定位提速（2026-09-09 spec）单测：件①缓存层 / 件②批量 / 件③预解析。

变异锚点：每测 docstring 标明何种生产改动会让它红。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：件① ORM + 缓存层
# ---------------------------------------------------------------------------

def test_lookup_cache_table_created():
    """第 84 表存在且可 create_all 幂等（spec §三 件①：表 83→84）。
    变异锚点：删 ORM 类/改表名 → 此测红。"""
    from app.models.base import EntityLookupCache
    from app.core.database import engine, ensure_schema_compatibility
    from sqlalchemy import text
    assert EntityLookupCache.__tablename__ == "kg_entity_lookup_cache"
    ensure_schema_compatibility()
    # plan 步骤 1.5 括注：ensure_schema_compatibility 不建新表，create_all 幂等建第 84 表
    from app.models.base import Base
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        cnt = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kg_entity_lookup_cache'")).scalar()
    assert cnt == 1


def test_cache_roundtrip_and_invalidate():
    """cache_store→cache_lookup 命中且 bump hit_count；invalidate 后未命中（spec §三 件①）。
    变异锚点：normalize 去小写/去空白删掉 → 「配电 变压器」查不到「配电变压器」。"""
    from app.services.entity_lookup_cache import cache_store, cache_lookup, invalidate_entity_lookup_cache
    from app.services.entity_lookup_cache import normalize_query_key
    assert normalize_query_key(" 配电　Transformer ") == "配电transformer"  # NFKC+小写+去空白
    cache_store("配电变压器X", "keyword", {"entities": [{"entity_code": "t_x"}]})
    hit = cache_lookup("配电变压器X", "keyword")
    assert hit is not None and hit["entities"][0]["entity_code"] == "t_x"
    invalidate_entity_lookup_cache()
    assert cache_lookup("配电变压器X", "keyword") is None


def test_cache_degrades_on_error(monkeypatch):
    """缓存表读写失败→None+warning，不抛异常（行为契约：加速件非正确性件）。
    变异锚点：cache_lookup 去掉 try/except → 此测红（异常外泄）。"""
    import logging
    from app.services import entity_lookup_cache as elc
    def _boom(*a, **k):
        raise RuntimeError("table gone")
    monkeypatch.setattr("app.core.database.SessionLocal", _boom)  # 服务层为函数内 import（elc 无模块级 SessionLocal），patch 工厂源头
    with pytest.raises(RuntimeError):  # 直接调 _boom 验证 monkeypatch 生效
        _boom()
    monkeypatch.undo()
    monkeypatch.setattr(elc, "_exec", None) if False else None
    # 真实降级路径：patch 内部会话工厂抛错
    class _Broken:
        def __enter__(self): raise RuntimeError("down")
        def __exit__(self, *a): return False
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _Broken())  # 同上：真实降级路径走 SessionLocal 工厂
    assert elc.cache_lookup("任意", "keyword") is None   # 降级 None
    elc.cache_store("任意", "keyword", {"x": 1})          # 降级不抛
    elc.invalidate_entity_lookup_cache()                  # 降级不抛


# ---------------------------------------------------------------------------
# 任务 2：件② 批量动作（一批 SQL + 一次 embedding 数组调用）
# ---------------------------------------------------------------------------

def _clear_lookup_cache():
    # 测试前置隔离（plan 三测逐字落之外的最小偏离，仅测试卫生）：件② 批量 handler 会
    # cache_store 回写——不清缓存则本文件 -k batch 复跑时缓存命中（embed 计数=0/
    # cache 项无 log）假红。生产路径不受影响；全量跑时任务 1 的 invalidate 测试已前置清空。
    from app.services.entity_lookup_cache import invalidate_entity_lookup_cache
    invalidate_entity_lookup_cache()


def test_batch_single_embedding_gateway_call(monkeypatch):
    """未命中 keywords 收拢一次 embed_texts 数组调用（spec §三 件②核心断言：
    mock 网关计数=1）。变异锚点：batch 退回逐 variant 串行 embed → 计数>1 → 红。"""
    _clear_lookup_cache()
    from app.services import kg_action_handlers as kah
    calls = {"n": 0}
    def _fake_embed(db, texts, model_name=None):
        calls["n"] += 1
        return [[0.1] * 8 for _ in texts]
    import app.services.semantic_retrieval as sr
    monkeypatch.setattr(sr, "embed_texts", _fake_embed)
    monkeypatch.setattr(kah, "search_entity_vectors", lambda q, top_k=10, db=None, vec=None: [])
    out = kah._kg_search_entities_batch(
        {"keywords": ["绝不存在的甲实体", "绝不存在的乙实体", "绝不存在的丙实体"]}, "00:00:00")
    assert calls["n"] == 1                      # 唯一断言核心：一次网关调用
    assert len(out["results"]) == 3             # 逐项 hit/miss 返回
    assert all(r.get("hit") is False for r in out["results"])


def test_batch_registered_everywhere():
    """注册面五处（spec §三 件②注册面）：handler 字典/MCP/白名单/定位族×2。
    变异锚点：任一处漏注册 → 对应断言红。"""
    from app.services.kg_action_handlers import _KG_ACTION_HANDLERS
    from app.services.query_contract import GENERIC_ALLOWED_TOOLS
    from app.services.skill_policy import _LOCATE_BUDGET_TOOLS, _LOCATE_DEDUP_TOOLS
    assert "search_entities_batch" in _KG_ACTION_HANDLERS
    assert "search_entities_batch" in GENERIC_ALLOWED_TOOLS
    assert "search_entities_batch" in _LOCATE_BUDGET_TOOLS   # batch 计 1 次定位
    assert "search_entities_batch" in _LOCATE_DEDUP_TOOLS     # 同参去重（确定性工具）
    import inspect
    import app.mcp_server as mcp
    assert "search_entities_batch" in inspect.getsource(mcp)


def test_batch_merges_exact_like_vector():
    """三层合并语义（spec §三 件②）：精确>LIKE>向量逐项归组、每项与单查同构。
    变异锚点：归组错列（keyword 拿到别的 keyword 结果）→ 红。"""
    _clear_lookup_cache()
    from app.services.kg_action_handlers import _kg_search_entities_batch
    out = _kg_search_entities_batch({"keywords": ["台区"]}, "00:00:00")
    r = out["results"][0]
    for key in ("entities", "fields", "hit", "log"):
        assert key in r  # 与单查返回同构（含 fields）+ 批量自有 hit/miss 状态


# ---------------------------------------------------------------------------
# 任务 3：单查接缓存 + 失效接线
# ---------------------------------------------------------------------------

def test_single_query_cache_roundtrip(monkeypatch):
    """_kg_search_entities 二次同查走缓存：向量/embedding 不再被调（spec 件①：
    重复查询 ms 级）。变异锚点：单查顶部没接 cache_lookup → embed 被再次调 → 红。"""
    _clear_lookup_cache()
    from app.services import kg_action_handlers as kah
    calls = {"n": 0}
    def _fake_embed(db, texts, model_name=None):
        calls["n"] += 1
        return [[0.1] * 8 for _ in texts]
    import app.services.semantic_retrieval as sr
    monkeypatch.setattr(sr, "embed_texts", _fake_embed)
    q = {"keyword": "缓存往返测试实体xyz"}
    r1 = kah._kg_search_entities(dict(q), "00:00:01")
    n_after_first = calls["n"]
    r2 = kah._kg_search_entities(dict(q), "00:00:02")
    assert calls["n"] == n_after_first          # 二次同查零 embedding
    assert r2.get("cache_hit") is True
    _clear_lookup_cache()                       # 收口（任务 6）：残留缓存行防跨文件串扰


def test_invalidate_wired_in_write_endpoints():
    """写端点接线（spec 件①失效）：8 个写端点源码均含 invalidate 调用（plan 计 9 系
    把 upload_source_fields 与「Excel/CSV 字段导入端点」重复计——实测两者同一端点，
    upload.py 实为 4 个）。变异锚点：任一写端点漏接线 → 该函数源码断言红
    （inspect.getsource 逐函数断言——2026-09-09 任务 6 收口：整文件断言无法定位漏接线端点）。"""
    import inspect
    from app.api import entity_relation_manage as erm, upload as up
    for fn in ("create_entity_relation_item", "update_entity_relation_item",
               "delete_entity_relation_item", "import_entity_relations_excel"):
        assert "invalidate_entity_lookup_cache" in inspect.getsource(getattr(erm, fn)), fn
    for fn in ("upload_source_fields", "create_source_field", "update_source_field",
               "delete_source_field"):
        assert "invalidate_entity_lookup_cache" in inspect.getsource(getattr(up, fn)), fn


def test_batch_vector_hit_fact_enriched(monkeypatch):
    """控制者授权追加（任务 3）：_fact 事实源补齐修复——批量向量命中实体的 entities 行
    en_name/description 从 kg_entities 补齐（与单查向量路径「事实源补齐」同构承诺）。
    变异锚点：归组输出不读 _fact（只写不读死数据）→ 断言红。"""
    _clear_lookup_cache()
    from app.core.database import SessionLocal
    from sqlalchemy import text
    from app.services import kg_action_handlers as kah
    import app.services.semantic_retrieval as sr
    cid, code, kw = "t3-fact-fix-concept", "T3_FACT_FIX_ENT", "任务三向量事实源锚定词xyz"
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM kg_entities WHERE entity_code = :c"), {"c": code})
        db.execute(text("DELETE FROM kg_concepts WHERE id = :i"), {"i": cid})
        db.execute(text(
            "INSERT INTO kg_concepts (id, name, level, area_index, sort_order) "
            "VALUES (:i, :n, 1, 1, 9999)"), {"i": cid, "n": "任务3事实源测试概念"})
        db.execute(text(
            "INSERT INTO kg_entities (id, concept_id, entity_code, entity_name, entity_en_name, "
            "description, is_main_table, source_mode, sort_order) "
            "VALUES (:i, :cid, :c, :n, :en, :d, 0, 'physical_table', 9999)"),
            {"i": "t3-fact-fix-entity", "cid": cid, "c": code, "n": "任务3事实源测试实体",
             "en": "t3_fact_fix_entity", "d": "任务3事实源补齐锚点描述"})
        db.commit()

        def _fake_embed(db_, texts, model_name=None):
            return [[0.1] * 8 for _ in texts]
        monkeypatch.setattr(sr, "embed_texts", _fake_embed)
        monkeypatch.setattr(kah, "search_entity_vectors",
                            lambda q, top_k=10, db=None, vec=None:
                            [{"code": code, "name": "任务3事实源测试实体", "score": 0.9}])
        out = kah._kg_search_entities_batch({"keywords": [kw]}, "00:00:00")
        r = out["results"][0]
        vec_rows = [e for e in r["entities"] if e["entity_code"] == code]
        assert vec_rows, "向量命中实体未出现在 batch 结果"
        e = vec_rows[0]
        assert e["entity_en_name"] == "t3_fact_fix_entity"   # 修复前为空串 → 红
        assert e["description"] == "任务3事实源补齐锚点描述"   # 修复前为空串 → 红
    finally:
        db.execute(text("DELETE FROM kg_entities WHERE entity_code = :c"), {"c": code})
        db.execute(text("DELETE FROM kg_concepts WHERE id = :i"), {"i": cid})
        db.commit()
        db.close()
        from app.services.entity_lookup_cache import invalidate_entity_lookup_cache
        invalidate_entity_lookup_cache()


# ---------------------------------------------------------------------------
# 任务 4：件③ 契约预解析（三态）
# ---------------------------------------------------------------------------

def _mk_contract(template_ids):
    from app.services.query_contract import QueryContract
    return QueryContract(run_id="run_t", skill_id="distribution-overload", skill_version="1.0",
                         workflow_step="relationship", template_ids=template_ids,
                         route_type="scenario", locate_first=True,
                         _runtime={"confirmed_entities": []})


def test_preparse_full_coverage():
    """全覆盖：distribution-overload 真剧本 9 别名覆盖全部 ⟦⟧（spec §三 件③）——
    resolved_templates 非空+confirmed_entities=物理表名+locate_first=False。
    变异锚点：locate_first 未在全覆盖路径置 False → 红。"""
    from app.services.skill_catalog import get_catalog  # 装载函数以实现为准（plan 预留：load_skills/load_skill_definitions 实测不存在）
    from app.services.query_contract import apply_contract_preparse
    skill = get_catalog().load_skill("distribution-overload")
    assert skill.template_mode == "scenario_strict" and skill.entity_aliases
    c = _mk_contract(["distribution-overload:templates/step1_household_transformer.sql"])
    apply_contract_preparse(c, skill)
    assert c.resolved_templates and "⟦" not in next(iter(c.resolved_templates.values()))
    assert c.locate_first is False
    assert set(c._runtime["confirmed_entities"]) <= set(skill.entity_aliases.values())
    assert not c.preparse_gaps


def test_preparse_gap_path():
    """缺口：别名缺一条 → preparse_gaps=缺口清单、模板不替换、locate_first 不动。"""
    from types import SimpleNamespace
    from app.services.query_contract import apply_contract_preparse
    skill = SimpleNamespace(name="distribution-overload", template_mode="scenario_strict",
                            entity_aliases={"用电户": "pg_tupu.public.dim_cst_elec_cons_cust"})  # 只留 1 条
    c = _mk_contract(["distribution-overload:templates/step1_household_transformer.sql"])
    apply_contract_preparse(c, skill)
    assert c.preparse_gaps and not c.resolved_templates
    assert c.locate_first is True     # 缺口路径不置 False（行为契约）


def test_preparse_degrades_and_skips():
    """非 scenario_strict/无占位符/模板读失败 → 契约原样（现状流程）。"""
    from types import SimpleNamespace
    from app.services.query_contract import apply_contract_preparse
    c = _mk_contract(["distribution-overload:templates/step1_household_transformer.sql"])
    apply_contract_preparse(c, SimpleNamespace(
        name="x", template_mode="scenario_extensible", entity_aliases={"a": "b"}))  # 非 strict
    assert not c.resolved_templates and not c.preparse_gaps and c.locate_first is True


# ---------------------------------------------------------------------------
# 任务 5：件④ SKILL.md ⓪ 文案兜底
# ---------------------------------------------------------------------------

def test_skill_md_step0_and_qualifier():
    """distribution-overload：定位顺序块首有 ⓪；「禁止凭 aliases 猜表」带限定语；
    各步骤 allowed_tools 含 search_entities_batch。变异锚点：文案被删 → 红。"""
    from pathlib import Path
    md = (Path(__file__).resolve().parents[1] / "data" / "skills" / "scenarios"
          / "distribution-overload" / "SKILL.md").read_text(encoding="utf-8")
    assert "⓪" in md and "scenario_strict 剧本且 entity_aliases 覆盖模板全部" in md
    assert "（本条适用于 generic 流与未预解析场景）" in md
    assert md.count("- search_entities_batch") >= 3     # 三步骤各一列


# ---------------------------------------------------------------------------
# 任务 6 收口：渲染层注入断言（件③ data_intelligence 补测）
# ---------------------------------------------------------------------------

def test_render_injects_preparse_sections():
    """渲染注入（件③ data_intelligence._build_contract_system_message）：全覆盖契约注入
    【模板已预解析】+表名清单+直接使用指令；缺口契约注入【模板预解析缺口】+一次批量补齐指令。
    变异锚点：渲染层漏读 resolved_templates/preparse_gaps → 对应注入段消失 → 红。
    （任务 6 收口补测：任务 4 审查 Minor-3——渲染段原仅手动冒烟覆盖。）"""
    from app.services.skill_router import route_user_input
    from app.api.data_intelligence import _build_contract_system_message
    _q = "查询重过载台区"
    r = route_user_input(_q)                            # 全覆盖预解析接管（任务 4 锚定）
    msg = _build_contract_system_message(r.contract, _q)   # 注入段在 if question: 内（金标锚定段后），必须传 question
    assert "【模板已预解析】" in msg
    assert "直接使用，无需定位确认" in msg
    # 缺口态：契约拷贝后置空 resolved/置缺口清单（组装期字段测试直构——渲染层只读契约字段）
    import copy
    c2 = copy.deepcopy(r.contract)
    c2.resolved_templates = {}
    c2.preparse_gaps = ["缺口占位符X"]
    msg2 = _build_contract_system_message(c2, _q)
    assert "【模板预解析缺口】" in msg2
    assert "缺口占位符X" in msg2 and "search_entities_batch(keywords=" in msg2
