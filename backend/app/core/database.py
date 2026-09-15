from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost:33066/tupu?charset=utf8mb4",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # M01 金标准对齐（spec §五「独立 session 执行」）：commit 后不 expire，
                              # TaskWorker expunge 后 detached 实例可安全读已加载列——否则 _execute_task
                              # 首次访问 task.task_code 即 DetachedInstanceError（调度执行体从未真正跑过）
    bind=engine,
)


def ensure_schema_compatibility():
    """
    轻量级兼容迁移：为已存在旧库补齐新增字段，避免接口500。
    MySQL 版本：使用 INFORMATION_SCHEMA 替代 SQLite PRAGMA。
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "kg_source_field_imports" in table_names:
        existing_cols = {c["name"] for c in inspector.get_columns("kg_source_field_imports")}
        alter_sqls = []
        if "ref_table_en" not in existing_cols:
            alter_sqls.append("ALTER TABLE `kg_source_field_imports` ADD COLUMN `ref_table_en` VARCHAR(255)")
        if "ref_data_usage_desc" not in existing_cols:
            alter_sqls.append("ALTER TABLE `kg_source_field_imports` ADD COLUMN `ref_data_usage_desc` TEXT")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_source_field_import" in table_names and "kg_source_field_imports" in table_names:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS `kg_source_field_import`"))

    if "kg_entities" in table_names:
        entity_cols = {c["name"] for c in inspector.get_columns("kg_entities")}
        alter_sqls = []
        if "entity_en_name" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `entity_en_name` VARCHAR(255)")
        if "entity_explanation" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `entity_explanation` TEXT")
        if "sort_order" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0")
        if "source_mode" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `source_mode` VARCHAR(30) NOT NULL DEFAULT 'physical_table'")
        if "integration_sql" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `integration_sql` TEXT NULL")
        if "doris_catalog" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `doris_catalog` VARCHAR(255)")
        if "data_source_id" not in entity_cols:
            alter_sqls.append("ALTER TABLE `kg_entities` ADD COLUMN `data_source_id` VARCHAR(36) NULL")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))
        # 旧值迁移：table -> physical_table, api -> api_integration
        with engine.begin() as conn:
            conn.execute(text("UPDATE `kg_entities` SET `source_mode`='physical_table' WHERE `source_mode`='table'"))
            conn.execute(text("UPDATE `kg_entities` SET `source_mode`='api_integration' WHERE `source_mode`='api'"))

    if "kg_data_source_configs" in table_names:
        ds_cols = {c["name"] for c in inspector.get_columns("kg_data_source_configs")}
        if "doris_catalog_name" not in ds_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_data_source_configs` ADD COLUMN `doris_catalog_name` VARCHAR(255) NULL"))

    if "kg_llm_connection_configs" in table_names:
        llm_cols = {c["name"] for c in inspector.get_columns("kg_llm_connection_configs")}
        alter_sqls = []
        if "description" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `description` TEXT")
        if "api_path" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `api_path` VARCHAR(200) DEFAULT '/chat/completions'")
        if "is_default" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `is_default` TINYINT(1) NOT NULL DEFAULT 0")
        if "timeout_seconds" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `timeout_seconds` INT NOT NULL DEFAULT 60")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "skill_exec_logs" in table_names:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("skill_exec_logs")}
        if "idx_exec_logs_skill_time" not in existing_indexes:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX idx_exec_logs_skill_time ON `skill_exec_logs` (`skill_id`, `started_at`)"))

    # 批9：模板直出管道标记列（直通率/兜底率看板口径）
    if "kg_engine_query_logs" in table_names:
        _eql_cols = {c["name"] for c in inspector.get_columns("kg_engine_query_logs")}
        if "direct_pipeline" not in _eql_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_engine_query_logs` ADD COLUMN `direct_pipeline` TINYINT(1) NULL DEFAULT 0"))

    if "skill_api_bindings" not in table_names:
        create_sql = """
        CREATE TABLE `skill_api_bindings` (
            `binding_id` VARCHAR(36) PRIMARY KEY,
            `skill_id` VARCHAR(36) NOT NULL,
            `version_id` VARCHAR(36) NULL,
            `api_code` VARCHAR(100) NOT NULL,
            `api_name` VARCHAR(255) NOT NULL,
            `api_type` VARCHAR(50) NOT NULL DEFAULT 'capability',
            `provider_type` VARCHAR(50) NOT NULL DEFAULT 'internal',
            `target_ref` VARCHAR(255) NOT NULL,
            `enabled` TINYINT(1) NOT NULL DEFAULT 1,
            `timeout_seconds` INT NOT NULL DEFAULT 30,
            `retry_policy` JSON NULL,
            `auth_mode` VARCHAR(50) NULL,
            `route_config` JSON NULL,
            `remark` TEXT NULL,
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            `created_by` VARCHAR(100) NULL,
            `updated_by` VARCHAR(100) NULL,
            CONSTRAINT `uq_skill_api_binding` UNIQUE (`skill_id`, `api_code`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))
            conn.execute(text("CREATE INDEX idx_skill_api_bindings_enabled ON `skill_api_bindings` (`skill_id`, `enabled`)"))
    else:
        binding_cols = {c["name"] for c in inspector.get_columns("skill_api_bindings")}
        alter_sqls = []
        if "version_id" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `version_id` VARCHAR(36) NULL")
        if "api_code" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `api_code` VARCHAR(100) NOT NULL DEFAULT ''")
        if "api_name" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `api_name` VARCHAR(255) NOT NULL DEFAULT ''")
        if "api_type" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `api_type` VARCHAR(50) NOT NULL DEFAULT 'capability'")
        if "provider_type" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `provider_type` VARCHAR(50) NOT NULL DEFAULT 'internal'")
        if "target_ref" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `target_ref` VARCHAR(255) NOT NULL DEFAULT ''")
        if "enabled" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `enabled` TINYINT(1) NOT NULL DEFAULT 1")
        if "timeout_seconds" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `timeout_seconds` INT NOT NULL DEFAULT 30")
        if "retry_policy" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `retry_policy` JSON NULL")
        if "auth_mode" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `auth_mode` VARCHAR(50) NULL")
        if "route_config" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `route_config` JSON NULL")
        if "remark" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `remark` TEXT NULL")
        if "created_at" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP")
        if "updated_at" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        if "created_by" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `created_by` VARCHAR(100) NULL")
        if "updated_by" not in binding_cols:
            alter_sqls.append("ALTER TABLE `skill_api_bindings` ADD COLUMN `updated_by` VARCHAR(100) NULL")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("skill_api_bindings")}
        if "idx_skill_api_bindings_enabled" not in existing_indexes:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX idx_skill_api_bindings_enabled ON `skill_api_bindings` (`skill_id`, `enabled`)"))

    if "kg_dag_executions" in table_names:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("kg_dag_executions")}
        if "idx_dag_exec_workflow_time" not in existing_indexes:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX idx_dag_exec_workflow_time ON `kg_dag_executions` (`workflow_id`, `started_at`)"))

    if "kg_concepts" in table_names:
        concept_cols = {c["name"] for c in inspector.get_columns("kg_concepts")}
        alter_sqls = []
        if "sort_order" not in concept_cols:
            alter_sqls.append("ALTER TABLE `kg_concepts` ADD COLUMN `sort_order` INT NOT NULL DEFAULT 0")
        if "system_names" not in concept_cols:
            alter_sqls.append("ALTER TABLE `kg_concepts` ADD COLUMN `system_names` JSON")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_smart_skills" in table_names:
        skill_cols = {c["name"] for c in inspector.get_columns("kg_smart_skills")}
        alter_sqls = []
        if "skill_kind" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `skill_kind` VARCHAR(50) DEFAULT 'natural_language'")
        if "version" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `version` VARCHAR(50) DEFAULT 'v1'")
        if "skill_content" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `skill_content` TEXT")
        if "skill_descriptor" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `skill_descriptor` JSON")
        if "skill_type" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `skill_type` VARCHAR(100) DEFAULT 'natural'")
        if "tags" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `tags` JSON")
        if "input_schema" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `input_schema` JSON")
        if "output_schema" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `output_schema` JSON")
        if "http_config" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `http_config` JSON")
        if "dependencies" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `dependencies` JSON")
        if "updated_at" not in skill_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skills` ADD COLUMN `updated_at` DATETIME")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_smart_skill_types" not in table_names:
        create_sql = """
        CREATE TABLE `kg_smart_skill_types` (
            `id` VARCHAR(36) PRIMARY KEY,
            `type_key` VARCHAR(100) UNIQUE NOT NULL,
            `type_name` VARCHAR(255) NOT NULL,
            `icon` VARCHAR(100) DEFAULT 'fa-puzzle-piece',
            `editor_mode` VARCHAR(20) DEFAULT 'prompt',
            `default_template` TEXT,
            `description` TEXT,
            `enabled` TINYINT(1) DEFAULT 1,
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))
    else:
        type_cols = {c["name"] for c in inspector.get_columns("kg_smart_skill_types")}
        alter_sqls = []

    if "kg_entity_concept_links" not in table_names:
        create_sql = """
        CREATE TABLE `kg_entity_concept_links` (
            `id` VARCHAR(36) PRIMARY KEY,
            `entity_id` VARCHAR(36) NOT NULL,
            `concept_id` VARCHAR(36) NOT NULL,
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))
            # 迁移存量数据：将 Entity.concept_id 同步到中间表
            # 使用简单的 UUID 生成逻辑或直接插入
            migrate_sql = """
            INSERT INTO `kg_entity_concept_links` (id, entity_id, concept_id)
            SELECT UUID(), id, concept_id FROM `kg_entities`
            WHERE concept_id IS NOT NULL AND concept_id != ''
            """
            try:
                conn.execute(text(migrate_sql))
            except Exception as e:
                logger.warning(f"Migration failed (maybe UUID() not supported or empty table): {e}")

    if "kg_smart_skill_types" in table_names:
        type_cols = {c["name"] for c in inspector.get_columns("kg_smart_skill_types")}
        alter_sqls = []
        if "icon" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `icon` VARCHAR(100) DEFAULT 'fa-puzzle-piece'")
        if "editor_mode" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `editor_mode` VARCHAR(20) DEFAULT 'prompt'")
        if "default_template" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `default_template` TEXT")
        if "description" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `description` TEXT")
        if "enabled" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `enabled` TINYINT(1) DEFAULT 1")
        if "created_at" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP")
        if "updated_at" not in type_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_types` ADD COLUMN `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_entity_matrix_links" in table_names:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS `kg_entity_matrix_links`"))

    if "kg_llm_connection_configs" in table_names:
        llm_cols = {c["name"] for c in inspector.get_columns("kg_llm_connection_configs")}
        alter_sqls = []
        if "description" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `description` TEXT")
        if "api_path" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `api_path` VARCHAR(200) DEFAULT '/chat/completions'")
        if "is_default" not in llm_cols:
            alter_sqls.append("ALTER TABLE `kg_llm_connection_configs` ADD COLUMN `is_default` TINYINT(1) NOT NULL DEFAULT 0")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_smart_skill_workflows" in table_names:
        workflow_cols = {c["name"] for c in inspector.get_columns("kg_smart_skill_workflows")}
        alter_sqls = []
        if "target_menu" not in workflow_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_workflows` ADD COLUMN `target_menu` VARCHAR(50) DEFAULT 'connection'")
        if "strategy_config" not in workflow_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_skill_workflows` ADD COLUMN `strategy_config` JSON")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_smart_planner_configs" in table_names:
        planner_cols = {c["name"] for c in inspector.get_columns("kg_smart_planner_configs")}
        alter_sqls = []
        if "retrieval_mode" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `retrieval_mode` VARCHAR(20) DEFAULT 'hybrid'")
        if "vector_model_name" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `vector_model_name` VARCHAR(100) DEFAULT 'bge-large-zh-v1.5'")
        if "vector_model_path" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `vector_model_path` VARCHAR(500)")
        if "keyword_weight" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `keyword_weight` FLOAT DEFAULT 0.4")
        if "vector_weight" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `vector_weight` FLOAT DEFAULT 0.6")
        if "rerank_enabled" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `rerank_enabled` TINYINT(1) DEFAULT 1")
        if "query_entity_pipeline_code" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `query_entity_pipeline_code` VARCHAR(100) DEFAULT 'query_entity_pipeline'")
        if "query_entity_workflow_code" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `query_entity_workflow_code` VARCHAR(100) DEFAULT 'query_entity_main_workflow'")
        if "query_attribute_workflow_code" not in planner_cols:
            alter_sqls.append("ALTER TABLE `kg_smart_planner_configs` ADD COLUMN `query_attribute_workflow_code` VARCHAR(100) DEFAULT 'query_attribute_main_workflow'")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_entity_relations" in table_names:
        relation_cols = {c["name"] for c in inspector.get_columns("kg_entity_relations")}
        alter_sqls = []
        if "relation_category" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `relation_category` VARCHAR(50) DEFAULT '手工维护'")
        if "direction" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `direction` VARCHAR(20) DEFAULT 'forward'")
        if "cardinality" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `cardinality` VARCHAR(20) DEFAULT 'N:N'")
        if "source_field_name" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `source_field_name` VARCHAR(255)")
        if "target_field_name" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `target_field_name` VARCHAR(255)")
        if "join_expr" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `join_expr` TEXT")
        if "remark" not in relation_cols:
            alter_sqls.append("ALTER TABLE `kg_entity_relations` ADD COLUMN `remark` TEXT")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_metrics" in table_names:
        metric_cols = {c["name"] for c in inspector.get_columns("kg_metrics")}
        alter_sqls = []
        if "metric_level" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `metric_level` VARCHAR(32)")
        if "metric_unit" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `metric_unit` VARCHAR(64)")
        if "metric_subject" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `metric_subject` VARCHAR(128)")
        if "stat_grain" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `stat_grain` VARCHAR(32)")
        if "business_caliber" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `business_caliber` TEXT")
        if "business_owner" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `business_owner` VARCHAR(128)")
        if "business_dept" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `business_dept` VARCHAR(128)")
        if "requester_user" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `requester_user` VARCHAR(128)")
        if "tech_caliber" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `tech_caliber` TEXT")
        if "dev_owner" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `dev_owner` VARCHAR(128)")
        if "search_text" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `search_text` TEXT")
        if "similarity_threshold" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `similarity_threshold` FLOAT")
        if "manager_owner" not in metric_cols:
            alter_sqls.append("ALTER TABLE `kg_metrics` ADD COLUMN `manager_owner` VARCHAR(128)")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_metric_derived" in table_names:
        d_cols = {c["name"] for c in inspector.get_columns("kg_metric_derived")}
        alter_sqls = []
        if "config_mode" not in d_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_derived` ADD COLUMN `config_mode` VARCHAR(32) DEFAULT 'dsl'")
        if "expr_dsl" not in d_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_derived` ADD COLUMN `expr_dsl` TEXT")
        if "base_metric_id" not in d_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_derived` ADD COLUMN `base_metric_id` VARCHAR(36)")
        if "time_period" not in d_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_derived` ADD COLUMN `time_period` VARCHAR(64)")
        if "available_dims_json" not in d_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_derived` ADD COLUMN `available_dims_json` JSON")
        if "preset_filters_json" not in d_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_derived` ADD COLUMN `preset_filters_json` JSON")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_metric_query_logs" not in table_names:
        create_sql = """
        CREATE TABLE `kg_metric_query_logs` (
            `id` VARCHAR(36) PRIMARY KEY,
            `run_id` VARCHAR(36),
            `trace_id` VARCHAR(64),
            `user_query` TEXT NOT NULL,
            `intent` VARCHAR(32),
            `matched_metric_id` VARCHAR(36),
            `matched_metric_code` VARCHAR(128),
            `mql_json` JSON,
            `executed_sql` TEXT,
            `params_json` JSON,
            `data_source_id` VARCHAR(36),
            `query_status` VARCHAR(32) NOT NULL DEFAULT 'unknown',
            `error_msg` TEXT,
            `duration_ms` INT,
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))

    if "kg_metric_dim_bindings" in table_names:
        bind_cols = {c["name"] for c in inspector.get_columns("kg_metric_dim_bindings")}
        alter_sqls = []
        if "join_route_json" not in bind_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_dim_bindings` ADD COLUMN `join_route_json` JSON")
        if "join_route_status" not in bind_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_dim_bindings` ADD COLUMN `join_route_status` VARCHAR(32)")
        if "join_route_updated_at" not in bind_cols:
            alter_sqls.append("ALTER TABLE `kg_metric_dim_bindings` ADD COLUMN `join_route_updated_at` DATETIME")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "kg_smart_pipeline_step_runs" in table_names:
        step_cols = {c["name"] for c in inspector.get_columns("kg_smart_pipeline_step_runs")}
        if "logs" not in step_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_smart_pipeline_step_runs` ADD COLUMN `logs` JSON"))

    if "skills" in table_names:
        skill_cols = {c["name"] for c in inspector.get_columns("skills")}
        alter_sqls = []
        if "storage_path" not in skill_cols:
            alter_sqls.append("ALTER TABLE `skills` ADD COLUMN `storage_path` VARCHAR(500)")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "skill_exec_logs" in table_names:
        log_cols = {c["name"] for c in inspector.get_columns("skill_exec_logs")}
        alter_sqls = []
        if "is_debug" not in log_cols:
            alter_sqls.append("ALTER TABLE `skill_exec_logs` ADD COLUMN `is_debug` TINYINT(1) DEFAULT 0")
        if alter_sqls:
            with engine.begin() as conn:
                for sql in alter_sqls:
                    conn.execute(text(sql))

    if "skill_types" not in table_names:
        create_sql = """
        CREATE TABLE `skill_types` (
            `id` VARCHAR(36) PRIMARY KEY,
            `type_code` VARCHAR(50) UNIQUE NOT NULL,
            `name` VARCHAR(100) NOT NULL,
            `description` TEXT,
            `icon` VARCHAR(50),
            `color` VARCHAR(20),
            `is_active` TINYINT(1) DEFAULT 1,
            `sort_order` INT DEFAULT 0,
            `ext` VARCHAR(10),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))

    if "kg_skill_schedules" not in table_names:
        create_sql = """
        CREATE TABLE `kg_skill_schedules` (
            `id` VARCHAR(36) PRIMARY KEY,
            `schedule_code` VARCHAR(100) UNIQUE NOT NULL,
            `skill_id` VARCHAR(36) NOT NULL,
            `skill_code` VARCHAR(100) NOT NULL,
            `name` VARCHAR(255) NOT NULL,
            `cron_expression` VARCHAR(100) NOT NULL,
            `input_payload` JSON,
            `status` VARCHAR(20) DEFAULT 'active',
            `workspace_id` VARCHAR(36),
            `last_run_at` DATETIME,
            `next_run_at` DATETIME,
            `last_run_status` VARCHAR(20),
            `run_count` INT DEFAULT 0,
            `fail_count` INT DEFAULT 0,
            `created_by` VARCHAR(100),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))

    if "kg_standard_dict" not in table_names:
        create_sql = """
        CREATE TABLE `kg_standard_dict` (
            `id` VARCHAR(36) PRIMARY KEY,
            `non_standard` VARCHAR(255) NOT NULL,
            `standard` VARCHAR(255) NOT NULL,
            `category` VARCHAR(100),
            `enabled` TINYINT(1) DEFAULT 1,
            `description` VARCHAR(255),
            `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with engine.begin() as conn:
            conn.execute(text(create_sql))

    # 跨源改造：ApiEndpoint 增加 body_template（承载 ES _search 等 POST 请求体模板）
    if "kg_api_endpoints" in table_names:
        ep_cols = {c["name"] for c in inspector.get_columns("kg_api_endpoints")}
        if "body_template" not in ep_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_api_endpoints` ADD COLUMN `body_template` TEXT NULL"))
        # 数据引擎增强（批2）：API 内存缓存 TTL + 页码型分页配置
        if "cache_ttl_seconds" not in ep_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_api_endpoints` ADD COLUMN `cache_ttl_seconds` INT NOT NULL DEFAULT 300"))
        if "pagination" not in ep_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_api_endpoints` ADD COLUMN `pagination` JSON NULL"))
        # 数据引擎增强（P3）：限速/熔断 per-endpoint 运行配置
        if "run_config" not in ep_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_api_endpoints` ADD COLUMN `run_config` JSON NULL"))

    # 存量漂移修复：kg_doris_config 模型已有 database 列但旧表缺该列（Doris 配置页 GET 500）
    if "kg_doris_config" in table_names:
        cfg_cols = {c["name"] for c in inspector.get_columns("kg_doris_config")}
        if "database" not in cfg_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_doris_config` ADD COLUMN `database` VARCHAR(255) NOT NULL DEFAULT 'test_db'"))
    # 数据引擎增强（P4）：DorisCatalog 增加 es 类型字段
    if "kg_doris_catalog" in table_names:
        cat_cols = {c["name"] for c in inspector.get_columns("kg_doris_catalog")}
        if "es_hosts" not in cat_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_doris_catalog` ADD COLUMN `es_hosts` TEXT NULL"))
        if "es_user" not in cat_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_doris_catalog` ADD COLUMN `es_user` VARCHAR(255) NULL"))
        if "es_password" not in cat_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE `kg_doris_catalog` ADD COLUMN `es_password` VARCHAR(255) NULL"))

    # ④文档知识库（spec §七 Runbook 步骤1）：两表加列，幂等；存量语义等值（现网全是索引型）。
    if "kg_knowledge_base" in table_names:
        kb_cols = {c["name"] for c in inspector.get_columns("kg_knowledge_base")}
        kb_alters = []
        if "type" not in kb_cols:
            kb_alters.append("ADD COLUMN `type` VARCHAR(20) NOT NULL DEFAULT 'indexed'")
        if "rag_provider" not in kb_cols:
            kb_alters.append("ADD COLUMN `rag_provider` VARCHAR(40) NOT NULL DEFAULT 'qdrant'")
        if "pointer_params" not in kb_cols:
            kb_alters.append("ADD COLUMN `pointer_params` JSON NULL")
        if "embedding_signature" not in kb_cols:
            kb_alters.append("ADD COLUMN `embedding_signature` JSON NULL")
        if "enabled" not in kb_cols:
            kb_alters.append("ADD COLUMN `enabled` TINYINT(1) NOT NULL DEFAULT 1")
        if "version" not in kb_cols:
            kb_alters.append("ADD COLUMN `version` INT NOT NULL DEFAULT 1")
        if kb_alters:
            with engine.begin() as conn:
                for alter in kb_alters:
                    conn.execute(text(f"ALTER TABLE `kg_knowledge_base` {alter}"))

    if "kg_knowledge_document" in table_names:
        doc_cols = {c["name"] for c in inspector.get_columns("kg_knowledge_document")}
        doc_alters = []
        if "checksum" not in doc_cols:
            doc_alters.append("ADD COLUMN `checksum` VARCHAR(64) NULL")
        if "parse_cache_key" not in doc_cols:
            doc_alters.append("ADD COLUMN `parse_cache_key` VARCHAR(128) NULL")
        if "embedding_signature" not in doc_cols:
            doc_alters.append("ADD COLUMN `embedding_signature` JSON NULL")
        # ⑤批3（⑤d）：教材块结构列
        if "blocks_json" not in doc_cols:
            doc_alters.append("ADD COLUMN `blocks_json` JSON NULL")
        if doc_alters:
            with engine.begin() as conn:
                for alter in doc_alters:
                    conn.execute(text(f"ALTER TABLE `kg_knowledge_document` {alter}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
