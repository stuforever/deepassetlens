from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
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
    engine_observability,
    qa_examples,
    golden_qa,
    feedback,
    guards,
    capabilities,)
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
from .core.auth import AuthMiddleware, ENABLE_AUTH
from .services.skill_manager import VersionService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # F3-fix: 生产安全检查必须 fail-fast--在任何 DB 初始化、Qdrant/Neo4j 同步、worker 启动之前
    # 否则配置非法时已执行外部初始化/可能写数据/已启动工作线程，不是严格的启动前阻断
    import os as _os_f3
    if _os_f3.getenv("ENABLE_AUTH", "0") == "1":
        _startup_errors = []
        if not _os_f3.getenv("CORS_ORIGINS"):
            _startup_errors.append("ENABLE_AUTH=1 但未设 CORS_ORIGINS（生产禁止通配符+凭据组合）")
        if not _os_f3.getenv("AUTHENTIK_JWKS_URL"):
            _startup_errors.append("ENABLE_AUTH=1 但未设 AUTHENTIK_JWKS_URL（OIDC 验签无法工作）")
        if _startup_errors:
            for _err in _startup_errors:
                logger.error(f"[startup] FATAL: {_err}")
            raise RuntimeError("生产安全检查未通过：" + "; ".join(_startup_errors))
    # Startup
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    with SessionLocal() as db:
        init_db(db)
        # 安全控制中心：清理 30 天前 guard_events（防表膨胀）
        try:
            from .services.guard_config import cleanup_old_events
            _cleaned = cleanup_old_events(days=30)
            if _cleaned:
                logger.info(f"[startup] guard_events 清理 {_cleaned} 条（>30 天）")
        except Exception as _gce:
            logger.warning(f"[startup] guard_events 清理失败: {_gce}")
        # 能力开关中心（批13-Q）：清理 30 天前 capability_events
        try:
            from .services.capability_config import cleanup_old_events as _cap_cleanup
            _cap_cleaned = _cap_cleanup(days=30)
            if _cap_cleaned:
                logger.info(f"[startup] capability_events 清理 {_cap_cleaned} 条（>30 天）")
        except Exception as _cce:
            logger.warning(f"[startup] capability_events 清理失败: {_cce}")
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
            logger.info(f"[startup] master_activity category migrated: {_migrated}, dedup_deleted: {_dedup}")
        except Exception as _exc:
            logger.warning(f"[startup] master_activity migration error: {_exc}")
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
                    logger.info(f"[startup] qdrant_backend enabled: {sync_result}")
                else:
                    logger.warning(f"[startup] qdrant_sync failed: {sync_result}")
            else:
                logger.warning("[startup] qdrant healthcheck failed, staying on mysql backend")
        except Exception as _exc:
            logger.warning(f"[startup] qdrant_setup error (continuing with mysql): {_exc}")
        # Neo4j 启动钩子：全量重建单一 Category+ChainRoot 体系
        try:
            from .services.graph_query_neo4j import (
                neo4j_healthcheck,
                sync_all_to_neo4j,
            )
            if neo4j_healthcheck():
                neo4j_result = sync_all_to_neo4j(db, force=True)
                logger.info(f"[startup] neo4j_sync_all: {neo4j_result}")
            else:
                logger.warning("[startup] neo4j healthcheck failed")
        except Exception as _exc:
            logger.warning(f"[startup] neo4j_setup error (continuing without neo4j): {_exc}")
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
                    logger.info(f"[startup-bg] entity_vectors: {ent_result}")
                    logger.info(f"[startup-bg] attribute_vectors: {attr_result}")
                finally:
                    _db.close()
            except Exception as _exc:
                logger.warning(f"[startup-bg] vector_sync error: {_exc}")
        _threading.Thread(target=_bg_vector_sync, daemon=True).start()
    # 启动后台任务工作线程
    task_worker_manager.start(poll_interval=2.0)
    # 数据引擎增强（批1）：查询日志 30 天自动清理挂 TaskWorker 低优先级周期任务
    try:
        from app.services.engine_query_log import register_purge_job
        register_purge_job(task_worker_manager)
    except Exception as _pg_err:
        logger.warning(f"[startup] WARNING: 注册查询日志清理任务失败: {_pg_err}")
    # 数据引擎增强（P5）：预聚合加速器到期刷新挂 TaskWorker（300s 检查）
    try:
        from app.services.engine_accelerator import register_refresh_job
        register_refresh_job(task_worker_manager)
    except Exception as _ac_err:
        logger.warning(f"[startup] WARNING: 注册加速器刷新任务失败: {_ac_err}")
    # MCP 挂载检查：确认 /mcp 路由已注册（deepagent 首次请求依赖此端点）
    # 注意：lifespan startup 阶段 uvicorn 尚未开始监听，不能 HTTP 自请求，只检查路由注册
    try:
        _mcp_routes = [r for r in app.routes if getattr(r, "path", "").startswith("/mcp")]
        if _mcp_routes:
            logger.info(f"[startup] MCP /mcp 路由已挂载 ({len(_mcp_routes)} routes)，SSE endpoint: http://127.0.0.1:28000/mcp/sse")
        else:
            logger.warning("[startup] WARNING: MCP /mcp 路由未找到，deepagent 工具加载将失败")
    except Exception as _mcp_err:
        logger.warning(f"[startup] WARNING: MCP 挂载检查异常: {_mcp_err}")
    # 批13-N6：agent 单例启动预热——治重启后首问冷启动（MCP 工具加载 HTTP 自请求 2~5s）。
    # 注意：lifespan startup 阶段 uvicorn 尚未监听（不能自请求），故用后台任务延迟预热：
    # 服务开始接受连接后 sleep 1.5s 再构建单例；失败静默（首次请求时按原逻辑重建）。
    async def _warmup_tupu_agent():
        import asyncio
        import time as _time_mod
        try:
            await asyncio.sleep(1.5)
            from app.services.tupu_deepagent import get_tupu_agent
            _w_t0 = _time_mod.time()
            await get_tupu_agent("")
            logger.info(f"[startup-bg] tupu agent 单例预热完成 ({(_time_mod.time() - _w_t0) * 1000:.0f}ms)")
        except Exception as _warm_err:
            logger.warning(f"[startup-bg] tupu agent 预热失败（首次请求将按原逻辑重建）: {_warm_err}")

    try:
        import asyncio
        asyncio.get_running_loop().create_task(_warmup_tupu_agent())
    except Exception as _warm_task_err:
        logger.warning(f"[startup] WARNING: agent 预热任务创建失败: {_warm_task_err}")
    # 专家地基①（spec §九步骤 4）：checkpoint 三段键迁移——启动序列内、服务就绪前完成
    # （部署窗口单实例+此时机=迁移无并发写窗口，spec §十二.3）；失败不阻启动。
    try:
        from app.services.tupu_deepagent import _migrate_checkpoint_thread_ids
        _migrate_checkpoint_thread_ids()
    except Exception as _mig_err:
        logger.warning(f"[startup] checkpoint 迁移异常（不阻启动）: {_mig_err}")
    # F3-fix: 生产安全检查已移到 lifespan 最开头（fail-fast，在任何初始化之前）
    yield
    # Shutdown
    task_worker_manager.stop()
    # 关闭全局 DeepAgent checkpointer SQLite 连接
    try:
        from app.services.tupu_deepagent import close_tupu_agent
        await close_tupu_agent()
    except Exception as _e:
        logger.warning(f"[shutdown] close_tupu_agent error: {_e}")


