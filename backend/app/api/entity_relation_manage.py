from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from ..core.database import get_db
from ..models.base import Concept, Entity, EntityRelation
import io
import pandas as pd
import re
import uuid

router = APIRouter()

RELATION_GROUP_LABELS = {
    "master_master": "主数据-主数据",
    "master_activity": "主数据-业务活动",
    "activity_activity": "业务活动-业务活动",
}

RELATION_GROUP_LABEL_TO_KEY = {v: k for k, v in RELATION_GROUP_LABELS.items()}

EXPORT_COLUMNS = [
    "关系分组",
    "关系名称",
    "源L1",
    "源L2",
    "源L3",
    "源L4",
    "源实体中文",
    "源实体英文",
    "源实体编码",
    "目标L1",
    "目标L2",
    "目标L3",
    "目标L4",
    "目标实体中文",
    "目标实体英文",
    "目标实体编码",
    "基数",
    "源字段",
    "目标字段",
    "关联说明",
    "备注",
]


class RelationManagerUpsert(BaseModel):
    relation_group: str
    source_entity_id: str
    target_entity_id: str
    relation_name: Optional[str] = None
    relation_category: Optional[str] = "手工维护"
    direction: Optional[str] = "forward"
    cardinality: Optional[str] = "N:N"
    source_field_name: Optional[str] = None
    target_field_name: Optional[str] = None
    join_expr: Optional[str] = None
    remark: Optional[str] = None


def _norm_uuid_str(v: Optional[str], field_name: str = "id") -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if len(s) == 32 and re.fullmatch(r"[0-9a-fA-F]{32}", s):
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    try:
        uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format")
    return s


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _build_join_expr(source_field_name: Optional[str], target_field_name: Optional[str], join_expr: Optional[str]) -> Optional[str]:
    explicit = _clean_text(join_expr)
    if explicit:
        return explicit
    source_field = _clean_text(source_field_name)
    target_field = _clean_text(target_field_name)
    if source_field and target_field:
        return f"{source_field} = {target_field}"
    return None


def _entity_level(entity: Entity, concept_map: Dict[str, Concept]) -> Optional[int]:
    concept = concept_map.get(str(entity.concept_id))
    return concept.level if concept else None


def _lineage_for_entity(entity: Optional[Entity], concept_map: Dict[str, Concept]) -> Dict[str, Optional[str]]:
    result = {
        "l1_name": None,
        "l2_name": None,
        "l3_name": None,
        "l4_name": None,
        "entity_name": entity.entity_name if entity else None,
        "entity_en_name": entity.entity_en_name if entity else None,
        "entity_code": entity.entity_code if entity else None,
    }
    if not entity:
        return result
    concept = concept_map.get(str(entity.concept_id))
    if not concept:
        return result
    if concept.level == 2:
        result["l2_name"] = concept.name
        parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
        result["l1_name"] = parent.name if parent and parent.level == 1 else None
    elif concept.level == 4:
        result["l4_name"] = concept.name
        l3 = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
        result["l3_name"] = l3.name if l3 and l3.level == 3 else None
    return result


