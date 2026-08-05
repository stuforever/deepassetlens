from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.base import SourceMasterTable, SourceBusinessTable, SourceReferenceTable, SourceTableRelation
from pydantic import BaseModel
from typing import Optional, List, Literal

router = APIRouter()

class MasterTableCreate(BaseModel):
    major: Optional[str] = None
    deploy: Optional[str] = None
    sysName: Optional[str] = None
    sysCode: Optional[str] = None
    l1: Optional[str] = None
    l2: Optional[str] = None
    enName: Optional[str] = None
    cnName: Optional[str] = None
    type: Optional[str] = "主数据"

class BusinessTableCreate(BaseModel):
    major: Optional[str] = None
    deploy: Optional[str] = None
    sysName: Optional[str] = None
    sysCode: Optional[str] = None
    l3: Optional[str] = None
    l4: Optional[str] = None
    enName: Optional[str] = None
    cnName: Optional[str] = None
    type: Optional[str] = "业务表"
    relL1: Optional[str] = None
    relL2: Optional[str] = None

class ReferenceTableCreate(BaseModel):
    major: Optional[str] = None
    deploy: Optional[str] = None
    sysName: Optional[str] = None
    sysCode: Optional[str] = None
    category: Optional[str] = None
    enName: Optional[str] = None
    cnName: Optional[str] = None
    type: Optional[str] = "参考数据表"

class TableRelationCreate(BaseModel):
    relation_scope: Literal["l2", "l4", "cross"]
    l1: Optional[str] = None
    l2: Optional[str] = None
    l3: Optional[str] = None
    l4: Optional[str] = None
    relation_desc: Optional[str] = None
    main_table_cn: Optional[str] = None
    main_table_en: str
    related_table_cn: Optional[str] = None
    related_table_en: str
    relation_category: Optional[str] = None
    relation_expr: str
    remark: Optional[str] = None

class TableRelationsBulkSave(BaseModel):
    l2_relations: List[TableRelationCreate] = []
    l4_relations: List[TableRelationCreate] = []
    cross_relations: List[TableRelationCreate] = []

def _serialize_relation(r: SourceTableRelation):
    return {
        "id": str(r.id),
        "relation_scope": r.relation_scope,
        "l1": r.l1,
        "l2": r.l2,
        "l3": r.l3,
        "l4": r.l4,
        "relation_desc": r.relation_desc,
        "main_table_cn": r.main_table_cn,
        "main_table_en": r.main_table_en,
        "related_table_cn": r.related_table_cn,
        "related_table_en": r.related_table_en,
        "relation_category": r.relation_category,
        "relation_expr": r.relation_expr,
        "remark": r.remark,
    }


@router.post("/source_tables/bulk_save")
def bulk_save_tables(
    master_data: List[MasterTableCreate],
    business_data: List[BusinessTableCreate],
    reference_data: List[ReferenceTableCreate],
    db: Session = Depends(get_db)
):
    try:
        # 清空原有数据 (简单处理，直接全量替换)
        db.query(SourceMasterTable).delete()
        db.query(SourceBusinessTable).delete()
        db.query(SourceReferenceTable).delete()
        
        # 插入主数据
        for item in master_data:
            db.add(SourceMasterTable(**item.dict()))
            
        # 插入业务数据
        for item in business_data:
            db.add(SourceBusinessTable(**item.dict()))
            
        # 插入参考数据
        for item in reference_data:
            db.add(SourceReferenceTable(**item.dict()))
            
        db.commit()
        return {"code": 200, "message": "Success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/source_tables/all")
def get_all_tables(db: Session = Depends(get_db)):
    master = db.query(SourceMasterTable).all()
    business = db.query(SourceBusinessTable).all()
    reference = db.query(SourceReferenceTable).all()
    
    return {
        "code": 200,
        "data": {
            "master": master,
            "business": business,
            "reference": reference
        }
    }


@router.get("/source_tables/relations/all")
def get_all_table_relations(db: Session = Depends(get_db)):
    relations = db.query(SourceTableRelation).all()
    return {
        "code": 200,
        "data": {
            "l2_relations": [_serialize_relation(r) for r in relations if r.relation_scope == "l2"],
            "l4_relations": [_serialize_relation(r) for r in relations if r.relation_scope == "l4"],
            "cross_relations": [_serialize_relation(r) for r in relations if r.relation_scope == "cross"],
        }
    }


@router.post("/source_tables/relations/bulk_save")
def bulk_save_table_relations(payload: TableRelationsBulkSave, db: Session = Depends(get_db)):
    try:
        db.query(SourceTableRelation).delete()

        for item in payload.l2_relations:
            data = item.dict()
            data["relation_scope"] = "l2"
            db.add(SourceTableRelation(**data))
        for item in payload.l4_relations:
            data = item.dict()
            data["relation_scope"] = "l4"
            db.add(SourceTableRelation(**data))
        for item in payload.cross_relations:
            data = item.dict()
            data["relation_scope"] = "cross"
            db.add(SourceTableRelation(**data))

        db.commit()
        return {"code": 200, "message": "Success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
