# -*- coding: utf-8 -*-
"""S2 金标扩容测试：歧义澄清触发 + 容忍式 digest 匹配 + 澄清口径 eval 支持。

覆盖：skill_router.detect_vague_intent（纯规则）/
QueryContract.generic(clarify_required=True) 工具集收缩 /
_build_contract_system_message 澄清指令 / eval_golden.digest_matches 列顺序容忍 /
澄清金标判定（route.clarification 事件 + 无 sql_result 即 pass）。
"""
import importlib.util
from pathlib import Path

from app.api.data_intelligence import _build_contract_system_message
from app.services.query_contract import QueryContract
from app.services.skill_router import SkillRouter


def _load_eval():
    p = Path(__file__).resolve().parent.parent / "scripts" / "eval_golden.py"
    spec = importlib.util.spec_from_file_location("eval_golden_mod", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestVagueIntent:
    """S2 澄清层：歧义提问须触发澄清而非乱查（纯规则，不打模型）。"""

    def test_客户情况_触发澄清(self):
        assert SkillRouter.detect_vague_intent("客户情况") is True

    def test_分析一下用电客户_触发澄清(self):
        assert SkillRouter.detect_vague_intent("分析一下用电客户") is True

    def test_给我看看数据_触发澄清(self):
        assert SkillRouter.detect_vague_intent("给我看看数据") is True

    def test_统计计数_不触发(self):
        assert SkillRouter.detect_vague_intent("统计一下当前有多少用电客户") is False
        assert SkillRouter.detect_vague_intent("用电客户总数是多少") is False

    def test_聚合分布_不触发(self):
        assert SkillRouter.detect_vague_intent("各电压等级的用电客户分布是怎样的") is False

    def test_过滤与TopN_不触发(self):
        assert SkillRouter.detect_vague_intent("合同容量大于5000的用电客户") is False
        assert SkillRouter.detect_vague_intent("容量最大的用电客户是谁") is False


class TestClarifyContract:
    """S2 澄清契约：clarify_required -> 工具集收缩为空 + 系统消息含澄清指令。"""

    def test_工具集收缩为空(self):
        c = QueryContract.generic(clarify_required=True)
        assert c.allowed_tools == []
        assert c.clarify_required is True

    def test_普通generic_工具集完整(self):
        c = QueryContract.generic()
        assert c.allowed_tools != [] and c.clarify_required is False

    def test_系统消息含澄清指令(self):
        c = QueryContract.generic(clarify_required=True)
        msg = _build_contract_system_message(c)
        assert "意图不明确" in msg and "澄清" in msg and "禁止执行任何数据查询" in msg


class TestTolerantDigestMatch:
    """S2 容忍式 digest：明细/过滤列选择抖动 -> row_count + 首元素即对；聚合仍按首元素区分。"""

    def _load(self):
        return _load_eval()

    def test_列顺序抖动_算对(self):
        m = self._load()
        exp = {"row_count": 3, "first_row": ["CUS0001", "用电客户名称1", "承压名称1", 6024.82, 8916.77, "重要性等级名称1", "业务服务地址名称1"]}
        # agent 列选择不同（cust_no 前置、列集略异）但首元素同为 CUS0001、行数同为 3
        got = {"row_count": 3, "first_row": ["CUS0001", "CU-0001", "用电客户名称1", "承压名称1", 6024.82, 8916.77]}
        assert m.digest_matches(got, exp) is True

    def test_聚合仍按首元素区分明细(self):
        m = self._load()
        exp = {"row_count": 3, "first_row": ["承压名称1", 1]}
        got_agg = {"row_count": 3, "first_row": ["承压名称1", 1]}
        got_detail = {"row_count": 3, "first_row": ["CUS0001", "用电客户名称1", "承压名称1"]}
        assert m.digest_matches(got_agg, exp) is True
        assert m.digest_matches(got_detail, exp) is False  # 明细首元素=CUS0001 != 维度值 -> 仍判失败

    def test_行数不同_算错(self):
        m = self._load()
        exp = {"row_count": 3, "first_row": ["CUS0001", "用电客户名称1"]}
        got = {"row_count": 2, "first_row": ["CUS0001", "用电客户名称1"]}
        assert m.digest_matches(got, exp) is False

    def test_标量宽松_保持(self):
        m = self._load()
        exp = {"row_count": 1, "first_row": [3]}
        got = {"row_count": 3, "first_row": ["CUS0001", "用电客户名称1", "承压名称1"]}
        assert m.digest_matches(got, exp) is True
