from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from .api import (
    concept, mapping, chat, upload, source_tables,
    llm_admin, standard_semantic,
    data_source, v2_skills, runs,
    entity_relation_manage,
    metric_center, metadata,
    auth as auth_api,
    data_intelligence,
    data_sync,
    biz_work_order,
    kg_api,
    synonym,
    api_mapping,
    doris_config,
    knowledge_base,
)
from .models.base import Base
# 确保模型注册到 Base.metadata（避免循环导入，在这里集中导入）
from .models.skill import Skill, SkillVersion, SkillExecLog, SkillApiBinding, SkillType
from .models.scheduler import (
    TaskQueue, DebugSession,
    SkillSchedule, Conversation, ConversationMessage,
    AgentRun, RunEvent,
)
from .models.auth import User as AuthUserModel, Role, UserRole, ResourceACL
from .models.knowledge_base import KnowledgeBase, KnowledgeDocument
from .core.database import engine, SessionLocal, ensure_schema_compatibility
from .core.init_db import init_db
from .core.task_worker import task_worker_manager
from .core.auth import auth_middleware, ENABLE_AUTH
from .services.skill_manager import VersionService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    with SessionLocal() as db:
        init_db(db)
        # master_activity 关系统一为"打点维护"：把 source/target 为 L2/L4 的"手工维护"
        # 关系迁移为"打点维护"（与资产矩阵打点同义）；若该实体对已有打点维护关系则删掉重复手工条目。
        try:
            from .models.base import EntityRelation, Concept, Entity
            _concepts = db.query(Concept).all()
            _concept_map = {str(c.id): c for c in _concepts}
            _ents = db.query(Entity).all()
            _ent_map = {str(e.id): e for e in _ents}

            def _level_of(eid):
                e = _ent_map.get(str(eid))
                if not e:
                    return None
                c = _concept_map.get(str(e.concept_id))
                return c.level if c else None

            def _l2_l4_pair(src_id, tgt_id):
                """返回规范化 (L2_id, L4_id) 或 None（非 master_activity）。"""
                sl, tl = _level_of(src_id), _level_of(tgt_id)
                if {sl, tl} != {2, 4}:
                    return None
                return (str(src_id), str(tgt_id)) if sl == 2 else (str(tgt_id), str(src_id))

            # 已有"打点维护"的实体对
            _dotting_pairs = set()
            for r in db.query(EntityRelation).filter(EntityRelation.relation_category == "打点维护").all():
                pair = _l2_l4_pair(r.source_entity_id, r.target_entity_id)
                if pair:
                    _dotting_pairs.add(pair)
            _migrated = 0
            _dedup = 0
            for r in db.query(EntityRelation).filter(EntityRelation.relation_category == "手工维护").all():
                pair = _l2_l4_pair(r.source_entity_id, r.target_entity_id)
                if not pair:
                    continue
                if pair in _dotting_pairs:
                    db.delete(r)
                    _dedup += 1
                else:
                    r.relation_category = "打点维护"
                    _dotting_pairs.add(pair)
                    _migrated += 1
            db.commit()
            print(f"[startup] master_activity category migrated: {_migrated}, dedup_deleted: {_dedup}")
        except Exception as _exc:
            print(f"[startup] master_activity migration error: {_exc}")
        VersionService.normalize_all_versions_to_filesystem(db)
        # Qdrant 后端自动同步：如果 Qdrant 健康则自动同步标准语义词条到 Qdrant，
        # 并把全局开关 TUPU_VECTOR_BACKEND 设为 qdrant，让 step2 走 ANN 加速。
        try:
            from .services.standard_semantic_qdrant import sync_standard_semantic_to_qdrant
            from .services.tupu_qdrant_client import TupuQdrantClient
            import os as _os
            if TupuQdrantClient().healthcheck():
                sync_result = sync_standard_semantic_to_qdrant(db)
                if sync_result.get("ok"):
                    _os.environ["TUPU_VECTOR_BACKEND"] = "qdrant"
                    print(f"[startup] qdrant_backend enabled: {sync_result}")
                else:
                    print(f"[startup] qdrant_sync failed: {sync_result}")
            else:
                print("[startup] qdrant healthcheck failed, staying on mysql backend")
        except Exception as _exc:
            print(f"[startup] qdrant_setup error (continuing with mysql): {_exc}")
        # Neo4j 启动钩子：全量重建单一 Category+ChainRoot 体系
        try:
            from .services.graph_query_neo4j import (
                neo4j_healthcheck,
                sync_all_to_neo4j,
            )
            if neo4j_healthcheck():
                neo4j_result = sync_all_to_neo4j(db, force=True)
                print(f"[startup] neo4j_sync_all: {neo4j_result}")
            else:
                print("[startup] neo4j healthcheck failed")
        except Exception as _exc:
            print(f"[startup] neo4j_setup error (continuing without neo4j): {_exc}")
        # Qdrant 实体/属性向量同步（独立 collection，后台执行不阻塞 startup）
        import threading as _threading
        def _bg_vector_sync():
            try:
                from .services.entity_attr_vector_service import (
                    sync_entity_vectors,
                    sync_attribute_vectors,
                )
                from app.core.database import SessionLocal as _SL
                _db = _SL()
                try:
                    ent_result = sync_entity_vectors(_db, force=True)
                    attr_result = sync_attribute_vectors(_db, force=True)
                    print(f"[startup-bg] entity_vectors: {ent_result}")
                    print(f"[startup-bg] attribute_vectors: {attr_result}")
                finally:
                    _db.close()
            except Exception as _exc:
                print(f"[startup-bg] vector_sync error: {_exc}")
        _threading.Thread(target=_bg_vector_sync, daemon=True).start()
    # 启动后台任务工作线程
    task_worker_manager.start(poll_interval=2.0)
    yield
    # Shutdown
    task_worker_manager.stop()


