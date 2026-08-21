"""S3b（G9）追问改写 —— 纯规则检测 + 历史提取单测（生产代码 followup_rewrite.py）

验证核心场景：
1. is_followup_question：无历史不触发 / 短问题(<12 字)触发 / 指代词触发 / 长句无指代不触发
2. history_text_from_state：只取用户/助手文本，跳过工具/系统消息，取最近 N 条
"""
import pytest

from app.services.followup_rewrite import (
    is_followup_question, history_text_from_state,
)


def _mk_msg(cls: str, content):
    """每实例独立类（避免共享 __class__.__name__ 被改写），类名即 langchain 消息类型名。"""
    return type(cls, (), {"content": content, "__module__": "test_followup_rewrite"})()


def _mk_state(*msgs):
    class _State:
        values = {"messages": list(msgs)}
    return _State()


class TestIsFollowupQuestion:
    def test_无历史不触发(self):
        assert is_followup_question("那上个月呢", False) is False
        assert is_followup_question("统计用电客户总数", False) is False

    def test_空串不触发(self):
        assert is_followup_question("", True) is False
        assert is_followup_question(None, True) is False

    def test_短问题_有历史触发(self):
        assert is_followup_question("那上个月呢", True) is True
        assert is_followup_question("最大的是谁", True) is True

    def test_指代词触发(self):
        for p in ("那", "它", "上述", "该", "也", "再"):
            q = f"那{len(p) * 12}".replace("那", p)
            # 构造 12+ 字含指代词的问题（覆盖「指代词」分支而非「短问题」分支）
            long_q = f"请问{p}个维度的客户分布占比情况如何统计一下"
            assert is_followup_question(long_q, True) is True, f"{p} 应触发"

    def test_长句无指代不触发(self):
        q = "请统计一下当前所有用电客户的总数并按电压等级分组展示"
        assert is_followup_question(q, True) is False

    def test_短问题无历史不触发_有历史触发(self):
        assert is_followup_question("一共多少", False) is False
        assert is_followup_question("一共多少", True) is True


class TestHistoryTextFromState:
    def test_提取最近对话跳过工具系统(self):
        state = _mk_state(
            _mk_msg("SystemMessage", "你是问数助手"),
            _mk_msg("HumanMessage", "统计用电客户总数"),
            _mk_msg("ToolMessage", '{"rows": 3}'),
            _mk_msg("AIMessage", "当前共 3 个用电客户"),
            _mk_msg("HumanMessage", "那上个月呢"),
        )
        txt = history_text_from_state(state, tail=4)
        assert "用户: 统计用电客户总数" in txt
        assert "助手: 当前共 3 个用电客户" in txt
        assert "那上个月呢" in txt
        assert "ToolMessage" not in txt and "工具" not in txt
        assert "你是问数助手" not in txt

    def test_空状态返回空串(self):
        assert history_text_from_state(None, 4) == ""
        assert history_text_from_state(_mk_state(), 4) == ""

    def test_tail截断(self):
        state = _mk_state(
            _mk_msg("HumanMessage", "问1"),
            _mk_msg("AIMessage", "答1"),
            _mk_msg("HumanMessage", "问2"),
            _mk_msg("AIMessage", "答2"),
            _mk_msg("HumanMessage", "问3"),
        )
        txt = history_text_from_state(state, tail=2)
        # tail=2 只保留最后 2 条：答2 + 问3
        assert "问3" in txt and "答2" in txt
        assert "问1" not in txt and "答1" not in txt