def _normalize_relation_side(
    relation: EntityRelation,
    entities_by_id: Dict[str, Entity],
    concept_map: Dict[str, Concept],
) -> Optional[Dict[str, Any]]:
    source_entity = entities_by_id.get(str(relation.source_entity_id))
    target_entity = entities_by_id.get(str(relation.target_entity_id))
    if not source_entity or not target_entity:
        return None

    source_level = _entity_level(source_entity, concept_map)
    target_level = _entity_level(target_entity, concept_map)
    relation_group = None
    display_source = source_entity
    display_target = target_entity

    if source_level == 2 and target_level == 2:
        relation_group = "master_master"
    elif source_level == 4 and target_level == 4:
        relation_group = "activity_activity"
    elif {source_level, target_level} == {2, 4}:
        relation_group = "master_activity"
        display_source = source_entity if source_level == 2 else target_entity
        display_target = target_entity if target_level == 4 else source_entity
    else:
        return None

    source_meta = _lineage_for_entity(display_source, concept_map)
    target_meta = _lineage_for_entity(display_target, concept_map)
    join_expr = _build_join_expr(relation.source_field_name, relation.target_field_name, relation.join_expr)

    return {
        "id": str(relation.id),
        "relation_group": relation_group,
        "relation_group_label": RELATION_GROUP_LABELS[relation_group],
        "relation_name": relation.relation_name,
        "relation_category": relation.relation_category or "手工维护",
        "direction": relation.direction or "forward",
        "source_entity_id": str(display_source.id),
        "source_entity_name": source_meta["entity_name"],
        "source_entity_en_name": source_meta["entity_en_name"],
        "source_entity_code": source_meta["entity_code"],
        "source_l1_name": source_meta["l1_name"],
        "source_l2_name": source_meta["l2_name"],
        "source_l3_name": source_meta["l3_name"],
        "source_l4_name": source_meta["l4_name"],
        "target_entity_id": str(display_target.id),
        "target_entity_name": target_meta["entity_name"],
        "target_entity_en_name": target_meta["entity_en_name"],
        "target_entity_code": target_meta["entity_code"],
        "target_l1_name": target_meta["l1_name"],
        "target_l2_name": target_meta["l2_name"],
        "target_l3_name": target_meta["l3_name"],
        "target_l4_name": target_meta["l4_name"],
        "cardinality": relation.cardinality or "N:N",
        "source_field_name": relation.source_field_name,
        "target_field_name": relation.target_field_name,
        "join_expr": join_expr,
        "remark": relation.remark or relation.description,
        "created_at": relation.created_at,
    }


