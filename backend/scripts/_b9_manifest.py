# -*- coding: utf-8 -*-
"""批9 F2 manifest：h5 组页面/共享件清单+源行数对账+端点/testid 证据汇总。"""
import json
import subprocess
from pathlib import Path

FRONT = Path(r"D:\gitcangku\deepassetlens\frontend\src\pages\tutor\h5")
ORIG = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web")
BASE = Path(__file__).resolve().parent / "dt_baseline"

PAGES = [  # (复刻件, 源文件相对 web/)
    ("H5Home.tsx", "app/h5/page.tsx"),
    ("H5Chat.tsx", "app/h5/chat/page.tsx"),
    ("H5Learn.tsx", "app/h5/learn/page.tsx"),
    ("H5LearnTextbook.tsx", "app/h5/learn/textbook/page.tsx"),
    ("H5Classroom.tsx", "app/h5/classroom/page.tsx"),
    ("H5Review.tsx", "app/h5/review/page.tsx"),
    ("H5Wrong.tsx", "app/h5/wrong/page.tsx"),
    ("H5WrongBook.tsx", "app/h5/wrongbook/page.tsx"),
    ("H5Paths.tsx", "app/h5/paths/page.tsx"),
    ("H5PathBook.tsx", "app/h5/paths/[bookId]/page.tsx"),
    ("H5Report.tsx", "app/h5/report/page.tsx"),
    ("H5Atlas.tsx", "app/h5/atlas/page.tsx"),
    ("H5BookRead.tsx", "app/h5/book/[bookId]/page.tsx"),
    ("H5Me.tsx", "app/h5/me/page.tsx"),
    ("H5Share.tsx", "app/h5/share/page.tsx"),
]

def lines(p):
    try:
        return len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        return -1

pages = []
for tgt, src in PAGES:
    o, t = lines(ORIG / src), lines(FRONT / tgt)
    pages.append({"target": tgt, "source": src, "orig_lines": o, "tupu_lines": t,
                  "delta_pct": round((t - o) / max(o, 1) * 100, 1)})

shared = sorted(f.name for f in (FRONT / "h5shared").iterdir() if f.is_file())
learn_priv = sorted(f.name for f in (FRONT / "learn").iterdir() if f.is_file())

audit = json.loads((BASE / "batch9_端点核对.json").read_text(encoding="utf-8"))
l5 = json.loads((BASE / "batch9_字段清单.json").read_text(encoding="utf-8"))

routes = [
    "/e/tutor/h5", "/e/tutor/h5/chat", "/e/tutor/h5/learn", "/e/tutor/h5/learn/textbook",
    "/e/tutor/h5/classroom", "/e/tutor/h5/review", "/e/tutor/h5/wrong", "/e/tutor/h5/wrongbook",
    "/e/tutor/h5/paths", "/e/tutor/h5/paths/:bookId", "/e/tutor/h5/report", "/e/tutor/h5/atlas",
    "/e/tutor/h5/book/:bookId", "/e/tutor/h5/me", "/e/tutor/h5/share",
]

manifest = {
    "batch": "批9 F2：h5组→tutor空间15路由",
    "backend_change": {
        "file": "app/vendor/deeptutor/api/tutor_routers.py",
        "change": "sessions 路由补挂载（原仓 main.py L491 原形状，vendor sessions.py sha256 与原仓一致零改码）",
        "verified": "GET /api/v1/sessions?limit=1 → 200（原 30408 同 200）",
        "pytest": "1198 passed + 1 skipped",
    },
    "routes": routes,
    "pages": pages,
    "pages_total_tupu_lines": sum(p["tupu_lines"] for p in pages),
    "pages_total_orig_lines": sum(p["orig_lines"] for p in pages),
    "h5shared_files": shared,
    "h5shared_count": len(shared),
    "learn_private_files": learn_priv,
    "endpoint_audit": {"total_calls": audit["total_distinct_calls"],
                       "covered": len(audit["covered"]), "missing": len(audit["missing"]),
                       "missing_classified": "2 双侧同404容错调用+3 截断伪迹+2 动态派发并集=0 真缺口"},
    "l5_testids": {"orig_total": 80, "covered": len(l5["both"]), "missing": len(l5["orig_only"]),
                   "extras_verified": "36 条全源自 components/chat|quiz|self-learning 桌面原件（recite-* 源 self-learning/ReciteTab.tsx）"},
    "e2e": {"journey": "8/8 PASS（首页→学习→错题录入→错题本→精通之路→报告→我的→分享）",
            "wenshu_regression": "PASS（卡在位+对话面渲染，卡已还原停用）"},
    "screens": {"tupu": "screens_tupu_f2/ 13 屏", "orig_30408": "screens_orig_30408_h5/ 13 屏"},
    "tsc": "exit 0（全仓，tsconfig.typecheck.json）",
}
out = BASE / "batch9_manifest.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"manifest → {out}")
print(f"页面 {len(pages)}：tupu {manifest['pages_total_tupu_lines']} 行 / orig {manifest['pages_total_orig_lines']} 行")
for p in pages:
    print(f"  {p['target']}: {p['orig_lines']}→{p['tupu_lines']} ({p['delta_pct']:+.1f}%)")
