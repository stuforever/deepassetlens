# -*- coding: utf-8 -*-
"""⑤R B1 3.4：L2 基线重放对拍——B1 域端点（curriculum/mother-questions）。

口径（唯一交棒 §L2）：重放原仓基线样例请求到 tupu 复刻面，响应逐字段对拍；
豁免白名单=时间戳/ID 类键（计划钉死）；不一致=登记，修到一致或停。"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent / "dt_baseline" / "endpoints" / "get"
TUPU = "http://127.0.0.1:28000"

EXEMPT = re.compile(r"(_at$|_time$|timestamp|^time$|updated|created|last_indexed|_id$|^id$|session_id|task_id|retention)", re.I)

# 接线点2（路径根 env 单点）语义豁免：两侧 workspace/data 根归一化后对拍
_WS_ROOT = str(Path(__file__).resolve().parents[1] / "data" / "experts" / "tutor" / "workspace")
_DT_ROOT = r"D:\gitcangku\xiaobaohaohao\DeepTutor"


def norm_paths(obj):
    if isinstance(obj, dict):
        return {k: norm_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [norm_paths(x) for x in obj]
    if isinstance(obj, str):
        return obj.replace(_WS_ROOT, "<WS>").replace(_DT_ROOT, "<WS>").replace(_WS_ROOT.replace("\\", "/"), "<WS>").replace(_DT_ROOT.replace("\\", "/"), "<WS>")
    return obj


def strip_exempt(obj):
    if isinstance(obj, dict):
        return {k: strip_exempt(v) for k, v in obj.items() if not EXEMPT.search(k or "")}
    if isinstance(obj, list):
        return [strip_exempt(x) for x in obj]
    return obj


def deep_diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: 仅复刻侧")
            elif k not in b:
                out.append(f"{path}.{k}: 仅基线侧")
            else:
                out += deep_diff(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: 列表长 {len(a)}(基线) vs {len(b)}(复刻)")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += deep_diff(x, y, f"{path}[{i}]")
    elif a != b:
        sa, sb = str(a), str(b)
        out.append(f"{path}: {sa[:60]!r} vs {sb[:60]!r}")
    return out


import urllib.request
import urllib.error

samples = sorted(BASE.glob("api__v1__curriculum*.json")) + sorted(BASE.glob("api__v1__mother-questions*.json")) + sorted(BASE.glob("api__v1__knowledge*.json")) + sorted(BASE.glob("api__v1__learning*.json")) + sorted(BASE.glob("api__v1__self-learning*.json"))
print("B1 域样例:", len(samples))
results = []
for f in samples:
    rec = json.loads(f.read_text(encoding="utf-8"))
    p = rec["path"]
    try:
        req = urllib.request.Request(TUPU + p, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            live_status, body = r.status, r.read(4000000)
    except urllib.error.HTTPError as e:
        live_status, body = e.code, e.read(4000000)
    except Exception as e:
        results.append((p, f"异常 {e}"))
        continue
    if rec["status"] != live_status:
        results.append((p, f"状态 {rec['status']} vs {live_status}"))
        continue
    try:
        live_json = json.loads(body.decode("utf-8", "replace"))
        base_json = rec.get("body")
        if base_json is None:
            results.append((p, "基线非 JSON（跳过体比对，状态一致）"))
            continue
        diffs = deep_diff(strip_exempt(norm_paths(base_json)), strip_exempt(norm_paths(live_json)))
        results.append((p, "PASS" if not diffs else f"DIFF×{len(diffs)}: " + "; ".join(diffs[:3])))
    except Exception as e:
        results.append((p, f"比对异常 {e}"))

ok = sum(1 for _, s in results if s == "PASS")
print(f"\n=== L2 重放: {ok}/{len(results)} PASS ===")
for p, s in results:
    if s != "PASS":
        print(f"  {p}\n    -> {s[:300]}")
