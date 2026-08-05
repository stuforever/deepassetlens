"""SQLDatabase 工具 - 基于 langchain-community SQLDatabase

提供标准化的 schema 注入能力，替代手写 DESCRIBE/information_schema 查询。
供 assemble_sql / execute_sql 等 SQL 相关技能使用。

用法：
    from app.services.sql_db_helper import get_sql_database, get_table_info
    db = get_sql_database()
    info = get_table_info(db, ["kg_entity_modeling", "kg_ontology_attribute"])
"""
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

_sql_db = None


def get_sql_database():
    """获取 langchain-community SQLDatabase 单例

    复用业务数据源引擎（sql_executor._get_biz_engine，按 DataSourceConfig.db_type
    返回 PostgreSQL/MySQL），保证 schema 注入与 SQL 执行走同一业务库（实体业务
    数据已迁 PG）。避免 schema 注入连 MySQL 元数据库、执行却走 PG 的不一致。
    """
    global _sql_db
    if _sql_db is not None:
        return _sql_db

    try:
        from langchain_community.utilities import SQLDatabase
    except ImportError:
        logger.warning("langchain-community 未安装，SQLDatabase 不可用")
        return None

    try:
        from app.services.sql_executor import _get_biz_engine, _BIZ_ENGINE_CACHE
        engine = _get_biz_engine()
        _sql_db = SQLDatabase(engine=engine)
        logger.info("SQLDatabase 初始化成功（业务库: %s）", _BIZ_ENGINE_CACHE.get("source", ""))
        return _sql_db
    except Exception as e:
        logger.warning("SQLDatabase 初始化失败: %s", e)
        return None


def get_table_info(tables: Optional[List[str]] = None) -> str:
    """获取表结构信息（DDL + 样例行）

    Args:
        tables: 指定表名列表；None 则返回所有表

    Returns:
        表结构文本（CREATE TABLE 语句 + 样例行），可直接注入 prompt
    """
    db = get_sql_database()
    if db is None:
        return ""

    try:
        if tables:
            return db.get_table_info(table_names=tables)
        return db.get_context()
    except Exception as e:
        logger.warning("get_table_info 失败: %s", e)
        return ""


def run_sql(sql: str) -> str:
    """执行只读 SQL（SQLDatabase.run 自动加 LIMIT 保护）"""
    db = get_sql_database()
    if db is None:
        return ""
    try:
        return db.run(sql)
    except Exception as e:
        logger.warning("run_sql 失败: %s", e)
        return ""
