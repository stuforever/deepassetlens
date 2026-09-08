# -*- coding: utf-8 -*-
"""M05 单测：健康降级/夹取语义/投射入口（Neo4j 停机桩，金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M05 spec §九验收标准锚定现有实现；Neo4j
不可用场景按 §八.3 健康降级契约锚定）。
"""

# ---------------------------------------------------------------------------
# 验收标准映射（M05 spec §九，2026-09-08 测试补全）：
# §九.1 空库→sync_all(force)：节点/关系统计与种子计数一致（L2X/L4X 投射规则、RELATES_TO 属性
#       完整）+ 重复执行零增长（幂等） → test_sync_all_projection_rules_stats_idempotent
#       （本次补，本文件；内存桩图按引擎实际下发的 Cypher 语句族解释执行——真 Neo4j 真库
#       计数一致留联测域（§十 2026-09-07 行同口径），单测桩锚定投射/幂等语义，如实披露）
# §九.2 实体改挂概念→重同步后 HAS_PARENT 更新；非 L2/L4 概念下实体不投射 →
#       test_sync_all_remount_updates_has_parent（本次补，本文件）+
#       test_sync_all_projection_rules_stats_idempotent（本文件，跳过规则断言）
# §九.3 expand_entity_neighbors：1~3 hop 结果含 rel_type/label/hop，越界参数被夹取 →
#       test_expand_neighbors_hop_limit_clamped_in_query +
#       test_expand_neighbors_result_shape_rel_type_label_hop（均本次补，本文件，录句桩锚定
#       内联夹取真值——收窄 §十 2026-09-07 行「夹取真值留问数链联测」的范围）+
#       test_clip_semantics_inline（本文件既有，夹取表达式等价锚）
# §九.4 kg_api 9 端点：非法输入 4xx；execute_sql 走安全校验链（与 M21 联测） →
#       test_kg_api_invalid_inputs_4xx + test_kg_execute_sql_uses_safety_chain
#       （均本次补，本文件）；validate_safe_sql 语义族 → backend/tests/test_sql_safety.py
#       （既有他文件交叉引用）
# §九.5 Neo4j 停机：启动成功（warning）、kg_api 图查询降级不 500 →
#       test_kg_graph_queries_degrade_when_neo4j_down（本次补，本文件）+
#       test_m01_base.py::test_lifespan_degrades_external_deps_down（启动 warning，既有他文件）+
#       test_healthcheck_false_drives_degrade（本文件既有，引擎静默降级）
# §九.6 /graph/data、/graph/neo4j-data、subgraph-by-l1 三端点形状满足 M03 画布渲染 →
#       test_subgraph_by_l1_canvas_shape（本次补，本文件）+
#       test_m03_concept.py::test_force_view_full_data_contract（/graph/data，既有他文件）+
#       test_m03_concept.py::test_gallery_view_neo4j_stub_contract（/graph/neo4j-data，既有他文件）
# 附（spec §四/§十 双轨冻结登记态）：老 /sync 路径未收编 →
#       test_old_sync_endpoint_frozen_double_track（本次补，本文件）
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inspect  # noqa: E402
import re  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

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
    sig = inspect.signature(G.sync_all_to_neo4j)
    assert "db" in sig.parameters
    assert sig.parameters["force"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# 2026-09-08 测试补全（批次 2·图谱域）：spec §九 验收缺口补测
# 测试基建：内存桩 Neo4j（按引擎实际下发的 Cypher 语句族解释执行）+ 录句桩 +
#           独立内存 SQLite（M05 投射三表），防误写真实图谱数据（M03/M04 批范式）。
# ---------------------------------------------------------------------------

class _FakeGraph:
    """内存桩 Neo4j：只解释 sync_all_to_neo4j/_count_all 下发的语句族（spec §三投射）。

    支持：MATCH (n) DETACH DELETE n（force 清库）/ MERGE 节点 upsert（code 幂等键，SET
    字面量+参数混合解析）/ MATCH…MERGE HAS_PARENT、RELATES_TO（带属性）边 upsert /
    WHERE n.level IN […] BELONGS_TO_CHAIN 批量挂链 / RETURN count(n|r) AS c 计数。
    未支持语句 raise AssertionError——生产 Cypher 投射形状漂移即红（录句桩严格契约）。
    """

    def __init__(self):
        self.nodes = {}  # code -> {属性}
        self.edges = {}  # (src_code, rel_type, dst_code) -> {属性}
        self.log = []    # [(query, params)] 录句

    # ---- 结果 / 会话 / 驱动桩 -------------------------------------------------
    class _Result:
        def __init__(self, g, q, p):
            self._g, self._q, self._p = g, q, (p or {})

        def consume(self):
            self._g._execute(self._q, self._p)

        def single(self):
            out = self._g._execute(self._q, self._p)
            return out if out is not None else {"c": 0}

    class _Session:
        def __init__(self, g):
            self._g = g

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def run(self, q, **p):
            return _FakeGraph._Result(self._g, q, p)

    class _Driver:
        def __init__(self, g):
            self._g = g

        def session(self):
            return _FakeGraph._Session(self._g)

    def driver(self):
        return _FakeGraph._Driver(self)

    # ---- 语句族解释 -----------------------------------------------------------
    @staticmethod
    def _parse_props(q, p):
        setpart = q.split("SET", 1)[1] if "SET" in q else ""
        props = {}
        for k, pn in re.findall(r"\.(\w+)\s*=\s*\$(\w+)", setpart):
            props[k] = p.get(pn)
        for k, lit in re.findall(r"\.(\w+)\s*=\s*'([^']*)'", setpart):
            props[k] = lit
        return props

    def _execute(self, q, p):
        self.log.append((q, dict(p)))
        if "RETURN count(n) AS c" in q:
            return {"c": len(self.nodes)}
        if "RETURN count(r) AS c" in q:
            return {"c": len(self.edges)}
        if re.search(r"MATCH \(n\)\s+DETACH DELETE", q):
            self.nodes.clear()
            self.edges.clear()
            return None
        if "BELONGS_TO_CHAIN" in q:
            lv = re.search(r"WHERE n\.level IN \[([^\]]+)\]", q)
            root = re.search(r"ChainRoot \{code:'([^']+)'\}", q)
            assert lv and root, f"内存桩未支持的 BELONGS_TO_CHAIN 语句: {q[:120]}"
            levels = {s.strip().strip("'\"") for s in lv.group(1).split(",")}
            for code, props in self.nodes.items():
                if props.get("level") in levels:
                    self.edges[(code, "BELONGS_TO_CHAIN", root.group(1))] = {}
            return None
        edge_m = (re.search(r"MERGE \((\w+)\)-\[:(\w+)\]->\((\w+)\)", q)      # -[:TYPE]->
                  or re.search(r"MERGE \((\w+)\)-\[\w+:(\w+)\]->\((\w+)\)", q))  # -[v:TYPE]->
        if edge_m:
            binds = dict(re.findall(r"\((\w+):Category \{code:\$(\w+)\}\)", q))
            src_var, rel, dst_var = edge_m.groups()
            assert src_var in binds and dst_var in binds, f"边语句缺 code 绑定: {q[:120]}"
            key = (p[binds[src_var]], rel, p[binds[dst_var]])
            self.edges.setdefault(key, {}).update(self._parse_props(q, p))
            return None
        node_m = re.search(r"MERGE \(\w+:([\w:]+) \{code:\$(\w+)\}\)", q)
        if node_m:
            self.nodes.setdefault(p[node_m.group(2)], {}).update(self._parse_props(q, p))
            return None
        node_lit = re.search(r"MERGE \(\w+:([\w:]+) \{code:'([^']+)'\}\)", q)
        if node_lit:
            self.nodes.setdefault(node_lit.group(2), {}).update(self._parse_props(q, p))
            return None
        raise AssertionError(f"内存桩未支持的语句: {q[:160]}")


class _ExpandStub:
    """录句桩：捕获 expand_entity_neighbors 下发的 Cypher+参数，按需吐预置行。"""

    def __init__(self, rows):
        self.rows = rows
        self.queries = []  # [(query, params)]

    class _Result:
        def __init__(self, stub, q, p):
            self._s, self._q, self._p = stub, q, (p or {})

        def __iter__(self):
            self._s.queries.append((self._q, dict(self._p)))
            return iter(self._s.rows)

    class _Session:
        def __init__(self, stub):
            self._s = stub

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def run(self, q, **p):
            return _ExpandStub._Result(self._s, q, p)

    class _Driver:
        def __init__(self, stub):
            self._s = stub

        def session(self):
            return _ExpandStub._Session(self._s)


def _sqlite_db():
    """独立内存 SQLite（M05 投射三表+挂接表），供投射/改挂/子图测试——防误写真实图谱数据。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import (
        Base, Concept, Entity, EntityConceptLink, EntityRelation,
    )
    eng = create_engine("sqlite://")
    Base.metadata.create_all(bind=eng, tables=[
        m.__table__ for m in (Concept, Entity, EntityConceptLink, EntityRelation)
    ])
    return sessionmaker(bind=eng)()


def _seed_m05_chain(db):
    """种子 m05t 双链：L0 dom / L1 grp / L2 l2a（父=grp）/ L3 l3（父=dom）/ L4 l4（父=l3）
    + L2 主数据实体 e_md、L4 活动实体 e_act、挂 L3 的 e_skip（非 L2/L4 → 投射跳过）
    + 打点关系 e_md→e_act + 跳过实体关系 e_skip→e_act（应不投射）。"""
    from app.models.base import Concept, Entity, EntityConceptLink, EntityRelation
    dom = Concept(name="m05t_dom", level=0, area_index=91)
    grp = Concept(name="m05t_grp", level=1, area_index=92)
    db.add_all([dom, grp])
    db.flush()
    l2a = Concept(name="m05t_l2a", level=2, parent_id=grp.id, area_index=92)
    l3 = Concept(name="m05t_l3", level=3, parent_id=dom.id, area_index=91)
    db.add_all([l2a, l3])
    db.flush()
    l4 = Concept(name="m05t_l4", level=4, parent_id=l3.id, area_index=91)
    db.add(l4)
    db.flush()
    e_md = Entity(concept_id=l2a.id, entity_code="m05t_md", entity_name="m05t主数据实体",
                  entity_en_name="m05t_md", is_main_table=True, properties_schema=[],
                  data_layer="ods")
    e_act = Entity(concept_id=l4.id, entity_code="m05t_act", entity_name="m05t活动实体",
                   entity_en_name="m05t_act", is_main_table=False, properties_schema=[])
    e_skip = Entity(concept_id=l3.id, entity_code="m05t_skip", entity_name="m05t跳过实体",
                    entity_en_name="m05t_skip", is_main_table=False, properties_schema=[])
    db.add_all([e_md, e_act, e_skip])
    db.flush()
    rel = EntityRelation(source_entity_id=e_md.id, target_entity_id=e_act.id,
                         relation_name="m05t打点", relation_category="打点维护",
                         cardinality="1:N", join_expr="m05t_md.cust_id = m05t_act.cust_id")
    rel_skip = EntityRelation(source_entity_id=e_skip.id, target_entity_id=e_act.id,
                              relation_name="m05t跳过实体关系", relation_category="手工维护")
    db.add_all([rel, rel_skip])
    db.add(EntityConceptLink(entity_id=e_md.id, concept_id=l2a.id))
    db.commit()
    return {"dom": dom, "grp": grp, "l2a": l2a, "l3": l3, "l4": l4,
            "e_md": e_md, "e_act": e_act, "e_skip": e_skip, "rel": rel, "rel_skip": rel_skip}


def _arm_fake_graph(monkeypatch):
    """healthcheck=True + driver→内存桩图（投射/改挂测试共用基座）。"""
    fake = _FakeGraph()
    monkeypatch.setattr(G, "neo4j_healthcheck", lambda: True)
    monkeypatch.setattr(G, "_get_driver", lambda: fake.driver())
    return fake


# ---------------------------------------------------------------------------
# §九.1 全量投射：L2X/L4X 投射规则 / RELATES_TO 属性完整 / 统计一致 / 幂等零增长
# ---------------------------------------------------------------------------

def test_sync_all_projection_rules_stats_idempotent(monkeypatch):
    """空桩库→sync_all(force) 投射规则与统计一致 + 重复执行零增长（spec §九.1/§三）：
    概念 code=f"L{n}-{id前8}"（§八.5 code 即幂等键）；实体仅 L2/L4 概念下者投射且
    L2→L2X(MD)/L4→L4X(BZ)、code=entity_code、附 entity_en_name/is_main_table/data_layer；
    RELATES_TO 五属性完整（relation_id/label/category/cardinality/join_expr）；
    BELONGS_TO_CHAIN 链归属 L1/L2/L2X→ROOT_MD、L3/L4/L4X→ROOT_BZ；
    force 重建与非 force 重跑均零增长（MERGE 幂等）。
    变异锚点：code 生成式改 → 概念 code 断言红；L2/L4 限定删 → e_skip 入桩库红；
    RELATES_TO 属性漏 SET → 属性字典红；链归属 WHERE 集合改 → BELONGS 断言红；
    MERGE 改 CREATE → 重跑计数增长红；force 清库删 → force 重跑不归零重建红。"""
    db = _sqlite_db()
    seed = _seed_m05_chain(db)
    fake = _arm_fake_graph(monkeypatch)
    res = G.sync_all_to_neo4j(db=db, force=True)
    assert res["ok"] is True
    assert res["concepts_synced"] == 5
    assert res["relations_synced"] == 1  # 跳过实体的关系不计入（entity_code_map 无键）
    # 节点/关系统计与种子计数一致：2 链根 + 5 概念 + 2 投射实体 = 9；
    # HAS_PARENT(3 概念 + 2 实体) + BELONGS_TO_CHAIN(3 MD + 3 BZ) + RELATES_TO(1) = 12
    assert res["total_nodes"] == 9 == len(fake.nodes)
    assert res["total_relations"] == 12 == len(fake.edges)
    # 投射规则：概念 code 规则（§八.5）
    code_of = {v.get("concept_id"): k for k, v in fake.nodes.items()}
    assert code_of[str(seed["l2a"].id)] == f"L2-{str(seed['l2a'].id)[:8]}"
    assert code_of[str(seed["grp"].id)] == f"L1-{str(seed['grp'].id)[:8]}"
    # 实体 L2→L2X(MD) / L4→L4X(BZ)，code=entity_code，附三配置面字段
    md = fake.nodes["m05t_md"]
    assert md["level"] == "L2X" and md["chain_type"] == "MD" and md["entity_type"] == "leaf"
    assert md["entity_en_name"] == "m05t_md" and md["is_main_table"] is True
    assert md["data_layer"] == "ods"
    act = fake.nodes["m05t_act"]
    assert act["level"] == "L4X" and act["chain_type"] == "BZ" and act["entity_type"] == "leaf"
    # 非 L2/L4 概念下实体不投射（§三跳过规则），其关系也不投射
    assert "m05t_skip" not in fake.nodes
    assert not any("m05t_skip" in k for k in fake.edges)
    assert not any(v.get("relation_id") == str(seed["rel_skip"].id) for v in fake.edges.values())
    # RELATES_TO 属性完整（§三 L366-382）
    assert fake.edges[("m05t_md", "RELATES_TO", "m05t_act")] == {
        "relation_id": str(seed["rel"].id), "label": "m05t打点", "category": "打点维护",
        "cardinality": "1:N", "join_expr": "m05t_md.cust_id = m05t_act.cust_id",
    }
    # HAS_PARENT：概念父子 + 实体挂接
    assert (f"L2-{str(seed['l2a'].id)[:8]}", "HAS_PARENT",
            f"L1-{str(seed['grp'].id)[:8]}") in fake.edges
    assert ("m05t_md", "HAS_PARENT", f"L2-{str(seed['l2a'].id)[:8]}") in fake.edges
    assert ("m05t_act", "HAS_PARENT", f"L4-{str(seed['l4'].id)[:8]}") in fake.edges
    # BELONGS_TO_CHAIN 链归属
    for code in (f"L1-{str(seed['grp'].id)[:8]}", f"L2-{str(seed['l2a'].id)[:8]}", "m05t_md"):
        assert (code, "BELONGS_TO_CHAIN", "ROOT_MD") in fake.edges
    for code in (f"L3-{str(seed['l3'].id)[:8]}", f"L4-{str(seed['l4'].id)[:8]}", "m05t_act"):
        assert (code, "BELONGS_TO_CHAIN", "ROOT_BZ") in fake.edges
    # 幂等：force 重建与非 force 重跑均零增长（MERGE on code）
    res2 = G.sync_all_to_neo4j(db=db, force=True)
    assert (res2["total_nodes"], res2["total_relations"]) == (9, 12)
    res3 = G.sync_all_to_neo4j(db=db)  # 非 force 增量重跑
    assert (res3["total_nodes"], res3["total_relations"]) == (9, 12)
    assert len(fake.nodes) == 9 and len(fake.edges) == 12


# ---------------------------------------------------------------------------
# §九.2 实体改挂概念 → 重同步后 HAS_PARENT 更新
# ---------------------------------------------------------------------------

def test_sync_all_remount_updates_has_parent(monkeypatch):
    """实体改挂概念 → 重同步后 HAS_PARENT 更新（spec §九.2）：
    增量重同步（非 force）以 MERGE on code 重投射出新指向边（M03 批
    test_hierarchy_change_incremental_reprojection 同范式）；force 重建后权威干净态——
    改挂实体仅挂新概念。
    变异锚点：code 生成式改 → 重投射目标失配红；HAS_PARENT 循环删/实体漏挂 → 新指向边缺红；
    force 清库删 → 重建后残留旧挂接红。"""
    from app.models.base import Concept
    db = _sqlite_db()
    seed = _seed_m05_chain(db)
    fake = _arm_fake_graph(monkeypatch)
    G.sync_all_to_neo4j(db=db, force=True)
    ent_code = seed["e_md"].entity_code  # m05t_md
    a_code = f"L2-{str(seed['l2a'].id)[:8]}"
    assert (ent_code, "HAS_PARENT", a_code) in fake.edges
    # 改挂到新 L2 概念 b → 增量重同步（非 force）后 HAS_PARENT 更新到新概念
    b = Concept(name="m05t_l2b", level=2, parent_id=seed["grp"].id, area_index=93)
    db.add(b)
    db.commit()
    b_code = f"L2-{str(b.id)[:8]}"
    seed["e_md"].concept_id = b.id
    db.commit()
    res = G.sync_all_to_neo4j(db=db)  # 非 force 增量
    assert res["ok"] is True
    assert (ent_code, "HAS_PARENT", b_code) in fake.edges
    # force 重建：权威干净态——改挂后实体仅挂新概念
    G.sync_all_to_neo4j(db=db, force=True)
    ent_edges = {k for k in fake.edges if k[0] == ent_code and k[1] == "HAS_PARENT"}
    assert ent_edges == {(ent_code, "HAS_PARENT", b_code)}


# ---------------------------------------------------------------------------
# §九.3 expand_entity_neighbors：hop/limit 夹取 + 结果三元组形态
# ---------------------------------------------------------------------------

def test_expand_neighbors_hop_limit_clamped_in_query(monkeypatch):
    """越界参数被夹取（spec §九.3/§八.4）：hop 0/-1→1、2→2、4/99→3（内联表达式真值，
    录句桩断言下发 Cypher 的变长路径上界）；limit 0→1、500→200、20→20（参数 $lim）。
    变异锚点：夹取表达式改宽/删（如直接用 max_hop 拼查询）→ 上界断言红；
    limit 夹取删 → $lim 越界值透传红。"""
    stub = _ExpandStub([])
    monkeypatch.setattr(G, "neo4j_healthcheck", lambda: True)
    monkeypatch.setattr(G, "_get_driver", lambda: _ExpandStub._Driver(stub))
    for hop_in, hop_q in ((0, 1), (-1, 1), (1, 1), (2, 2), (3, 3), (4, 3), (99, 3)):
        G.expand_entity_neighbors(["e1"], max_hop=hop_in)
        q, _ = stub.queries[-1]
        assert f"[r*1..{hop_q}]" in q, f"max_hop={hop_in} 应夹取为 {hop_q}：{q}"
    for lim_in, lim_q in ((0, 1), (1, 1), (20, 20), (500, 200)):
        G.expand_entity_neighbors(["e1"], limit=lim_in)
        _, p = stub.queries[-1]
        assert p["lim"] == lim_q, f"limit={lim_in} 应夹取为 {lim_q}"


def test_expand_neighbors_result_shape_rel_type_label_hop(monkeypatch):
    """1~3 hop 结果含 rel_type/rel_label/hop（spec §九.3）：取路径最后一段关系类型/标签，
    hop 为整数路径长度；源/邻居实体 id 与路径全量关系类型随行（问数定位链消费）。
    变异锚点：行映射改键/取首段而非末段 → 三元组断言红；hop 未 int 化 → 类型红。"""
    stub = _ExpandStub([{
        "source_id": "s1", "neighbor_id": "n1", "neighbor_name": "邻居A", "neighbor_code": "NA",
        "hop": 2, "path_rel_types": ["RELATES_TO", "HAS_PARENT"],
        "path_rel_labels": ["m05t打点", "层级"],
    }])
    monkeypatch.setattr(G, "neo4j_healthcheck", lambda: True)
    monkeypatch.setattr(G, "_get_driver", lambda: _ExpandStub._Driver(stub))
    out = G.expand_entity_neighbors(["s1"], max_hop=2)
    assert len(out) == 1
    r = out[0]
    assert (r["rel_type"], r["rel_label"], r["hop"]) == ("HAS_PARENT", "层级", 2)
    assert r["source_entity_id"] == "s1" and r["neighbor_entity_id"] == "n1"
    assert r["neighbor_name"] == "邻居A" and r["neighbor_code"] == "NA"
    assert r["path_rel_types"] == ["RELATES_TO", "HAS_PARENT"]


# ---------------------------------------------------------------------------
# §九.4 kg_api 9 端点：非法输入 4xx + execute_sql 安全校验链
# ---------------------------------------------------------------------------

def test_kg_api_invalid_inputs_4xx():
    """kg_api 9 端点在案 + 非法输入 4xx（spec §九.4/§五 端点表）：
    缺必填体的 POST → 422（FastAPI 请求校验层，先于处理器，不触库）。
    变异锚点：端点增删改名 → 端点计数/路径集红；请求模型必填校验放宽（如 Optional 化）
    → 422 断言红。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.kg_api import router
    paths = {r.path for r in router.routes}
    assert len(router.routes) == 9, f"kg_api 端点数漂移：{sorted(paths)}"
    assert paths == {
        "/api/kg/fetch_l1_l2_tree", "/api/kg/validate_l2", "/api/kg/fetch_subgraph/{l2_id}",
        "/api/kg/validate_attributes", "/api/kg/fetch_join_expr/{source_entity}/{target_entity}",
        "/api/kg/validate_safe_sql", "/api/kg/execute_sql",
        "/api/kg/entity_source_mode/{entity_code}", "/api/kg/batch_entity_source_mode",
    }
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.post("/api/kg/validate_l2").status_code == 422              # 缺体
    assert client.post("/api/kg/validate_safe_sql").status_code == 422        # 缺 sql
    assert client.post("/api/kg/validate_attributes", json={}).status_code == 422  # 缺 entity_code
    assert client.post("/api/kg/execute_sql", json={}).status_code == 422     # 缺 sql


def test_kg_execute_sql_uses_safety_chain(monkeypatch):
    """execute_sql 走 M21 安全校验链（secure_query_executor.validate_sql，不可绕过）：
    不安全 SQL → 403「SQL安全校验未通过」；通过校验 → 执行函数收到强制 LIMIT 改写后的
    sanitized SQL（§九.4/§一 M21 协同；validate_safe_sql 端点语义族由
    backend/tests/test_sql_safety.py 交叉锚定）。
    变异锚点：execute_sql 跳过 validate_sql 直连执行 → 403 断言红；
    sanitized SQL 未透传 exec_fn（绕过校验链产物）→ LIMIT 断言红。"""
    from app.api.kg_api import ExecuteSqlRequest, execute_sql
    monkeypatch.setattr("app.services.guard_config.guard_enabled",
                        lambda gid, sub=None: True)  # 确定性：守卫基线开启（fail-closed）
    with pytest.raises(HTTPException) as ei:
        execute_sql(ExecuteSqlRequest(sql="DROP TABLE m05t_t"))
    assert ei.value.status_code == 403
    assert "SQL安全校验未通过" in str(ei.value.detail)

    captured = {}

    def _exec_fn(sql):
        captured["sql"] = sql
        return {"ok": True}

    monkeypatch.setattr("app.services.sql_executor._build_execute_query_fn", lambda: _exec_fn)
    res = execute_sql(ExecuteSqlRequest(sql="select cust_id from m05t_t"))
    assert res == {"ok": True}
    assert captured["sql"].upper().startswith("SELECT")
    assert "LIMIT" in captured["sql"].upper()  # 强制 LIMIT（M21 校验链产物）随 sanitized SQL 透传


# ---------------------------------------------------------------------------
# §九.5 Neo4j 停机：kg_api 图查询降级不 500
# ---------------------------------------------------------------------------

def test_kg_graph_queries_degrade_when_neo4j_down(monkeypatch):
    """Neo4j 停机 → kg_api 图查询面降级不 500（spec §九.5/§八.3/§一连接隐藏）：
    fetch_l1_l2_tree/fetch_subgraph 走 MySQL 面照常返回结构化结果（不触 Neo4j 不抛）；
    引擎函数静默降级由 test_healthcheck_false_drives_degrade（本文件既有）锚定，
    启动成功+warning 由 test_m01_base.py::test_lifespan_degrades_external_deps_down 锚定。
    变异锚点：图查询面改直连 Neo4j driver 且无降级护栏 → 停机桩下抛异常红。"""
    from app.api import kg_api
    monkeypatch.setattr(G, "neo4j_healthcheck", lambda: False)
    tree = kg_api.fetch_l1_l2_tree()
    assert isinstance(tree, dict) and "l1_list" in tree
    sub = kg_api.fetch_subgraph("m05t-nonexistent-l2")
    assert isinstance(sub, dict) and {"l2_name", "l2x_entities", "cross_chain"} <= set(sub)


# ---------------------------------------------------------------------------
# §九.6 /graph/subgraph-by-l1 画布形状契约
# ---------------------------------------------------------------------------

def test_subgraph_by_l1_canvas_shape():
    """/graph/subgraph-by-l1 三段形状契约满足 M03 画布渲染（spec §九.6/§六）：
    meta（l1_id/l1_name/node_count/edge_count）与 nodes/edges 计数自洽；节点含
    id/label/type（concept|entity），边含 id/source/target/edge_type（concept_hierarchy/
    concept_entity_link/entity_generation）；主数据半（L1/L2/主数据实体）在案，业务活动半
    （L0/L3/L4/活动实体）经实体关系展开；未知 L1 → 404。
    /graph/data 与 /graph/neo4j-data 形状由 test_m03_concept.py 两测交叉锚定（既有）。
    变异锚点：meta 计数不自洽/节点缺 type/边缺 edge_type → 画布数据断红；
    未知 L1 不 404 → 过滤器契约红。"""
    from app.api.concept_graph import get_subgraph_by_l1
    db = _sqlite_db()
    seed = _seed_m05_chain(db)
    res = get_subgraph_by_l1(str(seed["grp"].id), db=db)
    assert set(res) == {"nodes", "edges", "meta"}
    meta = res["meta"]
    assert meta["l1_id"] == str(seed["grp"].id) and meta["l1_name"] == "m05t_grp"
    assert meta["node_count"] == len(res["nodes"]) and meta["edge_count"] == len(res["edges"])
    for n in res["nodes"]:
        assert {"id", "label", "type"} <= set(n) and n["type"] in ("concept", "entity")
    for e in res["edges"]:
        assert {"id", "source", "target", "edge_type"} <= set(e)
    nodes = {n["id"]: n for n in res["nodes"]}
    # 主数据半：L1/L2 概念 + 主数据实体
    assert nodes[str(seed["grp"].id)]["level"] == 1
    assert nodes[str(seed["l2a"].id)]["level"] == 2
    assert nodes[str(seed["e_md"].id)]["type"] == "entity"
    assert nodes[str(seed["e_md"].id)]["entity_category"] == "master_entity"
    # 业务活动半经实体关系展开：L4/L3/L0 概念 + 活动实体
    assert nodes[str(seed["l4"].id)]["level"] == 4
    assert nodes[str(seed["l3"].id)]["level"] == 3
    assert nodes[str(seed["dom"].id)]["level"] == 0
    assert nodes[str(seed["e_act"].id)]["type"] == "entity"
    assert nodes[str(seed["e_act"].id)]["entity_category"] == "activity_entity"
    etypes = {e["edge_type"] for e in res["edges"]}
    assert {"concept_hierarchy", "concept_entity_link", "entity_generation"} <= etypes
    # 未知 L1 → 404
    with pytest.raises(HTTPException) as ei:
        get_subgraph_by_l1("m05t-nonexistent-l1", db=db)
    assert ei.value.status_code == 404


# ---------------------------------------------------------------------------
# 附：老 /sync 双轨冻结登记态（spec §四/§十，禁改清单件）
# ---------------------------------------------------------------------------

def test_old_sync_endpoint_frozen_double_track():
    """老 /sync 路径双轨冻结登记态（spec §四/§十——收编前行为不变）：POST /sync 仍走老
    Neo4jSyncService（Concept/Entity 旧标签体系逐节点同步），未收编到新引擎
    sync_all_to_neo4j；本测仅断言登记态本身，收编须过设计批次，不许顺手收编。
    变异锚点：未登记收编即改道新引擎/老服务标签体系漂移 → 冻结态破坏红。"""
    from app.api import concept_graph as CG
    from app.services import graph_sync as gs
    src = inspect.getsource(CG.sync_to_neo4j)
    assert "Neo4jSyncService" in src and "sync_concept" in src  # 老服务逐节点路径
    assert "sync_all_to_neo4j" not in src  # 未收编（新引擎不经此端点）
    old_src = inspect.getsource(gs.Neo4jSyncService._create_concept_node)
    assert "MERGE (c:Concept {id: $id})" in old_src  # 旧标签体系（Concept+动态 Level）冻结
