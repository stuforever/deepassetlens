"""G2 自纠错闭环测试（融合设计 §4.3）。

覆盖：
  1. 纠错指引注入（ToolMessage 附加 correction 字段）：
     - SYNTAX -> validate_attributes 指引；TABLE_MISSING -> search_entities/list_tables 指引
     - 成功但 0 行 -> sample_column_values 空结果指引；非数据工具不注入
  2. 计数闸门：corrections 上限 2，超限 set_stop_reached（数据工具移除 + terminal -> 出失败卡）
  3. EXPLAIN 预检：坏表/坏列提前拦截（error_class），好 SQL / 连接异常放行
  4. correction.attempt SSE 透传（stream 白名单含该事件名）

运行方式：
    cd backend && python -m pytest tests/test_g2_self_heal.py -v
"""
import pytest

from app.services.query_contract import QueryContract
from app.services.skill_policy import SkillPolicyMiddleware


class _RT:
    config = None


class _Req:
    tool_call = {"id": "tc1", "name": "execute_sql", "args": {}}
    runtime = _RT()


@pytest.fixture
def mw():
    return SkillPolicyMiddleware()


@pytest.fixture
def qc():
    return QueryContract.generic()


class TestG2CorrectionGuidance:
    def test_syntax_指引(self, mw):
        res = {"error": "syntax err", "error_class": "SYNTAX"}
        mw._inject_correction_guidance("execute_sql", res, '{"error":"syntax err","error_class":"SYNTAX"}')
        assert "validate_attributes" in res.get("correction", "")

    def test_table_missing_指引(self, mw):
        res = {"error": "Table 'db.no_such' doesn't exist", "error_class": "TABLE_MISSING"}
        mw._inject_correction_guidance("execute_sql", res,
                                       '{"error":"Table \'db.no_such\' doesn\'t exist","error_class":"TABLE_MISSING"}')
        assert "search_entities" in res.get("correction", "")
        assert "no_such" in res.get("correction", "")  # 提取表名

    def test_空结果_指引(self, mw):
        res = {"columns": ["a"], "rows": [], "row_count": 0}
        mw._inject_correction_guidance("execute_sql", res, '{"columns":["a"],"rows":[],"row_count":0}')
        assert "sample_column_values" in res.get("correction", "")

    def test_非数据工具不注入(self, mw):
        res = {"error": "x", "error_class": "SYNTAX"}
        mw._inject_correction_guidance("search_entities", res, '{"error":"x","error_class":"SYNTAX"}')
        assert "correction" not in res

    def test_已带correction不重复(self, mw):
        res = {"error": "x", "error_class": "SYNTAX", "correction": "已有指引"}
        mw._inject_correction_guidance("execute_sql", res, '{"error":"x","error_class":"SYNTAX"}')
        assert res["correction"] == "已有指引"


class TestG2CorrectionGate:
    def test_计数递增(self, mw, qc):
        mw._check_controlled_degradation(qc, "execute_sql", '{"error":"x","error_class":"SYNTAX"}', _Req())
        assert qc._runtime["corrections"] == 1
        mw._check_controlled_degradation(qc, "execute_sql", '{"error":"x","error_class":"SYNTAX"}', _Req())
        assert qc._runtime["corrections"] == 2
        assert not qc.stop_reached  # 未超限

    def test_超限终止(self, mw, qc):
        for _ in range(3):
            mw._check_controlled_degradation(qc, "execute_sql", '{"error":"x","error_class":"SYNTAX"}', _Req())
        assert qc._runtime["corrections"] == 3
        assert qc.stop_reached and qc._runtime.get("terminal")
        assert "execute_sql" not in qc.allowed_tools  # 数据工具被移除 -> 出失败卡
        assert "execute_doris_sql" not in qc.allowed_tools

    def test_非可纠错类不计数(self, mw, qc):
        mw._check_controlled_degradation(qc, "execute_sql", '{"error":"x","error_class":"AUTH"}', _Req())
        assert qc._runtime.get("corrections", 0) == 0

    def test_非数据工具不计(self, mw, qc):
        mw._check_controlled_degradation(qc, "search_entities", '{"error":"x","error_class":"SYNTAX"}', _Req())
        assert qc._runtime.get("corrections", 0) == 0


class TestG2ExplainPrecheck:
    @staticmethod
    def _bad_table(sql):
        raise Exception('(psycopg2.errors.UndefinedTable) relation "no_such" does not exist')

    @staticmethod
    def _bad_col(sql):
        return {"error": 'column "badcol" does not exist', "error_class": "TABLE_MISSING",
                "columns": [], "rows": []}

    @staticmethod
    def _ok(sql):
        return {"columns": ["QUERY PLAN"], "rows": [["Seq Scan"]], "row_count": 1}

    @staticmethod
    def _conn_err(sql):
        raise Exception("could not connect to server")

    def test_坏表提前拦截(self):
        from app.services.kg_action_handlers import _explain_precheck
        r = _explain_precheck(self._bad_table, "SELECT 1 FROM no_such", "00:00:00")
        assert r is not None and r.get("error_class") == "TABLE_MISSING"

    def test_坏列提前拦截(self):
        from app.services.kg_action_handlers import _explain_precheck
        r = _explain_precheck(self._bad_col, "SELECT badcol FROM t", "00:00:00")
        assert r is not None and r.get("error_class") == "TABLE_MISSING"

    def test_好SQL放行(self):
        from app.services.kg_action_handlers import _explain_precheck
        assert _explain_precheck(self._ok, "SELECT 1", "00:00:00") is None

    def test_连接异常放行(self):
        from app.services.kg_action_handlers import _explain_precheck
        assert _explain_precheck(self._conn_err, "SELECT 1", "00:00:00") is None


class TestG2SSEWiring:
    def test_stream透传白名单含correction_attempt(self):
        """stream 自定义事件白名单含 correction.attempt（SSE 实时可见）。"""
        from pathlib import Path

        p = Path(__file__).resolve().parent.parent / "app" / "api" / "data_intelligence_stream.py"
        src = p.read_text(encoding="utf-8")
        assert '"correction.attempt"' in src
        assert 'elif _cname == "correction.attempt":' in src

    def test_skill_policy_常量(self):
        """纠错上限与可纠错类常量符合设计。"""
        import app.services.skill_policy as sp
        assert sp._CORRECTION_LIMIT == 2
        assert {"TABLE_MISSING", "SYNTAX", "TIMEOUT"} <= sp._CORRECTABLE_CLASSES
