# -*- coding: utf-8 -*-
"""引擎批1 冒烟：桥端点 SSE 消费断言（L6 tutor_chat.md TC1-TC5）。
串行执行；PYTHONUTF8=1。exit 0=全过。"""
import json
import sys
import time

import requests

BASE = "http://127.0.0.1:28000"
URL = f"{BASE}/api/v2/skills/capability"

failures = []


def stream(req_body, timeout=180):
    """消费 SSE 流→事件列表（event 名+data dict）。"""
    evs = []
    with requests.post(URL, json=req_body, stream=True, timeout=timeout) as r:
        cur_event = None
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip("\r")
            if line.startswith("event:"):
                cur_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                try:
                    data = json.loads(line.split(":", 1)[1].strip())
                except Exception:
                    data = {"raw": line}
                evs.append((cur_event, data))
    return evs


def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name} {detail}")
    if not cond:
        failures.append(name)


def types_of(evs):
    return [e for e, _ in evs]


# TC1 多轮对话
t0 = time.time()
evs = stream({"skill_code": "tutor/chat", "message": "你好，用一句话自我介绍"})
ty = types_of(evs)
check("TC1 session_meta 首帧", ty[:1] == ["session_meta"], f"types={ty[:6]}")
sm = evs[0][1] if evs else {}
check("TC1 session/turn id 回传", bool(sm.get("session_id")) and bool(sm.get("turn_id")),
      f"session={sm.get('session_id')} turn={sm.get('turn_id')}")
check("TC1 stage 序", "stage_start" in ty and "stage_end" in ty)
contents = [d.get("content", "") for e, d in evs if e == "content"]
full = "".join(contents)
check("TC1 content 流非空", len(full) > 5, f"len={len(full)}")
res = next((d for e, d in evs if e == "result"), {})
check("TC1 result=拼接一致", res.get("content", "") == full)
done = next((d for e, d in evs if e == "done"), {})
check("TC1 done ok=true", done.get("metadata", {}).get("ok") is True)
check("TC1 耗时<150s", time.time() - t0 < 150)

# TC1b 同 session 第二轮（记忆线程）
sid = sm.get("session_id")
evs_b = stream({"skill_code": "tutor/chat", "message": "我上一句话问了你什么？",
                "session_id": sid})
ty_b = types_of(evs_b)
check("TC1b 复用 session 同 id 回传", evs_b and evs_b[0][1].get("session_id") == sid)
check("TC1b 第二轮 result 非空", any(e == "result" and d.get("content") for e, d in evs_b))

# TC2 工具调用 web_search
evs2 = stream({"skill_code": "tutor/chat", "message": "搜索 DeepTutor 项目简介",
               "tools": ["web_search"]})
ty2 = types_of(evs2)
check("TC2 tool_call(web_search) 在序列", "tool_call" in ty2)
tc2_call = next((d for e, d in evs2 if e == "tool_call"), {})
check("TC2 tool_call name=web_search", tc2_call.get("metadata", {}).get("name") == "web_search")
i_call = ty2.index("tool_call") if "tool_call" in ty2 else -1
i_res = ty2.index("tool_result") if "tool_result" in ty2 else -1
check("TC2 tool_call 先于 tool_result", 0 <= i_call < i_res)
tc2_res = next((d for e, d in evs2 if e == "tool_result"), {})
check("TC2 tool_result ref", tc2_res.get("metadata", {}).get("ref") == "tool://web_search")
check("TC2 pre_retrieval 如实标记", tc2_call.get("metadata", {}).get("pre_retrieval") is True)

# TC3 KB 引用（取平台任一 KB id）
try:
    kbs = requests.get(f"{BASE}/api/v1/knowledge-bases", timeout=15).json()
    rows = (kbs.get("data") if isinstance(kbs, dict) else kbs) or []
    # 择库：优先 L6 测试库（残留空壳库 collection 已失——kb_query 404 零命中）
    kb_id = next((k.get("id") for k in rows if isinstance(k, dict)
                  and k.get("name") == "引擎批1-L6测试库"), "")
except Exception as e:
    kb_id = ""
    print(f"[WARN] KB 列表获取失败: {e}")
if kb_id:
    evs3 = stream({"skill_code": "tutor/chat",
                   "message": "知识库里有哪些内容？概括一两条",
                   "knowledge_bases": [kb_id]})
    ty3 = types_of(evs3)
    check("TC3 sources 事件", "sources" in ty3)
    se3 = next((d for e, d in evs3 if e == "stage_end" and d.get("stage") == "prepare"), {})
    check("TC3 kb_block=true", se3.get("metadata", {}).get("kb_block") is True)
    check("TC3 done", "done" in ty3)
else:
    print("[SKIP] TC3 无既有 KB")

# TC4 编排未就绪（tutor/quiz）
evs4 = stream({"skill_code": "tutor/quiz", "message": "出题"})
ty4 = types_of(evs4)
check("TC4 error 未就绪", ty4 == ["error"] and "未就绪" in (evs4[0][1].get("content", "") if evs4 else ""))

# TC5 未知技能
evs5 = stream({"skill_code": "tutor/notexist", "message": "x"})
ty5 = types_of(evs5)
check("TC5 error 未知技能", ty5 == ["error"] and "未知技能" in (evs5[0][1].get("content", "") if evs5 else ""))

print(f"\n==== 冒烟结果：{'全过' if not failures else '失败 ' + str(failures)} ====")
sys.exit(0 if not failures else 1)
