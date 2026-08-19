"""图/Neo4j/层级相关端点 -- 从 concept.py 拆分（机械迁移，行为等价）

迁移内容：sync-hierarchy / sync / graph/data / graph/subgraph-by-l1 / graph/neo4j-data 端点。
矩阵端点（graph/matrix、entities 矩阵打点）因行数平衡移入 concept_admin.py。
由 concept.py 聚合挂载，对外路由路径不变。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..models.base import Concept, Entity, EntityRelation, EntityConceptLink
from ..core.database import get_db
from .concept_support import (
    _sort_concepts, _sort_entities,
)

router = APIRouter()


@router.post("/sync-hierarchy")
def sync_hierarchy_to_neo4j():
    """一键同步业务链层级到 Neo4j

    包含：
      - ROOT_MD / ROOT_BZ 链根节点
      - L1/L2/L2X/L3/L4/L4X 全部 Category 节点
      - HAS_PARENT 父子关系
      - BELONGS_TO_CHAIN 链归属关系
      - RELATES_TO 跨链关系（含传递闭包派生）
      - RELATED_BY 反向关系（图谱可视化用）

    数据源：backend/data/business_chain_spec.yaml
    """
    try:
        import yaml
        from pathlib import Path
        from ..services.graph_query_neo4j import _get_driver

        spec_path = Path(__file__).parent.parent.parent / "data" / "business_chain_spec.yaml"
        if not spec_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"业务链 spec 不存在: {spec_path}",
            )

        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

        driver = _get_driver()
        with driver.session() as s:
            # 1. 清旧 L4/L4X
            s.run("MATCH (n) WHERE n.level IN ['L4', 'L4X'] DETACH DELETE n").consume()

            # 2. 链根
            s.run("""
                MERGE (r:ChainRoot:Category {code: 'ROOT_MD'})
                SET r.name = '主数据链根', r.level = 'ROOT', r.chain_type = 'MD'
            """).consume()
            s.run("""
                MERGE (r:ChainRoot:Category {code: 'ROOT_BZ'})
                SET r.name = '业务链根', r.level = 'ROOT', r.chain_type = 'BZ'
            """).consume()

            # 3. L1/L2/L2X → ROOT_MD, L3 → ROOT_BZ
            s.run("""
                MATCH (n:Category) WHERE n.level IN ['L1', 'L2', 'L2X']
                MATCH (r:ChainRoot {code: 'ROOT_MD'})
                MERGE (n)-[:BELONGS_TO_CHAIN]->(r)
            """).consume()
            s.run("""
                MATCH (n:Category) WHERE n.level = 'L3'
                MATCH (r:ChainRoot {code: 'ROOT_BZ'})
                MERGE (n)-[:BELONGS_TO_CHAIN]->(r)
            """).consume()

            # 4. L4 + HAS_PARENT → L3
            l4_count = 0
            for l3_code, l3_spec in spec.items():
                for l4 in l3_spec.get("L4", []):
                    s.run("""
                        MERGE (n:Category:Entity {code: $code})
                        SET n.level = 'L4',
                            n.name = $name,
                            n.chain_type = 'BZ',
                            n.entity_type = 'category'
                    """, code=l4["code"], name=l4["name"])
                    s.run("""
                        MATCH (l4:Category {code: $l4}), (l3:Category {code: $l3})
                        MERGE (l4)-[:HAS_PARENT]->(l3)
                    """, l4=l4["code"], l3=l3_code)
                    l4_count += 1

            # 5. L4X + HAS_PARENT → L4 + RELATES_TO → L2X
            l4x_count = 0
            rel_count = 0
            for l3_code, l3_spec in spec.items():
                for l4x in l3_spec.get("L4X", []):
                    s.run("""
                        MERGE (n:Category:Entity {code: $code})
                        SET n.level = 'L4X',
                            n.name = $name,
                            n.chain_type = 'BZ',
                            n.entity_type = 'leaf'
                    """, code=l4x["code"], name=l4x["name"])
                    s.run("""
                        MATCH (l4x:Category {code: $l4x}), (l4:Category {code: $l4})
                        MERGE (l4x)-[:HAS_PARENT]->(l4)
                    """, l4x=l4x["code"], l4=l4x["parent"])
                    l4x_count += 1

                    if l4x.get("relates_to"):
                        s.run("""
                            MATCH (l4x:Category {code: $l4x}), (l2x:Category {code: $l2x})
                            MERGE (l4x)-[r:RELATES_TO]->(l2x)
                            SET r.created_at = timestamp(),
                                r.relation_category = 'cross_chain'
                        """, l4x=l4x["code"], l2x=l4x["relates_to"])
                        rel_count += 1

            # 6. 传递闭包
            closure_count = s.run("""
                MATCH (l4x:Category)-[:RELATES_TO]->(l2x:Category)
                MATCH (l4x)-[:HAS_PARENT*1..2]->(l4:Category)
                MATCH (l2x)-[:HAS_PARENT*1..2]->(l2:Category)
                WHERE l4.level IN ['L4', 'L3'] AND l2.level IN ['L2', 'L1']
                MERGE (l4)-[r2:RELATES_TO]->(l2)
                ON CREATE SET r2.derived_from = 'transitive_closure',
                              r2.relation_category = 'cross_chain_derived'
                RETURN count(r2) AS cnt
            """).single()["cnt"]

            # 7. 反向
            back_count = s.run("""
                MATCH (a)-[r:RELATES_TO]->(b)
                MERGE (b)-[r2:RELATED_BY]->(a)
                ON CREATE SET r2.derived_from = 'reverse'
                RETURN count(r2) AS cnt
            """).single()["cnt"]

        return {
            "message": "Successfully synced business chain hierarchy to Neo4j",
            "l4_count": l4_count,
            "l4x_count": l4x_count,
            "cross_chain_relations": rel_count,
            "transitive_closure_count": closure_count,
            "reverse_relations": back_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"层级同步失败: {e}") from e


@router.post("/sync")
def sync_to_neo4j(db: Session = Depends(get_db)):
    """一键同步 Postgres 元数据到 Neo4j"""
    try:
        from ..services.graph_sync import Neo4jSyncService
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Neo4j sync dependency is not installed",
        ) from exc

    sync_service = Neo4jSyncService()
    try:
        # 1. 同步所有概念
        concepts = db.query(Concept).all()
        for c in concepts:
            sync_service.sync_concept(
                concept_id=str(c.id),
                name=c.name,
                level=c.level,
                parent_id=str(c.parent_id) if c.parent_id else None
            )
        
        # 2. 同步所有实体
        entities = db.query(Entity).all()
        for e in entities:
            sync_service.sync_entity(
                entity_id=str(e.id),
                name=e.entity_name,
                concept_id=str(e.concept_id)
            )
        
        return {"message": "Successfully synced to Neo4j", "concepts_count": len(concepts), "entities_count": len(entities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
    finally:
        sync_service.close()

@router.get("/graph/data")
def get_graph_data(db: Session = Depends(get_db)):
    """从本地关系型数据库生成图谱数据，概念间不再自动补边，仅展示实体关系"""
    try:
        nodes = []
        edges = []
        
        # 仅获取 level > 0 的概念（过滤业务域分类节点）
        concepts = _sort_concepts(db.query(Concept).filter(Concept.level > 0).all())
        concept_map = {str(c.id): c for c in concepts}
        
        for c in concepts:
            node_data = {
                "id": str(c.id),
                "name": c.name,  # 为了兼容 RightPanel 内部逻辑
                "label": c.name,
                "type": "concept",
                "level": c.level,
                "description": c.description,
                "system_names": c.system_names or [],
            }
            
            if c.level in [2, 4]:
                # 通过中间表查询关联的所有实体
                entity_links_for_c = db.query(EntityConceptLink).filter(EntityConceptLink.concept_id == c.id).all()
                entity_ids_for_c = [link.entity_id for link in entity_links_for_c]
                entities_for_c = db.query(Entity).filter(Entity.id.in_(entity_ids_for_c)).all() if entity_ids_for_c else []
                
                node_data["entities"] = [
                    {
                        "id": str(e.id), 
                        "concept_id": str(e.concept_id),
                        "entity_code": e.entity_code, 
                        "entity_name": e.entity_name,
                        "entity_explanation": e.entity_explanation,
                        "sort_order": e.sort_order or 0,
                        "description": e.description,
                        "is_main_table": e.is_main_table,
                        "data_layer": e.data_layer,
                        "landing_table_en_name": e.entity_en_name,
                        "properties_schema": e.properties_schema
                    }
                    for e in _sort_entities(entities_for_c)
                ]
                
            nodes.append(node_data)
            
        # 只显示在 kg_entity_concept_links 里有挂载的主数据(L2)/业务活动(L4)实体
        # 与主数据建模页面一致，避免展示 concept_id 关联但未挂载的 seed 实体，level 兜底排除 data_entity
        _linked_entity_ids = [link.entity_id for link in db.query(EntityConceptLink).all()]
        _ma_cids = {c.id for c in concepts if c.level in (2, 4)}
        entities = _sort_entities(
            db.query(Entity).filter(
                Entity.id.in_(_linked_entity_ids),
                Entity.concept_id.in_(_ma_cids)
            ).all()
        ) if _linked_entity_ids and _ma_cids else []
        for e in entities:
            e_id_str = str(e.id)
            entity_category = "data_entity"
            if e.concept_id and str(e.concept_id) in concept_map:
                entity_concept = concept_map[str(e.concept_id)]
                if entity_concept.level == 2:
                    entity_category = "master_entity"
                elif entity_concept.level == 4:
                    entity_category = "activity_entity"
            nodes.append({
                "id": e_id_str,
                "label": e.entity_name,
                "type": "entity",
                "entity_category": entity_category,
                "concept_id": str(e.concept_id),
                "entity_id": e_id_str,
                "entity_name": e.entity_name,
                "entity_code": e.entity_code,
                "entity_en_name": e.entity_en_name,
                "entity_explanation": e.entity_explanation,
                "description": e.description,
                "is_main_table": e.is_main_table,
                "data_layer": e.data_layer,
                "sort_order": e.sort_order or 0,
                "source_mode": e.source_mode or "physical_table",
                "integration_sql": e.integration_sql,
                "doris_catalog": e.doris_catalog,
                "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                "landing_table_en_name": e.entity_en_name,
                "properties_schema": e.properties_schema,
                "concept_ids": [str(l.concept_id) for l in db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == e.id).all()]
            })
            
            # 实体与概念的关联边：只用 kg_entity_concept_links（与主数据建模一致，不用 concept_id）
            links = db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == e.id).all()
            for link in links:
                edges.append({
                    "id": f"ec-link-{e_id_str}-{link.concept_id}",
                    "source": e_id_str,
                    "target": str(link.concept_id),
                    "label": "所属",
                    "edge_type": "concept_entity_link",
                })
            
        entity_relations = db.query(EntityRelation).all()
        for rel in entity_relations:
            edge_type = "entity_generation" if (rel.relation_category or "") == "打点维护" else "entity_relation"
            edges.append({
                "id": f"er-{rel.id}",
                "source": str(rel.source_entity_id),
                "target": str(rel.target_entity_id),
                "label": "生成" if edge_type == "entity_generation" else (rel.relation_name or "实体关系"),
                "edge_type": edge_type,
                "relation_name": rel.relation_name,
                "relation_category": rel.relation_category or "手工维护",
                "direction": rel.direction or "forward",
                "cardinality": rel.cardinality or "N:N",
                "source_field_name": rel.source_field_name,
                "target_field_name": rel.target_field_name,
                "join_expr": rel.join_expr,
                "description": rel.description,
                "remark": rel.remark,
            })
        
        # 概念间层级关系（L2->L1, L4->L3 主数据/业务活动建模）
        for c in concepts:
            if c.parent_id and str(c.parent_id) in concept_map:
                parent = concept_map[str(c.parent_id)]
                child_lv = {1:'L1',2:'L2',3:'L3',4:'L4'}.get(c.level,'')
                parent_lv = {1:'L1',2:'L2',3:'L3',4:'L4'}.get(parent.level,'')
                edges.append({
                    "id": f"cp-{c.id}-{c.parent_id}",
                    "source": str(c.id),
                    "target": str(c.parent_id),
                    "label": "层级",
                    "edge_type": "concept_hierarchy",
                    "child_level": child_lv,
                    "parent_level": parent_lv,
                })
        
        # 跨链关系已清除（用户要求：关系只查维护的关系，不展示初始化/跨链）

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate graph data: {str(e)}")


@router.get("/graph/subgraph-by-l1/{l1_id}")
def get_subgraph_by_l1(
    l1_id: str,
    db: Session = Depends(get_db),
):
    """按 L1 行业域过滤子图：返回该 L1 下的 L2、实体、关系

    用途：力导向图按 L1 顶点过滤（如选"客户"展示客户域子图）。

    Args:
        l1_id: L1 概念节点 ID

    Return:
        {nodes: [...], edges: [...], meta: {l1_id, l1_name, ...}}
    """
    try:
        l1 = db.query(Concept).filter(Concept.id == l1_id, Concept.level == 1).first()
        if not l1:
            raise HTTPException(status_code=404, detail=f"L1 不存在: {l1_id}")

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_ids = set()

        # L1 节点
        nodes.append({
            "id": str(l1.id), "name": l1.name, "label": l1.name,
            "type": "concept", "level": 1, "description": l1.description,
        })
        node_ids.add(str(l1.id))

        # L2 节点（parent_id = L1）
        l2_list = db.query(Concept).filter(Concept.parent_id == l1.id, Concept.level == 2).all()
        l2_ids = [str(c.id) for c in l2_list]
        for c in l2_list:
            nodes.append({
                "id": str(c.id), "name": c.name, "label": c.name,
                "type": "concept", "level": 2, "description": c.description,
            })
            node_ids.add(str(c.id))
            # L2 → L1 层级边
            edges.append({
                "id": f"cp-{c.id}-{l1.id}",
                "source": str(c.id), "target": str(l1.id),
                "label": "层级", "edge_type": "concept_hierarchy",
                "child_level": "L2", "parent_level": "L1",
            })

        # 实体节点（concept_id in L2_ids）
        entities = db.query(Entity).filter(Entity.concept_id.in_(l2_ids)).all() if l2_ids else []
        # 多对多挂载（EntityConceptLink）
        link_concept_ids = set(l2_ids)
        extra_links = db.query(EntityConceptLink).filter(EntityConceptLink.concept_id.in_(link_concept_ids)).all() if link_concept_ids else []
        extra_entity_ids = {str(l.entity_id) for l in extra_links}
        if extra_entity_ids:
            extra_entities = db.query(Entity).filter(Entity.id.in_(list(extra_entity_ids))).all()
            # 合并去重
            existing = {str(e.id) for e in entities}
            for e in extra_entities:
                if str(e.id) not in existing:
                    entities.append(e)

        entity_id_set = {str(e.id) for e in entities}

        for e in entities:
            entity_category = "data_entity"
            if e.concept_id and str(e.concept_id) in {str(c.id) for c in l2_list}:
                entity_category = "master_entity"
            nodes.append({
                "id": str(e.id), "label": e.entity_name, "type": "entity",
                "entity_category": entity_category,
                "concept_id": str(e.concept_id) if e.concept_id else None,
                "entity_id": str(e.id),
                "entity_name": e.entity_name,
                "entity_code": e.entity_code, "entity_en_name": e.entity_en_name,
                "entity_explanation": e.entity_explanation,
                "description": e.description,
                "is_main_table": e.is_main_table,
                "data_layer": e.data_layer,
                "source_mode": e.source_mode or "physical_table",
                "integration_sql": e.integration_sql,
                "doris_catalog": e.doris_catalog,
                "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                "landing_table_en_name": e.entity_en_name,
                "properties_schema": e.properties_schema,
            })
            node_ids.add(str(e.id))
            # 实体 -> L2 所属边
            if e.concept_id and str(e.concept_id) in node_ids:
                edges.append({
                    "id": f"ec-{e.id}-{e.concept_id}",
                    "source": str(e.id), "target": str(e.concept_id),
                    "label": "所属", "edge_type": "concept_entity_link",
                })

        # === 通过实体关系查业务活动树（L0->L3->L4->L4实体）===
        # 概念体系是两套独立树：主数据(L1->L2->L2实体) + 业务活动(L0->L3->L4->L4实体)
        # 两套树通过实体关系（L2实体->L4实体，含打点维护+手工维护）连接
        if entity_id_set:
            # 查所有 source 在集合内的关系，按 target 实体的 concept level=4 过滤
            all_src_rels = db.query(EntityRelation).filter(
                EntityRelation.source_entity_id.in_(list(entity_id_set)),
            ).all()
            # 收集 target 实体并查其 concept level
            tgt_ids = {str(r.target_entity_id) for r in all_src_rels}
            l4_entity_ids = set()
            matrix_rels = []
            if tgt_ids:
                tgt_entities = db.query(Entity).filter(Entity.id.in_(list(tgt_ids))).all()
                tgt_concept_ids = {str(e.concept_id) for e in tgt_entities if e.concept_id}
                tgt_concepts = {str(c.id): c for c in db.query(Concept).filter(
                    Concept.id.in_(list(tgt_concept_ids))
                ).all()} if tgt_concept_ids else {}
                for e in tgt_entities:
                    c = tgt_concepts.get(str(e.concept_id))
                    if c and c.level == 4:
                        l4_entity_ids.add(str(e.id))
                # 筛选指向 L4 实体的关系
                l4_entity_id_strs = l4_entity_ids
                matrix_rels = [r for r in all_src_rels if str(r.target_entity_id) in l4_entity_id_strs]

            if l4_entity_ids:
                l4_entities = db.query(Entity).filter(Entity.id.in_(list(l4_entity_ids))).all()
                # L4 概念
                l4_concept_ids = {str(e.concept_id) for e in l4_entities if e.concept_id}
                l4_concepts = db.query(Concept).filter(
                    Concept.id.in_(list(l4_concept_ids)), Concept.level == 4
                ).all() if l4_concept_ids else []
                # L3 概念
                l3_concept_ids = {str(c.parent_id) for c in l4_concepts if c.parent_id}
                l3_concepts = db.query(Concept).filter(
                    Concept.id.in_(list(l3_concept_ids)), Concept.level == 3
                ).all() if l3_concept_ids else []
                # L0 业务域
                l0_concept_ids = {str(c.parent_id) for c in l3_concepts if c.parent_id}
                l0_concepts = db.query(Concept).filter(
                    Concept.id.in_(list(l0_concept_ids)), Concept.level == 0
                ).all() if l0_concept_ids else []

                # L0 业务域节点
                for c in l0_concepts:
                    if str(c.id) not in node_ids:
                        nodes.append({
                            "id": str(c.id), "name": c.name, "label": c.name,
                            "type": "concept", "level": 0, "description": c.description,
                        })
                        node_ids.add(str(c.id))
                # L3 节点 + L3->L0 层级边
                for c in l3_concepts:
                    if str(c.id) not in node_ids:
                        nodes.append({
                            "id": str(c.id), "name": c.name, "label": c.name,
                            "type": "concept", "level": 3, "description": c.description,
                        })
                        node_ids.add(str(c.id))
                    if str(c.parent_id) in node_ids:
                        edges.append({
                            "id": f"cp-{c.id}-{c.parent_id}",
                            "source": str(c.id), "target": str(c.parent_id),
                            "label": "层级", "edge_type": "concept_hierarchy",
                            "child_level": "L3", "parent_level": "L0",
                        })
                # L4 节点 + L4->L3 层级边
                for c in l4_concepts:
                    if str(c.id) not in node_ids:
                        nodes.append({
                            "id": str(c.id), "name": c.name, "label": c.name,
                            "type": "concept", "level": 4, "description": c.description,
                        })
                        node_ids.add(str(c.id))
                    if str(c.parent_id) in node_ids:
                        edges.append({
                            "id": f"cp-{c.id}-{c.parent_id}",
                            "source": str(c.id), "target": str(c.parent_id),
                            "label": "层级", "edge_type": "concept_hierarchy",
                            "child_level": "L4", "parent_level": "L3",
                        })
                # L4 实体节点 + 实体->L4概念边
                for e in l4_entities:
                    if str(e.id) not in node_ids:
                        nodes.append({
                            "id": str(e.id), "label": e.entity_name, "type": "entity",
                            "entity_category": "activity_entity",
                            "concept_id": str(e.concept_id) if e.concept_id else None,
                            "entity_id": str(e.id),
                            "entity_name": e.entity_name,
                            "entity_code": e.entity_code, "entity_en_name": e.entity_en_name,
                            "entity_explanation": e.entity_explanation,
                            "description": e.description,
                            "is_main_table": e.is_main_table,
                            "data_layer": e.data_layer,
                            "source_mode": e.source_mode or "physical_table",
                            "integration_sql": e.integration_sql,
                            "doris_catalog": e.doris_catalog,
                            "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                            "landing_table_en_name": e.entity_en_name,
                            "properties_schema": e.properties_schema,
                        })
                        node_ids.add(str(e.id))
                        entity_id_set.add(str(e.id))
                    if e.concept_id and str(e.concept_id) in node_ids:
                        edges.append({
                            "id": f"ec-{e.id}-{e.concept_id}",
                            "source": str(e.id), "target": str(e.concept_id),
                            "label": "所属", "edge_type": "concept_entity_link",
                        })
                # 打点关系边（L2实体 -> L4实体）
                for r in matrix_rels:
                    if str(r.target_entity_id) in node_ids:
                        edges.append({
                            "id": f"er-{r.id}",
                            "source": str(r.source_entity_id), "target": str(r.target_entity_id),
                            "label": r.relation_name or "生成",
                            "edge_type": "entity_generation",
                            "relation_name": r.relation_name,
                            "relation_category": r.relation_category or "打点维护",
                            "direction": r.direction or "forward",
                            "cardinality": r.cardinality or "N:N",
                            "source_field_name": r.source_field_name,
                            "target_field_name": r.target_field_name,
                            "join_expr": r.join_expr,
                            "description": r.description,
                            "remark": r.remark,
                        })

        # 实体间关系（两端都在当前实体集合内）
        if entity_id_set:
            rels = db.query(EntityRelation).filter(
                EntityRelation.source_entity_id.in_(list(entity_id_set)),
                EntityRelation.target_entity_id.in_(list(entity_id_set)),
            ).all()
            for rel in rels:
                edge_type = "entity_generation" if (rel.relation_category or "") == "打点维护" else "entity_relation"
                edges.append({
                    "id": f"er-{rel.id}",
                    "source": str(rel.source_entity_id), "target": str(rel.target_entity_id),
                    "label": "生成" if edge_type == "entity_generation" else (rel.relation_name or "实体关系"),
                    "edge_type": edge_type,
                    "relation_name": rel.relation_name,
                    "relation_category": rel.relation_category or "手工维护",
                    "direction": rel.direction or "forward",
                    "cardinality": rel.cardinality or "N:N",
                    "source_field_name": rel.source_field_name,
                    "target_field_name": rel.target_field_name,
                    "join_expr": rel.join_expr,
                    "description": rel.description,
                    "remark": rel.remark,
                })

        return {
            "nodes": nodes, "edges": edges,
            "meta": {
                "l1_id": str(l1.id), "l1_name": l1.name,
                "node_count": len(nodes), "edge_count": len(edges),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 L1 子图失败: {str(e)}")


@router.get("/graph/neo4j-data")
def get_neo4j_graph_data():
    """从 Neo4j 图数据库生成力导图数据

    节点：Category（L1/L2/L3/L4 + L2X/L4X 实体）
    边：
      - HAS_PARENT（L2->L1, L4->L3, L2X->L2, L4X->L4）
      - RELATED_BY（L2->L3 跨链抽象）
      - RELATES_TO（L2X->L4X 打点维护）
    """
    try:
        from app.services.graph_query_neo4j import _get_driver
        driver = _get_driver()
        nodes = []
        edges = []
        node_ids = set()

        with driver.session() as s:
            # 1. 查所有 Category 节点（只取有效层级，过滤脏数据）
            valid_levels = ["L1", "L2", "L3", "L4", "L2X", "L4X"]
            rows = s.run("""
                MATCH (c:Category)
                WHERE c.level IN $validLevels
                RETURN c.code AS code, c.name AS name, c.level AS level,
                       c.concept_id AS concept_id, c.description AS description
                ORDER BY c.level, c.code
            """, validLevels=valid_levels).data()

            for r in rows:
                code = r.get("code") or ""
                level = r.get("level") or ""
                name = r.get("name") or code
                # 根据层级推断类型
                if level in ("L1", "L2", "L3", "L4"):
                    ntype = "concept"
                else:
                    ntype = "entity"
                # 标准化层级标签
                level_num = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}.get(level, 0)
                nodes.append({
                    "id": code,
                    "label": f"{level} {name}" if level else name,
                    "name": name,
                    "type": ntype,
                    "level": level_num,
                    "level_label": level,
                    "code": code,
                    "concept_id": r.get("concept_id"),
                    "description": r.get("description") or "",
                })
                node_ids.add(code)

            # 2. 查 HAS_PARENT 边（层级关系）
            rows = s.run("""
                MATCH (a:Category)-[:HAS_PARENT]->(b:Category)
                RETURN a.code AS src, b.code AS tgt, a.level AS src_lv, b.level AS tgt_lv
            """).data()
            for r in rows:
                src, tgt = r.get("src"), r.get("tgt")
                if src in node_ids and tgt in node_ids:
                    edges.append({
                        "id": f"hp-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "label": "层级",
                        "edge_type": "concept_hierarchy",
                        "child_level": r.get("src_lv"),
                        "parent_level": r.get("tgt_lv"),
                    })

            # 3. 查 RELATED_BY 边（L2-L3 跨链抽象）
            rows = s.run("""
                MATCH (a:Category)-[r:RELATED_BY]->(b:Category)
                RETURN a.code AS src, b.code AS tgt,
                       r.rel_type AS rel_type, r.derived_from AS derived_from
            """).data()
            for r in rows:
                src, tgt = r.get("src"), r.get("tgt")
                if src in node_ids and tgt in node_ids:
                    edges.append({
                        "id": f"cc-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "label": "跨链",
                        "edge_type": "concept_cross_chain",
                        "relation_name": "跨链抽象",
                        "derived_from": r.get("derived_from") or "",
                    })

            # 4. 查 RELATES_TO 边（L2X-L4X 打点维护）
            rows = s.run("""
                MATCH (a:Category)-[r:RELATES_TO]->(b:Category)
                RETURN a.code AS src, b.code AS tgt, r.relation_name AS rname
            """).data()
            for r in rows:
                src, tgt = r.get("src"), r.get("tgt")
                if src in node_ids and tgt in node_ids:
                    edges.append({
                        "id": f"rt-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "label": r.get("rname") or "打点维护",
                        "edge_type": "entity_generation",
                    })

        return {"nodes": nodes, "edges": edges, "source": "neo4j"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Neo4j graph data: {str(e)}")
