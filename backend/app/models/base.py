from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, JSON, DateTime, Text, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

# 兼容老代码：从 app.models.base 也能 import SessionLocal / engine / DATABASE_URL
from app.core.database import SessionLocal, engine, DATABASE_URL  # noqa: E402,F401


def _uuid_str():
    return str(uuid.uuid4())


class Concept(Base):
    __tablename__ = "kg_concepts"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=False)
    level = Column(Integer, nullable=False)
    parent_id = Column(String(36), ForeignKey("kg_concepts.id"), nullable=True)
    area_index = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    system_names = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceMasterTable(Base):
    __tablename__ = "kg_source_master_tables"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    major = Column(String(100), nullable=True)
    deploy = Column(String(100), nullable=True)
    sysName = Column(String(100), nullable=True)
    sysCode = Column(String(100), nullable=True)
    l1 = Column(String(100), nullable=True)
    l2 = Column(String(100), nullable=True)
    enName = Column(String(255), nullable=True)
    cnName = Column(String(255), nullable=True)
    type = Column(String(100), nullable=True, default="主数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceBusinessTable(Base):
    __tablename__ = "kg_source_business_tables"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    major = Column(String(100), nullable=True)
    deploy = Column(String(100), nullable=True)
    sysName = Column(String(100), nullable=True)
    sysCode = Column(String(100), nullable=True)
    l3 = Column(String(100), nullable=True)
    l4 = Column(String(100), nullable=True)
    enName = Column(String(255), nullable=True)
    cnName = Column(String(255), nullable=True)
    type = Column(String(100), nullable=True, default="业务表")
    relL1 = Column(String(100), nullable=True)
    relL2 = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceReferenceTable(Base):
    __tablename__ = "kg_source_reference_tables"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    major = Column(String(100), nullable=True)
    deploy = Column(String(100), nullable=True)
    sysName = Column(String(100), nullable=True)
    sysCode = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    enName = Column(String(255), nullable=True)
    cnName = Column(String(255), nullable=True)
    type = Column(String(100), nullable=True, default="参考数据表")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Entity(Base):
    __tablename__ = "kg_entities"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    concept_id = Column(String(36), ForeignKey("kg_concepts.id"), nullable=False)
    entity_code = Column(String(100), unique=True, nullable=False)
    entity_name = Column(String(255), nullable=False)
    entity_en_name = Column(String(255), nullable=True)
    entity_explanation = Column(Text, nullable=True)
    properties_schema = Column(JSON, nullable=True)

    description = Column(Text, nullable=True)
    is_main_table = Column(Boolean, default=False)
    data_layer = Column(String(100), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    source_mode = Column(String(30), nullable=False, default="physical_table")  # physical_table / sql_integration / api_integration
    integration_sql = Column(Text, nullable=True)  # 模式2：多源SQL整合(Doris)的整合SQL
    doris_catalog = Column(String(255), nullable=True)  # sql_integration 使用的 Doris catalog（可选，执行前 SWITCH）
    data_source_id = Column(String(36), nullable=True)  # physical_table 模式绑定的数据源（kg_data_source_configs.id），空=用全局默认

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EntityLookupCache(Base):
    """剧本定位提速件①（2026-09-09 spec §三）：实体查找持久化历史缓存，第 84 张表。
    加速件非正确性件——读写失败一律降级直查（services/entity_lookup_cache.py）。"""
    __tablename__ = "kg_entity_lookup_cache"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    query_key = Column(String(255), unique=True, nullable=False, index=True)  # 归一化：NFKC/小写/去空白
    query_kind = Column(String(20), nullable=False)                            # keyword | entity_code
    result_json = Column(JSON, nullable=True)                                   # 与 search_entities 单查返回同构
    hit_count = Column(Integer, nullable=False, default=1)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EntityRelation(Base):
    __tablename__ = "kg_entity_relations"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    source_entity_id = Column(String(36), ForeignKey("kg_entities.id"), nullable=False)
    target_entity_id = Column(String(36), ForeignKey("kg_entities.id"), nullable=False)
    relation_name = Column(String(255), nullable=False)
    relation_category = Column(String(50), nullable=True, default="手工维护")
    direction = Column(String(20), nullable=False, default="forward")
    cardinality = Column(String(20), nullable=False, default="N:N")
    source_field_name = Column(String(255), nullable=True)
    target_field_name = Column(String(255), nullable=True)
    join_expr = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EntityConceptLink(Base):
    __tablename__ = "kg_entity_concept_links"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    entity_id = Column(String(36), ForeignKey("kg_entities.id"), nullable=False)
    concept_id = Column(String(36), ForeignKey("kg_concepts.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConceptRelation(Base):
    """概念间关系（L2-L3 跨链抽象等）"""
    __tablename__ = "kg_concept_relations"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    source_concept_id = Column(String(36), ForeignKey("kg_concepts.id"), nullable=False)
    target_concept_id = Column(String(36), ForeignKey("kg_concepts.id"), nullable=False)
    relation_type = Column(String(50), nullable=False, default="CROSS_CHAIN")
    relation_name = Column(String(255), nullable=True)
    derived_from = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceTable(Base):
    __tablename__ = "kg_source_tables"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    table_name = Column(String(255), nullable=False)
    schema_name = Column(String(255), nullable=True)
    column_metadata = Column(JSON, nullable=True)
    connection_info = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EntityMappingRule(Base):
    __tablename__ = "kg_entity_mapping_rules"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=True)
    source_table_ids = Column(JSON, nullable=False)
    entity_ids = Column(JSON, nullable=False)
    field_mappings = Column(JSON, nullable=True)
    is_advanced_sql = Column(Boolean, default=False)
    sql_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceFieldImport(Base):
    __tablename__ = "kg_source_field_imports"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    seq_no = Column(String(50), nullable=True)
    table_cn = Column(String(255), nullable=True)
    table_en = Column(String(255), nullable=True)
    sys_code = Column(String(100), nullable=True)
    table_def = Column(Text, nullable=True)
    field_cn = Column(String(255), nullable=True)
    field_en = Column(String(255), nullable=True)
    field_desc = Column(Text, nullable=True)
    data_type = Column(String(100), nullable=True)
    length_precision = Column(String(50), nullable=True)
    scale = Column(String(50), nullable=True)
    pk_fk = Column(String(100), nullable=True)
    is_ref_data = Column(String(50), nullable=True)
    ref_data_desc = Column(Text, nullable=True)
    ref_table_en = Column(String(255), nullable=True)
    ref_data_usage_desc = Column(Text, nullable=True)
    is_history = Column(String(50), nullable=True)
    mod_status = Column(String(100), nullable=True)
    mod_time = Column(String(100), nullable=True)
    mod_reason = Column(Text, nullable=True)
    app_scope = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SourceTableRelation(Base):
    __tablename__ = "kg_source_table_relations"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    relation_scope = Column(String(50), nullable=False)
    l1 = Column(String(255), nullable=True)
    l2 = Column(String(255), nullable=True)
    l3 = Column(String(255), nullable=True)
    l4 = Column(String(255), nullable=True)
    relation_desc = Column(Text, nullable=True)
    main_table_cn = Column(String(255), nullable=True)
    main_table_en = Column(String(255), nullable=False)
    related_table_cn = Column(String(255), nullable=True)
    related_table_en = Column(String(255), nullable=False)
    relation_category = Column(String(100), nullable=True)
    relation_expr = Column(Text, nullable=False)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EntityModeling(Base):
    __tablename__ = "kg_entity_modelings"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    entity_id = Column(String(36), nullable=True)
    entity_code = Column(String(255), nullable=False)
    entity_name = Column(String(255), nullable=False)
    model_target = Column(String(50), nullable=False, default="database")
    model_table_en = Column(String(255), nullable=False)
    model_table_cn = Column(String(255), nullable=True)
    model_columns = Column(JSON, nullable=True)
    model_ddl = Column(Text, nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EntityInitData(Base):
    __tablename__ = "kg_entity_init_data"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    entity_id = Column(String(36), nullable=True)
    entity_code = Column(String(255), nullable=False)
    entity_name = Column(String(255), nullable=False)
    source_table_en = Column(String(255), nullable=True)
    init_mode = Column(String(50), nullable=False, default="manual")
    init_sql = Column(Text, nullable=True)
    init_data = Column(JSON, nullable=True)
    remark = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SmartJoinReview(Base):
    __tablename__ = "kg_smart_join_reviews"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    app_type = Column(String(50), nullable=False, default="smart_join")
    intent = Column(Text, nullable=False)
    candidate_id = Column(String(100), nullable=False)
    candidate_payload = Column(JSON, nullable=True)
    confidence = Column(String(20), nullable=True)
    need_manual_review = Column(Boolean, nullable=False, default=True)
    approved = Column(Boolean, nullable=False, default=False)
    executed = Column(Boolean, nullable=False, default=False)
    execution_status = Column(String(50), nullable=True)
    execution_error = Column(Text, nullable=True)
    reviewer = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SmartSkillType(Base):
    __tablename__ = "kg_smart_skill_types"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    type_key = Column(String(100), unique=True, nullable=False)
    type_name = Column(String(255), nullable=False)
    icon = Column(String(100), nullable=True, default="fa-puzzle-piece")
    editor_mode = Column(String(20), nullable=False, default="prompt")
    default_template = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SmartSkill(Base):
    __tablename__ = "kg_smart_skills"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    skill_code = Column(String(100), unique=True, nullable=False)
    skill_name = Column(String(255), nullable=False)
    app_type = Column(String(50), nullable=False, default="smart_join")
    status = Column(String(20), nullable=False, default="draft")
    description = Column(Text, nullable=True)
    skill_type = Column(String(100), nullable=False, default="natural")
    skill_kind = Column(String(50), nullable=False, default="natural_language")
    version = Column(String(50), nullable=True, default="0.1.0")
    skill_content = Column(Text, nullable=True)
    skill_descriptor = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    target_menu = Column(String(50), nullable=True, default="connection")
    input_schema = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)
    http_config = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    runtime_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SmartSkillWorkflow(Base):
    __tablename__ = "kg_smart_skill_workflows"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    workflow_code = Column(String(100), unique=True, nullable=False)
    workflow_name = Column(String(255), nullable=False)
    app_type = Column(String(50), nullable=False, default="smart_join")
    target_menu = Column(String(50), nullable=True, default="connection")
    strategy_config = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    steps = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SmartWorkflowRun(Base):
    __tablename__ = "kg_smart_workflow_runs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    workflow_id = Column(String(36), nullable=False)
    workflow_code = Column(String(100), nullable=False)
    app_type = Column(String(50), nullable=False, default="smart_join")
    status = Column(String(20), nullable=False, default="success")
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    step_logs = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SmartPipelineRun(Base):
    __tablename__ = "kg_smart_pipeline_runs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_code = Column(String(100), unique=True, nullable=False)
    scene = Column(String(50), nullable=False, default="smart_qa")  # smart_qa | smart_connection | smart_traceability
    mode = Column(String(20), nullable=False, default="user")  # user | developer
    workflow_code = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="running")  # running | waiting_user_input | success | failed | rewound
    trace_id = Column(String(100), nullable=True)
    parent_run_id = Column(String(36), nullable=True)
    rewind_from_step_order = Column(Integer, nullable=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    context_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SmartPipelineStepRun(Base):
    __tablename__ = "kg_smart_pipeline_step_runs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_id = Column(String(36), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_code = Column(String(100), nullable=False)
    skill_code = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="success")  # running | success | failed | skipped
    confidence = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    logs = Column(JSON, nullable=True)
    next_action = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SmartPipelineRewindLog(Base):
    __tablename__ = "kg_smart_pipeline_rewind_logs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    source_run_id = Column(String(36), nullable=False)
    target_run_id = Column(String(36), nullable=False)
    rewind_to_step_order = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    operator = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMConnectionConfig(Base):
    __tablename__ = "kg_llm_connection_configs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(100), nullable=False, unique=True)
    provider = Column(String(50), nullable=False, default="openai_compatible")
    capability = Column(String(20), nullable=False, default="chat")
    description = Column(Text, nullable=True)
    base_url = Column(String(500), nullable=False)
    api_path = Column(String(200), nullable=True, default="/chat/completions")
    api_key = Column(String(500), nullable=True)
    model_name = Column(String(100), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    temperature = Column(String(20), nullable=True, default="0.2")
    max_tokens = Column(Integer, nullable=True, default=512)
    timeout_seconds = Column(Integer, nullable=False, default=60)
    extra_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SmartPlannerConfig(Base):
    __tablename__ = "kg_smart_planner_configs"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    planner_mode = Column(String(20), nullable=False, default="rule")
    llm_connection_id = Column(String(36), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    system_prompt = Column(Text, nullable=True)
    retrieval_mode = Column(String(20), nullable=False, default="hybrid")
    vector_model_name = Column(String(100), nullable=True, default="bge-large-zh-v1.5")
    vector_model_path = Column(String(500), nullable=True)
    keyword_weight = Column(Float, nullable=False, default=0.4)
    vector_weight = Column(Float, nullable=False, default=0.6)
    rerank_enabled = Column(Boolean, nullable=False, default=True)
    query_entity_pipeline_code = Column(String(100), nullable=True, default="query_entity_pipeline")
    query_entity_workflow_code = Column(String(100), nullable=True, default="query_entity_main_workflow")
    query_attribute_workflow_code = Column(String(100), nullable=True, default="query_attribute_main_workflow")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SemanticEmbedding(Base):
    __tablename__ = "kg_semantic_embeddings"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    object_type = Column(String(50), nullable=False)
    object_id = Column(String(255), nullable=False)
    text_content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
    model_name = Column(String(100), nullable=False, default="bge-large-zh-v1.5")
    content_hash = Column(String(64), nullable=False)
    extra_meta = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IntentSemanticAsset(Base):
    __tablename__ = "kg_intent_semantic_assets"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    asset_type = Column(String(50), nullable=False)
    asset_key = Column(String(100), nullable=False, default="default")
    content = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StandardSemanticTerm(Base):
    __tablename__ = "kg_standard_semantic_terms"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    term = Column(String(255), nullable=False)
    term_type = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False, default="graph_extract")
    ontology_ref_type = Column(String(50), nullable=True)
    ontology_ref_id = Column(String(255), nullable=True)
    canonical_text = Column(Text, nullable=False)
    text_payload = Column(JSON, nullable=True)
    model_name = Column(String(100), nullable=True)
    vector_dim = Column(Integer, nullable=True)
    vector_status = Column(String(20), nullable=False, default="pending")
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StandardSemanticVectorTask(Base):
    __tablename__ = "kg_standard_semantic_vector_tasks"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    task_code = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="running")
    total_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    progress = Column(Float, nullable=False, default=0.0)
    message = Column(Text, nullable=True)
    request_config = Column(JSON, nullable=True)
    task_logs = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CommonStopWord(Base):
    __tablename__ = "kg_common_stop_words"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    word = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False, default="filler")
    enabled = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StandardDict(Base):
    __tablename__ = "kg_standard_dict"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    non_standard = Column(String(255), nullable=False)
    standard = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SemanticTimeNorm(Base):
    __tablename__ = "kg_semantic_time_norm"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    word = Column(String(100), nullable=False)
    time_code = Column(String(50), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SemanticTimeCypherMap(Base):
    __tablename__ = "kg_semantic_time_cypher_map"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    time_code = Column(String(50), nullable=False, unique=True)
    cypher_expr = Column(String(500), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SemanticIntentNorm(Base):
    __tablename__ = "kg_semantic_intent_norm"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    word = Column(String(100), nullable=False, unique=True)
    standard = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SemanticExplodeNorm(Base):
    __tablename__ = "kg_semantic_explode_norm"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    phrase = Column(String(255), nullable=False, unique=True)
    agg_hint = Column(String(50), nullable=False)
    time_field = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OntologyMetric(Base):
    __tablename__ = "kg_ontology_metrics"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_name = Column(String(255), nullable=False)
    entity_name = Column(String(255), nullable=False)
    metric_code = Column(String(255), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CypherTemplate(Base):
    __tablename__ = "kg_cypher_templates"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    template_name = Column(String(255), nullable=False, unique=True)
    template_text = Column(Text, nullable=False)
    description = Column(String(500), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GraphSchema(Base):
    __tablename__ = "kg_graph_schema"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    field_name = Column(String(255), nullable=False, unique=True)
    field_type = Column(String(50), nullable=False, default="node")
    description = Column(String(500), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DataSourceConfig(Base):
    __tablename__ = "kg_data_source_configs"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=False)
    db_type = Column(String(50), nullable=False, default="mysql")
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=3306)
    database = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    doris_catalog_name = Column(String(255), nullable=True)  # 跨源联邦时 Doris catalog 名（3段命名前缀，在 Doris 配置页建好）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DorisConfig(Base):
    """Doris 连接配置（单例：表内首行为当前生效配置）"""
    __tablename__ = "kg_doris_config"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    host = Column(String(255), nullable=False, default="localhost")
    port = Column(Integer, nullable=False, default=9030)
    user = Column(String(255), nullable=False, default="root")
    password = Column(String(255), nullable=False, default="")
    database = Column(String(255), nullable=False, default="test_db")
    charset = Column(String(50), nullable=False, default="utf8mb4")
    connect_timeout = Column(Integer, nullable=False, default=10)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DorisCatalog(Base):
    """Doris Catalog 定义（jdbc/es 联邦，便于 UI 创建/编辑/重建）"""
    __tablename__ = "kg_doris_catalog"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(100), unique=True, nullable=False)
    catalog_type = Column(String(50), nullable=False, default="jdbc")   # jdbc | es | internal
    jdbc_url = Column(Text, nullable=True)
    jdbc_user = Column(String(255), nullable=True)
    jdbc_password = Column(String(255), nullable=True)
    driver_class = Column(String(255), nullable=True)
    driver_url = Column(Text, nullable=True)
    es_hosts = Column(Text, nullable=True)      # P4：ES catalog 地址（逗号分隔，如 http://host:9200）
    es_user = Column(String(255), nullable=True)
    es_password = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Metric(Base):
    __tablename__ = "kg_metrics"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_code = Column(String(128), nullable=False, unique=True)
    metric_name = Column(String(255), nullable=False)
    metric_name_en = Column(String(255), nullable=True)
    metric_type = Column(String(32), nullable=False, default="atomic")
    domain = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    metric_level = Column(String(32), nullable=True)
    metric_unit = Column(String(64), nullable=True)
    metric_subject = Column(String(128), nullable=True)
    stat_grain = Column(String(32), nullable=True)

    business_caliber = Column(Text, nullable=True)
    business_owner = Column(String(128), nullable=True)
    business_dept = Column(String(128), nullable=True)
    requester_user = Column(String(128), nullable=True)

    tech_caliber = Column(Text, nullable=True)
    dev_owner = Column(String(128), nullable=True)

    search_text = Column(Text, nullable=True)
    similarity_threshold = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="draft")
    owner_user = Column(String(128), nullable=True)
    reviewer_user = Column(String(128), nullable=True)
    manager_owner = Column(String(128), nullable=True)
    version_current = Column(Integer, nullable=False, default=1)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetricAlias(Base):
    __tablename__ = "kg_metric_aliases"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    alias = Column(String(255), nullable=False)
    alias_type = Column(String(32), nullable=False, default="synonym")
    weight = Column(Float, nullable=False, default=1.0)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetricAtom(Base):
    __tablename__ = "kg_metric_atoms"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    fact_entity_id = Column(String(36), nullable=False)
    fact_entity_name = Column(String(255), nullable=True)
    fact_table_en = Column(String(255), nullable=True)
    data_source_id = Column(String(36), nullable=True)
    agg_func = Column(String(32), nullable=False)
    measure_field_en = Column(String(255), nullable=True)
    measure_field_cn = Column(String(255), nullable=True)
    measure_data_type = Column(String(64), nullable=True)
    time_field_en = Column(String(255), nullable=False)
    time_field_cn = Column(String(255), nullable=True)
    default_limit = Column(Integer, nullable=False, default=200)
    grain_default = Column(String(32), nullable=False, default="day")
    definition_json = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetricAtomFilter(Base):
    __tablename__ = "kg_metric_atom_filters"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    atom_id = Column(String(36), ForeignKey("kg_metric_atoms.id"), nullable=False)
    field_full_name = Column(String(255), nullable=False)
    op = Column(String(32), nullable=False)
    value_json = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetricDerived(Base):
    __tablename__ = "kg_metric_derived"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    config_mode = Column(String(32), nullable=False, default="dsl")
    expr_dsl = Column(Text, nullable=True)
    base_metric_id = Column(String(36), nullable=True)
    time_period = Column(String(64), nullable=True)
    available_dims_json = Column(JSON, nullable=True)
    preset_filters_json = Column(JSON, nullable=True)
    unit = Column(String(64), nullable=True)
    precision = Column(Integer, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetricDep(Base):
    __tablename__ = "kg_metric_deps"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    dep_metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    dep_role = Column(String(32), nullable=True)


class MetricDimBinding(Base):
    __tablename__ = "kg_metric_dim_bindings"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    dim_entity_id = Column(String(36), nullable=False)
    dim_entity_name = Column(String(255), nullable=True)
    join_path_id = Column(String(36), nullable=True)
    join_route_json = Column(JSON, nullable=True)
    join_route_status = Column(String(32), nullable=True)
    join_route_updated_at = Column(DateTime(timezone=True), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)


class MetricFilterWhitelist(Base):
    __tablename__ = "kg_metric_filter_whitelist"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    field_full_name = Column(String(255), nullable=False)
    field_cn = Column(String(255), nullable=True)
    data_type = Column(String(64), nullable=True)
    op_whitelist_json = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)


class MetricVersion(Base):
    __tablename__ = "kg_metric_versions"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="published")
    snapshot_json = Column(JSON, nullable=True)
    created_by = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetricAuditLog(Base):
    __tablename__ = "kg_metric_audit_logs"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    action = Column(String(64), nullable=False)
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    operator = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MetricUsageStat(Base):
    __tablename__ = "kg_metric_usage_stats"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    metric_id = Column(String(36), ForeignKey("kg_metrics.id"), nullable=False)
    query_fingerprint = Column(String(64), nullable=False)
    hit_count = Column(Integer, nullable=False, default=0)
    last_hit_at = Column(DateTime(timezone=True), nullable=True)


class MetricQueryLog(Base):
    __tablename__ = "kg_metric_query_logs"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_id = Column(String(36), nullable=True)
    trace_id = Column(String(64), nullable=True)
    user_query = Column(Text, nullable=False)
    intent = Column(String(32), nullable=True)
    matched_metric_id = Column(String(36), nullable=True)
    matched_metric_code = Column(String(128), nullable=True)
    mql_json = Column(JSON, nullable=True)
    executed_sql = Column(Text, nullable=True)
    params_json = Column(JSON, nullable=True)
    data_source_id = Column(String(36), nullable=True)
    query_status = Column(String(32), nullable=False, default="unknown")
    error_msg = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SynonymGroup(Base):
    __tablename__ = "kg_synonym_groups"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    standard_term = Column(String(255), nullable=False)
    synonyms = Column(JSON, nullable=False)
    category = Column(String(100), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ApiEndpoint(Base):
    """多源API映射端点（DuckDB联邦查询用，配置驱动，加新API零改代码）"""
    __tablename__ = "kg_api_endpoints"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=False)                       # 中文名
    table_name = Column(String(100), unique=True, nullable=False)    # DuckDB虚拟表名(SQL里用)
    entity_id = Column(String(36), ForeignKey("kg_entities.id"), nullable=True)  # 关联实体(可空)
    api_url = Column(Text, nullable=False)                           # API URL(ES _search 或外部REST)
    method = Column(String(10), default="POST")                      # GET/POST
    params = Column(JSON, nullable=True)        # [{"name":"pspid","column":"pspid","map_to":"query"}] 过滤参数
    columns = Column(JSON, nullable=False)      # [{"name":"pspid","json_path":"pspid","type":"VARCHAR","dtype":"int64"}] 返回列
    data_path = Column(String(255), nullable=True)   # 响应JSON提取路径(如 PROJECT_DEFINITION)
    headers = Column(JSON, nullable=True)             # 请求头
    body_template = Column(Text, nullable=True)       # POST请求体模板(如ES _search的query DSL, 含match_all等)
    cache_ttl_seconds = Column(Integer, nullable=False, default=300)  # 批2：API内存缓存TTL(0=禁用)
    pagination = Column(JSON, nullable=True)          # 批2：{"page_param","size_param","page_size","max_pages"}
    run_config = Column(JSON, nullable=True)          # P3：{"rate_limit_min_interval_ms","circuit_threshold","circuit_open_seconds"}
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EntityApiMapping(Base):
    """对象API映射规则（对象层面整合多源API，对齐EntityMappingRule模式）"""
    __tablename__ = "kg_entity_api_mappings"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=True)
    entity_id = Column(String(36), ForeignKey("kg_entities.id"), nullable=False)  # 对象(主数据/业务活动)
    api_endpoint_ids = Column(JSON, nullable=False)   # API端点ID数组(引用ApiEndpoint,虚拟表资源池)
    field_mappings = Column(JSON, nullable=True)      # 属性<-API字段映射(对齐EntityMappingRule结构)
    pseudo_sql = Column(Text, nullable=False)         # 伪逻辑SQL(引用虚拟表,不含WHERE,LLM调用时动态加)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EngineQueryLog(Base):
    """引擎查询日志（批1：两引擎 execute 出口统一落库，30 天自动清理）"""
    __tablename__ = "kg_engine_query_logs"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_id = Column(String(64), nullable=True)          # 会话/请求标识
    engine = Column(String(32), nullable=False)         # duckdb | doris | sql
    sql_hash = Column(String(16), nullable=True)        # sha1 前 8 位（聚合去重用）
    sql = Column(Text, nullable=True)
    rows_returned = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, default="ok")   # ok | error
    error_class = Column(String(32), nullable=True)     # 批1 错误分类
    direct_pipeline = Column(Boolean, nullable=True, default=False)  # 批9：模板直出管道标记（直通率/兜底率看板）
    # 批13-I C4：LLM 前缀缓存观测（contextvar 桥：llm_client 探测 -> execute 出口附列）。
    # nullable：LLM 未透传缓存字段时为 NULL（降级 TTFT 基线，设计允许）。
    cache_hit_tokens = Column(Integer, nullable=True)
    cache_miss_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EngineAccelerator(Base):
    """预聚合加速器（P5：高频聚合物化到 Doris internal 表，命中拦截 + 数据截至标注）

    - 单值加速器（agg_expr 如 COUNT(*)/SUM(col)）：try_serve 对同形 SELECT 拦截改写
    - 分组加速器（agg_expr 为空）：目标表直接可查，查询命中目标表时标注 data_as_of
    """
    __tablename__ = "kg_engine_accelerators"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_tables = Column(JSON, nullable=False)        # 被覆盖源表名数组（拦截判据）
    agg_expr = Column(String(255), nullable=True)       # 单值聚合表达式（COUNT(*)/SUM(col)…），空=仅直查
    agg_col = Column(String(255), nullable=True)        # 目标表承载预聚合值的列（拦截改写 SELECT 该列）
    target_catalog = Column(String(100), nullable=False, default="internal")
    target_db = Column(String(100), nullable=False, default="test_db")
    target_table = Column(String(100), nullable=False)
    refresh_sql = Column(Text, nullable=False)          # 计算 SELECT（INSERT OVERWRITE / CREATE TABLE AS 用）
    refresh_minutes = Column(Integer, nullable=False, default=60)
    staleness_note = Column(Boolean, nullable=False, default=True)  # 结果标注「数据截至 HH:MM」
    enabled = Column(Boolean, nullable=False, default=True)
    last_refresh_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String(30), nullable=True)     # ok | error
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KgVerifiedQaExample(Base):
    """验证过的问答示例库（融合设计 §4.1 G1）。

    经用户确认/人工/金标集写入的「问题 -> 验证通过 SQL」示例；
    向量存 Qdrant 集合 tupu_qa_examples，问答时按问题 embedding 语义检索 top-3
    注入 SystemMessage（仅供构造 SQL 参考，禁止照抄执行）。schema 漂移联动置 disabled。
    """

    __tablename__ = "kg_verified_qa_examples"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    question_norm = Column(String(500), nullable=False)  # 归一化问题（复用标准语义词条管线，可为原文）
    question_raw = Column(String(500), nullable=False)   # 原始问题
    sql = Column(Text, nullable=True)                    # 验证通过的 SQL 模板
    entity_codes = Column(JSON, nullable=True)           # 涉及实体，供漂移失效联动
    route_type = Column(String(20), nullable=True)       # generic | scenario
    engine = Column(String(20), nullable=True)           # 取数引擎
    example_type = Column(String(20), nullable=True)     # user_confirmed | manual | golden
    status = Column(String(10), nullable=False, default="enabled")  # enabled | disabled | review
    hit_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KgExampleHitLog(Base):
    """G1 示例命中事件（S4：examples.injected 命中落库，供「30 天命中」统计与运营回顾）。

    每次问答把示例注入 SystemMessage 时写一行（bump_hit_count 内批量插入）；
    「30 天命中」= 近 30 天（now - interval 30 day）的行数。表由 create_all 自动建，
    命中为高频打点，只保留示例 id + 时间戳（最小列集，便于按时间聚合与清理）。
    """

    __tablename__ = "kg_example_hit_logs"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    example_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class KgGoldenQaSet(Base):
    """金标评估集（融合设计 §6.2 G6；批13-C 升级为运行时唯一锚定源）。

    「问题 -> 期望 SQL -> 结果 digest（row_count + 首行 sha1）」供 eval_golden.py
    逐条走流式问答比对结果 digest（比结果不比 SQL 文本）。
    批13-C：question 向量化入 Qdrant tupu_golden_qa（增删改同步）；运行时契约
    组装切 build_golden_payload（直通判定源 golden_hits）；example_type 灌示例库
    的旧路径移除（👍👎 改纯观测聚合，无任何自动写路径）。
    """

    __tablename__ = "kg_golden_qa_set"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    question = Column(String(500), nullable=False)
    expected_sql = Column(Text, nullable=True)                 # 期望 SQL（供参考/审计，比对以 digest 为准）
    expected_result_digest = Column(JSON, nullable=False)      # {row_count, first_row_hash}
    route_type = Column(String(32), nullable=False, default="generic")  # generic | scenario
    scenario_tag = Column(String(100), nullable=True)          # 场景标签（distribution-overload 等）
    enabled = Column(Boolean, nullable=False, default=True)
    engine = Column(String(16), nullable=True)                 # 批13-C：doris | physical | duckdb | api_integration（直通/锁引擎依据；NULL 时由 SQL 前缀推断）
    hit_count = Column(Integer, nullable=False, default=0)     # 批13-C：命中统计（注入/直通后 +1）
    last_hit_at = Column(DateTime(timezone=True), nullable=True)  # 批13-C：最近命中时间（管理页可见）
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KgFeedbackLog(Base):
    """批13-C：👍👎 观测表（重定义为纯观测信号）。

    每条反馈落一行（verdict=up|down + 原问题 + SQL 存证）；不再有任何示例库
    自动写路径（G1 upsert/审核队列移除）。候选推荐队列 = 近 N 天按 question
    聚合（up 优先、计数排序）且金标无覆盖的问题 TopM（golden_qa_service.
    list_candidate_recommendations）。
    """
    __tablename__ = "kg_feedback_logs"
    id = Column(String(36), primary_key=True, default=_uuid_str)
    run_id = Column(String(64), nullable=True, index=True)
    verdict = Column(String(8), nullable=False)                # up | down
    question = Column(String(500), nullable=True)              # 原问题存证（MetricQueryLog/EngineQueryLog 回溯）
    sql = Column(Text, nullable=True)                          # 实际执行 SQL 存证
    corrected_sql = Column(Text, nullable=True)                # 用户修正 SQL（如有）
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class GuardPolicy(Base):
    """安全控制中心：守卫策略（《安全控制中心实施设计》2.1）

    guard_id 六条基线（五类对外 + 审批轨）：
      capability / sql_safety / template / engine_lock / output / approval_track
    开关（enabled）热生效：version+1 -> TTL 5s 缓存过期 -> run_guards 下轮读到新配置。
    close_reason 红级关闭必填；risk_level 决定前端确认强度（red/yellow/green）。
    """

    __tablename__ = "guard_policies"
    guard_id = Column(String(64), primary_key=True)
    title = Column(String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    mode = Column(String(16), nullable=False, default="block")      # block|warn|log
    params = Column(JSON, nullable=True)                            # {"limit_max":500, ...}
    risk_level = Column(String(8), nullable=False, default="yellow")  # red|yellow|green
    description = Column(JSON, nullable=True)                       # {what,lose,remain} 三段式
    confirm_required = Column(Boolean, nullable=False, default=True)
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    close_reason = Column(String(500), nullable=True)               # 红级关闭必填
    version = Column(Integer, nullable=False, default=1)


class GuardEvent(Base):
    """安全控制中心：拦截/试探/变更全量事件（《安全控制中心实施设计》2.1）

    action: block|warn|pass|probe|toggle|reset；verdict: blocked|passed|probe_ok|probe_fail。
    只留 30 天（启动时清理，防止表膨胀）。
    """

    __tablename__ = "guard_events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    guard_id = Column(String(64), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    action = Column(String(16), nullable=False)                    # block|warn|pass|probe|toggle|reset
    question_digest = Column(String(200), nullable=True)           # 脱敏摘要
    verdict = Column(String(16), nullable=True)                    # blocked|passed|probe_ok|probe_fail
    detail = Column(JSON, nullable=True)
    updated_by = Column(String(64), nullable=True)


class CapabilityPolicy(Base):
    """能力开关中心：DeepAgents 能力策略（《能力开关中心与subagents受限启用设计》批13-Q 二）

    capability_id 16 行基线：14 可切（skills/filesystem_tools/memory/summarization/rubric/
    patch_tool_calls/message_eviction/response_format/store/subagents/permissions/debug/
    approval_track…）+ 4 灰显锁定（prompt_caching/video/local_shell/sandbox，
    physical_blocked=TRUE，PATCH 一律 403）。
    enabled 默认基线全开（批13-F 全量启用定调）；version 并入 agent 缓存键（装配类）或 TTL 刷新（运行时类）。
    """

    __tablename__ = "capability_policies"
    capability_id = Column(String(64), primary_key=True)
    title = Column(String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    params = Column(JSON, nullable=True)              # subagents:{specs,max_concurrent} / response_format:{schema} / store:{max_prefs}
    risk_level = Column(String(8), nullable=False, default="yellow")
    description = Column(JSON, nullable=True)         # {what,lose,remain} 三段式
    confirm_required = Column(Boolean, nullable=False, default=True)
    physical_blocked = Column(Boolean, nullable=False, default=False)  # 灰显锁定
    blocked_reason = Column(String(255), nullable=True)
    updated_by = Column(String(64), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    close_reason = Column(String(500), nullable=True)
    version = Column(Integer, nullable=False, default=1)


class CapabilityEvent(Base):
    """能力开关中心：变更/重建/探针/subagents 委派审计流（批13-Q 二）

    action: toggle|rebuild|probe|task_invoke|task_reject|spec_invalid|fallback。
    """

    __tablename__ = "capability_events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    capability_id = Column(String(64), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    action = Column(String(16), nullable=False)
    detail = Column(JSON, nullable=True)              # {actor,reason,spec_name,duration_ms,result_digest}
    updated_by = Column(String(64), nullable=True)
