# -*- coding: utf-8 -*-
"""M08 单测：词条状态机列/双同义面区分/同义词组重复 400/字典检索（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M08 spec §八验收标准锚定现有实现）。
"""

# 验收标准映射（M08 spec §八，2026-09-08 测试补全）：
# §八.1 词条生命周期 extract→terms 列表→vectorize（任务进度 total/success/failed/progress 推进）→query 语义命中→export
#       → test_lifecycle_extract_terms_vectorize_query_export（本次补，本文件，外部件 embed/Qdrant 桩面断言）
# §八.2 content_hash 变更词条重新向量化 → test_content_hash_change_reembeds_on_force（本次补，本文件）；
#       失败记 retry_count/last_error → test_vectorize_failure_records_retry_count_and_last_error（本次补，本文件）
# §八.3 同义词组 CRUD → test_synonym_create_ok（本文件既有，create 面）+
#       test_synonym_update_delete_roundtrip（本次补，本文件，update/delete 面）；
#       重复 standard_term 400 → test_synonym_duplicate_rejected（本文件既有）；
#       enabled 过滤供检索（与 M09 联测改写生效）→ test_synonym_enabled_filter_feeds_retrieval_rewrite（本次补，本文件，
#       锚 hybrid_retrieval L187-188 只取 enabled 组）；改写展开行为锚交叉引用
#       tests/test_m09_vectors.py::test_expand_synonyms_static_fallback 与
#       tests/test_batch8_hybrid.py::TestSynonymExpansion::test_colloquial_words_expand
# §八.4 停用词三端点 → test_stop_words_three_endpoints（本次补，本文件，HTTP 面锚）；
#       标准字典 CRUD+关键词检索 → tests/test_cov_db_crud.py::test_standard_dict_create_dedup_and_keyword_search（既有，
#       服务层锚；该文件在 C4 门禁 --ignore 排除内，锚定非装饰性），字典 U/D 服务面同文件
#       test_standard_dict_update_and_missing / test_standard_dict_delete_semantics，停用词服务层 CRUD 同文件
#       test_stop_word_create_then_duplicate_returns_existing / test_stop_word_list_filters /
#       test_stop_word_update_partial_and_missing / test_stop_word_delete_semantics
# §八.5 nl2cypher 模板/schema 三端点写入 M05 辅助表 → test_nl2cypher_template_and_schema_write_m05_tables（本次补，本文件）
# §八.6 traceability/analyze 32 位 UUID 自动归一 → test_traceability_32bit_uuid_normalized（本次补，本文件）；
#       空 entity_ids 400 → test_traceability_empty_entity_ids_rejected（本次补，本文件）；
#       32/36 位双形态兼容范式交叉引用 tests/test_m07_mapping.py::test_lineage_uuid_compat_32_36_match（M07 溯源面）
# §八.7 归一化四族服务层函数可用（list/create/update/delete 幂等）→ test_norm_families_crud_idempotent（本次补，本文件）；
#       四族无 HTTP 面（登记态守卫，禁改清单专项）→ test_norm_families_no_http_face（本次补，本文件，守卫范式同
#       tests/test_m07_mapping.py::test_smart_join_review_reserved_table_no_consumer）
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.base import (  # noqa: E402
    CommonStopWord,
    StandardDict,
    StandardSemanticTerm,
    SynonymGroup,
)


# ---------------------------------------------------------------------------
# 任务 1：词条生命周期模型（spec §三）
# ---------------------------------------------------------------------------

def test_term_lifecycle_columns():
    """词条状态机列契约（spec §三：vector_status/retry_count/last_error/content_hash + 默认值）。
    变异锚点：content_hash 列删 → 变更检测断；source 默认非 graph_extract → 词条凭空手造。"""
    cols = {c.name for c in StandardSemanticTerm.__table__.columns}
    assert {"vector_status", "retry_count", "last_error", "content_hash",
            "canonical_text", "ontology_ref_type", "ontology_ref_id"} <= cols
    assert StandardSemanticTerm.__table__.c.source.default.arg == "graph_extract"
    assert StandardSemanticTerm.__table__.c.vector_status.default.arg == "pending"


def test_two_synonym_surfaces_distinct():
    """双同义面：SynonymGroup(standard_term+synonyms) ≠ StandardDict(non_standard→standard)。
    变异锚点：两表混用 → 检索改写与口径映射语义互污染。"""
    sg = {c.name for c in SynonymGroup.__table__.columns}
    sd = {c.name for c in StandardDict.__table__.columns}
    assert sg != sd
    assert "standard_term" in sg and "synonyms" in sg
    assert "non_standard" in sd and "standard" in sd


def test_stop_word_model():
    """停用词模型（spec §四：word/category/enabled）。
    变异锚点：category 列删 → 清洗分类断。"""
    cols = {c.name for c in CommonStopWord.__table__.columns}
    assert {"word", "category", "enabled"} <= cols


# ---------------------------------------------------------------------------
# 任务 4：同义词组重复 400（spec §八.3）
# ---------------------------------------------------------------------------

