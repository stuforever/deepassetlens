from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..models.base import Concept, Entity, EntityRelation, EntityConceptLink, ConceptRelation, EntityModeling, EntityInitData, EntityMappingRule
import pandas as pd
import io
import json
from ..schemas.concept import (
    ConceptCreate,
    ConceptResponse,
    ConceptUpdate,
    EntityCreate,
    EntityResponse,
    EntityUpdate,
    EntityRelationCreate,
    EntityRelationUpdate,
    EntityRelationResponse,
)
from ..core.database import get_db
from pydantic import BaseModel
import uuid
import re

router = APIRouter()


from .concept_support import (
    EntityExplanationSuggestRequest,
    _split_entity_explanation, _expand_entity_explanation_terms, _get_property_label,
    _extract_property_keyword_options, _build_entity_explanation_suggestions,
    _norm_uuid_str, _build_matrix_relation_name, _safe_int, _normalize_system_names,
    _sort_concepts, _sort_entities, _update_entity_concept_links,
)


# 拆分说明：原 concept.py 的处理器已按主题机械拆分到三个兄弟模块（零行为变更）：
#   - concept_graph.py：图/Neo4j/层级相关端点
#   - concept_entity.py：概念/实体/关系 CRUD（含 EntityEnNameAutoFillRequest）
#   - concept_admin.py：导出/导入/清空 + 矩阵端点
# 本模块仅聚合挂载；concept.router 仍是对外暴露的 router 对象
# （main.py 使用 include_router(concept.router, prefix="/api/v1")），路由路径与行为不变。
from .concept_graph import router as _graph_router
from .concept_entity import router as _entity_router
from .concept_admin import router as _admin_router
router.include_router(_graph_router)
router.include_router(_entity_router)
router.include_router(_admin_router)
