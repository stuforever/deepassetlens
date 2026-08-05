from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime

class ConceptBase(BaseModel):
    name: str
    level: int = Field(..., ge=0, le=4)
    parent_id: Optional[str] = None
    area_index: Optional[int] = 1
    sort_order: Optional[int] = None
    description: Optional[str] = None
    system_names: Optional[List[str]] = None

class ConceptCreate(ConceptBase):
    pass

class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    area_index: Optional[int] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None
    system_names: Optional[List[str]] = None

class ConceptResponse(ConceptBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True

class EntityBase(BaseModel):
    concept_id: str
    entity_code: str
    entity_name: str
    entity_en_name: Optional[str] = None
    entity_explanation: Optional[str] = None
    properties_schema: Optional[list] = None
    description: Optional[str] = None
    is_main_table: Optional[bool] = False
    data_layer: Optional[str] = None
    sort_order: Optional[int] = None
    source_mode: Optional[str] = "physical_table"
    integration_sql: Optional[str] = None
    doris_catalog: Optional[str] = None
    data_source_id: Optional[str] = None

class EntityCreate(EntityBase):
    concept_ids: Optional[List[str]] = None

class EntityUpdate(BaseModel):
    entity_name: Optional[str] = None
    entity_en_name: Optional[str] = None
    entity_explanation: Optional[str] = None
    entity_code: Optional[str] = None
    concept_id: Optional[str] = None
    concept_ids: Optional[List[str]] = None
    description: Optional[str] = None
    is_main_table: Optional[bool] = None
    data_layer: Optional[str] = None
    sort_order: Optional[int] = None
    properties_schema: Optional[list] = None
    source_mode: Optional[str] = None
    integration_sql: Optional[str] = None
    doris_catalog: Optional[str] = None
    data_source_id: Optional[str] = None

class EntityResponse(EntityBase):
    id: str
    created_at: datetime
    concept_ids: Optional[List[str]] = None

    class Config:
        orm_mode = True
        from_attributes = True

class EntityRelationBase(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relation_name: str
    relation_category: Optional[str] = "手工维护"
    direction: Optional[str] = "forward"
    cardinality: Optional[str] = "N:N"
    source_field_name: Optional[str] = None
    target_field_name: Optional[str] = None
    join_expr: Optional[str] = None
    description: Optional[str] = None
    remark: Optional[str] = None

class EntityRelationCreate(EntityRelationBase):
    pass


class EntityRelationUpdate(BaseModel):
    source_entity_id: Optional[str] = None
    target_entity_id: Optional[str] = None
    relation_name: Optional[str] = None
    relation_category: Optional[str] = None
    direction: Optional[str] = None
    cardinality: Optional[str] = None
    source_field_name: Optional[str] = None
    target_field_name: Optional[str] = None
    join_expr: Optional[str] = None
    description: Optional[str] = None
    remark: Optional[str] = None

class EntityRelationResponse(EntityRelationBase):
    id: str
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
