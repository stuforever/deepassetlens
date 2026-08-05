"""
graph_query 用的 Neo4j 实体邻居服务

提供两个能力：
1. sync_entities_and_relations_from_mysql(db)
   把 MySQL 的 Entity + Relation 灌到 Neo4j（幂等 MERGE）。
   仅同步当前 enabled 的实体与启用的关系。
2. expand_entity_neighbors(entity_ids, max_hop=1, limit=20)
   给定命中实体 ID 列表，返回 1-hop（默认）邻居与连接关系，
   用于"图问数"链路的图谱补足。

设计要点
    - 用 neo4j-driver 同步驱动（v6.x），单例 driver 在进程级共享。
    - 全部 Cypher 走参数化，杜绝注入。
    - 邻居返回保持 plain dict，方便 SSE / JSON 序列化。
    - sync 是幂等的：多次调用合并而不重复（MERGE on id）。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


_DRIVER = None
_DRIVER_LOCK = threading.Lock()


def _get_driver():
    global _DRIVER
    if _DRIVER is None:
        with _DRIVER_LOCK:
            if _DRIVER is None:
                from neo4j import GraphDatabase

                uri = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
                user = os.environ.get("NEO4J_USER", "neo4j")
                pwd = os.environ.get("NEO4J_PASSWORD", "")
                _DRIVER = GraphDatabase.driver(uri, auth=(user, pwd))
    return _DRIVER


def neo4j_healthcheck() -> bool:
    try:
        driver = _get_driver()
        with driver.session() as session:
            session.run("RETURN 1").consume()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("neo4j_healthcheck failed: %s", exc)
        return False


def neo4j_count_nodes_and_relations() -> Dict[str, int]:
    driver = _get_driver()
    with driver.session() as session:
        n = session.run("MATCH (n:Entity) RETURN count(n) AS c").single()["c"]
        r = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    return {"entities": int(n), "relations": int(r)}


def sync_entities_and_relations_from_mysql(db: Session, *, force: bool = False) -> Dict[str, Any]:
    """把 MySQL 实体 + 关系全量灌进 Neo4j。

    - Entity 节点：label = Entity，主键 id（UUID 字符串），属性含 name/code/en_name。
    - 实体关系：从 EntityRelation 表读取启用项，rel_type 用关系的 type_code（默认 RELATED_TO）。

    幂等：MERGE on id，多次调用结果一致。
    force=True 会先 DETACH DELETE 全部 Entity 节点。
    """
    started_at = time.time()
    if not neo4j_healthcheck():
        return {"ok": False, "error": "neo4j_unavailable"}

    from app.models.base import Entity, EntityRelation

    entities = db.query(Entity).all()
    relations = db.query(EntityRelation).all()

    driver = _get_driver()

    # 计数：当前 Neo4j 已有数据，幂等性保护
    pre_counts = neo4j_count_nodes_and_relations()
    if (
        not force
        and pre_counts.get("entities", 0) >= len(entities) > 0
        and pre_counts.get("relations", 0) >= len(relations)
    ):
        return {
            "ok": True,
            "synced_entities": 0,
            "synced_relations": 0,
            "total_entities": len(entities),
            "total_relations": len(relations),
            "took_ms": int((time.time() - started_at) * 1000),
            "note": "neo4j_already_in_sync",
            "pre_counts": pre_counts,
        }

    if force:
        with driver.session() as session:
            session.run("MATCH (n:Entity) DETACH DELETE n").consume()

    # 全量 upsert
    with driver.session() as session:
        for ent in entities:
            session.run(
                """
                MERGE (e:Entity {id: $id})
                SET e.name = $name,
                    e.code = $code,
                    e.en_name = $en_name,
                    e.entity_type = $etype
                """,
                id=str(ent.id),
                name=ent.entity_name or ent.entity_code or str(ent.id),
                code=ent.entity_code,
                en_name=ent.entity_en_name,
                etype=getattr(ent, "entity_type", None) or "data",
            ).consume()

        for rel in relations:
            rel_type_raw = (
                getattr(rel, "relation_name", None)
                or getattr(rel, "relation_type", None)
                or "RELATED_TO"
            ).strip() or "RELATED_TO"
            rel_type_safe = rel_type_raw.replace("`", "")
            session.run(
                f"""
                MATCH (s:Entity {{id: $sid}})
                MATCH (t:Entity {{id: $tid}})
                MERGE (s)-[r:`{rel_type_safe}`]->(t)
                SET r.relation_id = $rid,
                    r.label = $label,
                    r.category = $category
                """,
                sid=str(rel.source_entity_id),
                tid=str(rel.target_entity_id),
                rid=str(rel.id),
                label=rel_type_raw,
                category=getattr(rel, "relation_category", None) or "",
            ).consume()

    post_counts = neo4j_count_nodes_and_relations()
    return {
        "ok": True,
        "synced_entities": len(entities),
        "synced_relations": len(relations),
        "total_entities": post_counts.get("entities", 0),
        "total_relations": post_counts.get("relations", 0),
        "took_ms": int((time.time() - started_at) * 1000),
        "note": "fresh_sync",
    }


def expand_entity_neighbors(
    entity_ids: List[str],
    *,
    max_hop: int = 1,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """1~max_hop 邻居展开。返回邻居节点 + 路径上的关系类型。

    Args:
        entity_ids: 起始实体 id 列表（UUID 字符串）
        max_hop:   邻居展开跳数，默认 1
        limit:     单次返回的最大记录数（路径计数）

    Return:
        [
          {
            "source_entity_id": "...",
            "neighbor_entity_id": "...",
            "neighbor_name": "...",
            "rel_type": "...",
            "rel_label": "...",
            "hop": 1,
          },
          ...
        ]
    """
    if not entity_ids:
        return []
    if not neo4j_healthcheck():
        return []

    eids = [str(x).strip() for x in entity_ids if x]
    if not eids:
        return []

    hop_clip = max(1, min(int(max_hop), 3))
    lim = max(1, min(int(limit), 200))

    driver = _get_driver()
    with driver.session() as session:
        result = session.run(
            f"""
            MATCH (s:Entity)
            WHERE s.id IN $sids
            MATCH p = (s)-[r*1..{hop_clip}]-(n:Entity)
            WHERE n.id <> s.id
            RETURN s.id AS source_id,
                   n.id AS neighbor_id,
                   n.name AS neighbor_name,
                   n.code AS neighbor_code,
                   length(p) AS hop,
                   [rel IN r | type(rel)] AS path_rel_types,
                   [rel IN r | rel.label] AS path_rel_labels
            ORDER BY hop ASC
            LIMIT $lim
            """,
            sids=eids,
            lim=lim,
        )
        rows: List[Dict[str, Any]] = []
        for record in result:
            path_types = list(record["path_rel_types"] or [])
            path_labels = list(record["path_rel_labels"] or [])
            rows.append(
                {
                    "source_entity_id": record["source_id"],
                    "neighbor_entity_id": record["neighbor_id"],
                    "neighbor_name": record["neighbor_name"],
                    "neighbor_code": record["neighbor_code"],
                    "hop": int(record["hop"]),
                    "rel_type": path_types[-1] if path_types else None,
                    "rel_label": path_labels[-1] if path_labels else None,
                    "path_rel_types": path_types,
                }
            )
    return rows


def wipe_neo4j() -> Dict[str, Any]:
    """全库清空 Neo4j（MATCH (n) DETACH DELETE n）"""
    if not neo4j_healthcheck():
        return {"ok": False, "error": "neo4j_unavailable"}
    driver = _get_driver()
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    return {"ok": True, "message": "neo4j_wiped"}


def _count_all() -> Dict[str, int]:
    driver = _get_driver()
    with driver.session() as session:
        n = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        r = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    return {"nodes": int(n), "relations": int(r)}


def sync_all_to_neo4j(db: Session, *, force: bool = False) -> Dict[str, Any]:
    """全量同步 MySQL → Neo4j，重建单一 Category+ChainRoot 体系。

    节点: ChainRoot(ROOT_MD/ROOT_BZ), Category(L1/L2/L2X/L3/L4/L4X)
    关系: HAS_PARENT, BELONGS_TO_CHAIN, RELATES_TO
    幂等: MERGE on code，force=True 先全库清空。
    """
    started_at = time.time()
    if not neo4j_healthcheck():
        return {"ok": False, "error": "neo4j_unavailable"}

    from app.models.base import Concept, Entity, EntityRelation

    driver = _get_driver()

    if force:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n").consume()

    concepts = db.query(Concept).all()
    entities = db.query(Entity).all()
    relations = db.query(EntityRelation).all()

    level_map = {1: "L1", 2: "L2", 3: "L3", 4: "L4"}
    concept_dict = {str(c.id): c for c in concepts}
    concept_code_map: Dict[str, str] = {}
    entity_code_map: Dict[str, str] = {}

    with driver.session() as session:
        session.run(
            "MERGE (r:ChainRoot {code:'ROOT_MD'}) "
            "SET r.name='主数据链根', r.level='ROOT', r.chain_type='MD'"
        ).consume()
        session.run(
            "MERGE (r:ChainRoot {code:'ROOT_BZ'}) "
            "SET r.name='业务链根', r.level='ROOT', r.chain_type='BZ'"
        ).consume()

        for c in concepts:
            lvl = level_map.get(c.level, f"L{c.level}")
            code = f"{lvl}-{str(c.id)[:8]}"
            concept_code_map[str(c.id)] = code
            ct = "MD" if c.level in (1, 2) else "BZ"
            session.run(
                "MERGE (n:Category {code:$code}) "
                "SET n.level=$lvl, n.name=$name, n.chain_type=$ct, "
                "n.entity_type='category', n.concept_id=$cid",
                code=code, lvl=lvl, name=c.name, ct=ct, cid=str(c.id),
            ).consume()

        for e in entities:
            concept = concept_dict.get(str(e.concept_id))
            if not concept:
                continue
            parent_lvl = level_map.get(concept.level)
            if parent_lvl == "L2":
                ent_lvl, ct = "L2X", "MD"
            elif parent_lvl == "L4":
                ent_lvl, ct = "L4X", "BZ"
            else:
                continue
            ent_code = e.entity_code or f"{ent_lvl}-{str(e.id)[:8]}"
            entity_code_map[str(e.id)] = ent_code
            session.run(
                "MERGE (n:Category:Entity {code:$code}) "
                "SET n.level=$lvl, n.name=$name, n.chain_type=$ct, "
                "n.entity_type='leaf', n.entity_id=$eid, "
                "n.entity_en_name=$en, n.is_main_table=$main, n.data_layer=$dl",
                code=ent_code, lvl=ent_lvl, name=e.entity_name, ct=ct,
                eid=str(e.id), en=e.entity_en_name or "",
                main=bool(e.is_main_table), dl=e.data_layer or "",
            ).consume()

        for c in concepts:
            if c.parent_id:
                child_code = concept_code_map.get(str(c.id))
                parent_code = concept_code_map.get(str(c.parent_id))
                if child_code and parent_code:
                    session.run(
                        "MATCH (ch:Category {code:$c}), (pa:Category {code:$p}) "
                        "MERGE (ch)-[:HAS_PARENT]->(pa)",
                        c=child_code, p=parent_code,
                    ).consume()

        for e in entities:
            ent_code = entity_code_map.get(str(e.id))
            parent_code = concept_code_map.get(str(e.concept_id))
            if ent_code and parent_code:
                session.run(
                    "MATCH (ch:Category {code:$c}), (pa:Category {code:$p}) "
                    "MERGE (ch)-[:HAS_PARENT]->(pa)",
                    c=ent_code, p=parent_code,
                ).consume()

        session.run(
            "MATCH (n:Category) WHERE n.level IN ['L1','L2','L2X'] "
            "MATCH (r:ChainRoot {code:'ROOT_MD'}) "
            "MERGE (n)-[:BELONGS_TO_CHAIN]->(r)"
        ).consume()
        session.run(
            "MATCH (n:Category) WHERE n.level IN ['L3','L4','L4X'] "
            "MATCH (r:ChainRoot {code:'ROOT_BZ'}) "
            "MERGE (n)-[:BELONGS_TO_CHAIN]->(r)"
        ).consume()

        rel_count = 0
        for rel in relations:
            src_code = entity_code_map.get(str(rel.source_entity_id))
            tgt_code = entity_code_map.get(str(rel.target_entity_id))
            if src_code and tgt_code:
                session.run(
                    "MATCH (s:Category {code:$src}), (t:Category {code:$tgt}) "
                    "MERGE (s)-[r:RELATES_TO]->(t) "
                    "SET r.relation_id=$rid, r.label=$label, r.category=$cat, "
                    "r.cardinality=$card, r.join_expr=$join",
                    src=src_code, tgt=tgt_code, rid=str(rel.id),
                    label=(rel.relation_name or "RELATED_TO").strip() or "RELATED_TO",
                    cat=rel.relation_category or "",
                    card=rel.cardinality or "",
                    join=rel.join_expr or "",
                ).consume()
                rel_count += 1

    post = _count_all()
    return {
        "ok": True,
        "concepts_synced": len(concepts),
        "entities_synced": len(entities),
        "relations_synced": rel_count,
        "total_nodes": post["nodes"],
        "total_relations": post["relations"],
        "took_ms": int((time.time() - started_at) * 1000),
    }


def fetch_l1_l3() -> List[Dict[str, Any]]:
    """查全量 L1/L3 Category 列表"""
    if not neo4j_healthcheck():
        return []
    driver = _get_driver()
    with driver.session() as s:
        return s.run(
            "MATCH (c:Category) WHERE c.level IN ['L1','L3'] "
            "RETURN c.code AS code, c.name AS name, c.level AS level, "
            "c.chain_type AS chain_type ORDER BY c.level, c.code"
        ).data() or []


def fetch_children_by_parent(parent_code: str) -> List[Dict[str, Any]]:
    """查 L2/L4/L2X/L4X 子节点（按 parent code）"""
    if not parent_code or not neo4j_healthcheck():
        return []
    driver = _get_driver()
    with driver.session() as s:
        return s.run(
            "MATCH (p:Category {code:$code})<-[:HAS_PARENT]-(c:Category) "
            "RETURN c.code AS code, c.name AS name, c.level AS level, "
            "c.chain_type AS chain_type, c.entity_type AS entity_type, "
            "c.is_main_table AS is_main_table "
            "ORDER BY c.level, c.code",
            code=parent_code,
        ).data() or []


__all__ = [
    "neo4j_healthcheck",
    "neo4j_count_nodes_and_relations",
    "sync_entities_and_relations_from_mysql",
    "expand_entity_neighbors",
    "wipe_neo4j",
    "sync_all_to_neo4j",
    "fetch_l1_l3",
    "fetch_children_by_parent",
]
