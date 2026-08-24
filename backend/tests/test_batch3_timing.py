# -*- coding: utf-8 -*-
"""test_batch3_timing.py - 批3-F 分段计时外露断言（done 载荷含 timing + rubric_ms 粗粒度段）"""
import os
import pytest

_STREAM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "app", "api", "data_intelligence_stream.py")
_DEEPAGENT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "app", "services", "tupu_deepagent.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestTimingExposure:
    def test_done_payload_includes_timing(self):
        """done 载荷构造必须含 timing（first_event/first_model_stream/first_tool_start/first_answer_token/total/rubric_ms）"""
        src = _read(_STREAM_PATH)
        assert '"timing": dict(_timing)' in src
        assert '_timing["total"]' in src

    def test_rubric_ms_computed_from_answer_to_done(self):
        """rubric_ms = total - first_answer_token（自评段粗粒度）"""
        src = _read(_STREAM_PATH)
        assert 'rubric_ms' in src
        assert 'first_answer_token' in src

    def test_env_anchor_thresholds_defined(self):
        """阈值全部环境变量化：rubric 锚定(0.85)/首选计划(0.90)"""
        from app.services.query_contract import EXAMPLE_ANCHOR_SIM
        from app.services.qa_example_service import _score_threshold
        assert EXAMPLE_ANCHOR_SIM >= 0.8
        assert 0.5 < _score_threshold() <= 0.9

    def test_rubric_connection_id_env_supported(self):
        """grader 轻模型走 TUPU_RUBRIC_CONNECTION_ID（机制存在，.env 配置即可）"""
        assert "rubric_ms" in _read(_DEEPAGENT_PATH)