def test_synonym_duplicate_rejected():
    """重复 standard_term→400（spec §八.3；synonym.py L58-60）。
    变异锚点：重复校验删 → 同义词组数据漂移。"""
    from app.api.synonym import create_synonym
    from app.api.synonym import SynonymGroupCreate
    from app.core.database import SessionLocal
    from fastapi import HTTPException
    from app.models.base import SynonymGroup
    db = SessionLocal()
    try:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08dup").delete()
        db.add(SynonymGroup(standard_term="m08dup", synonyms=["a"]))
        db.commit()
        try:
            create_synonym(SynonymGroupCreate(standard_term="m08dup", synonyms=["b"]), db=db)
            assert False, "应 400"
        except HTTPException as e:
            assert e.status_code == 400
    finally:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08dup").delete()
        db.commit(); db.close()


def test_synonym_create_ok():
    """合法同义词组创建（spec §八.3）。
    变异锚点：创建路径断 → 检索改写资产无源。"""
    from app.api.synonym import SynonymGroupCreate, create_synonym
    from app.core.database import SessionLocal
    from app.models.base import SynonymGroup
    db = SessionLocal()
    try:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08ok").delete()
        db.commit()
        res = create_synonym(SynonymGroupCreate(standard_term="m08ok", synonyms=["x", "y"]), db=db)
        assert isinstance(res, dict)
    finally:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08ok").delete()
        db.commit(); db.close()


# ---------------------------------------------------------------------------
# spec §八.1：词条生命周期全链（extract→terms 列表→vectorize→query→export）
# ---------------------------------------------------------------------------

def test_lifecycle_extract_terms_vectorize_query_export():
    """词条生命周期全链（spec §八.1）：extract 从图谱抽词条（ontology_ref 回链+pending）→
    terms 列表 API 可见 → vectorize 桩面下任务进度 total/success/failed/progress 推进且任务行落库 →
    query 桩命中 → export 桩出向量行。外部依赖件（embedding 模型/Qdrant）按桩面断言契约，
    真连路径属 M09（tests/test_m09_vectors.py）。
    变异锚点：extract 丢 ontology_ref 回链 → 图谱词条无源；任务进度列/返回值不推进 →
    前端任务轮询空转；query/export 断链 → 语义消费无出口。"""
    import uuid as _u

    from app.api.standard_semantic import list_semantic_terms_api
    from app.core.database import SessionLocal
    from app.models.base import (
        Concept,
        Entity,
        EntityRelation,
        SemanticEmbedding,
        StandardSemanticVectorTask,
    )
    from app.services import standard_semantic_qdrant as SSQ
    from app.services import standard_semantic_service as SSS
    from app.services.tupu_qdrant_client import TupuQdrantClient

    db = SessionLocal()
    suffix = _u.uuid4().hex[:6]
    ent_name = f"m08生命周期实体{suffix}"
    rel_name = f"{ent_name}关系"
    attr_cn = f"生命周期字段{suffix}"
    term_names = [ent_name, rel_name, attr_cn]
    concept_id = entity_id = rel_id = None
    task_codes = []
    orig_embed = SSS.embed_texts
    orig_upsert = SSQ.upsert_standard_semantic_vectors_to_qdrant
    orig_q = SSQ.query_standard_semantic_matches_qdrant
    orig_gp = TupuQdrantClient.get_points
    try:
        # 种图谱源（词条之源，spec §七.2）：Concept+Entity+EntityRelation
        concept = Concept(name=f"{ent_name}概念", level=4, area_index=99)
        db.add(concept)
        db.commit(); db.refresh(concept)
        concept_id = str(concept.id)
        entity = Entity(concept_id=concept_id, entity_code=ent_name, entity_name=ent_name,
                        entity_en_name=f"m08lc{suffix}",
                        properties_schema=[{"name": f"m08lc_{suffix}", "cnName": attr_cn}])
        db.add(entity)
        db.commit(); db.refresh(entity)
        entity_id = str(entity.id)
        rel = EntityRelation(source_entity_id=entity_id, target_entity_id=entity_id,
                             relation_name=rel_name)
        db.add(rel)
        db.commit(); db.refresh(rel)
        rel_id = str(rel.id)

        # 1) extract：从图谱抽词条
        res = SSS.extract_graph_semantic_terms(db, extract_mode="all")
        assert res["created"] >= 1
        term = db.query(StandardSemanticTerm).filter(
            StandardSemanticTerm.term == ent_name,
            StandardSemanticTerm.term_type == "entity").first()
        assert term is not None
        assert term.source == "graph_extract"
        assert term.ontology_ref_type == "entity" and term.ontology_ref_id == entity_id
        assert term.vector_status == "pending"
        term_id = str(term.id)

        # 2) terms 列表（API 面）
        lst = list_semantic_terms_api(term_type="entity", keyword=ent_name, db=db)
        rows = [i for i in lst["data"] if i["term"] == ent_name]
        assert rows and rows[0]["vector_status"] == "pending"
        assert rows[0]["ontology_ref_id"] == entity_id

        # 3) vectorize（embed+qdrant 桩）→ 任务进度四字段推进
        embed_calls = []

        def _fake_embed(db_, texts, model_name=None):
            embed_calls.append(list(texts))
            return [[0.1, 0.2] for _ in texts]

        SSS.embed_texts = _fake_embed
        SSQ.upsert_standard_semantic_vectors_to_qdrant = lambda *a, **k: {"ok": True}
        try:
            vres = SSS.vectorize_terms(db, term_ids=[term_id])
        finally:
            SSS.embed_texts = orig_embed
            SSQ.upsert_standard_semantic_vectors_to_qdrant = orig_upsert
        assert vres["total"] == 1 and vres["success"] == 1 and vres["failed"] == 0
        assert vres["progress"] == 1.0 and vres["status"] == "done"
        task_codes.append(vres["task_code"])
        db.refresh(term)
        assert term.vector_status == "ready" and term.vector_dim == 2
        task = db.query(StandardSemanticVectorTask).filter(
            StandardSemanticVectorTask.task_code == vres["task_code"]).first()
        assert task is not None
        assert (task.total_count, task.success_count, task.failed_count, task.skipped_count) == (1, 1, 0, 0)
        assert task.progress == 1.0 and task.status == "done"
        # embed 桩收到 canonical_text（向量化文本来源契约，spec §三）
        assert embed_calls and embed_calls[-1] == [term.canonical_text]

        # 4) query 语义命中（qdrant 查询桩）
        SSQ.query_standard_semantic_matches_qdrant = lambda db_, q, **k: [
            {"term": ent_name, "term_type": "entity", "score": 0.9}]
        try:
            hits = SSS.query_standard_semantic_matches(db, ent_name, hybrid=False)
        finally:
            SSQ.query_standard_semantic_matches_qdrant = orig_q
        assert hits and hits[0]["term"] == ent_name and hits[0]["score"] == 0.9

        # 5) export（Qdrant get_points 桩）
        TupuQdrantClient.get_points = lambda self, coll, ids, **k: [
            {"id": term_id, "vector": [0.1, 0.2], "payload": {"model_name": "stub"}}]
        try:
            ex = SSS.export_vectors(db, entity_scope="all")
        finally:
            TupuQdrantClient.get_points = orig_gp
        assert ex["total"] == 1 and ex["rows"][0]["term"] == ent_name
        assert ex["rows"][0]["ontology_ref_type"] == "entity"
        assert ex["rows"][0]["vector_dim"] == 2
    finally:
        SSS.embed_texts = orig_embed
        SSQ.upsert_standard_semantic_vectors_to_qdrant = orig_upsert
        SSQ.query_standard_semantic_matches_qdrant = orig_q
        TupuQdrantClient.get_points = orig_gp
        try:
            terms = db.query(StandardSemanticTerm).filter(
                StandardSemanticTerm.term.in_(term_names)).all()
            tids = [str(t.id) for t in terms]
            if tids:
                db.query(SemanticEmbedding).filter(
                    SemanticEmbedding.object_type == "standard_term",
                    SemanticEmbedding.object_id.in_(tids)).delete(synchronize_session=False)
            db.query(StandardSemanticTerm).filter(
                StandardSemanticTerm.term.in_(term_names)).delete(synchronize_session=False)
            if task_codes:
                db.query(StandardSemanticVectorTask).filter(
                    StandardSemanticVectorTask.task_code.in_(task_codes)).delete(
                    synchronize_session=False)
            if rel_id:
                db.query(EntityRelation).filter(EntityRelation.id == rel_id).delete(
                    synchronize_session=False)
            if entity_id:
                db.query(Entity).filter(Entity.id == entity_id).delete(synchronize_session=False)
            if concept_id:
                db.query(Concept).filter(Concept.id == concept_id).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# spec §八.2：content_hash 变更重嵌 + 失败 retry_count/last_error 记账
