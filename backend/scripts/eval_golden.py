# -*- coding: utf-8 -*-
"""eval_golden.py - 金标评估（融合设计 §6.2 G6）

逐条金标走流式问答，从 SSE sql_result 事件取实际结果 digest（row_count + 首行 sha1），
与金标 expected_result_digest 比对（比结果不比 SQL 文本，同结果不同写法算对）。
输出准确率 + 失败明细 JSON 到 docs/eval/。

用法：
    cd backend && python -u scripts/eval_golden.py [--limit N] [--stream-timeout 240] [--out DIR]
环境：需要 28000 后端运行中（含 G1/G2/G3/M3 装配）；金标由 POST /api/v1/golden-qa/seed 或管理页灌入。
"""
import argparse
import hashlib
import json
import os
import sys
import time

import requests

BASE = "http://127.0.0.1:28000"


def compute_digest(rows, row_count):
    first = None
    if rows:
        first = rows[0]
        try:
            json.dumps(first)
        except Exception:
            first = str(first)
    h = hashlib.sha1(json.dumps(first, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:16] if first is not None else ""
    return {"row_count": int(row_count or 0), "first_row_hash": h, "first_row": first}


def _norm_val(v):
    """数值类型归一（float/Decimal/str 数值视为同值），供值级比对。"""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    if isinstance(v, str):
        try:
            return round(float(v), 6)
        except Exception:
            return v
    return v


def _first_rows_eq(a, b):
    """首行值级比对：元素数值归一后相等即同（容忍 float vs str/DECIMAL 精度差异）。"""
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if isinstance(x, (int, float, str)) or isinstance(y, (int, float, str)):
            if _norm_val(x) != _norm_val(y):
                return False
        elif x != y:
            return False
    return True


def digest_matches(got, exp):
    """金标比对：值级（row_count 同 + 首行值归一化同）或标量宽松（COUNT 类期望单值，明细行数作答算对）。"""
    if not got or not exp:
        return False
    if got.get("row_count") == exp.get("row_count") and _first_rows_eq(got.get("first_row"), exp.get("first_row")):
        return True
    # 标量期望：exp 单行单值（如 COUNT(*)=3）-> 允许 agent 返回 N 明细行（同答案 3）
    ef = exp.get("first_row")
    if exp.get("row_count") == 1 and isinstance(ef, list) and len(ef) == 1:
        val = ef[0]
        if got.get("row_count") == _norm_val(val) or _norm_val(got.get("row_count")) == _norm_val(val):
            return True
        gf = got.get("first_row")
        if isinstance(gf, list) and len(gf) == 1 and _norm_val(gf[0]) == _norm_val(val):
            return True
    return False


def run_golden_question(question: str, thread_id: str, timeout: int) -> dict:
    """走流式问答，返回 {ok, digest?, reason, tool_count, examples_injected, corrections, confidence}。

    S1（b/c）：reason 四分类（no_sql_result / stream_timeout / stream_error / rubric_blocked）；
    观测采集修正——tool_count 按 `event: think` 带 tool_name 的条目计数，examples_injected/corrections
    取自 `event: done`（examples_used / corrections）。
    """
    url = f"{BASE}/api/data-intelligence/chat/freeplan/stream"
    events = {}
    buf = ""
    try:
        with requests.post(url, json={"user_input": question, "thread_id": thread_id},
                           stream=True, timeout=timeout) as r:
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("event:"):
                    buf = raw[len("event:"):].strip()
                    continue
                if raw.startswith("data:"):
                    try:
                        data = json.loads(raw[len("data:"):])
                    except Exception:
                        data = {"raw": raw[:120]}
                    events.setdefault(buf, []).append(data)
    except requests.exceptions.Timeout:
        return {"ok": False, "reason": "stream_timeout", "digest": None, "tool_count": 0,
                "examples_injected": 0, "corrections": 0, "confidence": None}
    except Exception as e:
        return {"ok": False, "reason": f"stream_error: {e}", "digest": None, "tool_count": 0,
                "examples_injected": 0, "corrections": 0, "confidence": None}
    # 观测采集（S1c）：tool_count 按 think 事件带 tool_name（工具启动）计数
    tool_count = len([e for e in events.get("think", []) if e.get("tool_name")])
    done = events.get("done")
    conf = None
    examples = []
    corrections = 0
    if done:
        _d = done[-1]
        conf = _d.get("confidence")
        _ev = _d.get("evidence") or {}
        examples = _ev.get("examples_used") or []
        corrections = int(_d.get("corrections") or _ev.get("corrections") or 0)
    examples_injected = len(examples)
    max_sim = None
    for _h in examples:
        _s = _h.get("sim")
        if _s is not None:
            try:
                _s = float(_s)
                max_sim = _s if max_sim is None else max(max_sim, _s)
            except Exception:
                pass
    sq = events.get("sql_result")
    if not sq:
        # S1b：有 rubric 且未 satisfied（有回答但未执行数据查询）-> rubric_blocked；否则 no_sql_result
        _rs = ""
        for _r in events.get("rubric", []):
            _rs = _r.get("status") or _rs
        if _rs and _rs not in ("satisfied",):
            reason = "rubric_blocked"
        else:
            reason = "no_sql_result"
        return {"ok": False, "reason": reason, "digest": None, "tool_count": tool_count,
                "examples_injected": examples_injected, "corrections": corrections, "confidence": conf}
    last = sq[-1]
    rows = last.get("rows") or []
    rc = last.get("row_count") or len(rows)
    digest = compute_digest(rows, rc)
    return {"ok": True, "digest": digest, "reason": "ok",
            "tool_count": tool_count, "examples_injected": examples_injected,
            "corrections": corrections, "confidence": conf}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全部）")
    ap.add_argument("--only", default="", help="只跑 id 含该前缀的金标（如 --only 0dc21a21）")
    ap.add_argument("--stream-timeout", type=int, default=240)
    ap.add_argument("--repeat", type=int, default=1, help="每条跑 N 次（平滑 LLM 方差），报告通过率与稳定通过率")
    ap.add_argument("--out", default="docs/eval", help="产物目录（相对 repo 根）")
    args = ap.parse_args()

    # 读金标（直连 DB，脚本运行于 backend/）
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.core.database import SessionLocal
    from app.models.base import KgGoldenQaSet

    db = SessionLocal()
    try:
        goldens = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.enabled == True).order_by(  # noqa: E712
            KgGoldenQaSet.created_at).all()
    finally:
        db.close()
    if args.limit:
        goldens = goldens[: args.limit]
    if args.only:
        goldens = [g for g in goldens if args.only in str(g.id)]
    if not goldens:
        print("[Eval] 无启用金标。请先 POST /api/v1/golden-qa/seed 或灌入数据。")
        sys.exit(1)

    print(f"== 金标评估：{len(goldens)} 条 × {args.repeat} 次，stream-timeout={args.stream_timeout}s ==")
    # 唯一运行前缀：每次调用全新会话（thread 复用会让 agent 从旧会话恢复而不执行，污染结果）
    run_uid = f"{time.strftime('%H%M%S')}_{os.getpid()}"
    results = []
    stable_pass = 0
    for i, g in enumerate(goldens, 1):
        q = g.question
        exp = g.expected_result_digest or {}
        runs = []
        pass_cnt = 0
        for r in range(args.repeat):
            print(f"  [{i}/{len(goldens)}] ({r + 1}/{args.repeat}) {q[:40]} ... ", end="", flush=True)
            res = run_golden_question(q, f"eval_{run_uid}_{g.id}_r{r}", args.stream_timeout)
            ok = False
            reason = res["reason"]
            if res["ok"] and res["digest"]:
                ok = digest_matches(res["digest"], exp)
            if ok:
                pass_cnt += 1
            mark = "PASS" if ok else "FAIL"
            print(f"{mark}  got={res.get('digest')}")
            runs.append({
                "run": r + 1, "pass": ok, "reason": reason,
                "got_digest": res.get("digest"), "tool_count": res.get("tool_count"),
                "examples_injected": res.get("examples_injected"),
                "corrections": res.get("corrections"),
                "confidence": res.get("confidence"),
            })
            time.sleep(0.5)
        stable = pass_cnt >= max(1, (args.repeat + 1) // 2)  # 半数以上算稳定通过
        if stable:
            stable_pass += 1
        print(f"      -> {pass_cnt}/{args.repeat} {'稳定PASS' if stable else 'FAIL'}")
        results.append({
            "id": g.id, "question": q, "expected_sql": g.expected_sql,
            "expected_digest": exp, "pass_ratio": pass_cnt,
            "stable": stable, "runs": runs,
        })

    total = len(results)
    first_pass = sum(1 for r in results if r["runs"][0]["pass"])
    acc = round(first_pass / total * 100, 1) if total else 0.0
    stable_acc = round(stable_pass / total * 100, 1) if total else 0.0
    # S1（b）：reason 四分类分布（no_sql_result / stream_timeout / stream_error / rubric_blocked / ok）
    from collections import Counter as _Counter
    _reason_dist = _Counter(str(_rc.get("reason")) for _r in results for _rc in _r["runs"])
    # S1（c）：逐题观测（tool_count / examples_injected / corrections / confidence）落盘可验
    _obs = []
    for _r in results:
        _tc = [_rc.get("tool_count") for _rc in _r["runs"]]
        _ex = [_rc.get("examples_injected") for _rc in _r["runs"]]
        _co = [_rc.get("corrections") for _rc in _r["runs"]]
        _obs.append({
            "id": _r["id"], "question": _r["question"][:60],
            "pass_ratio": _r["pass_ratio"], "stable": _r["stable"],
            "tool_count_min": min(_tc), "tool_count_max": max(_tc),
            "examples_injected_any": any(v and v > 0 for v in _ex),
            "corrections_max": max(_co),
        })
    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total, "repeat": args.repeat,
        "first_round_accuracy_pct": acc,   # 单轮口径（兼容环比：同 repeat=1 即首轮）
        "stable_accuracy_pct": stable_acc,  # 稳定通过口径（半数以上运行正确）
        "rubric": "on" if os.getenv("TUPU_RUBRIC_DISABLED") != "1" else "off",
        "reason_distribution": dict(_reason_dist),  # S1（b）：四分类观测
        "observations": _obs,  # S1（c）：tool_count/examples_injected/corrections 观测
        "unstable": [r for r in results if not r["stable"]],
    }
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = os.path.join(root, args.out)
    os.makedirs(out_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"eval_golden_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n== 结果：首轮准确率 {acc}% / 稳定通过率 {stable_acc}% （{stable_pass}/{total} 条稳定），明细 -> {os.path.relpath(out_path, root)} ==")
    for r in summary["unstable"]:
        print(f"  UNSTABLE {r['question'][:40]} :: pass_ratio={r['pass_ratio']}/{args.repeat}")


if __name__ == "__main__":
    main()
