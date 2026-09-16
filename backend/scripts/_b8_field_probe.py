# -*- coding: utf-8 -*-
"""⑤R F1 字段级对拍实测：F1 核心端点 tupu(28000) vs 原仓(31007) 响应字段逐项比对。
字段集合一致性 = 键名集合相等（值语义由 vendor 零改码保证，L2 56 样本已证）。"""
import json
from pathlib import Path
from urllib.request import urlopen, Request

TUPU = "http://127.0.0.1:28000"
ORIG = "http://127.0.0.1:31007"
OUT = Path(__file__).parent / "dt_baseline" / "batch8_字段对拍.json"

PROBES = [
    ("mq_list", "/api/v1/mother-questions?page=1&page_size=3"),
    ("mq_dict", "/api/v1/mother-questions/dict"),
    ("mq_stats", "/api/v1/mother-questions/analysis/comprehensive-stats"),
    ("mq_weak", "/api/v1/mother-questions/analysis/weak-points"),
    ("mq_by_subject", "/api/v1/mother-questions/analysis/by-subject"),
    ("mq_retention", "/api/v1/mother-questions/analysis/retention"),
    ("mq_trends", "/api/v1/mother-questions/analysis/trends?days=30"),
    ("mq_error_patterns", "/api/v1/mother-questions/analysis/error-patterns"),
    ("mq_review_plan", "/api/v1/mother-questions/reviews/plan"),
    ("mq_trash", "/api/v1/mother-questions/trash?page=1&page_size=3"),
    ("mq_due", "/api/v1/mother-questions/reviews/due?max_items=3"),
    ("book_list", "/api/v1/book/books"),
    ("cur_textbooks", "/api/v1/curriculum/textbooks"),
    ("cur_chapters", "/api/v1/curriculum/chapters"),
    ("cur_kp_tree", "/api/v1/curriculum/knowledge-points/tree"),
]

def shape(x, depth=0):
    """递归形状：dict->键->子形状（合并子键形状），list->元素形状，标量->类型名。"""
    if depth > 4:
        return "…"
    if isinstance(x, dict):
        return {k: shape(v, depth + 1) for k, v in sorted(x.items())}
    if isinstance(x, list):
        if not x:
            return "[]"
        shapes = [shape(v, depth + 1) for v in x[:3]]
        first = shapes[0]
        if all(s == first for s in shapes):
            return [first, "…"] if isinstance(first, dict) else f"[{first}]"
        return shapes
    return type(x).__name__

def get(base, path):
    req = Request(base + path, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"__error__": str(e)[:120]}

report = []
for name, path in PROBES:
    j1 = get(TUPU, path)
    j2 = get(ORIG, path)
    if "__error__" in j1 or "__error__" in j2:
        report.append({"probe": name, "path": path, "tupu_error": j1.get("__error__"), "orig_error": j2.get("__error__"), "verdict": "ERROR"})
        continue
    s1, s2 = shape(j1), shape(j2)
    same = s1 == s2
    diff_keys = []
    if not same:
        k1 = set(s1) if isinstance(s1, dict) else set()
        k2 = set(s2) if isinstance(s2, dict) else set()
        diff_keys = {"tupu_only": sorted(k1 - k2), "orig_only": sorted(k2 - k1)}
    report.append({"probe": name, "path": path, "verdict": "SAME" if same else "DIFF", "diff": diff_keys})

n_same = sum(1 for r in report if r["verdict"] == "SAME")
print(f"字段形状对拍: {n_same}/{len(report)} SAME")
for r in report:
    tag = r["verdict"]
    print(f"  [{tag}] {r['probe']} {r['path']}")
    if tag == "DIFF" and r.get("diff"):
        print("     tupu_only:", r["diff"]["tupu_only"][:8])
        print("     orig_only:", r["diff"]["orig_only"][:8])
    if tag == "ERROR":
        print("     tupu_err:", r.get("tupu_error"), "| orig_err:", r.get("orig_error"))
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("落盘", OUT.name)
