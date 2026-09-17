# -*- coding: utf-8 -*-
"""mastery 兜底链直诊：astream_events + aget_state（同桥参数）。"""
import asyncio, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def main():
    from app.services.tupu_deepagent import get_tupu_agent
    from app.services.expert_paths import thread_id
    from langchain_core.messages import HumanMessage

    agent = await get_tupu_agent(connection_id="", expert_id="tutor")
    sid = "diag-mastery-1"
    tid = thread_id("anonymous", "tutor", sid)
    config = {"configurable": {"thread_id": tid, "checkpoint_ns": "bridge"}, "recursion_limit": 80}
    directive = ("[mastery 模式]\n你是精通路径导师。基于已检索到的学情数据（见上）规划学习："
                 "先报当前状态，再给下一步。硬门：未经评测不得直接给答案。\n\n"
                 "[学情数据]\n{\"due_count\": 3, \"wrong_open\": 2}\n\n我现在的学情怎么样")
    st_acc = []
    content = []
    async for ev in agent.astream_events({"messages": [HumanMessage(content=directive)]},
                                         config=config, version="v2"):
        t = ev.get("event", "")
        if t == "on_chat_model_stream":
            chunk = ev.get("data", {}).get("chunk")
            c = getattr(chunk, "content", "") if chunk else ""
            rk = (getattr(chunk, "additional_kwargs", {}) or {}).get("reasoning_content")
            if rk:
                st_acc.append(rk)
            elif isinstance(c, str) and c:
                content.append(c)
        elif t == "on_tool_start":
            print("TOOL_START:", ev.get("name"), str(ev.get("data", {}).get("input"))[:120])
    print("content 合计:", sum(len(x) for x in content), "尾:", "".join(content)[-100:])
    print("thinking 合计:", sum(len(x) for x in st_acc))
    st = await agent.aget_state(config)
    vals = (st.values or {}) if st else {}
    print("state keys:", list(vals.keys())[:12])
    sr = vals.get("structured_response")
    print("structured_response:", json.dumps(sr, ensure_ascii=False, default=str)[:400] if sr else sr)
    msgs = vals.get("messages") or []
    if msgs:
        last = msgs[-1]
        print("last msg type:", type(last).__name__)
        print("last content 头:", str(getattr(last, 'content', ''))[:200])
        tcs = getattr(last, "tool_calls", None)
        if tcs:
            print("last tool_calls:", [(tc.get("name"), str(tc.get("args"))[:100]) for tc in tcs])

asyncio.run(main())