# ---------------------------------------------------------------------------

def test_content_hash_change_reembeds_on_force():
    """content_hash 变更驱动重向量化（spec §三/§八.2）：pending 词条重嵌时 hash 跟随
    canonical_text 重算（防脏向量）；ready 词条默认跳过（no_pending_terms 不重算），
    force_regenerate=True 才按新内容重算 hash。
    变异锚点：hash 不随内容重算 → 旧向量被新文本复用 → 检索命中脏；ready 过滤删 → 全量重嵌。"""
    import uuid as _u

    from app.core.database import SessionLocal
    from app.models.base import SemanticEmbedding, StandardSemanticVectorTask
    from app.services import standard_semantic_qdrant as SSQ
    from app.services import standard_semantic_service as SSS
    from app.services.semantic_retrieval import _hash_text

    db = SessionLocal()
    tag = f"m08hash词条{_u.uuid4().hex[:6]}"
    term_id = None
    task_codes = []
    orig_embed = SSS.embed_texts
    orig_upsert = SSQ.upsert_standard_semantic_vectors_to_qdrant
    try:
        db.query(StandardSemanticTerm).filter(StandardSemanticTerm.term == tag).delete()
        db.commit()
        t = StandardSemanticTerm(term=tag, term_type="entity", source="graph_extract",
                                 canonical_text=tag, vector_status="pending")
        db.add(t)
        db.commit(); db.refresh(t)
        term_id = str(t.id)

        SSS.embed_texts = lambda db_, texts, model_name=None: [[0.1, 0.2] for _ in texts]
        SSQ.upsert_standard_semantic_vectors_to_qdrant = lambda *a, **k: {"ok": True}
        res = SSS.vectorize_terms(db, model_name="bge-large-zh-v1.5", term_ids=[term_id])
        task_codes.append(res["task_code"])
        db.refresh(t)
        assert t.vector_status == "ready"
        emb = db.query(SemanticEmbedding).filter(
            SemanticEmbedding.object_type == "standard_term",
            SemanticEmbedding.object_id == term_id).first()
        assert emb is not None
        h1 = emb.content_hash
        assert h1 == _hash_text("bge-large-zh-v1.5", tag)

        # 内容变更：ready 词条默认跳过（不重算，status=no_pending_terms 且无新任务行）
        t.canonical_text = tag + "变更"
        db.commit()
        res_skip = SSS.vectorize_terms(db, model_name="bge-large-zh-v1.5", term_ids=[term_id])
        assert res_skip["status"] == "no_pending_terms" and res_skip["total"] == 0
        db.refresh(emb)
        assert emb.content_hash == h1

        # force_regenerate：按变更后内容重嵌重算 hash
        res_re = SSS.vectorize_terms(db, model_name="bge-large-zh-v1.5", term_ids=[term_id],
                                     force_regenerate=True)
        task_codes.append(res_re["task_code"])
        assert res_re["success"] == 1 and res_re["progress"] == 1.0
        db.refresh(emb)
        assert emb.content_hash == _hash_text("bge-large-zh-v1.5", tag + "变更")
        assert emb.content_hash != h1
        assert emb.text_content == tag + "变更"
    finally:
        SSS.embed_texts = orig_embed
        SSQ.upsert_standard_semantic_vectors_to_qdrant = orig_upsert
        try:
            db.query(SemanticEmbedding).filter(
                SemanticEmbedding.object_type == "standard_term",
                SemanticEmbedding.object_id == term_id).delete(synchronize_session=False)
            db.query(StandardSemanticTerm).filter(
                StandardSemanticTerm.id == term_id).delete(synchronize_session=False)
            if task_codes:
                db.query(StandardSemanticVectorTask).filter(
                    StandardSemanticVectorTask.task_code.in_(task_codes)).delete(
                    synchronize_session=False)
            db.commit()
        finally:
            db.close()


