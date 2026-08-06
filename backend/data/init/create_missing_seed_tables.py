#!/usr/bin/env python3
"""Create the non-ORM tables referenced by ``mysql_init_data.sql``.

The public seed dump contains data statements for historical source tables,
while the application ORM owns only the platform tables.  This utility derives
the missing table and column names from the dump so a clean installation can
load the complete demo dataset without relying on a private database backup.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import pymysql
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
SEED_FILE = Path(__file__).with_name("mysql_init_data.sql")
INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+`(?P<table>[^`]+)`\s*\((?P<columns>[^)]*)\)\s+VALUES",
    re.IGNORECASE,
)
TABLE_RE = re.compile(
    r"(?:INSERT\s+INTO|LOCK\s+TABLES|ALTER\s+TABLE)\s+`?(?P<table>[A-Za-z0-9_]+)`?",
    re.IGNORECASE,
)

# Some historical tables are empty in the dump, but application compatibility
# migrations still require these indexed columns to exist.
EMPTY_TABLE_COLUMNS = {
    "kg_dag_executions": {
        "id": "VARCHAR(36) NULL",
        "workflow_id": "VARCHAR(36) NULL",
        "started_at": "DATETIME NULL",
    },
    "kg_dag_step_executions": {"id": "VARCHAR(36) NULL"},
    "kg_dag_workflows": {"id": "VARCHAR(36) NULL"},
    "kg_entity_source_mappings": {"id": "VARCHAR(36) NULL"},
    "kg_skill_execution_logs": {"id": "VARCHAR(36) NULL"},
}


def connection_settings() -> dict[str, object]:
    load_dotenv(BACKEND_DIR / ".env", override=False)
    raw_url = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:root@127.0.0.1:33066/tupu?charset=utf8mb4",
    )
    parsed = urlparse(raw_url.replace("mysql+pymysql://", "mysql://", 1))
    if not parsed.hostname or not parsed.path:
        raise ValueError(f"Invalid DATABASE_URL: {raw_url!r}")
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or "root"),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/"),
        "charset": "utf8mb4",
    }


def seed_layout() -> dict[str, list[str]]:
    raw_seed = SEED_FILE.read_text(encoding="utf-8")
    layout: dict[str, list[str]] = {}
    for match in INSERT_RE.finditer(raw_seed):
        table = match.group("table")
        columns = re.findall(r"`([^`]+)`", match.group("columns"))
        if not columns:
            raise ValueError(f"Cannot derive columns for seed table {table}")
        layout.setdefault(table, columns)
    for match in TABLE_RE.finditer(raw_seed):
        table = match.group("table")
        layout.setdefault(table, list(EMPTY_TABLE_COLUMNS.get(table, {"id": "LONGTEXT NULL"})))
    return layout


def quote(identifier: str) -> str:
    return "`" + identifier.replace("`", "``") + "`"


def main() -> None:
    layout = seed_layout()
    settings = connection_settings()
    with pymysql.connect(**settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            existing = {row[0] for row in cursor.fetchall()}
            missing = {table: columns for table, columns in layout.items() if table not in existing}
            for table, columns in missing.items():
                special_types = EMPTY_TABLE_COLUMNS.get(table, {})
                column_sql = ", ".join(
                    f"{quote(column)} {special_types.get(column, 'LONGTEXT NULL')}"
                    for column in columns
                )
                cursor.execute(
                    f"CREATE TABLE {quote(table)} ({column_sql}) "
                    "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
                )
        connection.commit()
    print(f"Seed schema ready: created {len(missing)} table(s).")


if __name__ == "__main__":
    main()