app = FastAPI(title="数据智能分析组件 API", lifespan=lifespan)

# 启用 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentik OIDC 鉴权中间件（ENABLE_AUTH=0 时短路放行）
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

@app.get("/")
def read_root():
    return {"message": "欢迎使用 数据智能分析组件 API", "auth_enabled": ENABLE_AUTH}

# v1 API（兼容旧接口）
app.include_router(auth_api.router, prefix="/api/v1", tags=["auth"])
app.include_router(concept.router, prefix="/api/v1", tags=["concepts"])
app.include_router(mapping.router, prefix="/api/v1", tags=["mappings"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(source_tables.router, prefix="/api/v1", tags=["source_tables"])
app.include_router(llm_admin.router, prefix="/api/v1", tags=["llm_admin"])
app.include_router(standard_semantic.router, prefix="/api/v1", tags=["standard_semantic"])
app.include_router(data_source.router, prefix="/api/v1", tags=["data_source"])
app.include_router(entity_relation_manage.router, prefix="/api/v1", tags=["entity_relation_manage"])
app.include_router(metric_center.router, prefix="/api/v1", tags=["metrics"])
app.include_router(metadata.router, prefix="/api/v1", tags=["metadata"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
# v2 API（新技能管理架构）
app.include_router(v2_skills.router, prefix="/api/v2", tags=["skills-v2"])
app.include_router(data_intelligence.router)  # 自带 prefix="/api/data-intelligence"
app.include_router(data_sync.router)  # 自带 prefix="/api/v1/sync"
app.include_router(knowledge_base.router)  # 自带 prefix="/api/v1/knowledge-bases"
app.include_router(biz_work_order.router)  # 自带 prefix="/api/v1/biz_work_order"
app.include_router(kg_api.router)  # 自带 prefix="/api/kg"
app.include_router(synonym.router)  # 自带 prefix="/api/v1/synonyms"
app.include_router(api_mapping.router, prefix="/api/v1", tags=["api_mapping"])
app.include_router(doris_config.router, prefix="/api/v1", tags=["doris_config"])

# MCP Server（业务工具标准化，deepagent 和外部 client 共用，SSE 传输 /mcp/sse）
from app.mcp_server import mount_mcp
mount_mcp(app)