def test_vectorize_failure_records_retry_count_and_last_error():
    """vectorize 失败记账（spec §三 failed(retry_count++, last_error)/§八.2）：空向量、
    嵌入异常、Qdrant 上送异常三条失败路径均置 vector_status=failed、last_error 记录、
    retry_count 自增；任务行 failed_count/status 同步失败。
    变异锚点：任一失败路径漏记 retry_count/last_error → 失败词条无重试凭据，熔断失效。"""
    import uuid as _u

    from app.core.database import SessionLocal
    from app.models.base import SemanticEmbedding, StandardSemanticTerm, StandardSemanticVectorTask
    from app.services import standard_semantic_qdrant as SSQ
    from app.services import standard_semantic_service as SSS

    db = SessionLocal()
    base_tag = f"m08失败记账{_u.uuid4().hex[:6]}"
    term_ids = []
    task_codes = []
    orig_embed = SSS.embed_texts
    orig_upsert = SSQ.upsert_standard_semantic_vectors_to_qdrant

    def _seed(tag):
        db.query(StandardSemanticTerm).filter(StandardSemanticTerm.term == tag).delete()
        db.commit()
        t = StandardSemanticTerm(term=tag, term_type="entity", source="graph_extract",
                                 canonical_text=tag, vector_status="pending")
        db.add(t)
        db.commit(); db.refresh(t)
        term_ids.append(str(t.id))
        return t

    try:
        # 场景 1：空向量 → failed("Empty embedding")
        t1 = _seed(base_tag + "一")
        SSS.embed_texts = lambda db_, texts, model_name=None: [[] for _ in texts]
        SSQ.upsert_standard_semantic_vectors_to_qdrant = lambda *a, **k: {"ok": True}
        r1 = SSS.vectorize_terms(db, term_ids=[str(t1.id)])
        task_codes.append(r1["task_code"])
        db.refresh(t1)
        assert t1.vector_status == "failed" and t1.last_error == "Empty embedding"
        assert t1.retry_count == 1
        assert r1["failed"] == 1 and r1["progress"] == 0.0 and r1["status"] == "failed"

        # 场景 2：向量元素非数值 → 归一化抛异常 → failed 带 last_error
        t2 = _seed(base_tag + "二")
        SSS.embed_texts = lambda db_, texts, model_name=None: [["bad"] for _ in texts]
        r2 = SSS.vectorize_terms(db, term_ids=[str(t2.id)])
        task_codes.append(r2["task_code"])
        db.refresh(t2)
        assert t2.vector_status == "failed" and t2.last_error
        assert t2.retry_count == 1
        assert r2["failed"] == 1

        # 场景 3：Qdrant 上送抛异常 → 全批 failed，错误透传
        t3 = _seed(base_tag + "三")
        SSS.embed_texts = lambda db_, texts, model_name=None: [[0.1, 0.2] for _ in texts]

        def _boom(*a, **k):
            raise RuntimeError("qdrant down")

        SSQ.upsert_standard_semantic_vectors_to_qdrant = _boom
        r3 = SSS.vectorize_terms(db, term_ids=[str(t3.id)])
        task_codes.append(r3["task_code"])
        db.refresh(t3)
        assert t3.vector_status == "failed" and "qdrant down" in (t3.last_error or "")
        assert t3.retry_count == 1
        assert r3["failed"] == 1 and r3["qdrant"].get("ok") is False
        assert r3["status"] == "failed"
    finally:
        SSS.embed_texts = orig_embed
        SSQ.upsert_standard_semantic_vectors_to_qdrant = orig_upsert
        try:
            if term_ids:
                db.query(SemanticEmbedding).filter(
                    SemanticEmbedding.object_type == "standard_term",
                    SemanticEmbedding.object_id.in_(term_ids)).delete(synchronize_session=False)
                db.query(StandardSemanticTerm).filter(
                    StandardSemanticTerm.id.in_(term_ids)).delete(synchronize_session=False)
            if task_codes:
                db.query(StandardSemanticVectorTask).filter(
                    StandardSemanticVectorTask.task_code.in_(task_codes)).delete(
                    synchronize_session=False)
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# spec §八.3：同义词组 CRUD 补全（update/delete 往返 + enabled 过滤喂检索改写）
# ---------------------------------------------------------------------------

