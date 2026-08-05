from sqlalchemy.orm import Session
from app.models.base import (
    SemanticTimeNorm, SemanticTimeCypherMap,
    SemanticIntentNorm, SemanticExplodeNorm,
    StandardDict, OntologyMetric,
    CypherTemplate, GraphSchema, Entity
)
import uuid


# ---- time_norm ----

def list_time_norms(db: Session):
    return db.query(SemanticTimeNorm).filter(SemanticTimeNorm.enabled == True).all()


def create_time_norm(db: Session, word: str, time_code: str):
    check = db.query(SemanticTimeNorm).filter(SemanticTimeNorm.word == word).first()
    if check:
        return check, True
    item = SemanticTimeNorm(word=word, time_code=time_code, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_time_norm(db: Session, item_id: str, word: str = None, time_code: str = None):
    item = db.query(SemanticTimeNorm).filter(SemanticTimeNorm.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if word is not None:
        item.word = word
    if time_code is not None:
        item.time_code = time_code
    db.commit()
    db.refresh(item)
    return item


def delete_time_norm(db: Session, item_id: str):
    item = db.query(SemanticTimeNorm).filter(SemanticTimeNorm.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- time_cypher_map ----

def list_time_cypher_maps(db: Session):
    return db.query(SemanticTimeCypherMap).filter(SemanticTimeCypherMap.enabled == True).all()


def create_time_cypher_map(db: Session, time_code: str, cypher_expr: str):
    check = db.query(SemanticTimeCypherMap).filter(SemanticTimeCypherMap.time_code == time_code).first()
    if check:
        check.cypher_expr = cypher_expr
        db.commit()
        db.refresh(check)
        return check, True
    item = SemanticTimeCypherMap(time_code=time_code, cypher_expr=cypher_expr, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_time_cypher_map(db: Session, item_id: str, time_code: str = None, cypher_expr: str = None):
    item = db.query(SemanticTimeCypherMap).filter(SemanticTimeCypherMap.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if time_code is not None:
        item.time_code = time_code
    if cypher_expr is not None:
        item.cypher_expr = cypher_expr
    db.commit()
    db.refresh(item)
    return item


def delete_time_cypher_map(db: Session, item_id: str):
    item = db.query(SemanticTimeCypherMap).filter(SemanticTimeCypherMap.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- intent_norm ----

def list_intent_norms(db: Session):
    return db.query(SemanticIntentNorm).filter(SemanticIntentNorm.enabled == True).all()


def create_intent_norm(db: Session, word: str, standard: str):
    check = db.query(SemanticIntentNorm).filter(SemanticIntentNorm.word == word).first()
    if check:
        return check, True
    item = SemanticIntentNorm(word=word, standard=standard, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_intent_norm(db: Session, item_id: str, word: str = None, standard: str = None):
    item = db.query(SemanticIntentNorm).filter(SemanticIntentNorm.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if word is not None:
        item.word = word
    if standard is not None:
        item.standard = standard
    db.commit()
    db.refresh(item)
    return item


def delete_intent_norm(db: Session, item_id: str):
    item = db.query(SemanticIntentNorm).filter(SemanticIntentNorm.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- explode_norm ----

def list_explode_norms(db: Session):
    return db.query(SemanticExplodeNorm).filter(SemanticExplodeNorm.enabled == True).all()


def create_explode_norm(db: Session, phrase: str, agg_hint: str, time_field: str):
    check = db.query(SemanticExplodeNorm).filter(SemanticExplodeNorm.phrase == phrase).first()
    if check:
        return check, True
    item = SemanticExplodeNorm(phrase=phrase, agg_hint=agg_hint, time_field=time_field, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_explode_norm(db: Session, item_id: str, phrase: str = None, agg_hint: str = None, time_field: str = None):
    item = db.query(SemanticExplodeNorm).filter(SemanticExplodeNorm.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if phrase is not None:
        item.phrase = phrase
    if agg_hint is not None:
        item.agg_hint = agg_hint
    if time_field is not None:
        item.time_field = time_field
    db.commit()
    db.refresh(item)
    return item


def delete_explode_norm(db: Session, item_id: str):
    item = db.query(SemanticExplodeNorm).filter(SemanticExplodeNorm.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- synonym (standard dict) ----

def list_synonyms(db: Session):
    return db.query(StandardDict).filter(StandardDict.enabled == True).all()


def create_synonym(db: Session, non_standard: str, standard: str, category: str = None):
    item = StandardDict(non_standard=non_standard, standard=standard, category=category, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_synonym(db: Session, item_id: str, non_standard: str = None, standard: str = None, category: str = None):
    item = db.query(StandardDict).filter(StandardDict.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if non_standard is not None:
        item.non_standard = non_standard
    if standard is not None:
        item.standard = standard
    if category is not None:
        item.category = category
    db.commit()
    db.refresh(item)
    return item


def delete_synonym(db: Session, item_id: str):
    item = db.query(StandardDict).filter(StandardDict.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- ontology entities ----

def list_ontology_entities(db: Session):
    rows = db.query(Entity).all()

    class _EntityView:
        def __init__(self, e: Entity):
            self.id = str(e.id)
            self.entity_name = e.entity_name
            self.entity_code = e.entity_code
            self.description = e.description
            self.enabled = True

    return [_EntityView(e) for e in rows]


def create_ontology_entity(db: Session, entity_name: str, entity_code: str = None, description: str = None):
    check = db.query(Entity).filter(Entity.entity_name == entity_name).first()
    if check:
        return check, True
    raise ValueError("请在图谱实体管理中创建实体（需要 concept_id），语义管理不再维护独立实体表")


def update_ontology_entity(db: Session, item_id: str, entity_name: str = None, entity_code: str = None, description: str = None):
    item = db.query(Entity).filter(Entity.id == item_id).first()
    if not item:
        return None
    if entity_name is not None:
        item.entity_name = entity_name
    if entity_code is not None:
        item.entity_code = entity_code
    if description is not None:
        item.description = description
    db.commit()
    db.refresh(item)
    return item


def delete_ontology_entity(db: Session, item_id: str):
    item = db.query(Entity).filter(Entity.id == item_id).first()
    if not item:
        return False
    raise ValueError("请在图谱实体管理中删除实体，语义管理不再维护独立实体表")


# ---- ontology attributes ----

def list_ontology_attributes(db: Session):
    out = []
    for e in db.query(Entity).all():
        props = e.properties_schema if isinstance(e.properties_schema, list) else []
        for idx, p in enumerate(props):
            if not isinstance(p, dict):
                continue
            attr_name = p.get("cnName") or p.get("label") or p.get("display_name") or p.get("name_zh") or p.get("attribute_name") or p.get("name")
            if not attr_name:
                continue
            attr_code = p.get("name") or p.get("field_name") or p.get("attribute_en_name") or p.get("attr_code")
            out.append(
                {
                    "id": f"{e.id}::{idx}",
                    "attr_name": str(attr_name),
                    "entity_name": e.entity_name,
                    "attr_code": str(attr_code) if attr_code else None,
                    "enabled": True,
                }
            )
    return out


def create_ontology_attribute(db: Session, attr_name: str, entity_name: str, attr_code: str = None):
    ent = db.query(Entity).filter(Entity.entity_name == entity_name).first()
    if not ent:
        raise ValueError(f"实体不存在: {entity_name}")
    props = ent.properties_schema if isinstance(ent.properties_schema, list) else []
    for p in props:
        if not isinstance(p, dict):
            continue
        cn = str(p.get("cnName") or p.get("label") or p.get("name") or "").strip()
        if cn == attr_name:
            return {
                "id": str(ent.id),
                "attr_name": attr_name,
                "entity_name": entity_name,
                "attr_code": p.get("name") or p.get("field_name") or attr_code,
                "enabled": True,
            }

    props.append({"cnName": attr_name, "name": attr_code or attr_name})
    ent.properties_schema = props
    db.commit()
    return {
        "id": str(ent.id),
        "attr_name": attr_name,
        "entity_name": entity_name,
        "attr_code": attr_code or attr_name,
        "enabled": True,
    }


def update_ontology_attribute(db: Session, item_id: str, attr_name: str = None, entity_name: str = None, attr_code: str = None):
    # item_id 格式兼容: "<entity_id>::<index>"，否则按实体ID处理并更新第一条匹配属性
    entity_id, sep, idx_text = str(item_id).partition("::")
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        return None
    props = ent.properties_schema if isinstance(ent.properties_schema, list) else []
    target_idx = int(idx_text) if sep and idx_text.isdigit() else None
    if target_idx is None or target_idx < 0 or target_idx >= len(props):
        return None
    p = props[target_idx] if isinstance(props[target_idx], dict) else {}
    if attr_name is not None:
        p["cnName"] = attr_name
    if attr_code is not None:
        p["name"] = attr_code
    if entity_name is not None and entity_name != ent.entity_name:
        target_ent = db.query(Entity).filter(Entity.entity_name == entity_name).first()
        if not target_ent:
            return None
        target_props = target_ent.properties_schema if isinstance(target_ent.properties_schema, list) else []
        target_props.append(p)
        target_ent.properties_schema = target_props
        props.pop(target_idx)
        ent.properties_schema = props
    else:
        props[target_idx] = p
        ent.properties_schema = props
    db.commit()
    return {
        "id": item_id,
        "attr_name": p.get("cnName") or p.get("name"),
        "entity_name": entity_name or ent.entity_name,
        "attr_code": p.get("name"),
        "enabled": True,
    }


def delete_ontology_attribute(db: Session, item_id: str):
    entity_id, sep, idx_text = str(item_id).partition("::")
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        return False
    props = ent.properties_schema if isinstance(ent.properties_schema, list) else []
    if not (sep and idx_text.isdigit()):
        return False
    idx = int(idx_text)
    if idx < 0 or idx >= len(props):
        return False
    props.pop(idx)
    ent.properties_schema = props
    db.commit()
    return True


# ---- ontology metrics ----

def list_ontology_metrics(db: Session):
    return db.query(OntologyMetric).filter(OntologyMetric.enabled == True).all()


def create_ontology_metric(db: Session, metric_name: str, entity_name: str, metric_code: str = None):
    item = OntologyMetric(metric_name=metric_name, entity_name=entity_name, metric_code=metric_code, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_ontology_metric(db: Session, item_id: str, metric_name: str = None, entity_name: str = None, metric_code: str = None):
    item = db.query(OntologyMetric).filter(OntologyMetric.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if metric_name is not None:
        item.metric_name = metric_name
    if entity_name is not None:
        item.entity_name = entity_name
    if metric_code is not None:
        item.metric_code = metric_code
    db.commit()
    db.refresh(item)
    return item


def delete_ontology_metric(db: Session, item_id: str):
    item = db.query(OntologyMetric).filter(OntologyMetric.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- cypher templates ----

def list_cypher_templates(db: Session):
    return db.query(CypherTemplate).filter(CypherTemplate.enabled == True).all()


def create_cypher_template(db: Session, template_name: str, template_text: str, description: str = None):
    check = db.query(CypherTemplate).filter(CypherTemplate.template_name == template_name).first()
    if check:
        return check, True
    item = CypherTemplate(template_name=template_name, template_text=template_text, description=description, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_cypher_template(db: Session, item_id: str, template_name: str = None, template_text: str = None, description: str = None):
    item = db.query(CypherTemplate).filter(CypherTemplate.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if template_name is not None:
        item.template_name = template_name
    if template_text is not None:
        item.template_text = template_text
    if description is not None:
        item.description = description
    db.commit()
    db.refresh(item)
    return item


def delete_cypher_template(db: Session, item_id: str):
    item = db.query(CypherTemplate).filter(CypherTemplate.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- graph schema ----

def list_graph_schema(db: Session):
    return db.query(GraphSchema).filter(GraphSchema.enabled == True).all()


def create_graph_schema(db: Session, field_name: str, field_type: str = "node", description: str = None):
    check = db.query(GraphSchema).filter(GraphSchema.field_name == field_name).first()
    if check:
        return check, True
    item = GraphSchema(field_name=field_name, field_type=field_type, description=description, enabled=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item, False


def update_graph_schema(db: Session, item_id: str, field_name: str = None, field_type: str = None, description: str = None):
    item = db.query(GraphSchema).filter(GraphSchema.id == uuid.UUID(item_id)).first()
    if not item:
        return None
    if field_name is not None:
        item.field_name = field_name
    if field_type is not None:
        item.field_type = field_type
    if description is not None:
        item.description = description
    db.commit()
    db.refresh(item)
    return item


def delete_graph_schema(db: Session, item_id: str):
    item = db.query(GraphSchema).filter(GraphSchema.id == uuid.UUID(item_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
