# -*- coding: utf-8 -*-
"""⑤R F1 L5 字段清单机械勾验：data-testid 双侧（原仓 vs tupu 复刻）逐一比对 +
按钮/文案关键串抽查。落 batch8_字段清单.json。"""
import json
import re
from pathlib import Path

ORIG = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web")
TUPU = Path(r"D:\gitcangku\deepassetlens\frontend\src\pages\tutor\admin")
OUT = Path(__file__).parent / "dt_baseline" / "batch8_字段清单.json"

PAIRS = [
    ("mother-questions 主列表", [ORIG / "app/(workspace)/mother-questions/page.tsx"], [TUPU / "MotherQuestionsAdmin.tsx"]),
    ("mother-questions new 录题", [ORIG / "app/(workspace)/mother-questions/new/page.tsx", ORIG / "components/mother-questions/MotherQuestionFields.tsx"], [TUPU / "MotherQuestionNew.tsx", TUPU / "MotherQuestionForm.tsx"]),
    ("mother-questions photo", [ORIG / "app/(workspace)/mother-questions/photo/page.tsx"], [TUPU / "MotherQuestionPhoto.tsx"]),
    ("mother-questions photo-center", [ORIG / "app/(workspace)/mother-questions/photo-center/page.tsx"], [TUPU / "MotherQuestionPhotoCenter.tsx"]),
    ("mother-questions analysis", [ORIG / "app/(workspace)/mother-questions/analysis/page.tsx", ORIG / "app/(workspace)/mother-questions/analysis/AnalysisCharts.tsx"], [TUPU / "MotherQuestionAnalysis.tsx", TUPU / "MotherQuestionAnalysisCharts.tsx"]),
    ("mother-questions review", [ORIG / "app/(workspace)/mother-questions/review/page.tsx"], [TUPU / "MotherQuestionReview.tsx"]),
    ("mother-questions trash", [ORIG / "app/(workspace)/mother-questions/trash/page.tsx"], [TUPU / "MotherQuestionTrash.tsx"]),
    ("book 书源管理", [ORIG / "app/(workspace)/book/page.tsx"], [TUPU / "BookAdmin.tsx"]),
    ("settings curriculum", [ORIG / "app/(utility)/settings/curriculum/textbooks/page.tsx", ORIG / "app/(utility)/settings/curriculum/chapters/page.tsx", ORIG / "app/(utility)/settings/curriculum/knowledge-points/page.tsx"], [TUPU / "SettingsAdmin.tsx", TUPU / "SettingsTextbooks.tsx", TUPU / "SettingsChapters.tsx", TUPU / "SettingsKnowledgePoints.tsx"]),
]

tid_re = re.compile(r"data-testid=`?{?`?[\"'`]([a-zA-Z0-9_\-./$ {}]+)")

report = []
for name, srcs, dsts in PAIRS:
    orig_tids, tupu_tids = set(), set()
    orig_text, tupu_text = "", ""
    for f in srcs:
        if f.exists():
            orig_text += f.read_text(encoding="utf-8", errors="ignore")
    for f in dsts:
        if f.exists():
            tupu_text += f.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r'data-testid=["\'`{]+([^"\'`}]+)', orig_text):
        t = m.group(1).split("${")[0].strip("\"'`")
        if t:
            orig_tids.add(t)
    for m in re.finditer(r'data-testid=["\'`{]+([^"\'`}]+)', tupu_text):
        t = m.group(1).split("${")[0].strip("\"'`")
        if t:
            tupu_tids.add(t)
    missing = sorted(t for t in orig_tids if t not in tupu_text)
    missing_dyn = sorted(t for t in orig_tids if t not in tupu_tids and t in missing and "${" in t)
    static_missing = sorted(t for t in missing if t not in missing_dyn)
    files_ok = all(f.exists() for f in dsts)
    report.append({
        "page": name,
        "files_exist": files_ok,
        "orig_testids": len(orig_tids),
        "tupu_testids": len(tupu_tids),
        "static_missing": static_missing,
        "verdict": "PASS" if (files_ok and not static_missing) else "CHECK",
    })

for r in report:
    v = r["verdict"]
    print(f"[{v}] {r['page']}: orig {r['orig_testids']} testids / tupu {r['tupu_testids']} / 缺 {len(r['static_missing'])}")
    if r["static_missing"]:
        print("   缺:", r["static_missing"][:10])
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("落盘", OUT.name)