def test_synonym_update_delete_roundtrip():
    """同义词组 update/delete 往返（spec §八.3 CRUD）：update 持久化 synonyms/category/enabled；
    update 撞已有 standard_term 400；缺失 id 404；delete 后再删 404（幂等安全）。
    变异锚点：update 去重校验删 → 改名可撞已有组；delete 幂等破坏 → 二次删炸。"""
    import uuid as _u

    from app.api.synonym import SynonymGroupCreate, SynonymGroupUpdate, create_synonym
    from app.api.synonym import delete_synonym, update_synonym
    from app.core.database import SessionLocal
    from fastapi import HTTPException
    from app.models.base import SynonymGroup

    db = SessionLocal()
    tag_a = f"m08upd甲{_u.uuid4().hex[:5]}"
    tag_b = f"m08upd乙{_u.uuid4().hex[:5]}"
    created = []
    try:
        for tag in (tag_a, tag_b):
            db.query(SynonymGroup).filter(SynonymGroup.standard_term == tag).delete()
        db.commit()
        r = create_synonym(SynonymGroupCreate(standard_term=tag_a, synonyms=["旧同义"]), db=db)
        created.append(tag_a)
        gid = r["data"]["id"]

        # update 持久化
        u = update_synonym(gid, SynonymGroupUpdate(synonyms=["新同义1", "新同义2"],
                                                   category="m08cat", enabled=False), db=db)
        assert u["code"] == 200 and u["data"]["synonyms"] == ["新同义1", "新同义2"]
        assert u["data"]["category"] == "m08cat" and u["data"]["enabled"] is False
        row = db.query(SynonymGroup).filter(SynonymGroup.id == gid).first()
        assert row.synonyms == ["新同义1", "新同义2"] and bool(row.enabled) is False

        # update 改名撞已有组 → 400
        r_b = create_synonym(SynonymGroupCreate(standard_term=tag_b, synonyms=["乙"]), db=db)
        created.append(tag_b)
        try:
            update_synonym(gid, SynonymGroupUpdate(standard_term=tag_b), db=db)
            assert False, "应 400"
        except HTTPException as e:
            assert e.status_code == 400

        # 缺失 id（合法 uuid 但不存在）→ 404
        try:
            update_synonym(str(_u.uuid4()), SynonymGroupUpdate(synonyms=["x"]), db=db)
            assert False, "应 404"
        except HTTPException as e:
            assert e.status_code == 404

        # delete → 200；再删 → 404
        assert delete_synonym(gid, db=db)["code"] == 200
        created.remove(tag_a)
        try:
            delete_synonym(gid, db=db)
            assert False, "应 404"
        except HTTPException as e:
            assert e.status_code == 404
    finally:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term.in_(created)).delete(
            synchronize_session=False)
        db.commit(); db.close()


def test_synonym_enabled_filter_feeds_retrieval_rewrite():
    """enabled 过滤供检索改写（spec §八.3；hybrid_retrieval L187-188 只取 enabled 组）：
    enabled 组并入改写映射，禁用组被滤除。与 M09 联测的改写展开行为锚交叉引用
    tests/test_m09_vectors.py::test_expand_synonyms_static_fallback。
    变异锚点：enabled 过滤删 → 禁用同义词继续污染检索改写。"""
    from app.core.database import SessionLocal
    from app.services import hybrid_retrieval as H

    db = SessionLocal()
    tag_on = f"m08改写启用词{__import__('uuid').uuid4().hex[:5]}"
    tag_off = tag_on + "禁"
    saved_map = dict(H._SYNONYM_MAP)
    saved_at = H._SYNONYM_CACHE["loaded_at"]
    try:
        db.query(SynonymGroup).filter(
            SynonymGroup.standard_term.in_([tag_on, tag_off])).delete(synchronize_session=False)
        db.add(SynonymGroup(standard_term=tag_on, synonyms=["改写甲"], enabled=True))
        db.add(SynonymGroup(standard_term=tag_off, synonyms=["改写乙"], enabled=False))
        db.commit()
        H._SYNONYM_CACHE["loaded_at"] = 0.0  # 击穿 TTL 强制重载
        H.load_synonyms_from_db(db)
        assert H._SYNONYM_MAP.get(tag_on) == [tag_on, "改写甲"]
        assert tag_off not in H._SYNONYM_MAP
    finally:
        db.query(SynonymGroup).filter(
            SynonymGroup.standard_term.in_([tag_on, tag_off])).delete(synchronize_session=False)
        db.commit(); db.close()
        H._SYNONYM_MAP = saved_map
        H._SYNONYM_CACHE["loaded_at"] = saved_at


