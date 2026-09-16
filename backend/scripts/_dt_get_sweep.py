# -*- coding: utf-8 -*-
"""批1 1.3：原仓 GET 全量采样——响应原文+状态码落盘（对拍基线通货）。"""
import json
import time
from pathlib import Path

import urllib.request
import urllib.error

BASE = Path(__file__).resolve().parent / "dt_baseline"
EP = BASE / "endpoints" / "get"
EP.mkdir(parents=True, exist_ok=True)

safe_gets = json.loads((BASE / "endpoints_get_safe.json").read_text(encoding="utf-8"))
print("采样目标:", len(safe_gets))

results = []
for i, p in enumerate(safe_gets):
    fname = p.strip("/").replace("/", "__").replace("?", "_q_") or "root"
    fname = (fname[:120] + ".json") if len(fname) <= 120 else (fname[:120] + "_cut.json")
    rec = {"path": p, "status": None, "ctype": None, "error": None}
    try:
        req = urllib.request.Request("http://localhost:31007" + p, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            rec["status"] = r.status
            rec["ctype"] = r.headers.get("content-type", "")
            body = r.read(200000)
    except urllib.error.HTTPError as e:
        rec["status"] = e.code
        rec["ctype"] = e.headers.get("content-type", "") if e.headers else ""
        try:
            body = e.read(200000)
        except Exception:
            body = b""
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:160]
        body = b""
    out = {"path": p, "status": rec["status"], "content_type": rec["ctype"],
           "sample_error": rec["error"]}
    try:
        out["body"] = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        out["body_text"] = body.decode("utf-8", "replace")[:5000]
    (EP / fname).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    results.append(rec)
    time.sleep(0.15)

ok = sum(1 for r in results if r["status"] and 200 <= r["status"] < 300)
err4x = sum(1 for r in results if r["status"] and 400 <= r["status"] < 500)
err5x = sum(1 for r in results if r["status"] and r["status"] >= 500)
exc = sum(1 for r in results if r["error"])
print(f"GET 采样完成: 2xx={ok} 4xx={err4x} 5xx={err5x} 异常={exc} / {len(results)}")
by401 = [r["path"] for r in results if r["status"] == 401]
if by401:
    print("401 数:", len(by401), "示例:", by401[:3])
