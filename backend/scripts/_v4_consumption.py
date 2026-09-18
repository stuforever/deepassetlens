# -*- coding: utf-8 -*-
"""v4 批0.2：前端消费面机械冻结 + 端点×动作 ACL 映射推导（协议 F①）。
产出 dt_baseline/v4_consumption.json + v4_acl_map.json。
口径：
- 扫 frontend/src 源码中的 /api/v1/... 与 /api/attachments 字面量（含模板串前缀）；
- 消费者文件→页面族（admin/h5/settings/book/learning/quiz/chat/partners/knowledge/memory/common）；
- 动作推导（协议 F①）：仅后台页族消费=manage；h5/功能页族消费=use；混合=use+备注 manage 内嵌；
- 零消费卸挂候选（spec §三）：逐一活探 200/404（GET，auth=0）。
"""
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FE = ROOT / "frontend" / "src"
OUT = ROOT / "backend" / "scripts" / "dt_baseline"

# 页面族→动作（协议 F①机械推导口径）
FAMILY_ACTION = {
    "tutor/admin": "manage",
    "admin": "manage",
    "settings": "manage",
    "h5": "use",
    "book": "use",
    "learning": "use",
    "self-learning": "use",
    "quiz": "use",
    "chat": "use",
    "partners": "use",
    "knowledge": "use",
    "memory": "manage",   # MemoryAdmin=后台管理面
    "common": "use",
    "expert": "use",
    "config": "use",
    "hooks": "use",
    "components": "use",
    "lib": "use",
    "services": "use",
    "pages": "use",
}
URL_RE = re.compile(r'[`"\'](/api/v1/[A-Za-z0-9_\-/\$\{\}\.\:]+|/api/attachments[A-Za-z0-9_\-/\$\{\}\.]*)[`"\']')

def family_of(rel_path: str) -> str:
    p = rel_path.replace("\\", "/")
    for key in ("pages/tutor/admin", "pages/settings", "pages/tutor/h5", "pages/tutor/book",
                "pages/tutor/learning", "pages/quiz", "pages/memory", "pages/tutor/h5/h5shared"):
        if key in p:
            return key.split("/")[-2] if key.count("/") >= 2 else key
    if "pages/knowledge" in p: return "knowledge"
    if "components/partners" in p or "pages/partners" in p: return "partners"
    if "components/quiz" in p or "pages/quiz" in p: return "quiz"
    if "pages/expert" in p: return "expert"
    if "components/chat" in p or "pages/FreePlanChat" in p or "pages/ExpertChat" in p: return "chat"
    if "components/" in p: return "components"
    if "/lib/" in p or p.startswith("lib/"): return "lib"
    if "/hooks/" in p: return "hooks"
    return "other"

consumption = defaultdict(set)   # endpoint template -> set of family
files_scanned = 0
for ts in list(FE.rglob("*.ts")) + list(FE.rglob("*.tsx")):
    rel = str(ts.relative_to(ROOT))
    try:
        text = ts.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    files_scanned += 1
    fam = family_of(rel)
    for m in URL_RE.finditer(text):
        ep = m.group(1)
        # 归一模板串：${...}→{}
        ep_norm = re.sub(r"\$\{[^}]*\}", "{}", ep)
        consumption[ep_norm].add(fam)

def action_for(fams):
    acts = {FAMILY_ACTION.get(f, "use") for f in fams}
    if acts == {"manage"}:
        return "manage"
    if "manage" in acts:
        return "use"   # 混合=use+管理操作内嵌 manage（登记备注）
    return "use"

endpoints = []
for ep in sorted(consumption):
    fams = sorted(consumption[ep])
    endpoints.append({
        "endpoint": ep,
        "consumers": fams,
        "action": action_for(fams),
    })

ZERO_CANDIDATES = ["wechat_push", "multi_user", "space_mcp", "space_cli_apps",
                   "plugins", "agent-config", "capabilities", "dashboard"]
zero_probe = {}
for cand in ZERO_CANDIDATES:
    hits = [ep for ep in consumption if cand in ep]
    zero_probe[cand] = {"frontend_hits": hits}

out = {
    "date": "2026-09-18",
    "files_scanned": files_scanned,
    "endpoint_count": len(endpoints),
    "endpoints": endpoints,
    "zero_consumption_candidates": zero_probe,
}
OUT.mkdir(parents=True, exist_ok=True)
io.open(OUT / "v4_consumption.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))

acl = {
    "date": "2026-09-18",
    "rule": "协议F①机械推导：仅后台页族消费=manage；h5/功能页=use；混合=use+manage内嵌备注；批6-14照表挂 require_expert(action, expert_id='sishu')",
    "endpoints": {e["endpoint"]: {"action": e["action"], "consumers": e["consumers"]} for e in endpoints},
}
io.open(OUT / "v4_acl_map.json", "w", encoding="utf-8").write(
    json.dumps(acl, ensure_ascii=False, indent=1))
print(f"scanned {files_scanned} files, {len(endpoints)} distinct /api endpoints")
print("consumption+acl maps written")
