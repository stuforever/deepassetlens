# -*- coding: utf-8 -*-
"""⑤补补-5 步骤 7：A5 前半验收——错因分析注入 5 道带 error_type 错题→分布断言（LLM 断下限）。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from sqlalchemy import text

from app.services.learning.pg import _engine

BASE = "http://127.0.0.1:28000"
UID = "anonymous"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def cleanup():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": UID})


try:
    cleanup()
    # 注入 5 道带 error_type 的错题（3 concept / 1 careless / 1 technique，source 混合）
    rows = [
        ("concept", "chat"), ("concept", "practice"), ("concept", "manual"),
        ("careless", "practice"), ("technique", "chat"),
    ]
    with _engine.begin() as c:
        for i, (et, src) in enumerate(rows, 1):
            c.execute(text(
                "INSERT INTO learning_wrong_questions (wq_id, user_id, mother_question_id, "
                "variant_text, error_type, source) VALUES "
                "(:w, :u, 'mq-seed-0001', :v, :et, :src)"),
                {"w": f"wq-a5-{i}", "u": UID, "v": f"错题样本 {i}：{et}", "et": et, "src": src})
    requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
    time.sleep(6)
    r = requests.get(f"{BASE}/api/tutor/analyze-wrong-questions", timeout=20).json().get("data") or {}
    check("总数=5", r.get("total") == 5, f"total={r.get('total')}")
    dist = r.get("error_type_distribution") or {}
    check("占比结构（concept 60%）", dist.get("concept", {}).get("ratio") == 0.6 and dist.get("concept", {}).get("count") == 3, f"dist={dist}")
    check("有结论（含集中知识点与建议）", "错题最集中" in (r.get("conclusion") or "") and "建议" in (r.get("conclusion") or ""), r.get("conclusion", "")[:60])
    # 工具面同源断言（mcp 工具计数基线+2）
    import sys as _s
    _s.path.insert(0, ".")
    from app.mcp_server import mcp
    check("mcp 工具计数=基线+2（30）", len(mcp._tool_manager._tools) == 30, f"n={len(mcp._tool_manager._tools)}")
    # tutor manifest 对账：人格卡 AGENTS.md 变更不进卡 JSON——manifest 零差异（预期项）
    import json
    m = requests.get(f"{BASE}/api/capabilities/manifest", timeout=30).json()
    base = json.load(open("scripts/_diag_assembly_baselineC.json", encoding="utf-8"))
    bi, mi = base.get("items") or {}, m.get("items") or {}
    content_diff = [k for k in set(list(bi.keys()) + list(mi.keys())) if k != "card_version" and bi.get(k) != mi.get(k)]
    check("tutor manifest 内容零差异（AGENTS 文件不进卡 JSON=预期）", not content_diff, f"diff={content_diff}")
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "补-5 走查毕还原（错因分析验收）"}, timeout=20)
    cleanup()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 补-5 A5 前半验收：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
