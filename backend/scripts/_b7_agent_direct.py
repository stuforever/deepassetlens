# -*- coding: utf-8 -*-
"""⑤R E1 生产复现：ainvoke 真装配 agent（tutor），看 tool 轮是否发生。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import memory_runtime as _mr


async def main():
    from app.services.tupu_deepagent import get_tupu_agent
    agent = await get_tupu_agent(connection_id="", expert_id="tutor")
    _mr.set_runtime("tutor", "anonymous", "anon:tutor:b7direct1")
    out = await agent.ainvoke(
        {"messages": [("human", "请判分：一元二次方程 x^2-5x+6=0，我的答案是 x=2 和 x=-3，对吗？"
                                "请调用判分工具给出正式分数，错了就把这道错题录入错题本")]},
        config={"recursion_limit": 40,
                "configurable": {"thread_id": "anon:tutor:b7direct1", "checkpoint_ns": "freeplan"}},
    )
    msgs = out.get("messages", [])
    print("messages:", [m.__class__.__name__ for m in msgs])
    tool_calls_seen = []
    for m in msgs:
        tcs = getattr(m, "tool_calls", None) or []
        for tc in tcs:
            tool_calls_seen.append(tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "?"))
    print("tool_calls 全轮:", tool_calls_seen)
    last = msgs[-1]
    print("最后 content:", str(getattr(last, "content", ""))[:200])


asyncio.run(main())
