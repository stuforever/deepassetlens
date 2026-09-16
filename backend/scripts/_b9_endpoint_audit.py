# -*- coding: utf-8 -*-
"""批9 F2 端点审计：原仓 h5 页全部 fetch 调用提取 × 运行时 OpenAPI 比对。"""
import json
import re
from pathlib import Path

SRC = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web\app\h5")
OUT = Path(__file__).resolve().parent / "dt_baseline" / "batch9_端点核对.json"

# 提取 fetch(apiUrl('...')) / fetch('...') / fetch(`/api/v1/...${...}`) 的路径模板
PATTERNS = [
    re.compile(r"""fetch\(\s*apiUrl\(\s*['"`]([^'"`]+)['"`]""", re.X),
    re.compile(r"""fetch\(\s*['"`](/api/[^'"`]+)['"`]""", re.X),
    re.compile(r"""fetch\(\s*`([^`]*\$\{[^}]+\}[^`]*)`""", re.X),
    re.compile(r"""apiUrl\(\s*['"`](/api/[^'"`]+)['"`]\s*\)""", re.X),
]

calls = {}
for f in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
    if "components" in str(f) and "H5Shell" in f.name:
        pass
    text = f.read_text(encoding="utf-8", errors="ignore")
    rel = str(f.relative_to(SRC))
    for pat in PATTERNS:
        for m in pat.finditer(text):
            raw = m.group(1)
            # 归一化：${...} → {}；剥 query 串保留路径
            norm = re.sub(r"\$\{[^}]+\}", "{}", raw)
            path_only = norm.split("?")[0]
            if not path_only.startswith("/api"):
                continue
            calls.setdefault(path_only, set()).add(rel)

# OpenAPI 运行时面
openapi = json.load(open(Path(__file__).resolve().parent / "dt_baseline" / "_openapi_cache.json", encoding="utf-8"))
api_paths = set(openapi["paths"].keys())

def segs(p):
    return [s for s in p.split("/") if s != ""]

def is_param(seg):
    return seg.startswith("{") and seg.endswith("}")

def norm_seg(seg):
    # 段尾 '{}' 粘连 = query 模板残尾（apiUrl(`/x${qs}`) → x{}）；'{}' 本身是参数段不剥
    while seg.endswith("{}") and len(seg) > 2:
        seg = seg[:-2]
    return seg

def match(call_path):
    """参数感知匹配：段内 {} 通配 + 段尾 {} 粘连剥离。"""
    cs = [norm_seg(s) for s in segs(call_path)]
    cs = [s for s in cs if s]
    for api in api_paths:
        as_ = segs(api)
        if len(as_) != len(cs):
            continue
        if all((is_param(a) and is_param(c)) or a == c for a, c in zip(as_, cs)):
            return api
    return None

missing, covered = [], []
for call_path in sorted(calls):
    if call_path in api_paths or match(call_path):
        covered.append(call_path)
    else:
        missing.append({"call": call_path, "pages": sorted(calls[call_path])})

report = {
    "batch": "批9 F2 h5组",
    "total_distinct_calls": len(calls),
    "covered": sorted(covered),
    "missing": missing,
    "per_page_calls": {p: sorted(calls[p]) for p in sorted(calls)},
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"调用去重 {len(calls)} 条；OpenAPI 覆盖 {len(covered)}；未匹配 {len(missing)}")
for m in missing:
    print("  MISS", m["call"], "<-", ",".join(m["pages"]))
