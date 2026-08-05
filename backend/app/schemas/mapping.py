from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

# 数据源注册请求
class SourceTableBase(BaseModel):
    table_name: str
    schema_name: Optional[str] = "public"
    connection_info: Dict[str, Any] # 存储数据库连接配置 (host, port, user, pwd等)

class SourceTableCreate(SourceTableBase):
    pass

class SourceTableResponse(SourceTableBase):
    id: UUID
    column_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        orm_mode = True

# 映射保存请求
class MappingLogicItem(BaseModel):
    target_attr: str
    source_col: str

class EntityMappingCreate(BaseModel):
    entity_id: UUID
    source_table_id: UUID
    mapping_logic: Dict[str, str] # {"entity_attr": "table_column"}
    sql_fragment: Optional[str] = None

class EntityMappingResponse(EntityMappingCreate):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True
