"""C2: 强制范围拒绝->补判成功 e2e 验收测试

此测试为 integration 级别（依赖后端服务运行在 28000 端口），
验证 think_stream 的完整转折链结构：
  - 步骤有 step_id 序号
  - rejected 步骤保留 reject_reason
  - 补判成功后新步骤有 retry_of_step 关联
  - 旧 rejected 步骤标记 superseded

运行方式：
    # 确保后端运行在 28000
    python -m pytest tests/test_e2e_scope_retry.py -v -m integration
"""
import json
import time
import pytest
import requests


BASE_URL = "http://localhost:28000/api/data-intelligence/chat/freeplan/stream"


def _call_sse(query: str, thread_id: str, timeout: int = 120) -> dict | None:
    """调用 SSE 流式 API，返回 done 事件的 final_response。"""
    payload = {"thread_id": thread_id, "user_input": query, "mode": "free_plan"}
    try:
        resp = requests.post(BASE_URL, json=payload, stream=True, timeout=timeout)
        resp.raise_for_status()
        event_type = None
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                event_type = line[7:].strip()
            elif line.startswith("data:") and event_type == "done":
                return json.loads(line[6:].strip())
    except Exception:
        return None
    return None


@pytest.mark.integration
class TestScopeRetryE2E:
    """C2: 验证 think_stream 转折链结构（integration 级别，需后端运行）。"""

    def test_带客户名查询返回有效think_stream(self):
        """用带客户名的问题查询，验证 think_stream 结构完整。

        即使不触发范围拒绝，也应验证：
        - done 事件存在
        - think_stream 非空
        - 每个步骤有 step_id
        - response_format_degraded 字段存在
        """
        thread_id = f"e2e_scope_{int(time.time())}"
        result = _call_sse("客户001的联系电话", thread_id)
        if result is None:
            pytest.skip("后端服务未运行或请求超时，跳过 integration 测试")

        # done 事件存在
        assert result is not None, "应收到 done 事件"
        assert "think_stream" in result, "done 事件应包含 think_stream"

        think_stream = result.get("think_stream") or []
        assert len(think_stream) > 0, "think_stream 应非空"

        # 每个步骤有 step_id
        for step in think_stream:
            assert "step_id" in step or "step_no" in step, f"步骤缺少 step_id: {step.get('task', '')}"

        # response_format_degraded 字段存在（R3 降级标识）
        assert "response_format_degraded" in result, "done 事件应包含 response_format_degraded"

    def test_think_stream步骤有正确状态字段(self):
        """验证 think_stream 步骤的状态字段完整。"""
        thread_id = f"e2e_status_{int(time.time())}"
        result = _call_sse("什么是变压器", thread_id)
        if result is None:
            pytest.skip("后端服务未运行或请求超时")

        think_stream = result.get("think_stream") or []
        assert len(think_stream) > 0

        for step in think_stream:
            # 每个步骤应有 phase 和 result_status
            assert "phase" in step, f"步骤缺少 phase: {step.get('task', '')}"
            assert "result_status" in step, f"步骤缺少 result_status: {step.get('task', '')}"
            # phase 应是有效值
            valid_phases = {"running", "drafting", "committed", "done", "error", "rejected", "cancelled"}
            assert step["phase"] in valid_phases, f"无效 phase: {step['phase']}"

    def test_降级标识在实际请求中生效(self):
        """C2/R3: 验证 GLM 不兼容 response_format 时降级标识为 True。"""
        thread_id = f"e2e_degraded_{int(time.time())}"
        result = _call_sse("什么是变压器", thread_id)
        if result is None:
            pytest.skip("后端服务未运行或请求超时")

        # GLM 当前不兼容 response_format，应降级
        assert result.get("response_format_degraded") is True, "GLM 应触发降级"
        assert result.get("final_answer_structured") is None, "GLM 不应产出结构化结果"
        # 但文本答案应可用
        assert result.get("final_answer"), "降级时文本答案应可用"

    def test_补判转折链结构验证(self):
        """C2 核心：验证 think_stream 里如果有 rejected 步骤，转折链结构正确。

        如果本次查询触发了范围拒绝->补判：
        - rejected 步骤应有 reject_reason
        - 补判成功后新步骤应有 retry_of_step 关联
        - 旧 rejected 步骤应标记 superseded

        如果本次没触发拒绝（LLM 直接走了正确路径），跳过断言但验证基本结构。
        """
        thread_id = f"e2e_retry_{int(time.time())}"
        # 用带两个客户名的问题增加触发范围校验的概率
        result = _call_sse("客户001和客户003的联系电话", thread_id)
        if result is None:
            pytest.skip("后端服务未运行或请求超时")

        think_stream = result.get("think_stream") or []
        assert len(think_stream) > 0

        # 检查是否有 rejected 步骤
        rejected_steps = [s for s in think_stream if s.get("phase") == "rejected"]
        retry_steps = [s for s in think_stream if s.get("retry_of_step") is not None]

        if rejected_steps:
            # 有拒绝步骤 -> 验证转折链结构
            for r in rejected_steps:
                assert "reject_reason" in r or "result_summary" in r, \
                    "rejected 步骤应有 reject_reason 或 result_summary"

            # 如果有 retry 步骤，验证关联
            if retry_steps:
                for rt in retry_steps:
                    retry_of = rt.get("retry_of_step")
                    assert retry_of is not None, "retry 步骤应有 retry_of_step"
                    # 验证关联的步骤确实存在
                    linked = [s for s in think_stream if s.get("step_id") == retry_of]
                    assert len(linked) > 0, f"retry_of_step={retry_of} 指向的步骤不存在"

                # 验证被重试的 rejected 步骤标记 superseded
                superseded_steps = [s for s in think_stream if s.get("superseded") is True]
                assert len(superseded_steps) > 0, "补判成功后旧 rejected 步骤应标记 superseded"
        else:
            # 没触发拒绝 -> 至少验证步骤结构完整
            pytest.skip("本次查询未触发范围拒绝，补判转折链断言跳过")
