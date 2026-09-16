# -*- coding: utf-8 -*-
"""⑤R F1 字段级核对 v2（用户令）：前端调用 × 运行时 OpenAPI 权威路由表。"""
import json
import re
from pathlib import Path
from urllib.request import urlopen

ORIG = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web")
OUT = Path(__file__).parent / "dt_baseline" / "batch8_端点核对.json"

# 1. 前端调用收集（app+components+features ts/tsx）
call_re = re.compile(r"""(?:apiUrl|fetch)\(\s*[`"']([^`"']+)""")
endpoint_re = re.compile(r"/api/v1/[A-Za-z0-9_\-/\[\]{}.$`]*")
calls = {}
for base in [ORIG / "app", ORIG / "components", ORIG / "features"]:
    if not base.exists():
        continue
    for f in list(base.rglob("*.tsx")) + list(base.rglob("*.ts")):
        if ".next" in str(f) or f.name.endswith(".d.ts"):
            continue
        try:
            src = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in call_re.finditer(src):
            for em in endpoint_re.finditer(m.group(1)):
                calls.setdefault(em.group(0), []).append(str(f.relative_to(ORIG)))

def norm(ep: str):
    segs = ep.split("?")[0].strip("/").split("/")
    out = []
    for s in segs:
        s = re.sub(r"\$\{[^}]*\}", "", s)   # 剥模板拼接
        s = re.sub(r"^.*(?=\$\{)", "", s) if "${" in s else s  # 段内前缀+${..} 残留
        s = s.strip("{}[]`$").strip("'\"")
        out.append(s if s else "{}")
    return "/" + "/".join(out)

fe = {}
for ep in calls:
    fe.setdefault(norm(ep), []).append(ep)

# 2. 运行时 OpenAPI 路由表（双侧归一：{param} -> {}）
spec = json.loads(urlopen("http://127.0.0.1:28000/openapi.json", timeout=180).read())
_PARAM = "{" + "}"
be = set()
for p in spec.get("paths", {}).keys():
    be.add("/".join(_PARAM if seg.startswith("{") else seg for seg in p.split("/")))
be_ws = {p for p, ops in spec.get("paths", {}).items() if any("websocket" in str(o).lower() for o in ops.values())}

missing = {n: sorted(set(v)) for n, v in sorted(fe.items()) if n not in be}
out = {
    "openapi_paths": len(be),
    "front_unique_norm": len(fe),
    "missing_count": len(missing),
    "missing": missing,
    "covered": sorted(n for n in fe if n in be),
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OpenAPI 路径: {len(be)} | 前端唯一(归一): {len(fe)} | 覆盖: {len(out['covered'])} | 缺失: {len(missing)}")
for n, raw in missing.items():
    print("  MISS", n, "<-", raw[:2])
