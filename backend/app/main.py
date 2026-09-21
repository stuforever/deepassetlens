from fastapi import Depends, FastAPI
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
    # ③模型目录化（spec §六步骤1）：capabilities 列+存量等值回填（chat→tool_call=true /
    # embedding→false），幂等；失败不阻启动（列缺省时读取端 D5 统一规则兜底）。
    try:
        from app.core.database import SessionLocal as _SL
        from app.services.llm_admin import _ensure_capabilities_column
        _db = _SL()
        try:
            _ensure_capabilities_column(_db)
        finally:
            _db.close()
        logger.info("[startup] capabilities 列确保完成（③模型目录化）")
    except Exception as _cap_err:
        logger.warning(f"[startup] capabilities 列迁移异常（不阻启动）: {_cap_err}")
    # ⑤批1（spec §二 Runbook 步骤1）：教学引擎 PG 四表（幂等；失败不阻启动——教学工具
    # 面返回可读错误，L1/L2/L3 记忆不受影响）。
    # ⑤R R1（批12）：四表冻结（sishu_review_cards/sishu_review_records/
    # sishu_wrong_questions/sishu_mother_questions 保留不迁移不删除；
    # 先行版端点/工具面已退役，表=专家域数据自隔离铁律下的冻结存档，M00 已登记）。
    try:
        from app.services.learning.pg import ensure_tables
        ensure_tables()
        logger.info("[startup] learning PG 四表确保完成（⑤教学引擎，R1 起冻结）")
    except Exception as _pg_err:
        logger.warning(f"[startup] learning PG 四表迁移异常（不阻启动）: {_pg_err}")
    # 记忆插槽②批2（spec §九步骤2）：AGENTS.md 受控搬迁（warmup 前；fail-fast——等值前提
    # 被破坏时宁可不起）+ wenshu 记忆树骨架/RAW_MD 预创建（失败不阻启动）。
    from app.services.memory_tree_backend import _migrate_agents_md
    _migrate_agents_md()
    try:
        from app.services.memory_tree_backend import ensure_dirs
        from app.services import expert_config as _ec
        ensure_dirs("wenshu", _ec.get_card("wenshu"))
    except Exception as _ensure_err:
        logger.warning(f"[startup] 记忆树骨架创建异常（不阻启动）: {_ensure_err}")
    # 记忆插槽②批5（spec §七）：consolidator 周期扫描（默认 30 分钟，env 关不启动）。
    import os as _os_cons
    if _os_cons.getenv("TUPU_MEMORY_CONSOLIDATOR", "1") == "1":
        try:
            from app.services import memory_consolidator
            asyncio.get_running_loop().create_task(memory_consolidator.periodic_scan())
            logger.info("[consolidator] 周期扫描任务已挂载（默认 30 分钟）")
        except Exception as _cons_err:
            logger.warning(f"[startup] consolidator 任务创建失败: {_cons_err}")
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
# 引擎批8 8.3：dt_llm_sync（vendor→③同步适配层）退役删除——/llm-config 数据面已切③
# 直连（llmDirectory 适配器），LLM 合一反转③唯一源，vendor llm 块冻结（spec §七）。
app.include_router(standard_semantic.router, prefix="/api/v1", tags=["standard_semantic"])
app.include_router(data_source.router, prefix="/api/v1", tags=["data_source"])
app.include_router(entity_relation_manage.router, prefix="/api/v1", tags=["entity_relation_manage"])
app.include_router(metric_center.router, prefix="/api/v1", tags=["metrics"])
app.include_router(metadata.router, prefix="/api/v1", tags=["metadata"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
# v2 API（新技能管理架构）
app.include_router(v2_skills.router, prefix="/api/v2", tags=["skills-v2"])
# 引擎批1：deepagent 桥端点 POST /api/v2/skills/capability（SSE——自带 prefix="/api/v2/skills"）
from app.api import dt_agent_capabilities as _dt_agent_caps
app.include_router(_dt_agent_caps.router, tags=["agent-bridge"])
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
from app.api import experts
app.include_router(experts.router)  # 自带 prefix="/api/experts"（专家地基①）
# ⑤R R1（批12）：先行版 /api/tutor-admin 与 /api/tutor 两路由退役移除——
# 能力由 vendor 复刻件承接（mother-questions/learning 走 vendor tutor_routers 装配表）。
from app.api import memory
app.include_router(memory.router)  # 自带 prefix="/api/memory"（记忆插槽②）

# ⑤R B1（唯一交棒 批3.1）：vendor 子树挂载——原 prefix，端点契约不变。
# tutor_routers=(router, prefix, tags, deps) 逐对对齐原仓 main.py 挂载表（随批次增长）；
# 静态挂载照原仓 L342-376（workspace 根走 DEEPTUTOR_HOME=DT_TUTOR_WORKSPACE_ROOT 单点）。
# v4批6 6.C+6.6：学习数据域七域换平台路由（sishu_learning 包，require_expert+binding 全挂
# ——执行面零 vendor 导入），vendor 对应六行摘除（curriculum/knowledge/book 等仍 vendor）。
from app.vendor.deeptutor.api.tutor_routers import static_mounts as _dt_static_mounts
from app.vendor.deeptutor.api.tutor_routers import tutor_routers as _dt_tutor_routers

# 批6 摘行集：tags 元组首元素标识（与 tutor_routers 装配表逐字对应）
# 批11深水扩：personas/capabilities 平台路由 5+2 端点全量 1:1 承接，vendor 行摘除；
# voice 平台路由 tts/stt 全量 1:1（services/voice 批6已移植）同摘除。
_SISHU_BATCH6_UNMOUNTED = {
    "mother-questions", "learner-profile", "mastery-path",
    "self-learning", "notebook", "question-notebook", "book", "sessions",
    "personas", "capabilities", "voice", "memory",
    # 批14深水：四小域平台面承接 vendor 行摘除
    "h5-links", "h5-settings", "imports", "attachments",
    # 批14深水：零消费域显式卸挂登记（前端 grep 0 文件+后端非 vendor 消费 0——
    # dashboard/wechat-push/space-mcp/space-cli-apps/plugins/agent-config；
    # multi-user 同为零消费但属 auth 邻接面，批15 C5 探针组 gate 后再登记卸挂）
    "dashboard", "wechat-push", "space-mcp", "space-cli-apps", "plugins", "agent-config",
}

from app.api import sishu_learning as _sishu_learning
from app.api.sishu_learning._enforce import SISHU_ROUTER_DEPS as _sishu_deps

for _r, _prefix, _tags in _sishu_learning.SISHU_MOUNTS:
    app.include_router(_r, prefix=_prefix, tags=_tags, dependencies=_sishu_deps)

# 三轨M13(批7)：book REST PG 面（vendor book 行摘除——SISHU_BATCH6_UNMOUNTED 扩 book）
from app.api.sishu_book import router as _sishu_book_router
app.include_router(_sishu_book_router, prefix="/api/v1/book", tags=["book"], dependencies=_sishu_deps)

# 三轨M14(批8)：会话族 REST PG 面（vendor sessions 行摘除——SISHU_BATCH6_UNMOUNTED 扩 sessions）
from app.api.sishu_sessions import router as _sishu_sessions_router
app.include_router(_sishu_sessions_router, prefix="/api/v1/sessions", tags=["sessions"], dependencies=_sishu_deps)

# 三轨M15(批9)：curriculum 读面 PG 换芯（同前缀 vendor curriculum router 仍挂 LLM 写面——读面先注册恒优先）
from app.api.sishu_curriculum import router as _sishu_curriculum_router
app.include_router(_sishu_curriculum_router, prefix="/api/v1/curriculum", tags=["curriculum"], dependencies=_sishu_deps)

# 三轨M17(批10 深水)：knowledge 平台路由——8 读/写端点先注册恒优先；
# 其余低频面（上传/进度 WS/RAG 配置等 41 端点）vendor 同前缀续服务（E-85）。
# 补件：file_routing/embedding/pocketbase_client/embedding_signature/index_versioning
# 已由 scripts/_v4_port_batch10_kb_deps.py 机械移植（KBM base_dir=vendor 同源解析）。
from app.api.sishu_knowledge import router as _sishu_knowledge_router
app.include_router(_sishu_knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"], dependencies=_sishu_deps)

# 批11深水(1/4)：settings 平台路由——vendor settings.py 消费面 27 端点 1:1（全静态
# 径零遮挡）；codex-oauth/mineru/document-parsing/fetch-models/tour 低频面 vendor 续服务。
from app.api.sishu_settings import router as _sishu_settings_router
app.include_router(_sishu_settings_router, prefix="/api/v1/settings", tags=["settings"], dependencies=_sishu_deps)

# 批11深水(2/4)：capabilities 平台路由——2 端点全量 1:1（vendor 行摘除）。
from app.api.sishu_capabilities import router as _sishu_capabilities_router
app.include_router(_sishu_capabilities_router, prefix="/api/v1/capabilities", tags=["capabilities"], dependencies=_sishu_deps)

# 批11深水(3/4)：personas 平台路由——5 端点全量 1:1（services/persona+core/i18n 补件移植）。
from app.api.sishu_personas import router as _sishu_personas_router
app.include_router(_sishu_personas_router, prefix="/api/v1/personas", tags=["personas"], dependencies=_sishu_deps)

# 批11深水(4/4)：system 平台路由——/status 端点 1:1；vendor 余四端点零消费续服务。
from app.api.sishu_system import router as _sishu_system_router
app.include_router(_sishu_system_router, prefix="/api/v1/system", tags=["system"], dependencies=_sishu_deps)

# 批11深水(5/5)：voice 平台路由——tts/stt 全量 1:1（vendor voice 行摘除）。
from app.api.sishu_voice import router as _sishu_voice_router
app.include_router(_sishu_voice_router, prefix="/api/v1/voice", tags=["voice"], dependencies=_sishu_deps)

# 批12深水：memory 平台路由——vendor memory.py 27 端点全量 1:1（services/memory 移植包
# 与 vendor 逐文件齐全，import 前缀机械改写；vendor memory 行摘除）。三层记忆槽 MD（平台
# D1 既有）不动；数据面仍为 workspace MD+sidecar 文件（PG 化=数据层远期池）。
from app.api.sishu_memory import router as _sishu_memory_router
app.include_router(_sishu_memory_router, prefix="/api/v1/memory", tags=["memory"], dependencies=_sishu_deps)

# 批14深水(1/4)：h5-links 平台路由——vendor h5_links.py links 面 3 端点 1:1
# （compat h5/paths 同源解析 data/h5_links.json，零漂移）。
from app.api.sishu_h5_links import router as _sishu_h5_links_router
app.include_router(_sishu_h5_links_router, prefix="/api/v1/h5-links", tags=["h5-links"], dependencies=_sishu_deps)

# 批14深水(2/4)：h5-settings 平台路由——vendor h5_links.settings_router 2 端点 1:1。
from app.api.sishu_h5_links import settings_router as _sishu_h5_settings_router
app.include_router(_sishu_h5_settings_router, prefix="/api/v1/h5-settings", tags=["h5-settings"], dependencies=_sishu_deps)

# 批14深水(3/4)：imports 平台路由——vendor imports.py 2 端点 1:1（sqlite_store 1902 行
# 单件移植=vendor sqlite 会话库零漂移写径；vendor session 全包 turn_runtime 闭包=远期池不整搬）。
from app.api.sishu_imports import router as _sishu_imports_router
app.include_router(_sishu_imports_router, prefix="/api/v1/imports", tags=["imports"], dependencies=_sishu_deps)

# 批14深水(4/4)：attachments 平台路由——vendor attachments.py 1 端点 1:1
# （GET /api/attachments/{sid}/{aid}/{filename}，storage 移植包同名件承接）。
from app.api.sishu_attachments import router as _sishu_attachments_router
app.include_router(_sishu_attachments_router, prefix="/api/attachments", tags=["attachments"], dependencies=_sishu_deps)

for _r, _prefix, _tags, _deps in _dt_tutor_routers:
    if _tags and _tags[0] in _SISHU_BATCH6_UNMOUNTED:
        continue  # v4批6 6.6：七域 vendor 行摘除（平台 sishu_learning 承接同前缀）
    # 三轨M16(批10)+批11/13/14深水：knowledge/skills/subagents/partners/co_writer
    # vendor 行续服务+执法补挂（协议 F⑤——不扩造登记为主；前端消费面经 vendor 栈服务）。
    # 批11：voice 已全量换芯摘除；skills/subagents/partners/co_writer 运行时闭包直击
    # 引擎本体（orchestrator/tool_registry/builtin/skill/cron/mcp/co_writer 包/stream_bus/
    # 准入层=装配域远期池）登记远期池。imports/attachments 批14 已平台化摘除。
    # 执法=require_expert("use", sishu) 叠加 vendor 原生 _auth/_admin（deps 叠加不互替）。
    if _tags and _tags[0] in (
        "knowledge", "skills", "subagents", "partners", "co_writer",
    ):
        app.include_router(_r, prefix=_prefix, tags=_tags,
                           dependencies=[Depends(_sishu_deps[0].dependency), *(_deps or [])])
        continue
    app.include_router(_r, prefix=_prefix, tags=_tags, dependencies=_deps)
from fastapi.staticfiles import StaticFiles as _DtStaticFiles

# 批6 6.3：mother-questions/files 静态挂载平台化（vendor static_mounts 对应项跳过，
# 平台经移植 path_service 解析同一目录——与 vendor 数据零漂移）。
from app.services.sishu.services.path_service import get_path_service as _sishu_gps

for _mp, _mdir, _mname in _dt_static_mounts():
    if _mname == "mother-question-images":
        continue
    app.mount(_mp, _DtStaticFiles(directory=str(_mdir)), name=_mname)
_mq_img_dir = _sishu_gps().get_workspace_dir() / "mother_questions" / "images"
_mq_img_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/v1/mother-questions/files", _DtStaticFiles(directory=str(_mq_img_dir)),
          name="mother-question-images")

# MCP Server（业务工具标准化，deepagent 和外部 client 共用，SSE 传输 /mcp/sse）
from app.mcp_server import mount_mcp
mount_mcp(app)
