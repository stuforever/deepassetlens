# -*- coding: utf-8 -*-
"""缺失端点分类 v2（精确规则）：
1) raw 含未闭合 ${…}（截断）→ 截到该段前，重归一再查 OpenAPI → 命中=假阳性(基路径已覆盖)
2) 余下按域前缀分类：F1 域(母题库/书源/curriculum) vs F2/F3 域(memory/settings/co_writer/…)"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent / "dt_baseline"
spec = json.loads((BASE / "_openapi_cache.json").read_text(encoding="utf-8"))
audit = json.loads((BASE / "batch8_端点核对.json").read_text(encoding="utf-8"))

_PARAM = "{" + "}"
be = set()
for p in spec.get("paths", {}).keys():
    be.add("/".join(_PARAM if seg.startswith("{") else seg for seg in p.split("/")))

def norm(ep: str):
    segs = ep.split("?")[0].strip("/").split("/")
    out = []
    for s in segs:
        s = re.sub(r"\$\{[^}]*\}", "", s).strip("{}[]`$")
        out.append(s if s else "{}")
    return "/" + "/".join(out)

F2_F3_PREFIXES = ("/api/v1/memory", "/api/v1/settings", "/api/v1/co_writer", "/api/v1/partners",
                  "/api/v1/sessions", "/api/v1/multi-user", "/api/v1/plugins", "/api/v1/capabilities",
                  "/api/v1/system", "/api/v1/tools", "/api/v1/learner-profile",
                  "/api/v1/self-learning", "/api/v1/notebook", "/api/v1/learning")

cls = {"f1_domain_missing": [], "f2f3_domain": {}, "false_positive_base_covered": []}
f2f3 = {}
for n, raws in audit["missing"].items():
    resolved = False
    for raw in raws:
        # 截断检测：最后一个未闭合 ${ 段
        m = re.search(r"\$\{[^}]*$", raw)
        if m:
            base_ep = raw[: m.start()]
            nb = norm(base_ep)
            if nb in be:
                cls["false_positive_base_covered"].append(n)
                resolved = True
                break
        nb = norm(raw)
        if nb in be and nb != n:
            cls["false_positive_base_covered"].append(n)
            resolved = True
            break
    if resolved:
        continue
    if n.startswith(("/api/v1/mother-questions", "/api/v1/book", "/api/v1/curriculum")):
        cls["f1_domain_missing"].append(n)
    else:
        dom = n.split("/")[3] if len(n.split("/")) > 3 else n
        f2f3.setdefault(dom, []).append(n)

cls["f2f3_domain"] = f2f3
print("F1 域真缺口:", cls["f1_domain_missing"] or "无 ✓")
for dom, items in f2f3.items():
    print(f"  F2/F3 [{dom}]: {len(items)} 条")
print("假阳性(基路径已覆盖):", len(cls["false_positive_base_covered"]))

merged = dict(audit)
merged["classification_v2"] = cls
(BASE / "batch8_端点核对.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
print("已并入 batch8_端点核对.json")
