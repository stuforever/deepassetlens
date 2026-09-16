# -*- coding: utf-8 -*-
"""⑤R E1 图内二分：裸 deepagents + 逐件加回，定位 tool_call 丢失层。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm_client import get_chat_model
from app.services.learning.tutor_inprocess import build_inprocess_tutor_tools
from app.core.database import SessionLocal
from app.models.base import ExpertProfile

db = SessionLocal()
r = db.query(ExpertProfile).filter(ExpertProfile.expert_id == "tutor").first()
sp = r.system_prompt or ""
db.close()

TOOLS = build_inprocess_tutor_tools()
MODEL = get_chat_model(temperature=0.1, streaming=True, connection_id="")
Q = "请判分：一元二次方程 x^2-5x+6=0，我的答案是 x=2 和 x=-3，对吗？请调用判分工具给出正式分数"


async def run(tag: str, **kw):
    from deepagents import create_deep_agent
    agent = create_deep_agent(model=MODEL, tools=list(TOOLS), system_prompt=sp, **kw)
    out = await agent.ainvoke({"messages": [("human", Q)]})
    msgs = out.get("messages", [])
    kinds = [m.__class__.__name__ for m in msgs]
    tool_msgs = [m for m in msgs if m.__class__.__name__ == "ToolMessage"]
    last = msgs[-1] if msgs else None
    print(f"[{tag}] messages={kinds}")
    print(f"[{tag}] ToolMessage 数={len(tool_msgs)} 最后content={str(getattr(last, 'content', ''))[:80]!r}")


async def main():
    await run("A 裸图")
    from langgraph.checkpoint.memory import MemorySaver
    await run("B +checkpointer", checkpointer=MemorySaver())
    from app.services.skill_policy import SkillPolicyMiddleware
    await run("C +SkillPolicy", middleware=[SkillPolicyMiddleware(allow_missing_contract=True)])


asyncio.run(main())
