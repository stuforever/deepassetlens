"""导出/导入/清空及矩阵端点 -- 从 concept.py 拆分（机械迁移，行为等价）

迁移内容：export/excel、concepts/clear、import/excel 端点，
_clear_graph_data / _relink_entity_dependencies 助手；
另含 graph/matrix 与 entities/glm-5.3_common/matrix/toggle
（因 concept_graph.py 行数平衡自该模块移入）。
由 concept.py 聚合挂载，对外路由路径不变。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, Dict
from ..models.base import (
    Concept, Entity, EntityRelation, EntityConceptLink,
    ConceptRelation, EntityModeling, EntityInitData, EntityMappingRule,
)
import pandas as pd
import io
import uuid

from ..core.database import get_db
from .concept_support import (
    _norm_uuid_str, _build_matrix_relation_name,
    _sort_concepts, _sort_entities,
    _safe_int, _normalize_system_names, _update_entity_concept_links,
)

router = APIRouter()


@router.get("/export/excel")
def export_graph_to_excel(mode: Optional[str] = None, db: Session = Depends(get_db)):
    """导出图谱结构数据；指定模式时仅导出当前模式的分类、实体、属性。"""
    try:
        concept_columns = ["ID", "概念名称", "层级", "父级名称", "业务域索引", "顺序", "描述", "所属系统"]
        entity_columns = ["ID", "所属概念", "顺序", "实体编码", "实体名称", "实体英文名", "解释(别名同义词)", "描述", "是否主表", "数据层级"]
        property_columns = ["实体名称", "实体编码", "属性名(EN)", "属性名(CN)", "类型", "是否主键", "描述"]
        relation_columns = [
            "关系类别", "关系名称",
            "源实体", "源实体编码", "源实体所属分类",
            "目标实体", "目标实体编码", "目标实体所属分类",
            "方向", "基数", "关联条件", "描述"
        ]

        # 1. 概念清单
        query_concepts = db.query(Concept)
        if mode == 'master':
            query_concepts = query_concepts.filter(Concept.level.in_([1, 2]))
        elif mode == 'activity':
            query_concepts = query_concepts.filter(Concept.level.in_([0, 3, 4]))
        
        concepts = _sort_concepts(query_concepts.all())
        concept_map = {str(c.id): c for c in concepts}
        # 建立全量 map 用于找父级名称（即使父级不在导出范围内，也能显示名称）
        full_concept_map = {str(c.id): c for c in db.query(Concept).all()}
        
        concepts_df = pd.DataFrame([{
            "ID": str(c.id),
            "概念名称": c.name,
            "层级": c.level,
            "父级名称": full_concept_map.get(str(c.parent_id)).name if c.parent_id and full_concept_map.get(str(c.parent_id)) else "",
            "业务域索引": c.area_index,
            "顺序": c.sort_order or 0,
            "描述": c.description,
            "所属系统": "、".join(c.system_names or []) if c.level == 3 else "",
        } for c in concepts], columns=concept_columns)

        # 2. 实体清单
        concept_ids = [c.id for c in concepts]
        query_entities = db.query(Entity)
        if mode:
            query_entities = query_entities.filter(Entity.concept_id.in_(concept_ids))
        
        entities = _sort_entities(query_entities.all())
        entity_map = {str(e.id): e for e in entities}
        entities_df = pd.DataFrame([{
            "ID": str(e.id),
            "所属概念": concept_map.get(str(e.concept_id)).name if concept_map.get(str(e.concept_id)) else "",
            "顺序": e.sort_order or 0,
            "实体编码": e.entity_code,
            "实体名称": e.entity_name,
            "实体英文名": e.entity_en_name,
            "解释(别名同义词)": e.entity_explanation,
            "描述": e.description,
            "是否主表": "是" if e.is_main_table else "否",
            "数据层级": e.data_layer
        } for e in entities], columns=entity_columns)

        # 3. 实体属性
        props_data = []
        for e in entities:
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            for p in props:
                props_data.append({
                    "实体名称": e.entity_name,
                    "实体编码": e.entity_code,
                    "属性名(EN)": p.get("name"),
                    "属性名(CN)": p.get("cnName"),
                    "类型": p.get("type"),
                    "是否主键": "是" if p.get("isPrimaryKey") else "否",
                    "描述": p.get("description")
                })
        props_df = pd.DataFrame(props_data, columns=property_columns)

        # 写入 Excel 缓冲区
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            concepts_df.to_excel(writer, sheet_name='概念清单', index=False)
            entities_df.to_excel(writer, sheet_name='实体清单', index=False)
            props_df.to_excel(writer, sheet_name='实体属性', index=False)
            if not mode:
                relation_rows = []
                full_entity_map = {str(e.id): e for e in db.query(Entity).all()}
                relations = db.query(EntityRelation).all()
                for r in relations:
                    source_entity = full_entity_map.get(str(r.source_entity_id))
                    target_entity = full_entity_map.get(str(r.target_entity_id))
                    source_concept = full_concept_map.get(str(source_entity.concept_id)) if source_entity else None
                    target_concept = full_concept_map.get(str(target_entity.concept_id)) if target_entity else None
                    relation_rows.append({
                        "关系类别": r.relation_category or "手工维护",
                        "关系名称": r.relation_name,
                        "源实体": source_entity.entity_name if source_entity else "",
                        "源实体编码": source_entity.entity_code if source_entity else "",
                        "源实体所属分类": source_concept.name if source_concept else "",
                        "目标实体": target_entity.entity_name if target_entity else "",
                        "目标实体编码": target_entity.entity_code if target_entity else "",
                        "目标实体所属分类": target_concept.name if target_concept else "",
                        "方向": r.direction,
                        "基数": r.cardinality,
                        "关联条件": r.join_expr,
                        "描述": r.description
                    })
                relations_df = pd.DataFrame(relation_rows, columns=relation_columns)
                relations_df.to_excel(writer, sheet_name='实体关系', index=False)
        
        output.seek(0)
        
        filename = "graph_metadata.xlsx"
        if mode == 'master': filename = "master_data_metadata.xlsx"
        elif mode == 'activity': filename = "business_activity_metadata.xlsx"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


def _clear_graph_data(db: Session, mode: Optional[str] = None, auto_commit: bool = True) -> Dict[str, int]:
    """C3（三轨M1）：auto_commit=False 时清空不提交——供 clear+import 同事务原子化。"""
    """清空图谱结构数据。指定 mode 时仅清空当前模式（master=L1/L2, activity=L0/L3/L4），否则清全部。
    MySQL InnoDB 外键为 RESTRICT，必须子先父后删除；概念自引用按层级深度优先（深层先删）。
    返回已删除的 concept/entity 计数。
    """
    if mode == 'master':
        levels = [1, 2]
    elif mode == 'activity':
        levels = [0, 3, 4]
    else:
        levels = None  # 全部

    # 范围内的概念 id
    if levels is not None:
        scope_concept_ids = [r[0] for r in db.query(Concept.id).filter(Concept.level.in_(levels)).all()]
    else:
        scope_concept_ids = None

    # 范围内的实体 id（实体所属概念在范围内）
    if scope_concept_ids is not None:
        scope_entity_ids = (
            [r[0] for r in db.query(Entity.id).filter(Entity.concept_id.in_(scope_concept_ids)).all()]
            if scope_concept_ids else []
        )
    else:
        scope_entity_ids = None

    # 1) 删实体相关子表（关系/概念关联）-> 再删实体
    if scope_entity_ids is not None:
        if scope_entity_ids:
            db.query(EntityRelation).filter(
                or_(EntityRelation.source_entity_id.in_(scope_entity_ids),
                    EntityRelation.target_entity_id.in_(scope_entity_ids))
            ).delete(synchronize_session=False)
            db.query(EntityConceptLink).filter(EntityConceptLink.entity_id.in_(scope_entity_ids)).delete(synchronize_session=False)
            db.query(Entity).filter(Entity.id.in_(scope_entity_ids)).delete(synchronize_session=False)
    else:
        db.query(EntityRelation).delete(synchronize_session=False)
        db.query(EntityConceptLink).delete(synchronize_session=False)
        db.query(Entity).delete(synchronize_session=False)

    # 2) 删概念：先清残留指向这些概念的链接/概念关系，再按层级深度优先删概念（满足自引用父外键）
    deleted_concepts = 0
    if scope_concept_ids is not None:
        if scope_concept_ids:
            db.query(EntityConceptLink).filter(EntityConceptLink.concept_id.in_(scope_concept_ids)).delete(synchronize_session=False)
            db.query(ConceptRelation).filter(
                or_(ConceptRelation.source_concept_id.in_(scope_concept_ids),
                    ConceptRelation.target_concept_id.in_(scope_concept_ids))
            ).delete(synchronize_session=False)
            # 深层优先：4→3→2→1→0，保证删父节点前子节点已删
            level_order = [lv for lv in [4, 3, 2, 1, 0] if lv in (levels or [0, 1, 2, 3, 4])]
            for lv in level_order:
                deleted_concepts += db.query(Concept).filter(
                    Concept.level == lv, Concept.id.in_(scope_concept_ids)
                ).delete(synchronize_session=False)
    else:
        db.query(EntityConceptLink).delete(synchronize_session=False)
        db.query(ConceptRelation).delete(synchronize_session=False)
        level_order = [4, 3, 2, 1, 0]
        for lv in level_order:
            deleted_concepts += db.query(Concept).filter(Concept.level == lv).delete(synchronize_session=False)

    if auto_commit:
        db.commit()
    deleted_entities = len(scope_entity_ids) if scope_entity_ids is not None else 'all'
    return {"concepts": deleted_concepts, "entities": deleted_entities}


def _relink_entity_dependencies(db: Session) -> Dict[str, int]:
    """实体按 entity_code 重新生成（clear+import 导致 uuid 变更）后，按 entity_code 重链
    EntityModeling / EntityInitData 的 entity_id，以及 EntityMappingRule.entity_ids。
    EntityMappingRule 无 entity_code 列，借 EntityModeling/EntityInitData 的 (旧entity_id, entity_code) 桥接。
    """
    code_to_id = {e.entity_code: str(e.id) for e in db.query(Entity).all()}
    # 旧 uuid -> entity_code 桥（来自仍带着旧 entity_id 的建模/初始化行）
    old_uuid_to_code: Dict[str, str] = {}
    for m in db.query(EntityModeling).all():
        if m.entity_id and m.entity_code:
            old_uuid_to_code.setdefault(str(m.entity_id), m.entity_code)
    for x in db.query(EntityInitData).all():
        if x.entity_id and x.entity_code:
            old_uuid_to_code.setdefault(str(x.entity_id), x.entity_code)

    rel_modeling = rel_initdata = rel_rules = 0
    # 1) EntityModeling：按 entity_code 重链 entity_id
    for m in db.query(EntityModeling).all():
        nid = code_to_id.get(m.entity_code)
        if nid and str(m.entity_id) != nid:
            m.entity_id = nid
            rel_modeling += 1
    # 2) EntityInitData
    for x in db.query(EntityInitData).all():
        nid = code_to_id.get(x.entity_code)
        if nid and str(x.entity_id) != nid:
            x.entity_id = nid
            rel_initdata += 1
    # 3) EntityMappingRule：entity_ids 旧 uuid 数组 -> code -> 新 uuid
    for r in db.query(EntityMappingRule).all():
        new_ids: list = []
        changed = False
        for eid in (r.entity_ids or []):
            seid = str(eid)
            if seid in code_to_id:           # 已是有效 uuid
                new_ids.append(seid)
            else:
                code = old_uuid_to_code.get(seid)
                if code and code in code_to_id:
                    new_ids.append(code_to_id[code]); changed = True
                else:
                    new_ids.append(seid)     # 无法恢复，保留原值
        if changed:
            r.entity_ids = new_ids
            rel_rules += 1
    db.commit()
    return {"modeling": rel_modeling, "initdata": rel_initdata, "rules": rel_rules}


@router.post("/concepts/clear")
def clear_graph_data(mode: Optional[str] = None, db: Session = Depends(get_db)):
    """清空图谱结构数据（按 mode 限定范围）。供“重置模板/清空数据”按钮调用。"""
    try:
        result = _clear_graph_data(db, mode)
        scope = {'master': '主数据', 'activity': '业务活动'}.get(mode, '全部')
        return {"code": 200, "message": f"已清空【{scope}】数据：概念 {result['concepts']}、实体 {result['entities']}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


@router.post("/import/excel")
async def import_graph_from_excel(mode: Optional[str] = None, clear: bool = False, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """导入图谱结构数据；指定模式时仅影响当前模式的分类、实体、属性。
    clear=True 时先清空当前模式数据再导入（清空重导入）。
    """
    contents = await file.read()
    # C3（三轨M1）：文件读取与解析校验先于清空——损坏文件在触碰图谱数据前即被拒
    try:
        excel_data = pd.read_excel(io.BytesIO(contents), sheet_name=None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {type(e).__name__}")
    try:
        if clear:
            _clear_graph_data(db, mode, auto_commit=False)
        # 导入计数（供前端反馈，避免"0 行也显示成功"的静默失败）
        counts = {"concepts": 0, "entities": 0, "entities_skipped": 0, "attributes": 0, "relations": 0}

        parent_level_map = {
            0: None,
            1: None,
            2: 1,
            3: 0,
            4: 3,
        }

        # 1. 导入概念
        if '概念清单' in excel_data:
            df = excel_data['概念清单']
            # 按层级排序，确保父节点先处理
            df = df.sort_values(by='层级')
            for _, row in df.iterrows():
                name = str(row['概念名称']).strip()
                level = int(row['层级'])
                
                # 模式过滤
                if mode == 'master' and level not in [1, 2]: continue
                if mode == 'activity' and level not in [0, 3, 4]: continue
                counts["concepts"] += 1

                parent_name = str(row.get('父级名称', '')).strip()
                
                parent_id = None
                if parent_name and parent_name != 'nan':
                    expected_parent_level = parent_level_map.get(level)
                    if expected_parent_level is not None:
                        parent = db.query(Concept).filter(Concept.name == parent_name, Concept.level == expected_parent_level).first()
                        if parent:
                            parent_id = parent.id
                
                existing = db.query(Concept).filter(Concept.name == name, Concept.level == level).first()
                if existing:
                    existing.parent_id = parent_id
                    existing.area_index = _safe_int(row.get('业务域索引', 1), 1)
                    existing.sort_order = _safe_int(row.get('顺序', 0), 0)
                    existing.description = str(row.get('描述', '')) if row.get('描述') != 'nan' else None
                    existing.system_names = _normalize_system_names(row.get('所属系统')) if level == 3 else None
                else:
                    new_concept = Concept(
                        name=name,
                        level=level,
                        parent_id=parent_id,
                        area_index=_safe_int(row.get('业务域索引', 1), 1),
                        sort_order=_safe_int(row.get('顺序', 0), 0),
                        description=str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                        system_names=_normalize_system_names(row.get('所属系统')) if level == 3 else None,
                    )
                    db.add(new_concept)
                    db.flush()  # autoflush=False：显式刷新，使后续 L2/L4 的父级查找能查到本轮新建的父概念
            db.flush()  # C3：阶段内只 flush，统一提交

        # 2. 导入实体
        if '实体清单' in excel_data:
            df = excel_data['实体清单']
            imported_entity_ids = []
            for _, row in df.iterrows():
                concept_name = str(row['所属概念']).strip()
                code = str(row['实体编码']).strip()
                name = str(row['实体名称']).strip()
                
                # 按 mode 优先查对应层级的概念（避免重名概念查到错误层级）
                # activity 模式查 L0/L3/L4，master 模式查 L1/L2，无 mode 查全部
                if mode == 'activity':
                    concept = db.query(Concept).filter(
                        Concept.name == concept_name, Concept.level.in_([0, 3, 4])
                    ).first()
                elif mode == 'master':
                    concept = db.query(Concept).filter(
                        Concept.name == concept_name, Concept.level.in_([1, 2])
                    ).first()
                else:
                    concept = db.query(Concept).filter(Concept.name == concept_name).first()
                if not concept:
                    counts["entities_skipped"] += 1
                    continue
                counts["entities"] += 1

                existing = db.query(Entity).filter(Entity.entity_code == code).first()
                if existing:
                    existing.concept_id = concept.id
                    existing.entity_name = name
                    existing.entity_en_name = str(row.get('实体英文名', '')) if row.get('实体英文名') != 'nan' else None
                    existing.entity_explanation = str(row.get('解释(别名同义词)', '')) if row.get('解释(别名同义词)') != 'nan' else None
                    existing.sort_order = _safe_int(row.get('顺序', 0), 0)
                    existing.description = str(row.get('描述', '')) if row.get('描述') != 'nan' else None
                    existing.is_main_table = (str(row.get('是否主表', '')) == '是')
                    existing.data_layer = str(row.get('数据层级', '')) if row.get('数据层级') != 'nan' else None
                    imported_entity_ids.append(str(existing.id))
                else:
                    new_entity = Entity(
                        concept_id=concept.id,
                        entity_code=code,
                        entity_name=name,
                        entity_en_name=str(row.get('实体英文名', '')) if row.get('实体英文名') != 'nan' else None,
                        entity_explanation=str(row.get('解释(别名同义词)', '')) if row.get('解释(别名同义词)') != 'nan' else None,
                        sort_order=_safe_int(row.get('顺序', 0), 0),
                        description=str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                        is_main_table=(str(row.get('是否主表', '')) == '是'),
                        data_layer=str(row.get('数据层级', '')) if row.get('数据层级') != 'nan' else None,
                        properties_schema=[]
                    )
                    db.add(new_entity)
                    db.flush()
                    imported_entity_ids.append(str(new_entity.id))
            db.flush()
            for entity_id in imported_entity_ids:
                entity = db.query(Entity).filter(Entity.id == entity_id).first()
                if entity:
                    _update_entity_concept_links(db, str(entity.id), [str(entity.concept_id)], mode=mode)
            db.flush()  # C3：阶段内只 flush，统一提交

        # 3. 导入实体属性
        if '实体属性' in excel_data:
            df = excel_data['实体属性']
            # 按实体编码分组处理
            for code, group in df.groupby('实体编码'):
                entity = db.query(Entity).filter(Entity.entity_code == str(code).strip()).first()
                if not entity:
                    continue

                new_props = []
                for _, row in group.iterrows():
                    new_props.append({
                        "name": str(row['属性名(EN)']).strip(),
                        "cnName": str(row['属性名(CN)']).strip(),
                        "type": str(row.get('类型', 'string')).strip(),
                        "isPrimaryKey": (str(row.get('是否主键', '')) == '是'),
                        "description": str(row.get('描述', '')) if row.get('描述') != 'nan' else ""
                    })
                entity.properties_schema = new_props
                counts["attributes"] += len(new_props)
            db.flush()  # C3：阶段内只 flush，统一提交

        # 4. 导入实体关系
        # 模式导入下不处理关系，避免跨主数据/业务活动互相污染。
        # 关系导入后续走独立功能。
        if not mode and '实体关系' in excel_data:
            df = excel_data['实体关系']
            for _, row in df.iterrows():
                relation_category = str(row.get('关系类别', '手工维护')).strip() if row.get('关系类别') != 'nan' else "手工维护"
                rel_name = str(row['关系名称']).strip()
                source_name = str(row['源实体']).strip()
                target_name = str(row['目标实体']).strip()
                
                source = db.query(Entity).filter(Entity.entity_name == source_name).first()
                target = db.query(Entity).filter(Entity.entity_name == target_name).first()
                
                if not source or not target:
                    continue
                
                # 模式过滤（仅当源实体属于当前模式的概念时导入）
                source_concept = db.query(Concept).filter(Concept.id == source.concept_id).first()
                if mode == 'master' and source_concept.level not in [1, 2]: continue
                if mode == 'activity' and source_concept.level not in [0, 3, 4]: continue

                existing = db.query(EntityRelation).filter(
                    EntityRelation.source_entity_id == source.id,
                    EntityRelation.target_entity_id == target.id,
                    EntityRelation.relation_name == rel_name,
                    EntityRelation.relation_category == relation_category,
                ).first()
                
                rel_data = {
                    "source_entity_id": source.id,
                    "target_entity_id": target.id,
                    "relation_name": rel_name,
                    "relation_category": relation_category,
                    "direction": str(row.get('方向', 'forward')).strip(),
                    "cardinality": str(row.get('基数', 'N:N')).strip(),
                    "join_expr": str(row.get('关联条件', '')) if row.get('关联条件') != 'nan' else None,
                    "description": str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                    "remark": str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                }
                
                if existing:
                    for k, v in rel_data.items():
                        setattr(existing, k, v)
                else:
                    db.add(EntityRelation(**rel_data))
                counts["relations"] += 1
            db.flush()  # C3：阶段内只 flush，统一提交

        # clear+import 会重建实体（uuid 变更），按 entity_code 重链建模表/初始化数据/映射规则，避免断链
        if clear:
            _relink_entity_dependencies(db)

        db.commit()  # C3（三轨M1）：全部阶段成功后统一提交——任一阶段失败走 rollback 零残留
        total = counts["concepts"] + counts["entities"] + counts["attributes"] + counts["relations"]
        # 模式不匹配判定：文件里有实体但全部找不到所属概念（概念/实体均为 0）
        mode_mismatch = counts["entities"] == 0 and counts["entities_skipped"] > 0
        if mode_mismatch:
            msg = f"未导入任何概念/实体（跳过 {counts['entities_skipped']} 个）：文件与当前页面模式不匹配，请在对应页面（主数据/业务活动）导入"
            status = "warning"
        elif total == 0:
            msg = "未导入任何数据：请检查文件与当前页面模式是否匹配（主数据/业务活动）"
            status = "warning"
        else:
            skipped = f"，跳过 {counts['entities_skipped']} 个无所属概念的实体" if counts["entities_skipped"] else ""
            msg = f"导入成功：概念 {counts['concepts']}、实体 {counts['entities']}、属性 {counts['attributes']}、关系 {counts['relations']}{skipped}"
            status = "success"
        return {"code": 200, "message": msg, "counts": counts, "total": total, "status": status}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/graph/matrix")
def get_graph_matrix(db: Session = Depends(get_db)):
    """获取资产矩阵数据：左侧 业务域/L3/L4 及其下属实体，顶部 L1/L2 及其下属实体"""
    try:
        # 1. 获取所有概念，按层级分类
        concepts = _sort_concepts(db.query(Concept).all())
        concept_map = {str(c.id): c for c in concepts}
        # 业务域定义为 level=0（不在图谱展示，仅用于矩阵分类）
        domains = [c for c in concepts if c.level == 0]
        l1_l2 = [c for c in concepts if c.level in [1, 2]]
        l3_l4 = [c for c in concepts if c.level in [3, 4]]
        
        # 2. 获取有挂载的实体（与主数据建模页面一致，只用 kg_entity_concept_links 里挂载的）
        _linked_entity_ids = [link.entity_id for link in db.query(EntityConceptLink).all()]
        entities = _sort_entities(
            db.query(Entity).filter(Entity.id.in_(_linked_entity_ids)).all()
        ) if _linked_entity_ids else []
        entity_map = {str(e.id): e for e in entities}
        
        # 获取打点维护关系：统一从实体关系表读取
        matrix_links = db.query(EntityRelation).filter(EntityRelation.relation_category == "打点维护").all()
        link_map = {}
        link_detail_map = {}
        for link in matrix_links:
            source_entity = entity_map.get(str(link.source_entity_id))
            target_entity = entity_map.get(str(link.target_entity_id))
            source_concept = concept_map.get(str(source_entity.concept_id)) if source_entity else None
            target_concept = concept_map.get(str(target_entity.concept_id)) if target_entity else None
            if not source_entity or not target_entity or not source_concept or not target_concept:
                continue
            if source_concept.level != 2 or target_concept.level != 4:
                continue
            sid = str(target_entity.id)
            tid = str(source_entity.id)
            if sid not in link_map:
                link_map[sid] = []
            link_map[sid].append(tid)
            if sid not in link_detail_map:
                link_detail_map[sid] = {}
            link_detail_map[sid][tid] = {
                "id": str(link.id),
                "relation_name": link.relation_name,
                "relation_category": "打点维护",
                "direction": link.direction or "forward",
                "cardinality": link.cardinality or "N:N",
                "join_expr": link.join_expr,
                "description": link.description,
                "source_field_name": link.source_field_name,
                "target_field_name": link.target_field_name,
                "remark": link.remark,
            }

        # 构建实体所属主要概念 map: {concept_id: [entity, ...]}
        concept_entities_map = {}
        for e in entities:
            cid = str(e.concept_id)
            if cid not in concept_entities_map:
                concept_entities_map[cid] = []
            concept_entities_map[cid].append(e)
            
        # 3. 构造响应结构
        return {
            "code": 200,
            "data": {
                "columns": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "level": c.level,
                        "parent_id": str(c.parent_id) if c.parent_id else None,
                        "sort_order": c.sort_order or 0,
                        "entities": [
                            {
                                "id": str(e.id),
                                "name": e.entity_name,
                                "code": e.entity_code,
                                "en_name": e.entity_en_name,
                                "is_main_table": e.is_main_table,
                                "sort_order": e.sort_order or 0,
                            } for e in _sort_entities(concept_entities_map.get(str(c.id), []))
                        ] if c.level == 2 else []
                    } for c in l1_l2
                ],
                "domains": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "level": c.level,
                        "parent_id": str(c.parent_id) if c.parent_id else None,
                        "sort_order": c.sort_order or 0,
                    } for c in domains
                ],
                "rows": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "level": c.level,
                        "parent_id": str(c.parent_id) if c.parent_id else None,
                        "sort_order": c.sort_order or 0,
                        "entities": [
                            {
                                "id": str(e.id),
                                "name": e.entity_name,
                                "code": e.entity_code,
                                "en_name": e.entity_en_name,
                                "sort_order": e.sort_order or 0,
                                "linked_entity_ids": link_map.get(str(e.id), []),
                                "linked_entity_map": link_detail_map.get(str(e.id), {})
                            } for e in _sort_entities([item for item in entities if str(item.concept_id) == str(c.id)])
                        ]
                    } for c in l3_l4
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate matrix data: {str(e)}")


@router.post("/entities/{entity_id}/matrix/toggle")
def toggle_entity_matrix_link(entity_id: str, target_entity_id: str, db: Session = Depends(get_db)):
    """在矩阵中切换业务实体(L4)与主数据实体(L2)的打点关联"""
    activity_id = _norm_uuid_str(entity_id, "entity_id")
    master_id = _norm_uuid_str(target_entity_id, "target_entity_id")
    activity_entity = db.query(Entity).filter(Entity.id == activity_id).first()
    master_entity = db.query(Entity).filter(Entity.id == master_id).first()
    if not activity_entity or not master_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    existing = db.query(EntityRelation).filter(
        EntityRelation.source_entity_id == master_id,
        EntityRelation.target_entity_id == activity_id,
        EntityRelation.relation_category == "打点维护",
    ).first()

    if existing:
        db.delete(existing)
        action = "unlinked"
        link_id = str(existing.id)
    else:
        new_link = EntityRelation(
            id=str(uuid.uuid4()),
            source_entity_id=master_id,
            target_entity_id=activity_id,
            relation_name=_build_matrix_relation_name(master_entity, activity_entity),
            relation_category="打点维护",
            direction="forward",
            cardinality="N:N",
            join_expr=None,
            description="由资产矩阵打点自动生成的实体关系",
            remark="由资产矩阵打点自动生成的实体关系",
        )
        db.add(new_link)
        action = "linked"
        link_id = str(new_link.id)
        
    db.commit()
    return {"code": 200, "message": "success", "action": action, "link_id": link_id}
