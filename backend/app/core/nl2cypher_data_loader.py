"""
NL2Cypher 语义数据加载器
从数据库加载所有语义配置数据为纯 Python 数据结构，供沙箱注入
"""
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def load_semantic_data(db: Session) -> dict:
    """加载所有语义管理数据为字典"""
    data = {}

    try:
        from app.models.base import (
            CommonStopWord, SemanticTimeNorm, SemanticTimeCypherMap,
            SemanticIntentNorm, SemanticExplodeNorm, StandardDict,
            OntologyMetric, Entity,
            CypherTemplate, GraphSchema
        )

        # stop_words: set
        rows = db.query(CommonStopWord).filter(CommonStopWord.enabled == True).all()
        data["stop_words"] = {r.word for r in rows}

        # time_norm: dict {word: time_code}
        rows = db.query(SemanticTimeNorm).filter(SemanticTimeNorm.enabled == True).all()
        data["time_norm"] = {r.word: r.time_code for r in rows}

        # time_cypher_map: dict {time_code: cypher_expr}
        rows = db.query(SemanticTimeCypherMap).filter(SemanticTimeCypherMap.enabled == True).all()
        data["time_cypher_map"] = {r.time_code: r.cypher_expr for r in rows}

        # intent_norm: dict {word: standard}
        rows = db.query(SemanticIntentNorm).filter(SemanticIntentNorm.enabled == True).all()
        data["intent_norm"] = {r.word: r.standard for r in rows}

        # explode_norm: dict {phrase: {"agg_hint": ..., "time_field": ...}}
        rows = db.query(SemanticExplodeNorm).filter(SemanticExplodeNorm.enabled == True).all()
        data["explode_norm"] = {
            r.phrase: {"agg_hint": r.agg_hint, "time_field": r.time_field}
            for r in rows
        }

        # synonym_norm: dict {non_standard: standard}
        rows = db.query(StandardDict).filter(StandardDict.enabled == True).all()
        data["synonym_norm"] = {r.non_standard: r.standard for r in rows}

        # ontology_words: list (实体名 + 属性名 + 指标名)
        entity_data_rows = db.query(Entity).all()
        attr_rows = []
        for e in entity_data_rows:
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            for p in props:
                if not isinstance(p, dict):
                    continue
                attr_name = (
                    p.get("cnName")
                    or p.get("label")
                    or p.get("display_name")
                    or p.get("name_zh")
                    or p.get("attribute_name")
                    or p.get("name")
                )
                if not attr_name:
                    continue
                attr_rows.append({"attr_name": str(attr_name), "entity_name": e.entity_name})
        metric_rows = db.query(OntologyMetric).filter(OntologyMetric.enabled == True).all()
        data["ontology_words"] = (
            [e.entity_name for e in entity_data_rows if e.entity_name]
            + [r["attr_name"] for r in attr_rows]
            + [r.metric_name for r in metric_rows]
        )

        # entity_table: set
        data["entity_table"] = {e.entity_name for e in entity_data_rows if e.entity_name}

        # attr_table: dict {attr_name: entity_name}
        data["attr_table"] = {r["attr_name"]: r["entity_name"] for r in attr_rows}

        # metric_table: dict {metric_name: entity_name}
        data["metric_table"] = {r.metric_name: r.entity_name for r in metric_rows}

        # cypher_templates: dict {template_name: template_text}
        rows = db.query(CypherTemplate).filter(CypherTemplate.enabled == True).all()
        data["cypher_templates"] = {r.template_name: r.template_text for r in rows}

        # graph_schema: set (所有字段名)
        rows = db.query(GraphSchema).filter(GraphSchema.enabled == True).all()
        data["graph_schema"] = {r.field_name for r in rows}

        # risk_keywords 和 data_keywords
        data["risk_keywords"] = {"删除", "销户", "停电", "DROP", "DELETE"}
        data["data_keywords"] = {"统计", "查询", "多少", "查", "算", "几个"}

        logger.debug(f"NL2Cypher语义数据加载完成: stop_words={len(data['stop_words'])}, time_norm={len(data['time_norm'])}, time_cypher_map={len(data['time_cypher_map'])}, entities={len(data['entity_table'])}, attrs={len(data['attr_table'])}, metrics={len(data['metric_table'])}, templates={len(data['cypher_templates'])}, schema={len(data['graph_schema'])}")

    except Exception as e:
        logger.warning(f"加载NL2Cypher语义数据失败: {e}")
        data = {
            "stop_words": set(),
            "time_norm": {},
            "time_cypher_map": {},
            "intent_norm": {},
            "explode_norm": {},
            "synonym_norm": {},
            "ontology_words": [],
            "entity_table": set(),
            "attr_table": {},
            "metric_table": {},
            "cypher_templates": {},
            "graph_schema": set(),
            "risk_keywords": {"删除", "销户", "停电"},
            "data_keywords": {"统计", "查询", "多少"},
        }

    return data
