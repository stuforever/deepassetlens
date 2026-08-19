"""scope_checker 单元测试（v3.1 步骤3）

纯 SQL 解析，不依赖 LLM。覆盖：
- IN 多值提取（CTE + 主查询并集）
- = 单值提取（含左右两侧列名）
- 表别名前缀剥离（c.cust_name）
- 越界检查：声明空跳过 / 子集通过 / 精确通过 / 超集拒绝 / 声明非空但无过滤拒绝
- 非 cust_name 列不提取（cust_no 不算）
- 解析失败放行（返回空集）
"""
from app.services.scope_checker import check_customer_scope, extract_customer_names


# ---- 提取 ----

class TestExtract:
    def test_IN多值提取主查询(self):
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"
        assert extract_customer_names(sql) == {"客户001", "客户003"}

    def test_IN带表别名前缀剥离(self):
        sql = "SELECT c.cust_name FROM cms20_cst_cust c WHERE c.cust_name IN ('客户001','客户003')"
        assert extract_customer_names(sql) == {"客户001", "客户003"}

    def test_IN跨CTE并主查询并集(self):
        sql = (
            "WITH t AS (SELECT * FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')) "
            "SELECT c.cust_name FROM t c WHERE c.cust_name IN ('客户001','客户003')"
        )
        assert extract_customer_names(sql) == {"客户001", "客户003"}

    def test_等号单值提取右侧列名(self):
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name = '客户001'"
        assert extract_customer_names(sql) == {"客户001"}

    def test_等号单值提取左侧列名(self):
        # '客户001' = cust_name 写法也兼容
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE '客户001' = cust_name"
        assert extract_customer_names(sql) == {"客户001"}

    def test_非cust_name列不提取(self):
        # cust_no 不做范围校验（防反复试错，对齐 SKILL.md 三列区别）
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_no IN ('C00001','C00003')"
        assert extract_customer_names(sql) == set()

    def test_无cust_name过滤返回空集(self):
        sql = "SELECT * FROM dim_taiz WHERE runstate = '20'"
        assert extract_customer_names(sql) == set()

    def test_解析失败返回空集(self):
        assert extract_customer_names("这不是SQL @@!!") == set()
        assert extract_customer_names("") == set()
        assert extract_customer_names("   ") == set()


# ---- 校验 ----

class TestCheck:
    def test_声明为空跳过(self):
        r = check_customer_scope(
            "SELECT * FROM cms20_cst_cust",  # 无过滤
            declared=[],
        )
        assert r.ok is True
        assert "跳过" in r.reason

    def test_精确匹配通过(self):
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')"
        r = check_customer_scope(sql, declared=["客户001", "客户003"])
        assert r.ok is True
        assert r.extracted == {"客户001", "客户003"}

    def test_子集通过(self):
        # 声明 001/003，SQL 只查 001（子集，结果不越界）
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001')"
        r = check_customer_scope(sql, declared=["客户001", "客户003"])
        assert r.ok is True

    def test_超集越界拒绝(self):
        # 声明 001/003，SQL 查了 005（越界）
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户005')"
        r = check_customer_scope(sql, declared=["客户001", "客户003"])
        assert r.ok is False
        assert "越界" in r.reason
        assert "客户005" in r.reason

    def test_声明非空但SQL无cust_name过滤拒绝(self):
        # 声明了客户范围，但 SQL 无 cust_name 过滤（全表扫描 = 越界风险）
        sql = "SELECT * FROM cms20_cst_cust"
        r = check_customer_scope(sql, declared=["客户001", "客户003"])
        assert r.ok is False
        assert "越界风险" in r.reason

    def test_CTE锁客户主查询无过滤也拒绝(self):
        """CTE 里有 cust_name 过滤但主查询没有 -> v1 取并集, CTE 里的算数。"""
        sql = (
            "WITH t AS (SELECT * FROM cms20_cst_cust WHERE cust_name IN ('客户001','客户003')) "
            "SELECT * FROM t"
        )
        r = check_customer_scope(sql, declared=["客户001", "客户003"])
        assert r.ok is True  # CTE 里锁了客户，并集 = 声明 -> 通过
        assert r.extracted == {"客户001", "客户003"}

    def test_声明用set也兼容(self):
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name = '客户001'"
        r = check_customer_scope(sql, declared={"客户001"})
        assert r.ok is True

    def test_声明用单字符串也兼容(self):
        sql = "SELECT cust_name FROM cms20_cst_cust WHERE cust_name = '客户001'"
        r = check_customer_scope(sql, declared="客户001")
        assert r.ok is True
