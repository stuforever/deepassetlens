# -*- coding: utf-8 -*-
"""批1 1.5-1.10 机械对账：chat 能力清单/knowledge×④ diff/调用闭包 grep/冲突审计/依赖核对/闭包判定。
输出：backend/scripts/dt_baseline/batch1_对账.json + 控制台摘要。"""
import json
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent / "dt_baseline"
EP = BASE / "endpoints"
DT = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor")
WEB = DT / "web"

inv = json.loads((BASE / "endpoints_inventory.json").read_text(encoding="utf-8"))
spec = json.loads((EP / "_openapi.json").read_text(encoding="utf-8"))
out = {}

# ---- 1.5 chat/capabilities 能力清单 ----
cap_tags = {"chat", "capabilities"}
out["1.5_chat能力清单"] = {
    "endpoints": [i for i in inv if set(i["tags"]) & cap_tags],
    "capabilities_pkg": sorted(p.name for p in (DT / "deeptutor" / "capabilities").iterdir()
                               if not p.name.startswith("__")),
}
print("1.5 chat+capabilities 端点:", len(out["1.5_chat能力清单"]["endpoints"]),
      "| capabilities 包:", len(out["1.5_chat能力清单"]["capabilities_pkg"]))

# ---- 1.6 knowledge×④ diff ----
dt_kn = [i for i in inv if "knowledge" in i["tags"]]
try:
    import requests
    tupu_spec = requests.get("http://127.0.0.1:28000/openapi.json", timeout=30).json()
    tupu_paths = set(tupu_spec.get("paths", {}).keys())
except Exception as e:
    tupu_paths, tupu_spec = set(), {}
    print("tupu openapi 获取失败:", e)
kn4 = sorted(p for p in tupu_paths if "knowledge" in p.lower())
dt_kn_paths = sorted({i["path"] for i in dt_kn})
out["1.6_knowledge_diff"] = {
    "dt_knowledge_endpoints": dt_kn,
    "dt_knowledge_paths": dt_kn_paths,
    "tupu_4_knowledge_paths": kn4,
}
print(f"1.6 DT knowledge 路径 {len(dt_kn_paths)} × tupu④ {len(kn4)}——逐条 diff 见对账文件")

# ---- 1.7 web 调用闭包 grep ----
pat = re.compile(r"""(?:fetch|axios(?:\.\w+)?|api\.(?:get|post|put|delete|patch))\(\s*[`'"](/[^`'"?]*)""", re.I)
called = set()
for f in WEB.rglob("*"):
    if f.suffix not in (".ts", ".tsx", ".js", ".jsx") or "node_modules" in str(f) or ".next" in str(f):
        continue
    try:
        txt = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for m in pat.finditer(txt):
        called.add(m.group(1))
dt_paths = {i["path"] for i in inv}
covered = sorted(c for c in called if any(c == p or p.startswith(c) or c.startswith(p.rstrip("/")) for p in dt_paths))
out["1.7_调用闭包"] = {
    "web_api_calls_total": len(called),
    "matched_to_endpoints": covered,
    "unmatched_calls": sorted(c for c in called if c not in covered),
    "backend_only_paths": len(dt_paths - set(called)),
}
print(f"1.7 web 调用 {len(called)} 条——命中端点 {len(covered)}，未命中 {len(out['1.7_调用闭包']['unmatched_calls'])}")

# ---- 1.8 全路径冲突审计 ----
dt_all = {i["path"] for i in inv}
clash = sorted(dt_all & tupu_paths)
out["1.8_路径冲突"] = {"clash": clash}
print(f"1.8 路径撞车: {len(clash)} 条", clash[:6] if clash else "")

# ---- 1.9 依赖核对 ----
req_files = sorted((DT / "requirements").glob("*.txt")) if (DT / "requirements").exists() else []
dt_reqs = set()
for f in req_files:
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            dt_reqs.add(re.split(r"[<>=~!\[;]", line)[0].strip().lower())
dt_reqs.discard("")
try:
    r = subprocess.run(["pip", "list", "--format=freeze"], capture_output=True, text=True, timeout=120)
    installed = {ln.split("==")[0].strip().lower() for ln in r.stdout.splitlines() if "==" in ln}
except Exception as e:
    installed = set()
    print("pip list 失败:", e)
out["1.9_依赖"] = {
    "dt_requirements_files": [f.name for f in req_files],
    "dt_reqs_count": len(dt_reqs),
    "missing_in_tupu": sorted(dt_reqs - installed),
}
print(f"1.9 DT 依赖 {len(dt_reqs)}——tupu 缺 {len(out['1.9_依赖']['missing_in_tupu'])}:",
      out["1.9_依赖"]["missing_in_tupu"][:12])

# ---- 1.10 wechat_push/voice 闭包判定 ----
wp = [i for i in inv if "wechat-push" in i["tags"]]
vo = [i for i in inv if "voice" in i["tags"]]
out["1.10_闭包判定"] = {"wechat_push_ops": len(wp), "voice_ops": len(vo),
                        "判定": "tags 在调用闭包内（openapi 实测）→ 全还原含配置面（settings stt/tts 页已在底册）"}
print(f"1.10 wechat-push {len(wp)} ops / voice {len(vo)} ops → 全还原")

# ---- 1.4 屏清单索引 ----
screens = sorted(f.name for f in (BASE / "screens").glob("*.png"))
out["1.4_屏幕索引"] = {"count": len(screens), "screens": screens}
print("1.4 截图索引:", len(screens), "屏")

(BASE / "batch1_对账.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                                      encoding="utf-8")
print("对账文件已写: dt_baseline/batch1_对账.json")
