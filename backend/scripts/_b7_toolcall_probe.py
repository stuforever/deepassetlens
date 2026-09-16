# -*- coding: utf-8 -*-
"""⑤R E1 隔离探针：glm-5.3-flash + grade_answer twin 直连——tool_call 是否产生。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm_client import get_chat_model
from app.services.learning.tutor_inprocess import build_inprocess_tutor_tools

tools = {t.name: t for t in build_inprocess_tutor_tools()}
print("twin 工具:", sorted(tools))
model = get_chat_model(temperature=0.1, streaming=False, connection_id="")
bound = model.bind_tools([tools["grade_answer"]])
msgs = [("system", "你是私塾先生。判分必须调用 grade_answer 工具，绝不自评。"),
        ("human", "请判分：一元二次方程 x^2-5x+6=0，我的答案是 x=2 和 x=-3，对吗？")]
out = bound.invoke(msgs)
print("tool_calls:", [(tc.get("name"), str(tc.get("args"))[:120]) for tc in (out.tool_calls or [])])
print("content 前 200:", (out.content or "")[:200])