def _list_relation_rows(
    db: Session,
    relation_group: Optional[str] = None,
    relation_category: Optional[str] = None,
    keyword: Optional[str] = None,
    entity_id: Optional[str] = None,
    source_entity_id: Optional[str] = None,
    target_entity_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    concepts = db.query(Concept).all()
    concept_map = {str(item.id): item for item in concepts}
    entities = db.query(Entity).all()
    entities_by_id = {str(item.id): item for item in entities}
    rows: List[Dict[str, Any]] = []
    kw = (keyword or "").strip().lower()

    entity_id = _norm_uuid_str(entity_id, "entity_id") if entity_id else None
    source_entity_id = _norm_uuid_str(source_entity_id, "source_entity_id") if source_entity_id else None
    target_entity_id = _norm_uuid_str(target_entity_id, "target_entity_id") if target_entity_id else None

    for relation in db.query(EntityRelation).all():
        row = _normalize_relation_side(relation, entities_by_id, concept_map)
        if not row:
            continue
        if relation_group and row["relation_group"] != relation_group:
            continue
        if relation_category and (row.get("relation_category") or "手工维护") != relation_category:
            continue
        if entity_id and entity_id not in {str(row["source_entity_id"]), str(row["target_entity_id"])}:
            continue
        if source_entity_id and str(row["source_entity_id"]) != str(source_entity_id):
            continue
        if target_entity_id and str(row["target_entity_id"]) != str(target_entity_id):
            continue
        if kw:
            haystack = " ".join([
                row.get("relation_name") or "",
                row.get("source_entity_name") or "",
                row.get("source_entity_en_name") or "",
                row.get("source_entity_code") or "",
                row.get("target_entity_name") or "",
                row.get("target_entity_en_name") or "",
                row.get("target_entity_code") or "",
                row.get("source_field_name") or "",
                row.get("target_field_name") or "",
                row.get("join_expr") or "",
                row.get("remark") or "",
            ]).lower()
            if kw not in haystack:
                continue
        rows.append(row)

    rows.sort(key=lambda item: (
        item.get("relation_group_label") or "",
        item.get("source_l1_name") or "",
        item.get("source_l2_name") or "",
        item.get("source_l3_name") or "",
        item.get("source_l4_name") or "",
        item.get("source_entity_name") or "",
        item.get("target_entity_name") or "",
        item.get("relation_name") or "",
    ))
    return rows


def _validate_group_entities(
    relation_group: str,
    source_entity: Optional[Entity],
    target_entity: Optional[Entity],
    concept_map: Dict[str, Concept],
):
    if relation_group not in RELATION_GROUP_LABELS:
        raise HTTPException(status_code=400, detail="Unsupported relation_group")
    if not source_entity or not target_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    if str(source_entity.id) == str(target_entity.id):
        raise HTTPException(status_code=400, detail="Source and target entity cannot be the same")

    source_level = _entity_level(source_entity, concept_map)
    target_level = _entity_level(target_entity, concept_map)
    valid = (
        (relation_group == "master_master" and source_level == 2 and target_level == 2)
        or (relation_group == "master_activity" and source_level == 2 and target_level == 4)
        or (relation_group == "activity_activity" and source_level == 4 and target_level == 4)
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Entity levels do not match relation_group")


# 关联条件字段提取：匹配 t0.X = t1.Y 或整串 X = Y
_JOIN_FIELD_RE = re.compile(r't0\.(\w+)\s*=\s*t1\.(\w+)|^(\w+)\s*=\s*(\w+)\s*$')


def _entity_field_names(entity: Entity) -> set:
    """实体 properties_schema 中的全部字段名（英文 name + 中文 cnName）。"""
    names = set()
    for p in (entity.properties_schema or []):
        if isinstance(p, dict):
            for k in ("name", "cnName"):
                v = (p.get(k) or "").strip()
                if v:
                    names.add(v)
    return names


def _validate_relation_fields(
    source_entity: Entity,
    target_entity: Entity,
    source_field_name: Optional[str],
    target_field_name: Optional[str],
    join_expr: Optional[str],
):
    """校验关系字段是否真正存在于实体 properties_schema 中。
    空字段跳过；join_expr 形如 t0.X=t1.Y 或 X=Y 时也校验 X/Y。
    不存在则抛 400，导入时由外层捕获记入 skipped_rows，新增/更新时直接拒绝。
    """
    src_fields = _entity_field_names(source_entity)
    tgt_fields = _entity_field_names(target_entity)
    sf = _clean_text(source_field_name)
    tf = _clean_text(target_field_name)
    if sf and sf not in src_fields:
        raise HTTPException(
            status_code=400,
            detail=f"源字段 '{sf}' 不在实体 {source_entity.entity_code} 的属性中",
        )
    if tf and tf not in tgt_fields:
        raise HTTPException(
            status_code=400,
            detail=f"目标字段 '{tf}' 不在实体 {target_entity.entity_code} 的属性中",
        )
    je = _clean_text(join_expr) or ""
    m = _JOIN_FIELD_RE.search(je)
    if m:
        sx = m.group(1) or m.group(3)
        ty = m.group(2) or m.group(4)
        if sx and sx not in src_fields:
            raise HTTPException(
                status_code=400,
                detail=f"关联条件源字段 '{sx}' 不在实体 {source_entity.entity_code} 的属性中",
            )
        if ty and ty not in tgt_fields:
            raise HTTPException(
                status_code=400,
                detail=f"关联条件目标字段 '{ty}' 不在实体 {target_entity.entity_code} 的属性中",
            )


def _relation_payload(payload: RelationManagerUpsert, source_entity: Entity, target_entity: Entity) -> Dict[str, Any]:
    relation_name = _clean_text(payload.relation_name) or f"{source_entity.entity_name}关联{target_entity.entity_name}"
    source_field_name = _clean_text(payload.source_field_name)
    target_field_name = _clean_text(payload.target_field_name)
    remark = _clean_text(payload.remark)
    join_expr = _build_join_expr(source_field_name, target_field_name, payload.join_expr)
    return {
        "source_entity_id": str(source_entity.id),
        "target_entity_id": str(target_entity.id),
        "relation_name": relation_name,
        "relation_category": _clean_text(payload.relation_category) or "手工维护",
        "direction": _clean_text(payload.direction) or "forward",
        "cardinality": _clean_text(payload.cardinality) or "N:N",
        "source_field_name": source_field_name,
        "target_field_name": target_field_name,
        "join_expr": join_expr,
        "description": remark,
        "remark": remark,
    }


def _resolve_entity_from_row(row: pd.Series, entities: List[Entity]) -> Optional[Entity]:
    source_code = _clean_text(row.get("实体编码"))
    entity_code = _clean_text(row.get("源实体编码")) or _clean_text(row.get("目标实体编码")) or source_code
    entity_en_name = _clean_text(row.get("源实体英文")) or _clean_text(row.get("目标实体英文"))
    entity_name = _clean_text(row.get("源实体中文")) or _clean_text(row.get("目标实体中文"))
    if entity_code:
        hit = next((item for item in entities if str(item.entity_code) == entity_code), None)
        if hit:
            return hit
    if entity_en_name:
        hit = next((item for item in entities if str(item.entity_en_name or "") == entity_en_name), None)
        if hit:
            return hit
    if entity_name:
        hits = [item for item in entities if str(item.entity_name) == entity_name]
        if len(hits) == 1:
            return hits[0]
    return None


def _resolve_entity_for_side(row: pd.Series, side: str, entities: List[Entity]) -> Optional[Entity]:
    if side not in {"source", "target"}:
        return None
    prefix = "源" if side == "source" else "目标"
    entity_code = _clean_text(row.get(f"{prefix}实体编码"))
    entity_en_name = _clean_text(row.get(f"{prefix}实体英文"))
    entity_name = _clean_text(row.get(f"{prefix}实体中文"))
    if entity_code:
        hit = next((item for item in entities if str(item.entity_code) == entity_code), None)
        if hit:
            return hit
    if entity_en_name:
        hit = next((item for item in entities if str(item.entity_en_name or "") == entity_en_name), None)
        if hit:
            return hit
    if entity_name:
        hits = [item for item in entities if str(item.entity_name) == entity_name]
        if len(hits) == 1:
            return hits[0]
    return None


@router.get("/entity-relation-manager/items")
def list_entity_relation_items(
    relation_group: Optional[str] = None,
    relation_category: Optional[str] = None,
    keyword: Optional[str] = None,
    entity_id: Optional[str] = None,
    source_entity_id: Optional[str] = None,
    target_entity_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = _list_relation_rows(
        db,
        relation_group=relation_group,
        relation_category=relation_category,
        keyword=keyword,
        entity_id=entity_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
    )
    return {"code": 200, "message": "success", "data": {"items": rows, "total": len(rows)}}


@router.post("/entity-relation-manager/items")
def create_entity_relation_item(payload: RelationManagerUpsert, db: Session = Depends(get_db)):
    concepts = db.query(Concept).all()
    concept_map = {str(item.id): item for item in concepts}
    source_entity_id = _norm_uuid_str(payload.source_entity_id, "source_entity_id")
    target_entity_id = _norm_uuid_str(payload.target_entity_id, "target_entity_id")
    source_entity = db.query(Entity).filter(Entity.id == source_entity_id).first()
    target_entity = db.query(Entity).filter(Entity.id == target_entity_id).first()
    _validate_group_entities(payload.relation_group, source_entity, target_entity, concept_map)
    _validate_relation_fields(source_entity, target_entity, payload.source_field_name, payload.target_field_name, payload.join_expr)

    # master_activity 关系统一为"打点维护"（与资产矩阵打点同义）
    if payload.relation_group == "master_activity":
        payload = payload.model_copy(update={"relation_category": "打点维护"})
    relation_name = _clean_text(payload.relation_name) or f"{source_entity.entity_name}关联{target_entity.entity_name}"
    category = _clean_text(payload.relation_category) or "手工维护"

    # 唯一性：master_activity 按实体对+类别去重（一对实体一条打点关系）；其它按 +关系名
    if payload.relation_group == "master_activity":
        exists = db.query(EntityRelation).filter(
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_category == category,
        ).first()
    else:
        exists = db.query(EntityRelation).filter(
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_name == relation_name,
            EntityRelation.relation_category == category,
        ).first()
    if exists:
        detail = "该主数据-业务活动关系已存在，请直接编辑" if payload.relation_group == "master_activity" else "The same relation already exists"
        raise HTTPException(status_code=400, detail=detail)

    relation = EntityRelation(**_relation_payload(payload, source_entity, target_entity))
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return {"code": 200, "message": "success", "data": {"id": str(relation.id)}}


@router.put("/entity-relation-manager/items/{relation_id}")
def update_entity_relation_item(relation_id: str, payload: RelationManagerUpsert, db: Session = Depends(get_db)):
    relation_id = _norm_uuid_str(relation_id, "relation_id") or relation_id
    db_relation = db.query(EntityRelation).filter(EntityRelation.id == relation_id).first()
    if not db_relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    concepts = db.query(Concept).all()
    concept_map = {str(item.id): item for item in concepts}
    source_entity = db.query(Entity).filter(Entity.id == _norm_uuid_str(payload.source_entity_id, "source_entity_id")).first()
    target_entity = db.query(Entity).filter(Entity.id == _norm_uuid_str(payload.target_entity_id, "target_entity_id")).first()
    _validate_group_entities(payload.relation_group, source_entity, target_entity, concept_map)
    _validate_relation_fields(source_entity, target_entity, payload.source_field_name, payload.target_field_name, payload.join_expr)

    # master_activity 关系统一为"打点维护"（与资产矩阵打点同义）
    if payload.relation_group == "master_activity":
        payload = payload.model_copy(update={"relation_category": "打点维护"})
    relation_name = _clean_text(payload.relation_name) or f"{source_entity.entity_name}关联{target_entity.entity_name}"
    category = _clean_text(payload.relation_category) or "手工维护"

    # 唯一性：master_activity 按实体对+类别去重；其它按 +关系名
    if payload.relation_group == "master_activity":
        exists = db.query(EntityRelation).filter(
            EntityRelation.id != db_relation.id,
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_category == category,
        ).first()
    else:
        exists = db.query(EntityRelation).filter(
            EntityRelation.id != db_relation.id,
            EntityRelation.source_entity_id == source_entity.id,
            EntityRelation.target_entity_id == target_entity.id,
            EntityRelation.relation_name == relation_name,
            EntityRelation.relation_category == category,
        ).first()
    if exists:
        detail = "该主数据-业务活动关系已存在，请直接编辑" if payload.relation_group == "master_activity" else "The same relation already exists"
        raise HTTPException(status_code=400, detail=detail)

    for key, value in _relation_payload(payload, source_entity, target_entity).items():
        setattr(db_relation, key, value)
    db.commit()
    return {"code": 200, "message": "success"}


@router.delete("/entity-relation-manager/items/{relation_id}")
def delete_entity_relation_item(relation_id: str, db: Session = Depends(get_db)):
    relation_id = _norm_uuid_str(relation_id, "relation_id") or relation_id
    db_relation = db.query(EntityRelation).filter(EntityRelation.id == relation_id).first()
    if not db_relation:
        raise HTTPException(status_code=404, detail="Relation not found")
    db.delete(db_relation)
    db.commit()
    return {"code": 200, "message": "success"}


@router.get("/entity-relation-manager/export/excel")
def export_entity_relations_excel(
    relation_group: Optional[str] = None,
    relation_category: Optional[str] = None,
    keyword: Optional[str] = None,
    entity_id: Optional[str] = None,
    source_entity_id: Optional[str] = None,
    target_entity_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    rows = _list_relation_rows(
        db,
        relation_group=relation_group,
        relation_category=relation_category,
        keyword=keyword,
        entity_id=entity_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
    )
    export_rows = [{
        "关系分组": row["relation_group_label"],
        "关系名称": row["relation_name"],
        "源L1": row["source_l1_name"],
        "源L2": row["source_l2_name"],
        "源L3": row["source_l3_name"],
        "源L4": row["source_l4_name"],
        "源实体中文": row["source_entity_name"],
        "源实体英文": row["source_entity_en_name"],
        "源实体编码": row["source_entity_code"],
        "目标L1": row["target_l1_name"],
        "目标L2": row["target_l2_name"],
        "目标L3": row["target_l3_name"],
        "目标L4": row["target_l4_name"],
        "目标实体中文": row["target_entity_name"],
        "目标实体英文": row["target_entity_en_name"],
        "目标实体编码": row["target_entity_code"],
        "基数": row["cardinality"],
        "源字段": row["source_field_name"],
        "目标字段": row["target_field_name"],
        "关联说明": row["join_expr"],
        "备注": row["remark"],
    } for row in rows]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(export_rows, columns=EXPORT_COLUMNS).to_excel(writer, sheet_name="实体关系清单", index=False)
    output.seek(0)

    headers = {"Content-Disposition": 'attachment; filename="entity_relations.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.post("/entity-relation-manager/import/excel")
async def import_entity_relations_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    excel_data = pd.read_excel(io.BytesIO(contents), sheet_name=None)
    if "实体关系清单" not in excel_data:
        raise HTTPException(status_code=400, detail="Excel must contain sheet 实体关系清单")

    df = excel_data["实体关系清单"]
    concepts = db.query(Concept).all()
    concept_map = {str(item.id): item for item in concepts}
    entities = db.query(Entity).all()

    created_count = 0
    updated_count = 0
    skipped_rows: List[str] = []

    for idx, row in df.iterrows():
        try:
            relation_group_label = _clean_text(row.get("关系分组")) or "主数据-业务活动"
            relation_group = RELATION_GROUP_LABEL_TO_KEY.get(relation_group_label, relation_group_label)
            source_entity = _resolve_entity_for_side(row, "source", entities)
            target_entity = _resolve_entity_for_side(row, "target", entities)
            if not source_entity or not target_entity:
                skipped_rows.append(f"第{idx + 2}行: 无法识别源或目标实体")
                continue

            payload = RelationManagerUpsert(
                relation_group=relation_group,
                source_entity_id=str(source_entity.id),
                target_entity_id=str(target_entity.id),
                relation_name=_clean_text(row.get("关系名称")),
                relation_category=_clean_text(row.get("关系类别")) or "手工维护",
                direction="forward",
                cardinality=_clean_text(row.get("基数")) or "N:N",
                source_field_name=_clean_text(row.get("源字段")),
                target_field_name=_clean_text(row.get("目标字段")),
                join_expr=_clean_text(row.get("关联说明")),
                remark=_clean_text(row.get("备注")),
            )

            _validate_group_entities(relation_group, source_entity, target_entity, concept_map)
            _validate_relation_fields(source_entity, target_entity, payload.source_field_name, payload.target_field_name, payload.join_expr)
            # master_activity 关系统一为"打点维护"（与资产矩阵打点同义）
            if relation_group == "master_activity":
                payload = payload.model_copy(update={"relation_category": "打点维护"})
            payload_data = _relation_payload(payload, source_entity, target_entity)
            # 唯一性：master_activity 按实体对+类别去重；其它按 +关系名
            if relation_group == "master_activity":
                exists = db.query(EntityRelation).filter(
                    EntityRelation.source_entity_id == source_entity.id,
                    EntityRelation.target_entity_id == target_entity.id,
                    EntityRelation.relation_category == payload_data["relation_category"],
                ).first()
            else:
                exists = db.query(EntityRelation).filter(
                    EntityRelation.source_entity_id == source_entity.id,
                    EntityRelation.target_entity_id == target_entity.id,
                    EntityRelation.relation_name == payload_data["relation_name"],
                    EntityRelation.relation_category == payload_data["relation_category"],
                ).first()
            if exists:
                for key, value in payload_data.items():
                    setattr(exists, key, value)
                updated_count += 1
            else:
                db.add(EntityRelation(**payload_data))
                created_count += 1
        except HTTPException as exc:
            skipped_rows.append(f"第{idx + 2}行: {exc.detail}")
        except Exception as exc:
            skipped_rows.append(f"第{idx + 2}行: {str(exc)}")

    db.commit()
    return {
        "code": 200,
        "message": "success",
        "data": {
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_rows": skipped_rows[:50],
        },
    }
