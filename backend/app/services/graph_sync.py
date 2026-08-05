from neo4j import GraphDatabase
import os
import uuid

class Neo4jSyncService:
    def __init__(self):
        # 优先读 .env / 进程环境；与 graph_query_neo4j.py 对齐
        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        # 密码从 NEO4J_PASSWORD 环境变量读取（docker-compose 从 .env.infra 注入）
        pwd = os.getenv("NEO4J_PASSWORD") or os.getenv("NEO4J_PASS") or ""
        self.driver = GraphDatabase.driver(uri, auth=(user, pwd))

    def close(self):
        self.driver.close()

    def sync_concept(self, concept_id: str, name: str, level: int, parent_id: str = None):
        """同步概念节点到 Neo4j"""
        with self.driver.session() as session:
            session.execute_write(self._create_concept_node, concept_id, name, level)
            if parent_id:
                # 清理旧的 BELONGS_TO 关系以防重复
                session.run("MATCH (c:Concept {id: $child_id})-[r:BELONGS_TO]->(p:Concept {id: $parent_id}) DELETE r", child_id=concept_id, parent_id=parent_id)
                parent_level = level - 1 if level > 1 else 1
                session.execute_write(self._create_hierarchy_relation, concept_id, parent_id, parent_level, level)

    @staticmethod
    def _create_concept_node(tx, concept_id, name, level):
        # 使用 MERGE 确保幂等性，Labels 为 Concept 和对应的 Level
        query = (
            "MERGE (c:Concept {id: $id}) "
            "SET c.name = $name, c.level = $level "
            "SET c:Level" + str(level)
        )
        tx.run(query, id=concept_id, name=name, level=level)

    @staticmethod
    def _create_hierarchy_relation(tx, child_id, parent_id, parent_level, child_level):
        # 创建父子级层级关系，动态确定关系名称
        # L1到L2是细分，L2到L3是关联，L3到L4也是细分
        rel_type = "BELONGS_TO"
        if parent_level == 1 and child_level == 2:
            rel_type = "细分"
        elif parent_level == 2 and child_level == 3:
            rel_type = "关联"
        elif parent_level == 3 and child_level == 4:
            rel_type = "细分"

        query = (
            "MATCH (child:Concept {id: $child_id}) "
            "MATCH (parent:Concept {id: $parent_id}) "
            f"MERGE (parent)-[:`{rel_type}`]->(child)"
        )
        tx.run(query, child_id=child_id, parent_id=parent_id)

    def sync_entity(self, entity_id: str, name: str, concept_id: str):
        """同步数据实体节点到 Neo4j"""
        with self.driver.session() as session:
            # 清理旧的 INSTANCE_OF 关系
            session.run("MATCH (e:Entity {id: $id})-[r:INSTANCE_OF]->(c:Concept {id: $concept_id}) DELETE r", id=entity_id, concept_id=concept_id)
            query = (
                "MERGE (e:Entity {id: $id}) "
                "SET e.name = $name "
                "WITH e "
                "MATCH (c:Concept {id: $concept_id}) "
                "MERGE (c)-[:`实例化`]->(e)"
            )
            session.run(query, id=entity_id, name=name, concept_id=concept_id)

    def sync_relation(self, source_id: str, target_id: str, rel_type: str, properties: dict = None):
        """同步实体间业务关系"""
        with self.driver.session() as session:
            query = (
                "MATCH (s {id: $source_id}) "
                "MATCH (t {id: $target_id}) "
                f"MERGE (s)-[r:{rel_type}]->(t) "
                "SET r += $props"
            )
            session.run(query, source_id=source_id, target_id=target_id, props=properties or {})
