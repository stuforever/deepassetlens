# -*- coding: utf-8 -*-
"""批1 1.3/1.7：原仓端点闭包机械枚举——openapi 全量落盘+GET 遍历采样（错误形态含）。

口径：GET 全量机械采样（响应原文+状态码落盘）；POST/PUT/DELETE 不盲发（写操作），
契约以 openapi schema 留档，代表性 POST 样例随 B 批域内对拍录制。"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent / "dt_baseline"
EP = BASE / "endpoints"
EP.mkdir(parents=True, exist_ok=True)

import urllib.request

openapi_path = EP / "_openapi.json"
if not openapi_path.exists():
    with urllib.request.urlopen("http://localhost:31007/openapi.json", timeout=30) as r:
        openapi_path.write_bytes(r.read())

spec = json.loads(openapi_path.read_text(encoding="utf-8"))
paths = spec.get("paths", {})
print("openapi paths:", len(paths))

methods = {}
for p, ops in paths.items():
    for m in ops:
        if m in ("get", "post", "put", "delete", "patch"):
            methods.setdefault(m, []).append(p)
for m in sorted(methods):
    print(f"  {m}: {len(methods[m])}")

# 闭包清单落盘（端点×方法×tag）
inv = []
for p in sorted(paths):
    for m, op in paths[p].items():
        if m in ("get", "post", "put", "delete", "patch"):
            inv.append({"method": m.upper(), "path": p,
                        "tags": op.get("tags", []), "summary": op.get("summary", ""),
                        "has_path_params": "{" in p})
(BASE / "endpoints_inventory.json").write_text(
    json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
print("inventory saved:", len(inv))

# GET 无路径参数端点——可直接采样
safe_gets = sorted({i["path"] for i in inv if i["method"] == "GET" and not i["has_path_params"]})
(BASE / "endpoints_get_safe.json").write_text(
    json.dumps(safe_gets, ensure_ascii=False, indent=1), encoding="utf-8")
print("GET 无路径参数:", len(safe_gets))
tags = sorted({t for i in inv for t in i["tags"]})
print("tags:", tags)
