"""SecureQueryExecutor 单测：AST 级 SQL 安全校验。

验证：只读语句放行、DDL/DML 拦截、副作用函数拦截、强制 LIMIT、多语句拦截。
"""
import pytest
from app.services.secure_query_executor import validate_sql, SqlCheck


class TestReadOnlyEnforcement:
    """只允许 SELECT / WITH ... SELECT。"""

    def test_select_passes(self):
        chk = validate_sql("SELECT * FROM cms20_cst_cust")
        assert chk.ok, f"SELECT 被拒: {chk.reason}"

    def test_with_select_passes(self):
        chk = validate_sql("WITH t AS (SELECT 1) SELECT * FROM t")
        assert chk.ok, f"WITH SELECT 被拒: {chk.reason}"

    @pytest.mark.parametrize("ddl", [
        "DROP TABLE cms20_cst_cust",
        "DELETE FROM cms20_cst_cust WHERE 1=1",
        "UPDATE cms20_cst_cust SET cust_name='x'",
        "INSERT INTO cms20_cst_cust VALUES (1)",
        "ALTER TABLE cms20_cst_cust ADD COLUMN x int",
        "TRUNCATE TABLE cms20_cst_cust",
        "CREATE TABLE evil (id int)",
    ])
    def test_ddl_dml_blocked(self, ddl):
        chk = validate_sql(ddl)
        assert not chk.ok, f"危险语句未被拦截: {ddl}"

    def test_multi_statement_blocked(self):
        chk = validate_sql("SELECT 1; DROP TABLE x")
        assert not chk.ok, "多语句未被拦截"


class TestForbiddenFunctions:
    """禁止副作用函数。"""

    @pytest.mark.parametrize("sql", [
        "SELECT sleep(5)",
        "SELECT benchmark(1000000, md5('x'))",
        "SELECT load_file('/etc/passwd')",
    ])
    def test_forbidden_func_blocked(self, sql):
        chk = validate_sql(sql)
        assert not chk.ok, f"副作用函数未被拦截: {sql}"


class TestForceLimit:
    """无 LIMIT 自动追加，超限 LIMIT 被改写。"""

    def test_no_limit_gets_limit(self):
        chk = validate_sql("SELECT * FROM cms20_cst_cust")
        assert chk.ok
        assert "LIMIT" in chk.sql.upper(), f"未追加 LIMIT: {chk.sql}"

    def test_limit_within_bounds_kept(self):
        chk = validate_sql("SELECT * FROM cms20_cst_cust LIMIT 10")
        assert chk.ok
        assert "10" in chk.sql

    def test_limit_over_max_capped(self):
        chk = validate_sql("SELECT * FROM cms20_cst_cust LIMIT 99999", max_limit=500)
        assert chk.ok
        assert "500" in chk.sql, f"超大 LIMIT 未被改写: {chk.sql}"
        assert "99999" not in chk.sql


class TestTableWhitelist:
    """表白名单校验。"""

    def test_allowed_table_passes(self):
        chk = validate_sql("SELECT * FROM cms20_cst_cust", allowed_tables={"cms20_cst_cust"})
        assert chk.ok

    def test_non_whitelisted_table_blocked(self):
        chk = validate_sql("SELECT * FROM secret_table", allowed_tables={"cms20_cst_cust"})
        assert not chk.ok, "非白名单表未被拦截"

    def test_catalog_qualified_table_matches(self):
        # pg_tupu.public.cms20_cst_cust -> 归一化为 cms20_cst_cust 比对
        chk = validate_sql(
            "SELECT * FROM pg_tupu.public.cms20_cst_cust",
            allowed_tables={"cms20_cst_cust"},
        )
        assert chk.ok, f"三段命名表未匹配白名单: {chk.reason}"