# ---------------------------------------------------------------------------
# spec §八.4：停用词三端点（HTTP 面；标准字典服务层 CRUD 由 test_cov_db_crud.py 锚定）
# ---------------------------------------------------------------------------

def test_stop_words_three_endpoints():
    """停用词三端点（spec §八.4）：POST 创建（缺 word 400）→ GET 列表可见（模型列
    word/category 契约）→ DELETE → 再删 404。
    变异锚点：端点对齐 kg_common_stop_words 模型列（word/category/description）——
    幻影列（word_type/priority）回归 → 500。"""
    from app.api.standard_semantic import (
        create_stop_word_api,
        delete_stop_word_api,
        list_stop_words_api,
    )
    from app.core.database import SessionLocal
    from fastapi import HTTPException

    db = SessionLocal()
    tag = "m08停用词端点探针"
    try:
        db.query(CommonStopWord).filter(CommonStopWord.word == tag).delete()
        db.commit()
        # POST 合法
        r = create_stop_word_api({"word": tag, "category": "filler"}, db=db)
        assert r["code"] == 200 and r["data"]["word"] == tag
        # POST 缺 word → 400
        try:
            create_stop_word_api({}, db=db)
            assert False, "应 400"
        except HTTPException as e:
            assert e.status_code == 400
        # GET 列表可见（word/category 契约）
        lst = list_stop_words_api(db=db)
        hit = [i for i in lst["data"] if i["word"] == tag]
        assert hit and hit[0]["category"] == "filler"
        # DELETE
        assert delete_stop_word_api(hit[0]["id"], db=db)["code"] == 200
        try:
            delete_stop_word_api(hit[0]["id"], db=db)
            assert False, "应 404"
        except HTTPException as e:
            assert e.status_code == 404
    finally:
        db.query(CommonStopWord).filter(CommonStopWord.word == tag).delete(
            synchronize_session=False)
        db.commit(); db.close()


# ---------------------------------------------------------------------------
# spec §八.5：nl2cypher 模板/schema 三端点写入 M05 辅助表
# ---------------------------------------------------------------------------

def test_nl2cypher_template_and_schema_write_m05_tables():
    """nl2cypher 模板/schema 三端点写入 M05 辅助表（spec §五/§八.5：kg_cypher_templates/
    kg_graph_schema）：创建落表、重复 409、列表可见（响应键 cypher_pattern 由表列
    template_text 供值）、删除、再删 404；schema 面同构（field_type 持久化）。
    变异锚点：API↔服务层签名错位回归（cypher_pattern↔template_text）→ 500；
    重复 409 分支删 → 唯一键炸裸。"""
    import uuid as _u

    from app.api.standard_semantic import (
        CypherTemplateCreateRequest,
        GraphSchemaCreateRequest,
        create_cypher_template_api,
        create_graph_schema_api,
        delete_cypher_template_api,
        delete_graph_schema_api,
        list_cypher_templates_api,
        list_graph_schema_api,
    )
    from app.core.database import SessionLocal
    from app.models.base import CypherTemplate, GraphSchema
    from fastapi import HTTPException

    tpl_name = f"m08模板{_u.uuid4().hex[:5]}"
    field_name = f"m08字段{_u.uuid4().hex[:5]}"
    pattern = "MATCH (n:m08) RETURN n LIMIT 1"
    db = SessionLocal()
    try:
        db.query(CypherTemplate).filter(CypherTemplate.template_name == tpl_name).delete()
        db.query(GraphSchema).filter(GraphSchema.field_name == field_name).delete()
        db.commit()

        # 模板：创建 → 落 M05 表 kg_cypher_templates
        r = create_cypher_template_api(
            CypherTemplateCreateRequest(template_name=tpl_name, cypher_pattern=pattern), db=db)
        assert r["code"] == 200
        row = db.query(CypherTemplate).filter(CypherTemplate.template_name == tpl_name).first()
        assert row is not None and row.template_text == pattern
        # 重复创建 → 409
        r_dup = create_cypher_template_api(
            CypherTemplateCreateRequest(template_name=tpl_name, cypher_pattern=pattern), db=db)
        assert r_dup["code"] == 409
        # 列表可见，cypher_pattern 响应键由 template_text 供值
        lst = list_cypher_templates_api(db=db)
        hit = [i for i in lst["data"] if i["template_name"] == tpl_name]
        assert hit and hit[0]["cypher_pattern"] == pattern
        # 删除 → 200；再删 → 404
        assert delete_cypher_template_api(str(row.id), db=db)["code"] == 200
        try:
            delete_cypher_template_api(str(row.id), db=db)
            assert False, "应 404"
        except HTTPException as e:
            assert e.status_code == 404

        # schema：创建 → 落 M05 表 kg_graph_schema
        rs = create_graph_schema_api(
            GraphSchemaCreateRequest(field_name=field_name, field_type="node"), db=db)
        assert rs["code"] == 200
        srow = db.query(GraphSchema).filter(GraphSchema.field_name == field_name).first()
        assert srow is not None and srow.field_type == "node"
        assert create_graph_schema_api(
            GraphSchemaCreateRequest(field_name=field_name), db=db)["code"] == 409
        slst = list_graph_schema_api(db=db)
        shit = [i for i in slst["data"] if i["field_name"] == field_name]
        assert shit and shit[0]["field_type"] == "node"
        assert delete_graph_schema_api(str(srow.id), db=db)["code"] == 200
        try:
            delete_graph_schema_api(str(srow.id), db=db)
            assert False, "应 404"
        except HTTPException as e:
            assert e.status_code == 404
    finally:
        db.query(CypherTemplate).filter(CypherTemplate.template_name == tpl_name).delete(
            synchronize_session=False)
        db.query(GraphSchema).filter(GraphSchema.field_name == field_name).delete(
            synchronize_session=False)
        db.commit(); db.close()


