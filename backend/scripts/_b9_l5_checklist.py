# -*- coding: utf-8 -*-
"""批9 F2 L5：data-testid 双侧勾验（原仓 h5 组 vs tupu 复刻件）。"""
import re
from pathlib import Path

ORIG = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web\app\h5")
ORIG_COMP = Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web\components\h5")
TUPU = Path(r"D:\gitcangku\deepassetlens\frontend\src\pages\tutor\h5")

def testids(root):
    out = set()
    for f in list(root.rglob("*.tsx")) + list(root.rglob("*.ts")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'data-testid=["\'{]?([^"\'})]+)', text):
            seg = m.group(1).strip()
            # 模板串取字面头部（`mq-card-${m.id}` → mq-card-）
            seg = seg.split("${")[0].rstrip("`\"'")
            if seg:
                out.add(seg)
    return out

orig = testids(ORIG) | testids(ORIG_COMP)
tupu = testids(TUPU)

report = {"orig_only": sorted(orig - tupu), "tupu_only": sorted(tupu - orig), "both": sorted(orig & tupu)}
out = Path(__file__).resolve().parent / "dt_baseline" / "batch9_字段清单.json"
import json
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"原仓 testid {len(orig)} | tupu {len(tupu)} | 共有 {len(report['both'])}")
print("原仓独有（缺失候选）:", report["orig_only"])
print("tupu 独有（超出=需说明）:", report["tupu_only"])