app = FastAPI(title="数据智能分析组件 API", lifespan=lifespan)

# 启用 CORS（P3: 生产环境禁止通配符+凭据组合）
import os as _os
_cors_origins = _os.getenv("CORS_ORIGINS", "").split(",") if _os.getenv("CORS_ORIGINS") else ["*"]
_cors_credentials = bool(_os.getenv("CORS_ORIGINS"))  # 指定了具体 origin 才允许凭据
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentik OIDC 鉴权中间件（ENABLE_AUTH=0 时短路放行）
# 纯 ASGI 中间件：透传 send，不破坏 SSE StreamingResponse（BaseHTTPMiddleware 会断流）
app.add_middleware(AuthMiddleware)

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
app.include_router(qa_examples.router, prefix="/api/v1", tags=["qa_examples"])  # G1 验证示例库
app.include_router(golden_qa.router, prefix="/api/v1", tags=["golden_qa"])     # M4 G6 金标评估集
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])       # M4 G5 反馈闭环
app.include_router(api_mapping.router, prefix="/api/v1", tags=["api_mapping"])
app.include_router(doris_config.router, prefix="/api/v1", tags=["doris_config"])
# 数据引擎增强（批3）：观测端点（自带 prefix="/api/engine"）
app.include_router(engine_observability.router)
app.include_router(guards.router)  # 自带 prefix="/api/guards"（安全控制中心）
app.include_router(capabilities.router)  # 自带 prefix="/api/capabilities"（能力开关中心，批13-Q）

# MCP Server（业务工具标准化，deepagent 和外部 client 共用，SSE 传输 /mcp/sse）
from app.mcp_server import mount_mcp
mount_mcp(app)
