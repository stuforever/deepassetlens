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
import json

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
    def test_syntax_指引(self, mw, qc):
        res = {"error": "syntax err", "error_class": "SYNTAX"}
        mw._inject_correction_guidance(qc, "execute_sql", res, '{"error":"syntax err","error_class":"SYNTAX"}')
        assert "validate_attributes" in res.get("correction", "")

    def test_table_missing_指引(self, mw, qc):
        res = {"error": "Table 'db.no_such' doesn't exist", "error_class": "TABLE_MISSING"}
        mw._inject_correction_guidance(qc, "execute_sql", res,
                                       '{"error":"Table \'db.no_such\' doesn\'t exist","error_class":"TABLE_MISSING"}')
        assert "search_entities" in res.get("correction", "")
        assert "no_such" in res.get("correction", "")  # 提取表名

    def test_空结果_指引(self, mw, qc):
        res = {"columns": ["a"], "rows": [], "row_count": 0}
        mw._inject_correction_guidance(qc, "execute_sql", res, '{"columns":["a"],"rows":[],"row_count":0}')
        assert "sample_column_values" in res.get("correction", "")

    def test_非数据工具不注入(self, mw, qc):
        res = {"error": "x", "error_class": "SYNTAX"}
        mw._inject_correction_guidance(qc, "search_entities", res, '{"error":"x","error_class":"SYNTAX"}')
        assert "correction" not in res

    def test_已带correction不重复(self, mw, qc):
        res = {"error": "x", "error_class": "SYNTAX", "correction": "已有指引"}
        mw._inject_correction_guidance(qc, "execute_sql", res, '{"error":"x","error_class":"SYNTAX"}')
        assert res["correction"] == "已有指引"

    def test_聚合退化_注入改写指引(self, mw):
        """S1（L2）：聚合意图下成功但明细全表 -> 注入聚合改写指引。"""
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        res = {"columns": ["cust_id", "cust_name", "voltage_name", "ctrt_cap", "run_cap", "impt_lv_name", "bus_srv_addr_name"],
               "rows": [[1] * 7, [2] * 7, [3] * 7], "row_count": 3,
               "sql": "SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust"}
        out = '{"columns":["cust_id","cust_name","voltage_name","ctrt_cap","run_cap","impt_lv_name","bus_srv_addr_name"],"rows":[[1,1,1,1,1,1,1],[2,2,2,2,2,2,2],[3,3,3,3,3,3,3]],"row_count":3,"sql":"SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust"}'
        mw._inject_correction_guidance(qc, "execute_doris_sql", res, out)
        assert "GROUP BY" in res.get("correction", "")

    def test_聚合意图_已聚合不触发(self, mw):
        """S1（L2）：SQL 含 GROUP BY -> 不误判聚合退化。"""
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        res = {"columns": ["voltage_name", "cnt"], "rows": [["承压名称1", 1]], "row_count": 1,
               "sql": "SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name"}
        out = '{"columns":["voltage_name","cnt"],"rows":[["承压名称1",1]],"row_count":1,"sql":"SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name"}'
        mw._inject_correction_guidance(qc, "execute_doris_sql", res, out)
        assert "correction" not in res

    def test_无聚合意图_明细不触发(self, mw, qc):
        """S1（L2）：无 aggregate_intent（如清单类问题）-> 明细全表不误判。"""
        res = {"columns": ["cust_id", "cust_name", "voltage_name", "ctrt_cap", "run_cap", "impt_lv_name", "bus_srv_addr_name"],
               "rows": [[1] * 7, [2] * 7, [3] * 7], "row_count": 3,
               "sql": "SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust"}
        out = '{"columns":["cust_id","cust_name","voltage_name","ctrt_cap","run_cap","impt_lv_name","bus_srv_addr_name"],"rows":[[1,1,1,1,1,1,1],[2,2,2,2,2,2,2],[3,3,3,3,3,3,3]],"row_count":3,"sql":"SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust"}'
        mw._inject_correction_guidance(qc, "execute_doris_sql", res, out)
        assert "correction" not in res

    def test_结果文本_无sql字段_sql参数兜底(self, mw):
        """S1（L2）：结果 dict 有 row_count 但无 sql 字段 -> 用 tool 参数 sql 兜底判聚合退化。"""
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        res = {"columns": ["cust_id", "cust_name", "voltage_name", "ctrt_cap", "run_cap", "impt_lv_name", "bus_srv_addr_name"],
               "rows": [[1] * 7, [2] * 7, [3] * 7], "row_count": 3}
        out = '{"columns":["cust_id","cust_name","voltage_name","ctrt_cap","run_cap","impt_lv_name","bus_srv_addr_name"],"rows":[[1,1,1,1,1,1,1],[2,2,2,2,2,2,2],[3,3,3,3,3,3,3]],"row_count":3}'
        mw._inject_correction_guidance(
            qc, "execute_doris_sql", res, out,
            sql_hint="SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust")
        assert "GROUP BY" in res.get("correction", "")

    def test_结果不可解析_已聚合不误判(self, mw):
        """S1（L2）：sql 参数含 GROUP BY -> 不判聚合退化（即使结果文本不可解析）。"""
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        res = {"row_count": 3}
        out = "{'row_count': 3}"
        mw._inject_correction_guidance(
            qc, "execute_doris_sql", res, out,
            sql_hint="SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name")
        assert "correction" not in res

    def test_result_text_dict_序列化为JSON(self):
        """S1（L2）修复：_result_text 对 dict 输出合法 JSON（G2 计数与 L2 判定依赖解析）。"""
        from app.services.skill_policy import _result_text
        import json
        s = _result_text({"row_count": 3, "sql": "SELECT 1"})
        d = json.loads(s)
        assert d["row_count"] == 3 and "SELECT 1" in d["sql"]

    def test_ToolMessage_聚合退化_前置纠错指引(self, mw):
        """S1（L2）修复：生产环境 result 为 ToolMessage（content 块列表），纠错指引前置到 content。"""
        from langchain_core.messages import ToolMessage
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        inner = json.dumps({"columns": ["cust_id", "cust_name", "voltage_name", "ctrt_cap", "run_cap", "impt_lv_name", "bus_srv_addr_name"],
                            "rows": [[1] * 7, [2] * 7, [3] * 7], "row_count": 3,
                            "sql": "SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust"}, ensure_ascii=False)
        wrapped = json.dumps({"type": "text", "text": inner}, ensure_ascii=False)
        res = ToolMessage(content=[{"type": "text", "text": wrapped}], tool_call_id="tc1")
        mw._inject_correction_guidance(qc, "execute_doris_sql", res, wrapped)
        assert "[纠错指引]" in str(res.content)
        assert "GROUP BY" in str(res.content)
        # 已前置指引不重复注入
        mw._inject_correction_guidance(qc, "execute_doris_sql", res, wrapped)
        assert str(res.content).count("[纠错指引]") == 1

    def test_被拒结果_不算聚合退化(self, mw):
        """S1（L2）：模式守卫等被拒结果（含 error 键、无 error_class）不判聚合退化。"""
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        res = {"error": "模式守卫拒绝: 请用 execute_doris_sql", "log": "blocked"}
        out = '{"error":"模式守卫拒绝: 请用 execute_doris_sql","log":"blocked"}'
        mw._inject_correction_guidance(
            qc, "execute_sql", res, out,
            sql_hint="SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust")
        assert "correction" not in res
        mw._check_controlled_degradation(qc, "execute_sql", out, _Req(),
                                         sql_hint="SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust")
        assert qc._runtime.get("corrections", 0) == 0


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

    def test_聚合退化_计入纠错闭环(self, mw):
        """S1（L2）+S2：聚合退化计入 corrections 上限；S2 起聚合退化类上限放宽到 3
        （改写聚合方差多一次机会），其他错误类仍为 2。"""
        qc = QueryContract.generic(aggregate_intent={"trigger": "分布", "required_shape": "GROUP BY"})
        agg_out = ('{"columns":["cust_id","cust_name","voltage_name","ctrt_cap","run_cap","impt_lv_name","bus_srv_addr_name"],'
                   '"rows":[[1,1,1,1,1,1,1],[2,2,2,2,2,2,2],[3,3,3,3,3,3,3]],"row_count":3,'
                   '"sql":"SELECT * FROM pg_tupu.public.dim_cst_elec_cons_cust"}')
        mw._check_controlled_degradation(qc, "execute_doris_sql", agg_out, _Req())
        assert qc._runtime["corrections"] == 1
        assert not qc.stop_reached
        # 二次触发仍计数，未超限
        mw._check_controlled_degradation(qc, "execute_doris_sql", agg_out, _Req())
        assert qc._runtime["corrections"] == 2
        assert not qc.stop_reached
        # 三次（聚合退化上限 3）仍未超限
        mw._check_controlled_degradation(qc, "execute_doris_sql", agg_out, _Req())
        assert qc._runtime["corrections"] == 3
        assert not qc.stop_reached
        # 四次 -> 超限终止（失败卡）
        mw._check_controlled_degradation(qc, "execute_doris_sql", agg_out, _Req())
        assert qc.stop_reached and "execute_doris_sql" not in qc.allowed_tools


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

        p = Path(__file__).resolve().parent.parent / "app" / "api" / "freeplan" / "endpoint.py"
        src = p.read_text(encoding="utf-8")
        assert '"correction.attempt"' in src
        assert 'elif _cname == "correction.attempt":' in src

    def test_skill_policy_常量(self):
        """纠错上限与可纠错类常量符合设计。"""
        import app.services.skill_policy as sp
        assert sp._CORRECTION_LIMIT == 2
        assert {"TABLE_MISSING", "SYNTAX", "TIMEOUT"} <= sp._CORRECTABLE_CLASSES