# ---------------------------------------------------------------------------
# spec §八.6：traceability/analyze 空 entity_ids 400 + 32 位 UUID 自动归一
# ---------------------------------------------------------------------------

def test_traceability_empty_entity_ids_rejected():
    """traceability/analyze 空 entity_ids 400；全非法格式 400（spec §八.6）。
    变异锚点：空校验删 → 空 entity_ids 全表扫描空跑；格式校验删 → 脏 id 直入 in_ 查询炸 500。"""
    from app.api.standard_semantic import TraceabilityRequest, analyze_traceability
    from app.core.database import SessionLocal
    from fastapi import HTTPException

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as ei:
            analyze_traceability(TraceabilityRequest(entity_ids=[]), db=db)
        assert ei.value.status_code == 400 and "不能为空" in ei.value.detail
        with pytest.raises(HTTPException) as ei2:
            analyze_traceability(TraceabilityRequest(entity_ids=["xx-not-a-uuid-xx"]), db=db)
        assert ei2.value.status_code == 400 and "格式不正确" in ei2.value.detail
    finally:
        db.close()


def test_traceability_32bit_uuid_normalized():
    """traceability/analyze 32 位 UUID 自动归一（spec §六 L596-607/§八.6）：32 位紧凑形态
    与 36 位连字符形态命中同一实体，结果 entity_id 归一为 36 位；合法但不存在的 id 返回
    200 空结果不炸。32/36 位双形态兼容范式交叉引用
    tests/test_m07_mapping.py::test_lineage_uuid_compat_32_36_match（M07 溯源面）。
    变异锚点：32→36 归一删 → 紧凑 UUID 命中落空（entities 空）。"""
    import uuid as _u

    from app.api.standard_semantic import TraceabilityRequest, analyze_traceability
    from app.core.database import SessionLocal
    from app.models.base import Concept, Entity

    db = SessionLocal()
    tag = f"m08溯源实体{_u.uuid4().hex[:6]}"
    concept_id = entity_id = None
    try:
        concept = Concept(name=f"{tag}概念", level=4, area_index=99)
        db.add(concept)
        db.commit(); db.refresh(concept)
        concept_id = str(concept.id)
        entity = Entity(concept_id=concept_id, entity_code=tag, entity_name=tag)
        db.add(entity)
        db.commit(); db.refresh(entity)
        entity_id = str(entity.id)

        # 32 位紧凑形态自动归一并命中
        r32 = analyze_traceability(
            TraceabilityRequest(entity_ids=[entity_id.replace("-", "")]), db=db)
        assert r32["code"] == 200
        hit32 = [e for e in r32["data"]["entities"] if e["entity_id"] == entity_id]
        assert hit32 and hit32[0]["entity_name"] == tag

        # 36 位形态同命中
        r36 = analyze_traceability(TraceabilityRequest(entity_ids=[entity_id]), db=db)
        assert [e["entity_id"] for e in r36["data"]["entities"]] == [entity_id]

        # 合法但不存在的 id → 200 空结果
        r_miss = analyze_traceability(
            TraceabilityRequest(entity_ids=[str(_u.uuid4())]), db=db)
        assert r_miss["code"] == 200 and r_miss["data"]["entities"] == []
    finally:
        if entity_id:
            db.query(Entity).filter(Entity.id == entity_id).delete(synchronize_session=False)
        if concept_id:
            db.query(Concept).filter(Concept.id == concept_id).delete(synchronize_session=False)
        db.commit(); db.close()


# ---------------------------------------------------------------------------
# spec §八.7：归一化四族服务层 CRUD 幂等 + 无 HTTP 面（登记态守卫，禁改清单专项）
# ---------------------------------------------------------------------------

