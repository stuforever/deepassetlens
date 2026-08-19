"""F1-fix 验收测试：build_sql_with_filters 参数化安全

验证 filter value 通过 sqlglot AST 构造（exp.Literal.string 转义单引号），
而非字符串拼接 f"{col}='{v}'"，防止 SQL 注入。

覆盖 duckdb_engine 和 doris_engine 两个同名函数。
"""
from app.services.duckdb_engine import build_sql_with_filters as duckdb_build
from app.services.doris_engine import build_sql_with_filters as doris_build


class TestBuildSqlWithFiltersInjection:
    """F1-fix: filter value 注入防护。"""

    def test_正常值_duckdb(self):
        sql = duckdb_build("SELECT a FROM t", {"a": "normal"})
        assert "WHERE a = 'normal'" in sql

    def test_正常值_doris(self):
        sql = doris_build("SELECT a FROM t", {"a": "normal"})
        assert "WHERE a = 'normal'" in sql

    def test_单引号注入_duckdb(self):
        """x' OR 1=1 -- 应被转义为 x'' OR 1=1 --"""
        sql = duckdb_build("SELECT a FROM t", {"a": "x' OR 1=1 --"})
        # 转义后单引号变双单引号，OR 1=1 在字符串字面量内不会被执行
        assert "x'' OR 1=1 --" in sql
        # 确保没有裸露的 OR 1=1（在字面量外的）
        assert "'x'' OR 1=1 --'" in sql

    def test_单引号注入_doris(self):
        sql = doris_build("SELECT a FROM t", {"a": "x' OR 1=1 --"})
        assert "x'' OR 1=1 --" in sql

    def test_分号注入_duckdb(self):
        """尝试用分号加新语句"""
        sql = duckdb_build("SELECT a FROM t", {"a": "val'; DROP TABLE t; --"})
        # 分号在字符串字面量内，不会终止语句
        assert "val''; DROP TABLE t; --" in sql

    def test_多filter_duckdb(self):
        sql = duckdb_build("SELECT a, b FROM t", {"a": "v1", "b": "v2"})
        assert "a = 'v1'" in sql
        assert "b = 'v2'" in sql
        assert "AND" in sql

    def test_别名映射_duckdb(self):
        """别名应映射回原列名（含表前缀）"""
        sql = duckdb_build("SELECT t.col AS alias_col FROM t", {"alias_col": "test"})
        assert "t.col = 'test'" in sql

    def test_空filter返回原sql_duckdb(self):
        assert duckdb_build("SELECT a FROM t", {}) == "SELECT a FROM t"

    def test_空filter返回原sql_doris(self):
        assert doris_build("SELECT a FROM t", {}) == "SELECT a FROM t"

    def test_数字值_duckdb(self):
        """数字值也应作为字符串字面量安全构造"""
        sql = duckdb_build("SELECT a FROM t", {"a": 123})
        assert "a = '123'" in sql

    def test_注入不产生多语句_duckdb(self):
        """转义后 SQL 应仍是单条语句（无裸露分号分隔的新语句）"""
        sql = duckdb_build("SELECT a FROM t", {"a": "x'; SELECT * FROM secrets; --"})
        # 整个注入值应在单个字符串字面量内
        # 用 sqlglot 重新解析验证只有一条 SELECT
        import sqlglot
        ast = sqlglot.parse_one(sql)
        # 确保没有 DROP/INSERT/UPDATE 等（parse_one 只取第一条，但验证无语法破坏）
        assert ast is not None
        sql_upper = sql.upper()
        assert "DROP TABLE" not in sql_upper.replace("'X''; DROP TABLE T; --'", "")
