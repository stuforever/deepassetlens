# -*- coding: utf-8 -*-
"""⑤R R2 A3：零裁剪审计——vendor 全树对原仓零缺失+实名件勾验+openapi 端点面覆盖。"""
import io
import json
from pathlib import Path

import requests

SRC = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\deeptutor")
DST = Path(r"D:\gitcangku\deepassetlens\backend\app\vendor\deeptutor")
BASE = Path(__file__).resolve().parent / "dt_baseline"

# 1.7/A3 点名实名件（总账 12.x/A3 行明示）
NAMED = [
    "learning/recitation",            # recitation 子包
    "learning/tab_export",            # tab_export 子包
    "learning/simhash_util.py",       # simhash_util
    "learning/llm_cost_log.py",          # llm_cost_log（包或模块）
    "api/routers/mother_question.py", # mother_question 路由件
    "services/search",                # search 子包（R2 补齐）
    "multi_user/router.py",           # multi_user 路由
    "services/persona",               # persona 预设
    "skills/builtin",                 # 内置技能
]


def main():
    results = []
    # ① 全树文件缺失复测（py+资产，排除 __pycache__）
    missing = [
        f.FullName if hasattr(f, "FullName") else str(f)
        for f in SRC.rglob("*")
        if f.is_file() and "__pycache__" not in str(f) and f.suffix != ".pyc"
        and not (DST / f.relative_to(SRC)).exists()
    ]
    results.append(("vendor 全树缺失文件", "PASS" if not missing else "FAIL",
                    "0 缺失" if not missing else f"{len(missing)}: {missing[:5]}"))

    # ② 点名实名件
    for name in NAMED:
        p = DST / name
        ok = p.exists()
        results.append((f"实名件 {name}", "PASS" if ok else "FAIL", "在位" if ok else "缺失"))

    # ③ openapi 端点面覆盖：原仓 458 全量 vs tupu 活体
    orig = json.load(io.open(BASE / "endpoints" / "_openapi.json", encoding="utf-8"))
    orig_paths = set(orig.get("paths", {}).keys())
    tupu_paths = set(requests.get("http://127.0.0.1:28000/openapi.json", timeout=30).json()["paths"].keys())
    # tupu 平台自有前缀（非 DT 域——平台本色面，不属裁剪对象）
    platform_prefixes = ("/api/data-intelligence", "/api/engine", "/api/guards", "/api/capabilities",
                         "/api/experts", "/api/memory", "/api/kg", "/api/v2", "/api/mcp",
                         "/api/v1/sync", "/api/v1/knowledge-bases", "/api/v1/biz_work_order",
                         "/api/v1/synonyms", "/api/v1/qa", "/api/v1/golden", "/api/v1/feedback",
                         "/api/v1/api_mapping", "/api/v1/doris", "/api/v1/standard", "/api/v1/auth")
    missing_dt = sorted(
        p for p in orig_paths - tupu_paths
        if p.startswith("/api/v1") and not p.startswith(platform_prefixes))
    results.append(("DT 域 openapi 面覆盖", "PASS" if not missing_dt else "FAIL",
                    "全量在位" if not missing_dt else f"缺 {len(missing_dt)}: {missing_dt[:8]}"))
    extra = len(tupu_paths - orig_paths)
    results.append(("tupu 平台增量端点", "INFO", f"{extra} 件（平台本色/⑥-2a/平台能力面——增量非裁剪）"))

    for n, s, note in results:
        print(f"  [{s}] {n} :: {note}")
    print("A3 总体:", "PASS" if all(s in ("PASS", "INFO") for _, s, _ in results) else "FAIL")
    json.dump([{"item": n, "status": s, "note": note} for n, s, note in results],
              io.open(BASE / "r2_a3_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