def test_norm_families_crud_idempotent():
    """归一化四族服务层 list/create/update/delete 幂等可用（spec §四/§五/§八.7）：
    time_norm（word→time_code）/time_cypher_map（time_code→cypher_expr，重复创建按
    幂等语义更新表达式）/intent_norm（word→standard）/explode_norm（phrase→agg_hint+
    time_field）；缺失 id 更新 None、删除 False（幂等安全）；list 仅 enabled 行。
    变异锚点：任一族 create 重复幂等分支删 → 同键双行漂移；delete 幂等破坏 → 二次删炸。"""
    import uuid as _u

    from app.core.database import SessionLocal
    from app.models.base import (
        SemanticExplodeNorm,
        SemanticIntentNorm,
        SemanticTimeCypherMap,
        SemanticTimeNorm,
    )
    from app.services import semantic_manager_service as SMS

    db = SessionLocal()
    w_time = f"m08时间词{_u.uuid4().hex[:5]}"
    tc_map = f"m08时间码{_u.uuid4().hex[:5]}"
    w_intent = f"m08意图词{_u.uuid4().hex[:5]}"
    p_explode = f"m08炸开短语{_u.uuid4().hex[:5]}"
    missing_id = str(_u.uuid4())
    try:
        # time_norm
        item, dup = SMS.create_time_norm(db, w_time, "LAST_MONTH")
        assert dup is False
        item2, dup2 = SMS.create_time_norm(db, w_time, "LAST_MONTH")
        assert dup2 is True and str(item2.id) == str(item.id)
        upd = SMS.update_time_norm(db, str(item.id), time_code="THIS_MONTH")
        assert upd.time_code == "THIS_MONTH"
        assert SMS.update_time_norm(db, missing_id, time_code="X") is None
        assert any(r.word == w_time for r in SMS.list_time_norms(db))
        assert SMS.delete_time_norm(db, str(item.id)) is True
        assert SMS.delete_time_norm(db, str(item.id)) is False

        # time_cypher_map（重复创建幂等语义=更新表达式）
        cm, dup = SMS.create_time_cypher_map(db, tc_map, "MATCH (n) WHERE n.month=1")
        assert dup is False
        cm2, dup2 = SMS.create_time_cypher_map(db, tc_map, "MATCH (n) WHERE n.month=2")
        assert dup2 is True and str(cm2.id) == str(cm.id)
        assert cm2.cypher_expr == "MATCH (n) WHERE n.month=2"
        assert SMS.update_time_cypher_map(db, missing_id) is None
        assert any(r.time_code == tc_map for r in SMS.list_time_cypher_maps(db))
        assert SMS.delete_time_cypher_map(db, str(cm.id)) is True
        assert SMS.delete_time_cypher_map(db, str(cm.id)) is False

        # intent_norm
        it, dup = SMS.create_intent_norm(db, w_intent, "标准意图")
        assert dup is False
        it2, dup2 = SMS.create_intent_norm(db, w_intent, "标准意图")
        assert dup2 is True and str(it2.id) == str(it.id)
        assert SMS.update_intent_norm(db, str(it.id), standard="改后意图").standard == "改后意图"
        assert SMS.update_intent_norm(db, missing_id) is None
        assert any(r.word == w_intent for r in SMS.list_intent_norms(db))
        assert SMS.delete_intent_norm(db, str(it.id)) is True
        assert SMS.delete_intent_norm(db, str(it.id)) is False

        # explode_norm
        ex, dup = SMS.create_explode_norm(db, p_explode, "SUM", "stat_date")
        assert dup is False
        ex2, dup2 = SMS.create_explode_norm(db, p_explode, "SUM", "stat_date")
        assert dup2 is True and str(ex2.id) == str(ex.id)
        upd = SMS.update_explode_norm(db, str(ex.id), agg_hint="MAX", time_field="biz_date")
        assert upd.agg_hint == "MAX" and upd.time_field == "biz_date"
        assert SMS.update_explode_norm(db, missing_id) is None
        assert any(r.phrase == p_explode for r in SMS.list_explode_norms(db))
        assert SMS.delete_explode_norm(db, str(ex.id)) is True
        assert SMS.delete_explode_norm(db, str(ex.id)) is False
    finally:
        db.query(SemanticTimeNorm).filter(SemanticTimeNorm.word == w_time).delete(
            synchronize_session=False)
        db.query(SemanticTimeCypherMap).filter(SemanticTimeCypherMap.time_code == tc_map).delete(
            synchronize_session=False)
        db.query(SemanticIntentNorm).filter(SemanticIntentNorm.word == w_intent).delete(
            synchronize_session=False)
        db.query(SemanticExplodeNorm).filter(SemanticExplodeNorm.phrase == p_explode).delete(
            synchronize_session=False)
        db.commit(); db.close()


def test_norm_families_no_http_face():
    """归一化四族无 HTTP 面（spec §五登记态/禁改清单专项）：四族归一化是服务层函数
    （semantic_manager_service），无任何 API 端点注册——路由表无四族路径，app/api 全域
    无四族服务函数引用。按登记态断言（守卫范式同
    tests/test_m07_mapping.py::test_smart_join_review_reserved_table_no_consumer），
    不许测出「无 HTTP」就加路由实现它——启用管理面须过设计批次。
    变异锚点：有人给四族注册路由 → 路由表红；API 文件引用四族服务函数 → 静态扫描红。"""
    from app.main import app

    forbidden = ("time-norm", "time-cypher", "intent-norm", "explode-norm", "norm-famil")
    hit_paths = [getattr(r, "path", "") for r in app.routes
                 if any(k in getattr(r, "path", "").lower() for k in forbidden)]
    assert hit_paths == [], f"四族归一化出现 HTTP 面：{hit_paths}"

    api_dir = Path(__file__).resolve().parents[1] / "app" / "api"
    names = [
        "list_time_norms", "create_time_norm", "update_time_norm", "delete_time_norm",
        "list_time_cypher_maps", "create_time_cypher_map", "update_time_cypher_map",
        "delete_time_cypher_map", "list_intent_norms", "create_intent_norm",
        "update_intent_norm", "delete_intent_norm", "list_explode_norms",
        "create_explode_norm", "update_explode_norm", "delete_explode_norm",
    ]
    offenders = []
    for p in sorted(api_dir.rglob("*.py")):
        text = p.read_text(encoding="utf-8")
        for n in names:
            if n in text:
                offenders.append(f"{p.name}:{n}")
    assert offenders == [], f"app/api 出现四族归一化服务引用：{offenders}"
