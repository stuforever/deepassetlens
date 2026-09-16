# -*- coding: utf-8 -*-
"""⑤R R2 A1：端点契约对拍——1.3 基线 114 GET 样本全量重放 tupu 28000，响应形状 1:1。
豁免：时间戳/ID/URL/计数类字段只对型不对值；列表长度数据驱动不对值。
另含 knowledge 适配层端点专项补测（1.3 样本源=原仓 31007）。"""
import io
import json
import re
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent / "dt_baseline"
SRC = BASE / "endpoints" / "get"
TUPU = "http://127.0.0.1:28000"

# 数据驱动/易变字段：只对型（shape 比较本就不对值；此处控制「键缺失容差」与「精确值断言」）
VOLATILE_KEY = re.compile(
    r"(id|uuid|ts|time|date|created|updated|token|url|count|total|version|hash|duration|latency|ms|elapsed|session|request_id|trace)$",
    re.I)

WHITELIST_MISSING = {
    # 原仓有值字段但 tupu 数据态不同允许缺失的键（登记式）
}


def shape(v, key=""):
    """递归形状：dict=键集+子形状；list=元素形状（长度不计）；标量=类型。"""
    if isinstance(v, dict):
        return {k: shape(x, k) for k, x in sorted(v.items())}
    if isinstance(v, list):
        if not v:
            return []
        return [shape(v[0], key)]
    return type(v).__name__


def shape_diff(a, b, path="$", out=None, strict_keys=True):
    """形状差异收集。strict_keys=True 时键集必须相等；VOLATILE 键差异降级为 note。"""
    if out is None:
        out = []
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a.keys()), set(b.keys())
        for k in sorted(ka - kb):
            out.append(("missing_in_tupu", f"{path}.{k}"))
        for k in sorted(kb - ka):
            out.append(("extra_in_tupu", f"{path}.{k}"))
        for k in sorted(ka & kb):
            shape_diff(a[k], b[k], f"{path}.{k}", out, strict_keys)
    elif isinstance(a, list) and isinstance(b, list):
        if a and b:
            shape_diff(a[0], b[0], f"{path}[0]", out, strict_keys)
        elif bool(a) != bool(b):
            out.append(("list_empty_diff", path))
    elif type(a).__name__ != type(b).__name__:
        out.append(("type_diff", f"{path}: {type(a).__name__} vs {type(b).__name__}"))
    return out


def main():
    files = sorted(SRC.glob("*.json"))
    results = []
    for f in files:
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception as e:
            results.append((f.name, "SKIP", f"样本损坏 {e}"))
            continue
        path = d.get("path") or ""
        orig_status = d.get("status", 0)
        orig_body = d.get("body")
        if d.get("sample_error"):
            results.append((f.name, "SKIP", f"1.3 采样期错误（原面未采到）"))
            continue
        # WS 端点不做 HTTP GET 对拍
        if "ws" in f.name.lower():
            results.append((f.name, "SKIP", "WS 端点"))
            continue
        try:
            r = requests.get(TUPU + path, timeout=30)
        except Exception as e:
            results.append((f.name, "FAIL", f"请求异常 {e}"))
            continue
        status_ok = (r.status_code == orig_status) or (200 <= r.status_code < 300 and 200 <= orig_status < 300)
        if not status_ok:
            results.append((f.name, "FAIL", f"状态 {orig_status}→{r.status_code}"))
            continue
        try:
            tupu_body = r.json()
        except Exception:
            tupu_body = None
        if not isinstance(orig_body, (dict, list)) or not isinstance(tupu_body, (dict, list)):
            results.append((f.name, "PASS" if type(orig_body) is type(tupu_body) else "FAIL",
                            f"标量体 {type(orig_body).__name__} vs {type(tupu_body).__name__}"))
            continue
        diffs = shape_diff(orig_body, tupu_body)
        # 数据驱动差异（列表空/计数）降级 note；键差异与型差异=FAIL
        hard = [x for x in diffs if x[0] in ("missing_in_tupu", "extra_in_tupu", "type_diff")]
        soft = [x for x in diffs if x[0] not in ("missing_in_tupu", "extra_in_tupu", "type_diff")]
        if hard:
            results.append((f.name, "FAIL", f"形状差异 {len(hard)}: " + "; ".join(f"{t} {p}" for t, p in hard[:3])))
        else:
            results.append((f.name, "PASS", f"形状 1:1" + (f"（note {len(soft)}）" if soft else "")))
    # knowledge 适配层专项
    for kp in ["/api/v1/knowledge", "/api/v1/knowledge/bases"]:
        try:
            r = requests.get(TUPU + kp, timeout=20)
            results.append((f"knowledge适配层 {kp}", "PASS" if r.status_code < 500 else "FAIL", str(r.status_code)))
        except Exception as e:
            results.append((f"knowledge适配层 {kp}", "FAIL", str(e)[:60]))

    ok = sum(1 for _, s, _ in results if s == "PASS")
    skip = sum(1 for _, s, _ in results if s == "SKIP")
    fail = sum(1 for _, s, _ in results if s == "FAIL")
    for name, s, note in results:
        if s != "PASS":
            print(f"  [{s}] {name} :: {note}")
    print(f"== A1 汇总: PASS {ok} / SKIP {skip} / FAIL {fail} (总 {len(results)}) ==")
    json.dump([{"name": n, "status": s, "note": t} for n, s, t in results],
              io.open(BASE / "r2_a1_replay.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
